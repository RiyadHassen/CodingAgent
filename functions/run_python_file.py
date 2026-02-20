from .run_python import run_python_file as run_python_file_impl
from google.genai import types 

def run_python_file(working_directory, file_path, args=None):
    """Wrapper that delegates to `functions.run_python.run_python_file`.

    This file exists for compatibility with callers importing `run_python_file`.
    """
    return run_python_file_impl(working_directory, file_path, args=args)


schema_run_python_file =types.FunctionDeclaration(
    name = "run_python_file", 
    description = "Executes a Python file located within the working directory and returns its combined STDOUT/STDERR output along with exit code information.",
    parameters = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "file_path": types.Schema(
                type=types.Type.STRING,
                description="The path to the Python file to execute, relative to the working directory.",
            ),
            "args": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(type=types.Type.STRING, 
                                   description="A command-line argument to pass to the Python file."),
                description="Optional list of command-line arguments to pass to the Python file.",
            ),
        },  
        required=["file_path"],
    ),
)