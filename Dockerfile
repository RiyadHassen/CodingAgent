# Use official Python 3.13 slim image
FROM python:3.13-slim

# Set a non-root user (optional) and working directory
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Copy only dependency specification first (small layer)
COPY pyproject.toml /app/

# Install pip and build dependencies, then install runtime dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install google-genai==1.12.1 python-dotenv==1.1.0

# Copy application code
COPY . /app

# Expose nothing by default; this container runs CLI script

# Default entrypoint: run main.py
CMD ["python", "agent.py"]
# ─────────────────────────────────────────────────────────────────────────────
# Coding Agent — Docker Image
# ─────────────────────────────────────────────────────────────────────────────
# Build:
#   docker build -t coding-agent .
#
# Run (interactive REPL):
#   docker run -it --rm \
#     --env-file .env \
#     -v "$(pwd)/projects:/workspace/projects" \
#     coding-agent
#
# Run (one-shot prompt):
#   docker run -it --rm \
#     --env-file .env \
#     -v "$(pwd)/projects:/workspace/projects" \
#     coding-agent --prompt "Build a FastAPI REST API with SQLite"
#
# Notes:
#   - GEMINI_API_KEY must be set in .env or via --env GEMINI_API_KEY=...
#   - Mount a host directory to /workspace/projects to persist generated code
#   - The agent's change_directory tool moves inside /workspace, so all
#     generated projects land under your mounted volume automatically
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.13-slim

# ── Environment ───────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── System packages ───────────────────────────────────────────────────────────
# These are needed by the agent's shell tools (run_bash_command, grep_in_files)
# and by projects the agent may generate (git for version control, curl for
# downloading data, build-essential for packages that compile C extensions).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
        grep \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────────────────────
# /workspace is the agent's root. Generated projects land in subdirectories
# here and can be persisted by mounting a host volume at /workspace/projects.
WORKDIR /workspace

# ── Python dependencies ───────────────────────────────────────────────────────
# Copy only the dependency file first so Docker can cache this layer
# independently of source code changes.
COPY pyproject.toml /workspace/

RUN pip install --upgrade pip setuptools wheel \
    && pip install google-genai==1.12.1 python-dotenv==1.1.0

# ── Application source ────────────────────────────────────────────────────────
COPY . /workspace/

# ── Non-root user ─────────────────────────────────────────────────────────────
# Running as root inside containers is a security risk, especially since this
# agent executes arbitrary shell commands. The agent still has full access to
# /workspace (owned by agentuser) and can install packages via pip.
RUN useradd --create-home --shell /bin/bash agentuser \
    && chown -R agentuser:agentuser /workspace

USER agentuser

# ── Entrypoint ────────────────────────────────────────────────────────────────
# ENTRYPOINT locks in the interpreter + script.
# CMD provides default args (empty = interactive REPL).
# Any args passed to `docker run` after the image name override CMD only,
# so `docker run ... coding-agent --prompt "..."` works cleanly.
ENTRYPOINT ["python", "agent.py"]
CMD []