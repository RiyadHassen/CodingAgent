import os
from google.genai import types


def get_files_info(working_directory: str, directory: str = ".") -> str:
    """Return a newline-separated listing of files and directories inside `directory`.

    The function prevents access outside the supplied `working_directory` for safety.
    """
    abs_working_dir = os.path.abspath(working_directory)
    target_directory = os.path.abspath(os.path.join(abs_working_dir, directory))

    if not target_directory.startswith(abs_working_dir):
        return f"Error: Cannot list '{directory}' because it's outside the working directory"
    if not os.path.exists(target_directory):
        return f"Error: Directory '{directory}' does not exist."
    if not os.path.isdir(target_directory):
        return f"Error: '{directory}' is not a directory."

    entries = []
    for name in sorted(os.listdir(target_directory)):
        item_path = os.path.join(target_directory, name)
        if os.path.isfile(item_path):
            entries.append(f"File: {name}")
        elif os.path.isdir(item_path):
            entries.append(f"Directory: {name}")
        else:
            entries.append(f"Other: {name}")

    return "\n".join(entries)


schema_get_files_info = types.FunctionDeclaration(
    name="get_files_info",
    description="Lists files in the specified directory along with their sizes, constrained to the working directory.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "directory": types.Schema(
                type=types.Type.STRING,
                description="The directory path to list files in, relative to the working directory.",
            ),
        },
    ),
)
