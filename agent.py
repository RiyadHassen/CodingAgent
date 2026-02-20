import os
import sys
import argparse
import subprocess
import shutil
import json
import re
import warnings
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Suppress the Gemini SDK warning that fires when a response contains mixed
# function_call + text parts and you inspect any property of the response.
warnings.filterwarnings("ignore", message=".*non-text parts.*")

from functions.get_file_content import get_file_content, schema_get_file_content
from functions.write_file import write_file, schema_write_file
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.run_python_file import run_python_file, schema_run_python_file


# ─────────────────────────── Configuration ────────────────────────────────────

WORKING_DIRECTORY = os.path.abspath(".")
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_ITERATIONS = 30

SYSTEM_PROMPT = """
You are an expert software engineer and coding assistant. Your job is to help
users build complete, working software projects iteratively using the tools
available to you.

Capabilities:
  - List files and directories
  - Read file contents
  - Write or overwrite files
  - Execute Python files with optional arguments
  - Run shell commands (bash)
  - Search for text patterns inside files (grep)
  - Delete files or directories
  - Create directories

CRITICAL RULES — follow these exactly:
  1. Start by Creating a Project Folder and put every file in that folder 
  2. Do NOT describe what you are about to do in text before doing it with tools use the[Thinking...].
  3. Only output plain text when the ENTIRE task is fully complete and verified.
  4. After writing code always run it to verify it works; fix any errors found.
  5. Write a test to verify the process
  6. All paths must be relative to the working directory (injected automatically).
  7. Iterate: write → run → observe → fix until the task is done.
  8. Stop execution if you are done early 
  7. When the task is 100% complete, output a short summary of what was built .
  8. Write a readme for the project and steps for executing the project
"""


# ─────────────────────────── Extra Tool Functions ─────────────────────────────

def run_bash_command(command: str, working_directory: str, timeout: int = 30) -> str:
    """Run an arbitrary shell command and return combined stdout + stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=working_directory,
            timeout=timeout,
        )
        output = result.stdout
        if result.stderr:
            output += "\nSTDERR:\n" + result.stderr
        if result.returncode != 0:
            output += f"\n[Exit code: {result.returncode}]"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[Error] Command timed out after {timeout} seconds."
    except Exception as e:
        return f"[Error] {e}"


def grep_in_files(pattern: str, path: str, working_directory: str,
                  recursive: bool = True, case_sensitive: bool = True) -> str:
    """Search for a regex pattern in files under `path`."""
    try:
        flags = "" if case_sensitive else " -i"
        r_flag = " -r" if recursive else ""
        full_path = os.path.join(working_directory, path)
        cmd = f"grep{r_flag}{flags} -n --include='*.py' --include='*.txt' --include='*.md' --include='*.sh' -E {json.dumps(pattern)} {json.dumps(full_path)}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout or "(no matches found)"
    except Exception as e:
        return f"[Error] {e}"


def delete_file_or_directory(path: str, working_directory: str) -> str:
    """Delete a file or directory (recursively)."""
    try:
        full_path = os.path.join(working_directory, path)
        if not os.path.exists(full_path):
            return f"[Error] Path does not exist: {path}"
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
            return f"Deleted directory: {path}"
        else:
            os.remove(full_path)
            return f"Deleted file: {path}"
    except Exception as e:
        return f"[Error] {e}"


def create_directory(path: str, working_directory: str) -> str:
    """Create a directory (including all intermediate directories)."""
    try:
        full_path = os.path.join(working_directory, path)
        os.makedirs(full_path, exist_ok=True)
        return f"Created directory: {path}"
    except Exception as e:
        return f"[Error] {e}"


def install_package(package: str, working_directory: str) -> str:
    """Install a Python package via pip."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", package],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    return output or "(no output)"

schema_run_bash_command = types.FunctionDeclaration(
    name="run_bash_command",
    description=(
        "Run an arbitrary shell/bash command in the working directory. "
        "Use for installing packages, running tests, git commands, compiling, etc."
    ),
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "command": types.Schema(type=types.Type.STRING, description="The shell command to execute."),
            "timeout": types.Schema(type=types.Type.INTEGER, description="Timeout in seconds (default 30)."),
        },
        required=["command"],
    ),
)

schema_grep_in_files = types.FunctionDeclaration(
    name="grep_in_files",
    description="Search for a regex pattern inside files. Useful for finding usages, imports, or errors.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "pattern": types.Schema(type=types.Type.STRING, description="Regex pattern to search for."),
            "path": types.Schema(type=types.Type.STRING, description="Directory or file path to search in."),
            "recursive": types.Schema(type=types.Type.BOOLEAN, description="Search recursively (default true)."),
            "case_sensitive": types.Schema(type=types.Type.BOOLEAN, description="Case-sensitive search (default true)."),
        },
        required=["pattern", "path"],
    ),
)

schema_delete_file_or_directory = types.FunctionDeclaration(
    name="delete_file_or_directory",
    description="Delete a file or directory (recursively for directories). Use with caution.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING, description="Relative path to the file or directory to delete."),
        },
        required=["path"],
    ),
)

schema_create_directory = types.FunctionDeclaration(
    name="create_directory",
    description="Create a new directory (and any necessary parent directories).",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(type=types.Type.STRING, description="Relative path of the directory to create."),
        },
        required=["path"],
    ),
)

schema_install_package = types.FunctionDeclaration(
    name="install_package",
    description="Install a Python package using pip.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "package": types.Schema(type=types.Type.STRING, description="Package name (e.g. 'torch', 'numpy==1.25')."),
        },
        required=["package"],
    ),
)


