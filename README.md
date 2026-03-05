# AgenticAI

AgenticAI is a small CLI-first coding assistant toolkit that provides safe helpers for reading, writing, and executing Python code inside a restricted working directory. It's designed to be used by an LLM-based coding agent or interactively from the command line.

**Features**
- Safely list files/directories under a specified working directory.
- Read file contents (truncated to a safe size).
- Write files (with parent directory creation and UTF-8 encoding).
- Execute Python files and execute ad-hoc Python code by writing a temporary file (cleaned up afterwards).
- A polished CLI with subcommands: `list`, `read`, `write`, `runfile`, `runcode`.

**Requirements**
- Python 3.13+
- The project dependencies are in `pyproject.toml` (uses `google-genai` and `python-dotenv`).

Quick start
-----------
Clone or open the repository and run the CLI from the project root.

Sample run

```
python agent.py --prompt  "Build a FastAPI REST API With SQLite for inventory servies"
```

Sample run
```
python agent.py --prompt  "I want to build a transformer based  nanogpt model using pytorch and want to train the model and made inference for character level prediction, build me the model and training pipline and write a training script and sample inference script to load and run sample infernce"
```

Run the CLI help:
```bash
PYTHONPATH=./agenticai python agenticai/agent.py --help
```


- Read a file (up to the configured limit):

```bash
PYTHONPATH=./agenticai python agenticai/agent.py read calculator/pkg/calculator.py
```

- Write a file from a string:

```bash
PYTHONPATH=./agenticai python agenticai/agent.py write notes/new.txt --content "Hello from AgenticAI"
```

- Write a file from stdin:

```bash
echo "print(123)" | PYTHONPATH=./agenticai python agenticai/agent.py write scripts/print.py --stdin
```

- Run a python file inside the project:

```bash
PYTHONPATH=./agenticai python agenticai/agent.py runfile calculator/main.py
```

- Run ad-hoc Python code (from argument):

```bash
PYTHONPATH=./agenticai python agenticai/agent.py runcode --code "print('hi from temp')"
```

Docker
------
A `Dockerfile` is included for running the project in a container. To build and run the image:

```bash
cd agenticai
docker build -t agenticai:latest .
# Run, passing your GEMINI_API_KEY (if you will use the model features)
docker run --rm -e GEMINI_API_KEY="$GEMINI_API_KEY" agenticai:latest --help
```

Notes and security
------------------
- The helpers intentionally restrict file access to a provided working directory to reduce risk. However, executing arbitrary code is inherently risky; do not run untrusted code without additional sandboxing (e.g., separate container, user, seccomp, or resource limits).
- `get_file_content` truncates large files to a safe size to avoid feeding huge files into downstream LLM calls.

Development
-----------
- The CLI entrypoint is `agenticai/agent.py`.
- Helpers live in `agenticai/functions/`.
- To run tests or add more functionality, consider adding `pytest` and a `tests/` directory.

If you'd like, I can:
- Add unit tests for the helper functions and CLI commands.
- Add colorized CLI output (with `rich`).
- Provide an automated `docker-compose` dev configuration.
