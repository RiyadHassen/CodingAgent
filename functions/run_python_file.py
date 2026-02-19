from .run_python import run_python_file as run_python_file_impl


def run_python_file(working_directory, file_path, args=None):
    """Wrapper that delegates to `functions.run_python.run_python_file`.

    This file exists for compatibility with callers importing `run_python_file`.
    """
    return run_python_file_impl(working_directory, file_path, args=args)