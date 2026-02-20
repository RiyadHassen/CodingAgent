import os
from dotenv import load_dotenv
from google import genai
import sys
import argparse
from google.genai import types
import subprocess

from functions.get_file_content import get_file_content, schema_get_file_content
from functions.write_file import write_file, schema_write_file
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.run_python_file import run_python_file, schema_run_python_file


WORKING_DIRECTORY = os.path.dirname(os.path.abspath('./'))

def main():
    print("Hello from agenticai!")

def run_bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def call_function(func_call_part, verbose =False):
    if verbose:
        print(f"Calling function: {func_call_part.name}({func_call_part.args})")
    else:
        print(f" calling function : {func_call_part.name}")
    function_map = {
        "get_files_info": get_files_info,
        "get_file_content": get_file_content,
        "run_python_file": run_python_file,
        "write_file": write_file,
    }
    if func_call_part.name not in function_map:
        return types.Content(
            role = "tool", 
            parts = [
                types.Part.from_function_response(
                    name = func_call_part.name,
                    response = {"error": f"Function {func_call_part.name} is not implemented."}
                )
            ]
        )
    args = dict(func_call_part.args)
    args["working_directory"] = WORKING_DIRECTORY
    function_result = function_map[func_call_part.name](**args)
    return types.Content(
        role = "tool",
        parts = [
            types.Part.from_function_response(
                name = func_call_part.name,
                response = {"result": function_result}
            )
        ]
    )

def generate_content_loop(client, messages, verbose, max_iterations=20):
    for iteration in range(max_iterations):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=messages,
                config=types.GenerateContentConfig(
                    tools=[available_functions], system_instruction=system_prompt
                ),
            )
            if verbose:
                print("Prompt tokens:", response.usage_metadata.prompt_token_count)
                print("Response tokens:", response.usage_metadata.candidates_token_count)

            # Add model response to conversation
            for candidate in response.candidates:
                messages.append(candidate.content)

            # Check if we have a final text response
            if response.text:
                print("Final response:")
                print(response.text)
                break

            # Handle function calls
            if response.function_calls:
                function_responses = []
                for function_call_part in response.function_calls:
                    function_call_result = call_function(function_call_part, verbose)
                    if (
                        not function_call_result.parts
                        or not function_call_result.parts[0].function_response
                    ):
                        raise Exception("empty function call result")
                    if verbose:
                        print(f"-> {function_call_result.parts[0].function_response.response}")
                    function_responses.append(function_call_result.parts[0])
                if function_responses:
                    messages.append(types.Content(role="user", parts=function_responses))
                else:
                    raise Exception("no function responses generated, exiting.")
        except Exception as e:
            print(f"Error: {e}")
            break
    else:
        print(f"Reached maximum iterations ({max_iterations}). Agent may not have completed the task.")  

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="AgenticAI - A framework for building AI agents")
    #argument_parser.add_argument("--test", action="store_true", help="Run a test query to the Gemini API")
    argument_parser.add_argument("--model-name", default="gemini-2.0-flash-001")
    argument_parser.add_argument("--run_model",  action="store_false", help="Run the model with a prompt")
    argument_parser.add_argument("--run_tool", action="store_false", help="Run a tool function")
    argument_parser.add_argument("--prompt", help="prompt to send to the model")
    argument_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    argument_parser.add_argument("--normal_prompt", action="store_false", help="Use a normal prompt without tool access or system instructions" )
    load_dotenv()
    args = argument_parser.parse_args()
    model_name = args.model_name
    run_model = args.run_model
    run_tool = args.run_tool
    verbose = args.verbose
    normal_prompt = args.normal_prompt
    api_key = os.environ.get("GEMINI_API_KEY")
    client = genai.Client(api_key = api_key)
    #response = client.models.generate_content(model="gemini-2.0-flash-001", contents="What is the capital of France?")
    #print(response.text)
    #print(response)
    #print(response.usage_metadata.prompt_token_count)
    #print(response.usage_metadata.candidates_token_count)
    #main()
    # prompt = sys.argv[1] if len(sys.argv) > 1 else sys.exit(1)
    # print(prompt)
    # verbose = sys.argv[2]

    
    #keeping track of the conversation history
    conversation_history = []
    #each mesage in the conversation has a role in the contex of chat gpt  "user", "model"

    # use the types.Content to structure the conversation history
    user_prompt  = args.prompt if args.prompt else "Write a PyTorch model to classify text data, and write a bash script to train the model with a provided dataset in a txt file."
    message = [
        types.Content(role = "user", parts = [types.Part(text = user_prompt)])
    ]
    function_call_result = call_function(types.Part.from_function_call(name="get_files_info", args={"directory": "."}), verbose=verbose)
    try:
        print(f"-> {function_call_result.parts[0].function_response.response}")
    except Exception as e:
        print(f"Error parsing function response: {e}")
    system_prompt = """ 
    When a user asks a question or makes a request to build model make a function call plan. You can perform the following opreation
        - List files and directories
        - Read file contents
        - Execute Python files with optional arguments
        - Write or overwrite files
    All paths you provide should be relative to the working directory. You do not need to specify the working directory in your function calls as it is automatically injected for security reasons.
    """

    tool_access_prompt = """
    You have acess to the following tools and functions
    """

    user_prompt = """
    You're an expert NLP Machine learning engineer, You are going to assist the ML researcher write and build model, you build your models using PyTorch, 
     you write  a test to verify the model output is correct.
    """

    if normal_prompt:
        response = client.models.generate_content(
            model = "gemini-2.0-flash-001",
            contents = message, 
            config = types.GenerateContentConfig(system_instruction = system_prompt)
        )

    available_functions = types.Tool(
        function_declarations = [
            schema_get_file_content, 
            schema_get_files_info,
            schema_write_file,
            schema_run_python_file, 
        ]
    )
    config = types.GenerateContentConfig(
        tools=[available_functions],
        system_instruction = system_prompt
    )

    client = genai.Client(api_key = api_key)

    message = genai.types.Content(
        role= "user",
        parts=[genai.types.Part(text = user_prompt)]
    )

    generate_content_loop(client, [message], verbose)

    

    if verbose:
        print("Verbose mode enabled")
        print(response)
        print(response.text)
        print(response.usage_metadata.prompt_token_count)
        print(response.usage_metadata.candidates_token_count)

