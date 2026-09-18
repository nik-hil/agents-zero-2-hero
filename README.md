<h1 align="center">Agents Zero 2 Hero</h1>

<p align="center">
  <em>Build a Python coding-agent harness from first principles —<br>
  one git tag, one new capability at a time.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LLM-OpenRouter_|_DigitalOcean-8B5CF6" alt="Providers">
  <img src="https://img.shields.io/badge/style-no--framework-06B6D4" alt="No framework">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

---

## 🤔 What is an agent harness?

An **agent harness** is all the infrastructure that wraps an LLM to turn it into
a functional agent. The model provides the *intelligence*; the harness provides
the **hands, eyes, memory, and safety boundaries**:

```
harness = tools + knowledge + observation + action + permissions
```

This repo builds that harness **by hand, in plain Python**, so the mechanics are
visible instead of hidden inside a framework. (For a full-featured production
version of these ideas, see [HKUDS/OpenHarness](https://github.com/HKUDS/OpenHarness),
which inspired this curriculum.)

### The agent loop — the heart of it

```python
while True:
    response = client.chat.completions.create(messages, tools=TOOL_SCHEMAS)
    if not response.tool_calls:
        break                       # model has nothing more to do
    for call in response.tool_calls:
        result = TOOLS[call.name](**call.args)   # permission-checked execution
        messages.append(tool_result(call, result))
        if call.name == "finish":
            return result            # model signalled it's done
```

The model decides **what** to do; the harness decides **how** — safely and
observably.

---

## 📍 Current checkpoint

<!-- BEGIN:checkpoint -->
**You are on `v0.13-verify-loop` — lesson 13 of 13.**

### Verification loop

- **Pillar:** 🔄 Agent Loop
- **Adds:** `run_tests tool (run -> read failures -> fix -> rerun)`

Close the loop: give the agent a run_tests tool and prompt it to run the suite, read failures, fix the code, and rerun until green — turning "generate and hope" into "generate, verify, fix".

```bash
AGENT_VERIFY=1 python coding_agent.py
```
<!-- END:checkpoint -->

---

## 🚀 Quickstart

```bash
git clone https://github.com/nik-hil/agents-zero-2-hero.git
cd agents-zero-2-hero
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Provide your key via a **local `.env`** (never paste keys into chat, commits, or
issues). The harness speaks the OpenAI API, so it works with either **OpenRouter**
or **DigitalOcean Serverless Inference** — pick one with `LLM_PROVIDER`:

```bash
# Option A — OpenRouter (default)
cat > .env <<'EOF'
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
EOF

# Option B — DigitalOcean (model access key from the DO Control Panel)
cat > .env <<'EOF'
LLM_PROVIDER=digitalocean
DIGITALOCEAN_INFERENCE_KEY=your-do-model-access-key
# optional: pin an exact model ID from the DO catalog (note: hyphens, not slashes)
# LLM_MODEL=openai-gpt-4o-mini
EOF
```

Both providers are just an OpenAI-compatible `base_url` + key + model slug;
`client.py` selects the bundle. Smoke-test the client, then run the agent:

```bash
python client.py            # verify the LLM connection
python coding_agent.py      # run the coding agent demos
```

---

## 🧭 How to use this repo (learn tag-by-tag)

Each **git tag adds exactly one component**. Check one out and read its lesson to
learn that feature in isolation; `master` is the cumulative "hero" state.

```bash
git tag --sort=version:refname     # list lessons in order
git checkout v0.2-new-tools        # jump to a lesson
cat lessons/v0.2-new-tools.md      # read what it teaches
git checkout master                # back to the latest
```

The README you're reading is **stamped for the tag you're on** — check out an
older tag and this section reflects that lesson's state.

## 🗺️ Roadmap

<!-- BEGIN:roadmap -->
| | Tag | Lesson | Adds | Pillar |
|---|---|---|---|---|
| ✅ | `v0.1-basic-tool` | A minimal agent loop with one tool | `execute_code + finish` | 🔄 Agent Loop |
| ✅ | `v0.2-new-tools` | File tools | `list_files, read_file, write_file` | 🔧 Toolkit |
| ✅ | `v0.3-bash-tut` | A guarded shell tool | `bash (allowlisted) + Docker` | 🔧 Toolkit |
| ✅ | `v0.4-edit-tool` | Precise edits and search | `edit_file + code_search (ripgrep)` | 🔧 Toolkit |
| ✅ | `v0.5-multi-provider` | Multiple LLM providers | `provider switch (OpenRouter + DigitalOcean) + unit tests` | 🔌 Providers |
| ✅ | `v0.6-permissions` | Permission modes | `PermissionChecker (auto / default / plan + path & command rules)` | 🛡️ Governance |
| ✅ | `v0.7-hooks` | Lifecycle hooks | `PreToolUse / PostToolUse hooks (HookManager)` | 🛡️ Governance |
| ✅ | `v0.8-memory` | Persistent memory and context | `Memory (AGENTS.md injection + MEMORY.md + remember tool) + SessionStore` | 🧠 Context & Memory |
| ✅ | `v0.9-compaction` | Context compaction | `Compactor (summarize old turns when over a char budget)` | 🧠 Context & Memory |
| ✅ | `v0.10-skills` | On-demand skills | `SkillLibrary + list_skills / load_skill tools (SKILL.md)` | 🔧 Toolkit |
| ✅ | `v0.11-mcp` | An MCP client | `MCPClient (stdio JSON-RPC) + example server + tool mounting` | 🔧 Toolkit |
| ✅ | `v0.12-subagents` | Subagents | `spawn_subagent tool (depth-guarded delegation)` | 🤝 Swarm |
| 👉 | `v0.13-verify-loop` | Verification loop | `run_tests tool (run -> read failures -> fix -> rerun)` | 🔄 Agent Loop |

👉 you are here · ✅ shipped · 🚧 building next · ○ planned
<!-- END:roadmap -->

---

## 📂 Repository layout

```
client.py           # provider switch: OpenRouter / DigitalOcean (OpenAI-compatible)
coding_agent.py     # the harness: tools + tool schemas + the agent loop
permissions.py      # permission gate: auto/default/plan modes, path & command rules
hooks.py            # PreToolUse / PostToolUse lifecycle hooks (logging, metrics, redaction)
memory.py           # context injection (AGENTS.md), persistent memory (MEMORY.md), sessions
compaction.py       # summarize old turns when history exceeds the context budget
skills.py           # on-demand skills: catalog in the prompt, bodies loaded when needed
skills/             # SKILL.md files (python-style, git-commit, ...)
mcp_client.py       # minimal MCP client (stdio JSON-RPC) to mount external tools
mcp_servers/        # bundled example MCP server (echo_server.py) for the demo
verify.py           # run_tests: run the suite, report pass/fail for the verify loop
AGENTS.md           # human-authored project context, injected into the prompt each run
frameworks/         # the same idea via CrewAI / LangGraph (framework hides the loop)
tests/              # offline unit tests (no API key needed)
lessons/            # one short lesson doc per tag
lessons.yml         # single source of truth for the curriculum
scripts/            # tooling (README stamper, ...)
Dockerfile          # containerized demo (used from v0.3)
docker-compose.yml
```

---

## 🛠️ Maintainer notes

The **Current checkpoint** and **Roadmap** sections above are generated from
`lessons.yml` by `scripts/stamp_readme.py`. Add or edit a lesson there, then:

```bash
pip install -r requirements-dev.txt
python scripts/stamp_readme.py          # re-stamp README for the current tag
python scripts/stamp_readme.py --check  # CI: fail if README is stale
```

When shipping a new lesson: implement the component, add its entry to
`lessons.yml`, write `lessons/<tag>.md`, run the stamper, commit, then tag.

---

## 📄 License

MIT
