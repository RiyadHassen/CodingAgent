import os
import subprocess
import uuid
import pathlib


def run_python_file(working_directory, file_path, args=None):
    abs_working_dir = os.path.abspath(working_directory)
    abs_file_path = os.path.abspath(os.path.join(working_directory, file_path))
    if not abs_file_path.startswith(abs_working_dir):
        return f'Error: Cannot execute "{file_path}" as it is outside the permitted working directory'
    if not os.path.exists(abs_file_path):
        return f'Error: File "{file_path}" not found.'
    if not file_path.endswith(".py"):
        return f'Error: "{file_path}" is not a Python file.'
    try:
        commands = ["python", abs_file_path]
        if args:
            commands.extend(args)
        result = subprocess.run(
            commands,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=abs_working_dir,
        )
        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"Process exited with code {result.returncode}")
        return "\n".join(output) if output else "No output produced."
    except Exception as e:
        return f"Error: executing Python file: {e}"


def run_python_code(working_directory: str, code: str, args: list | None = None, timeout: int = 30) -> str:
    """Execute a Python code string by writing it to a temporary file inside working_directory.

    Returns combined STDOUT/STDERR and exit code info. The temporary file is removed after execution.
    """
    abs_working_dir = os.path.abspath(working_directory)
    if not os.path.isdir(abs_working_dir):
        return f"Error: working directory '{working_directory}' does not exist"

    temp_name = f"_temp_exec_{uuid.uuid4().hex}.py"
    temp_path = os.path.join(abs_working_dir, temp_name)

    try:
        # Write the code to the temp file
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Build command
        commands = ["python", temp_path]
        if args:
            commands.extend(args)

        result = subprocess.run(
            commands,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=abs_working_dir,
        )

        output = []
        if result.stdout:
            output.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output.append(f"STDERR:\n{result.stderr}")
        if result.returncode != 0:
            output.append(f"Process exited with code {result.returncode}")
        return "\n".join(output) if output else "No output produced."
    except Exception as e:
        return f"Error: executing Python code: {e}"
    finally:
        # Clean up the temporary file if it exists
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass