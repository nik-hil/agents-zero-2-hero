# AGENTS.md — project context for the agent

This file is human-authored, checked into the repo, and injected into the agent's
system prompt on every run (see `memory.py`). Use it for steady facts the agent
should always know about this project.

## About this project
- This is **agents-zero-2-hero**, a tag-by-tag tutorial that builds a coding-agent
  harness from scratch in plain Python.
- The agent does file work inside `agent_workspace/`, sandboxed by path checks.

## Conventions
- Prefer small, focused changes; explain the plan before acting.
- Use relative paths inside the workspace; never absolute paths.

> Try it: edit a line here, run `python coding_agent.py`, and watch the agent's
> behavior reflect this context. This is "context injection" — the cheapest form
> of memory.
