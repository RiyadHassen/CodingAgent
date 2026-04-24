import os
import sys
import time
import argparse
import subprocess
import shutil
import json
import warnings
from dotenv import load_dotenv
from google import genai
from google.genai import types

warnings.filterwarnings("ignore", message=".*non-text parts.*")

from functions.get_file_content import get_file_content, schema_get_file_content
from functions.write_file import write_file, schema_write_file
from functions.get_files_info import get_files_info, schema_get_files_info
from functions.run_python_file import run_python_file, schema_run_python_file

class C:
    _tty = sys.stdout.isatty()
    @staticmethod
    def _w(code, text): return f"{code}{text}\033[0m" if C._tty else text
    bold    = staticmethod(lambda t: C._w("\033[1m",    t))
    dim     = staticmethod(lambda t: C._w("\033[2m",    t))
    green   = staticmethod(lambda t: C._w("\033[32m",   t))
    cyan    = staticmethod(lambda t: C._w("\033[36m",   t))
    yellow  = staticmethod(lambda t: C._w("\033[33m",   t))
    blue    = staticmethod(lambda t: C._w("\033[34m",   t))
    magenta = staticmethod(lambda t: C._w("\033[35m",   t))
    red     = staticmethod(lambda t: C._w("\033[31m",   t))
    grey    = staticmethod(lambda t: C._w("\033[90m",   t))
    b_green = staticmethod(lambda t: C._w("\033[1;32m", t))
    b_cyan  = staticmethod(lambda t: C._w("\033[1;36m", t))
    b_blue  = staticmethod(lambda t: C._w("\033[1;34m", t))

TOOL_ICONS = {
    "get_files_info":           "📂",
    "get_file_content":         "📄",
    "write_file":               "✏️ ",
    "run_python_file":          "🐍",
    "run_bash_command":         "⚡",
    "grep_in_files":            "🔍",
    "delete_file_or_directory": "🗑️ ",
    "create_directory":         "📁",
    "install_package":          "📦",
}

WIDTH = 64
WORKING_DIRECTORY = os.path.abspath(".")
ROOT_DIRECTORY    = WORKING_DIRECTORY  # sandbox ceiling — agent cannot escape above this
DEFAULT_MODEL     = "gemini-2.5-pro"
MAX_ITERATIONS    = 30

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

CRITICAL RULES:
  1. Start by Creating a Project Folder and put every file in that folder  
   After creating a project folder, IMMEDIATELY call change_directory to
     switch into it before writing any files or running any commands

  2. NEVER write a plan or explanation before acting. Start EVERY response with
     a tool call. Think, then immediately call the tool.
  3. Do NOT describe what you are about to do before doing it with tools.
  4. Only output plain text when the ENTIRE task is fully complete and verified.
  5. After writing code, always run it to verify it works; fix any errors found.
  6. All paths must be relative to the working directory (injected automatically).
  7. Iterate: write -> run -> observe -> fix until the task is done.
  8 .Finally use Write README for the project.
