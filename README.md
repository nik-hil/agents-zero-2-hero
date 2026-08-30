# Agents Zero 2 Hero

A tiny, tag-by-tag tutorial repo for building a Python coding-agent harness from first principles. The goal is to show how Cursor/Grok-style coding agents work under the hood without hiding the core loop inside an agent framework.

## Current lesson: `v04-agent-loop`

This lesson focuses on a plain Python agent loop:

1. accept a user task;
2. send messages and tool schemas to an OpenRouter model;
3. let the model choose tools;
4. execute tool calls inside a workspace;
5. append tool results back to the conversation;
6. stop when the model calls `finish`;
7. fail safely when `--max-steps` is reached.

We intentionally skip CrewAI, LangGraph, and other frameworks in this lesson so the raw harness mechanics are visible.

## What is included

- `client.py` creates an OpenAI-compatible OpenRouter client.
- `coding_agent.py` contains the Python-only tools and the v04 agent loop.
- `tests/test_agent_loop.py` tests the loop with a fake model client, so no API key is needed for unit tests.
- `Dockerfile` and `docker-compose.yml` provide a containerized demo environment.

## OpenRouter model

The default model is configured through `OPENROUTER_MODEL` and defaults to:

```bash
openai/gpt-5.6-luna
```

If OpenRouter uses a different model slug for **GPT-5.6 Luna** in your account, set `OPENROUTER_MODEL` to the exact slug shown in the OpenRouter dashboard.

## How to provide your OpenRouter key

Do **not** paste your OpenRouter key into chat, source code, commits, screenshots, or issue comments.

Use a local `.env` file on your machine:

```bash
cat > .env <<'EOF_ENV'
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=openai/gpt-5.6-luna
EOF_ENV
```

Or export it only for your current shell session:

```bash
export OPENROUTER_API_KEY='sk-or-v1-your-key-here'
export OPENROUTER_MODEL='openai/gpt-5.6-luna'
```

The `.env` file should stay local and should not be committed.

## Run on macOS

From a fresh clone:

```bash
git clone <your-repo-url>
cd agents-zero-2-hero
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create your local `.env` file:

```bash
cat > .env <<'EOF_ENV'
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_MODEL=openai/gpt-5.6-luna
EOF_ENV
```

Run the API smoke test:

```bash
python client.py
```

Run the Python-only coding agent:

```bash
python coding_agent.py "Create hello.py that prints hello from the agent, then run it" --max-steps 8
```

Run unit tests without an API key:

```bash
python -m unittest discover -s tests
```

## Expected local behavior

- The agent creates and uses an `agent_workspace/` directory for its file operations.
- File tools reject paths outside that workspace.
- The loop stops when the model calls the `finish` tool.
- If the model does not finish before `--max-steps`, the loop raises a max-iteration error.

## Next lesson ideas

After `v04-agent-loop`, the natural next tags are:

- `v05-budgets-and-limits`: step budgets, output truncation, runtime limits;
- `v06-error-recovery`: retries, bad JSON recovery, unknown tool recovery, repeated-failure detection;
- `v07-safe-edits`: diff/patch-based edits and rollback;
- `v08-verification-loop`: run tests, inspect failures, fix, and rerun.