# ─────────────────────────── Function Dispatcher ──────────────────────────────

FUNCTION_MAP = {
    "get_files_info":          get_files_info,
    "get_file_content":        get_file_content,
    "run_python_file":         run_python_file,
    "write_file":              write_file,
    "run_bash_command":        run_bash_command,
    "grep_in_files":           grep_in_files,
    "delete_file_or_directory": delete_file_or_directory,
    "create_directory":        create_directory,
    "install_package":         install_package,
}

AVAILABLE_TOOLS = types.Tool(
    function_declarations=[
        schema_get_file_content,
        schema_get_files_info,
        schema_write_file,
        schema_run_python_file,
        schema_run_bash_command,
        schema_grep_in_files,
        schema_delete_file_or_directory,
        schema_create_directory,
        schema_install_package,
    ]
)


def call_function(func_call_part, verbose: bool = False) -> types.Content:
    """Dispatch a function call from the model and return a tool-role Content."""
    func_name = func_call_part.name
    if verbose:
        print(f"  ↳ [{func_name}] args={dict(func_call_part.args)}")
    else:
        print(f"  ↳ calling: {func_name}()")

    if func_name not in FUNCTION_MAP:
        response = {"error": f"Function '{func_name}' is not implemented."}
    else:
        args = dict(func_call_part.args)
        args["working_directory"] = WORKING_DIRECTORY
        try:
            result = FUNCTION_MAP[func_name](**args)
            response = {"result": result}
        except Exception as e:
            response = {"error": str(e)}

    if verbose:
        preview = str(response)[:300]
        print(f"     → {preview}{'...' if len(str(response)) > 300 else ''}")

    return types.Content(
        role="tool",
        parts=[
            types.Part.from_function_response(name=func_name, response=response)
        ],
    )


# ─────────────────────────── Agent Loop ───────────────────────────────────────

def run_agent(client: genai.Client, user_prompt: str, model: str, verbose: bool,
              max_iterations: int = MAX_ITERATIONS) -> None:
    """Main agentic loop: sends messages, handles tool calls, repeats until done."""

    messages = [
        types.Content(role="user", parts=[types.Part(text=user_prompt)])
    ]

    config = types.GenerateContentConfig(
        tools=[AVAILABLE_TOOLS],
        system_instruction=SYSTEM_PROMPT,
    )

    print(f"\n{'─'*60}")
    print(f"Agent starting  |  model: {model}  |  max_iter: {max_iterations}")
    print(f"{'─'*60}\n")

    for iteration in range(1, max_iterations + 1):
        print(f"[Iteration {iteration}/{max_iterations}]")

        try:
            response = client.models.generate_content(
                model=model,
                contents=messages,
                config=config,
            )
        except Exception as e:
            print(f"[API Error] {e}")
            break

        if verbose:
            meta = response.usage_metadata
            print(f"  tokens — prompt: {meta.prompt_token_count}, response: {meta.candidates_token_count}")

        # Parse parts directly from the candidate to avoid the SDK
        # "non-text parts in the response" warning that fires when you
        # access response.text on a mixed function_call + text response.
        candidate = response.candidates[0]
        messages.append(candidate.content)

        # Separate parts by type
        function_call_parts = [
            p for p in candidate.content.parts if p.function_call is not None
        ]
        text_parts = [
            p.text for p in candidate.content.parts
            if p.text is not None and p.function_call is None
        ]

        # ── Tool calls take priority ──────────────────────────────────────────
        # The model sometimes emits a text "plan" in the same turn as tool
        # calls. We ALWAYS process function calls when present — any
        # accompanying text is shown as live commentary, NOT a final answer.
        if function_call_parts:
            if text_parts:
                blurb = "".join(text_parts).strip()
                if blurb:
                    print(f"  [thinking] {blurb[:200]}{'...' if len(blurb) > 200 else ''}")

            tool_result_parts = []
            for part in function_call_parts:
                result_content = call_function(part.function_call, verbose)
                tool_result_parts.append(result_content.parts[0])

            messages.append(types.Content(role="user", parts=tool_result_parts))

        # ── Pure text only (zero function calls) → task is complete ──────────
        elif text_parts:
            final_text = "".join(text_parts).strip()
            print(f"\n{'─'*60}")
            print("Agent complete:")
            print(f"{'─'*60}")
            print(final_text)
            break

        # ── Neither → unexpected empty response ──────────────────────────────
        else:
            print("[Warning] Model returned no text and no function calls. Stopping.")
            break
    else:
        print(f"\n[Warning] Reached maximum iterations ({max_iterations}). Task may be incomplete.")


# ─────────────────────────── Interactive REPL ─────────────────────────────────

def run_interactive(client: genai.Client, model: str, verbose: bool) -> None:
    """A simple multi-turn REPL so the user can keep refining the project."""
    print("\n Coding Agent — Interactive Mode")
    print("Type your request and press Enter. Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        run_agent(client, user_input, model, verbose)
        print()

def parse_args():
    parser = argparse.ArgumentParser(
        description="Coding Agent — iteratively builds projects using Gemini + tools"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name")
    parser.add_argument("--prompt", "-p", help="One-shot prompt; omit for interactive mode")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show token counts and full tool responses")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS,
                        help=f"Max agentic loop iterations (default {MAX_ITERATIONS})")
    return parser.parse_args()


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("[Error] GEMINI_API_KEY not set. Add it to your .env file or environment.")

    client = genai.Client(api_key=api_key)

    if args.prompt:
        # One-shot mode
        run_agent(client, args.prompt, args.model, args.verbose, args.max_iterations)
    else:
        # Interactive REPL
        run_interactive(client, args.model, args.verbose)