"""


def run_bash_command(command: str, working_directory: str, timeout: int = 30) -> str:
    try:
        r = subprocess.run(command, shell=True, capture_output=True, text=True,
                           cwd=working_directory, timeout=timeout)
        out = r.stdout
        if r.stderr:   out += "\nSTDERR:\n" + r.stderr
        if r.returncode != 0: out += f"\n[Exit code: {r.returncode}]"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"[Error] Timed out after {timeout}s."
    except Exception as e:
        return f"[Error] {e}"

def grep_in_files(pattern: str, path: str, working_directory: str,
                  recursive: bool = True, case_sensitive: bool = True) -> str:
    try:
        flags  = "" if case_sensitive else " -i"
        r_flag = " -r" if recursive else ""
        exts   = "--include='*.py' --include='*.txt' --include='*.md' --include='*.sh'"
        full   = os.path.join(working_directory, path)
        cmd    = f"grep{r_flag}{flags} -n {exts} -E {json.dumps(pattern)} {json.dumps(full)}"
        r      = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout or "(no matches found)"
    except Exception as e:
        return f"[Error] {e}"

def delete_file_or_directory(path: str, working_directory: str) -> str:
    try:
        full = os.path.join(working_directory, path)
        if not os.path.exists(full): return f"[Error] Not found: {path}"
        shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)
        return f"Deleted: {path}"
    except Exception as e:
        return f"[Error] {e}"

def create_directory(path: str, working_directory: str) -> str:
    try:
        os.makedirs(os.path.join(working_directory, path), exist_ok=True)
        return f"Created: {path}"
    except Exception as e:
        return f"[Error] {e}"
def change_directory(path: str, working_directory: str) -> str:
    global WORKING_DIRECTORY
    candidate = path if os.path.isabs(path) else os.path.join(working_directory, path)
    candidate = os.path.normpath(candidate)
    # Prevent escaping above the original root directory
    if not candidate.startswith(ROOT_DIRECTORY):
        return f"[Error] Cannot navigate outside the workspace root: {ROOT_DIRECTORY}"
    if not os.path.isdir(candidate):
        return f"[Error] Not a directory: {candidate}"
    WORKING_DIRECTORY = candidate
    return f"Working directory changed to: {WORKING_DIRECTORY}"



def install_package(package: str, working_directory: str) -> str:
    r = subprocess.run([sys.executable, "-m", "pip", "install", package],
                       capture_output=True, text=True)
    return (r.stdout + r.stderr) or "(no output)"


schema_run_bash_command = types.FunctionDeclaration(
    name="run_bash_command",
    description="Run an arbitrary shell command in the working directory.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "command": types.Schema(type=types.Type.STRING, description="Shell command."),
        "timeout": types.Schema(type=types.Type.INTEGER, description="Timeout in seconds."),
    }, required=["command"]),
)
schema_grep_in_files = types.FunctionDeclaration(
    name="grep_in_files",
    description="Search for a regex pattern inside files.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "pattern":        types.Schema(type=types.Type.STRING,  description="Regex pattern."),
        "path":           types.Schema(type=types.Type.STRING,  description="Directory or file."),
        "recursive":      types.Schema(type=types.Type.BOOLEAN, description="Recurse (default true)."),
        "case_sensitive": types.Schema(type=types.Type.BOOLEAN, description="Case-sensitive (default true)."),
    }, required=["pattern", "path"]),
)
schema_delete_file_or_directory = types.FunctionDeclaration(
    name="delete_file_or_directory",
    description="Delete a file or directory recursively.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "path": types.Schema(type=types.Type.STRING, description="Relative path to delete."),
    }, required=["path"]),
)
schema_create_directory = types.FunctionDeclaration(
    name="create_directory",
    description="Create a directory including all parents.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "path": types.Schema(type=types.Type.STRING, description="Relative path to create."),
    }, required=["path"]),
)
schema_install_package = types.FunctionDeclaration(
    name="install_package",
    description="Install a Python package via pip.",
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "package": types.Schema(type=types.Type.STRING, description="Package name, e.g. 'fastapi'."),
    }, required=["package"]),
)

schema_change_directory = types.FunctionDeclaration(
    name="change_directory",
    description=(
        "Change the agent working directory into a subdirectory. "
        "Call this immediately after creating a project folder so all "
        "subsequent file and shell operations run inside it."
    ),
    parameters=types.Schema(type=types.Type.OBJECT, properties={
        "path": types.Schema(type=types.Type.STRING,
                             description="Relative or absolute path to switch into."),
    }, required=["path"]),
)


FUNCTION_MAP = {
    "get_files_info":           get_files_info,
    "get_file_content":         get_file_content,
    "run_python_file":          run_python_file,
    "write_file":               write_file,
    "run_bash_command":         run_bash_command,
    "grep_in_files":            grep_in_files,
    "delete_file_or_directory": delete_file_or_directory,
    "create_directory":         create_directory,
    "install_package":          install_package,
    "change_directory":         change_directory
}

AVAILABLE_TOOLS = types.Tool(function_declarations=[
    schema_get_file_content, schema_get_files_info, schema_write_file,
    schema_run_python_file, schema_run_bash_command, schema_grep_in_files,
    schema_delete_file_or_directory, schema_create_directory, schema_install_package,
    schema_change_directory
])


def _wrap(text: str, indent: int = 4) -> str:
    """Word-wrap text to WIDTH, indented by `indent` spaces."""
    pad   = " " * indent
    words = text.split()
    line, lines = "", []
    for w in words:
        if len(line) + len(w) + 1 > WIDTH - indent:
            if line: lines.append(pad + line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line: lines.append(pad + line)
    return "\n".join(lines)


def call_function(func_call, verbose: bool = False) -> types.Content:
    """
    Execute a single tool call requested by the model.
    """
    name = func_call.name
    args = dict(func_call.args)
    icon = TOOL_ICONS.get(name, "🔧")

    # Key arg preview (first value, truncated)
    preview = ""
    if args:
        first_val = str(next(iter(args.values())))
        preview = first_val[:52] + ("…" if len(first_val) > 52 else "")

    print(f"  {icon}  {C.b_cyan(name)}  {C.grey(repr(preview))}" if not verbose
          else f"  {icon}  {C.b_cyan(name)}")
    if verbose:
        for k, v in args.items():
            v_str = str(v)
            if len(v_str) > 80: v_str = v_str[:77] + "…"
            print(f"       {C.grey(k + ':')} {C.cyan(v_str)}")

    t0 = time.monotonic()
    if name not in FUNCTION_MAP:
        result  = f"[Error] Unknown tool: {name}"
        success = False
    else:
        try:
            result  = FUNCTION_MAP[name](**{**args, "working_directory": WORKING_DIRECTORY})
            success = not str(result).startswith("[Error]")
        except Exception as e:
            result  = f"[Error] {e}"
            success = False

    elapsed     = time.monotonic() - t0
    status      = C.green("✓") if success else C.red("✗")
    elapsed_str = C.grey(f"{elapsed:.2f}s")

    if verbose:
        out = str(result)
        if len(out) > 500: out = out[:497] + "…"
        print(f"     {status} {elapsed_str}")
        for ln in out.splitlines()[:20]:
            print(C.grey(f"       {ln}"))
        if len(str(result).splitlines()) > 20:
            print(C.grey("       … (truncated)"))
    else:
        first_line = str(result).splitlines()[0] if result else "(no output)"
        if len(first_line) > 72: first_line = first_line[:69] + "…"
        print(f"     {status} {C.grey(first_line)}  {elapsed_str}")

    return types.Content(role="tool", parts=[
        types.Part.from_function_response(name=name, response={"result": result})
    ])


def run_agent(client, user_prompt: str, model: str, verbose: bool,
              max_iterations: int = MAX_ITERATIONS) -> None:
    messages = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]
    config   = types.GenerateContentConfig(
        tools=[AVAILABLE_TOOLS],
        system_instruction=SYSTEM_PROMPT,
        candidate_count=1,  # always 1; we use candidates[0] deterministically
    )
    print()
    print(C.grey("─" * WIDTH))
    print(f"  {C.b_blue('◆ Coding Agent')}  {C.grey(model)}")
    print(C.grey("─" * WIDTH))
    task_preview = user_prompt if len(user_prompt) <= WIDTH - 10 else user_prompt[:WIDTH - 13] + "…"
    print(f"  {C.bold('Task')}  {task_preview}")
    print(C.grey("─" * WIDTH))
    print()

    start = time.monotonic()

    for iteration in range(1, max_iterations + 1):
        step_label = C.grey(f"  step {iteration}")
        divider    = C.grey(" ─" * ((WIDTH - 10) // 2))
        print(f"{step_label}{divider}")

        try:
            response = client.models.generate_content(
                model=model, contents=messages, config=config,
            )
        except Exception as e:
            print(f"\n  {C.red('✗ API Error:')} {e}\n")
            break

        if verbose:
            m = response.usage_metadata
            print(C.grey(f" ↳ {m.prompt_token_count} prompt tokens / {m.candidates_token_count} response tokens"))

        # We always use candidates[0] — see call_function docstring for rationale.
        candidate = response.candidates[0]
        messages.append(candidate.content)

        function_call_parts = [p for p in candidate.content.parts if p.function_call is not None]
        text_parts          = [p.text for p in candidate.content.parts
                               if p.text is not None and p.function_call is None]

        # Text alongside a tool call = model reasoning, shown as "thinking".
        # We NEVER treat this as the final answer — only tool-free text is final.
        if function_call_parts:
            if text_parts:
                blurb = " ".join(text_parts).strip()
                if blurb:
                    print(f"  {C.magenta('thinking')}")
                    print(_wrap(C.grey(blurb), indent=4))
                    print()

            tool_results = []
            for part in function_call_parts:
                rc = call_function(part.function_call, verbose)
                tool_results.append(rc.parts[0])
            print()
            messages.append(types.Content(role="user", parts=tool_results))

        elif text_parts:
            elapsed = time.monotonic() - start
            summary = "\n".join(text_parts).strip()

            print()
            print(C.grey("─" * WIDTH))
            print(f"  {C.b_green('✓ Complete')}  {C.grey(f'{elapsed:.1f}s · {iteration} step' + ('s' if iteration != 1 else ''))}")
            print(C.grey("─" * WIDTH))
            for para in summary.split("\n"):
                if para.strip():
                    print(_wrap(para, indent=2))
                else:
                    print()
            print(C.grey("─" * WIDTH))
            break

        else:
            print(f"\n  {C.yellow('⚠')}  Empty response — no text or tool calls. Stopping.\n")
            break
    else:
        elapsed = time.monotonic() - start
        print(f"\n  {C.yellow('⚠')}  Reached {max_iterations} iterations ({elapsed:.1f}s). Task may be incomplete.\n")



def run_interactive(client, model: str, verbose: bool) -> None:
    print()
    print(C.grey("─" * WIDTH))
    print(f"  {C.b_blue('◆ Coding Agent')}  {C.grey('interactive · ' + model)}")
    print(C.grey("─" * WIDTH))
    print(f"  {C.grey('Describe the project you want to build.')}")
    print(f"  {C.grey('Commands:')}  {C.grey('exit  quit  clear')}")
    print(C.grey("─" * WIDTH))
    print()

    while True:
        try:
            user_input = input(f"  {C.b_green('❯')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n  {C.grey('Goodbye!')}\n")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print(f"  {C.grey('Goodbye!')}\n")
            break
        if user_input.lower() == "clear":
            os.system("clear" if os.name != "nt" else "cls")
            continue

        run_agent(client, user_input, model, verbose)
        print()

def parse_args():
    p = argparse.ArgumentParser(
        description="Coding Agent — builds projects iteratively with Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            examples:
            python agentic.py                                         # interactive REPL
            python agentic.py -p "Build a FastAPI app with SQLite"   # one-shot
            python agentic.py -p "..." -v                            # verbose output
            python agentic.py -p "..." --max-iterations 50
        """,
    )
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--prompt", "-p",   help="One-shot prompt (omit for REPL)")
    p.add_argument("--verbose", "-v",  action="store_true", help="Full token counts + tool output")
    p.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    return p.parse_args()


if __name__ == "__main__":
    load_dotenv()
    args = parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(f"\n  {C.red('✗')} GEMINI_API_KEY not set. Add it to .env or your environment.\n")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    if args.prompt:
        run_agent(client, args.prompt, args.model, args.verbose, args.max_iterations)
    else:
        run_interactive(client, args.model, args.verbose)