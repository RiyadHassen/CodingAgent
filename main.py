import os
from dotenv import load_dotenv
from google import genai
import sys
import argparse
from google.genai import types
import subprocess



def main():
    print("Hello from agenticai!")

def run_bash(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(description="AgenticAI - A framework for building AI agents")
    #argument_parser.add_argument("--test", action="store_true", help="Run a test query to the Gemini API")
    argument_parser.add_argument("--model-name", default="gemini-2.0-flash-001")
    argument_parser.add_argument("--run_model",  action="store_false", help="Run the model with a prompt")
    argument_parser.add_argument("--run_tool", action="store_false", help="Run a tool function")
    argument_parser.add_argument("--prompt", help="prompt to send to the model")
    argument_parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    load_dotenv()
    args = argument_parser.parse_args()
    model_name = args.model_name
    run_model = args.run_model
    run_tool = args.run_tool
    verbose = args.verbose
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

    system_prompt = """ 
     When a user asks a question or makes a request to build model make a function call plan. You can perform the following opreation
     - list files and directories 
     - read file contents 
     - execute python files 
     - write or overwrite files
      
    Finally write a bash script to train the  model with provided dataset. In our case a simple txt file to train the 
        NLP model. 
    """

    tool_access_prompt = """
    You have acess to the following tools and functions
    """


    user_prompt = """You're an expert NLP Machine learning engineer, You are going to assist the ML researcher write and build model, you build your models using PyTorch, 
     you write  a test to verify the model output is correct. """



    if run_model:

        response = client.models.generate_content(
            model = "gemini-2.0-flash-001",
            contents = message, 
            config = types.GenerateContentConfig(system_instruction = system_prompt)
        )

    
    print(run_bash("python main.py"))


    if verbose:
        print("Verbose mode enabled")
        print(response)
        print(response.text)
        print(response.usage_metadata.prompt_token_count)
        print(response.usage_metadata.candidates_token_count)




