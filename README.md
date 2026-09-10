<h1 align="center">Agents Zero 2 Hero</h1>

<p align="center">
  <em>Build a Python coding-agent harness from first principles —<br>
  one git tag, one new capability at a time.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.10-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/LLM-OpenRouter-8B5CF6" alt="OpenRouter">
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
**You are on `v0.4-edit-tool` — lesson 4 of 12.**

### Precise edits and search

- **Pillar:** 🔧 Toolkit
- **Adds:** `edit_file + code_search (ripgrep)`

Targeted search/replace edits instead of rewriting whole files, plus fast code search with a ripgrep-or-Python fallback.

```bash
python coding_agent.py
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
| 👉 | `v0.4-edit-tool` | Precise edits and search | `edit_file + code_search (ripgrep)` | 🔧 Toolkit |
| 🚧 | `v0.5-permissions` | Permission modes | `PermissionChecker (ask / auto / plan + path & command rules)` | 🛡️ Governance |
| ○ | `v0.6-hooks` | Lifecycle hooks | `PreToolUse / PostToolUse hooks` | 🛡️ Governance |
| ○ | `v0.7-memory` | Persistent memory and context | `MEMORY.md + AGENTS.md injection + session resume` | 🧠 Context & Memory |
| ○ | `v0.8-compaction` | Context compaction | `auto-compact the message history` | 🧠 Context & Memory |
| ○ | `v0.9-skills` | On-demand skills | `Skill loader (.md files)` | 🔧 Toolkit |
| ○ | `v0.10-mcp` | An MCP client | `minimal Model Context Protocol client` | 🔧 Toolkit |
| ○ | `v0.11-subagents` | Subagents | `spawn + delegate to a subagent` | 🤝 Swarm |
| ○ | `v0.12-verify-loop` | Verification loop | `run tests -> read failures -> fix -> rerun` | 🔄 Agent Loop |

👉 you are here · ✅ shipped · 🚧 building next · ○ planned
<!-- END:roadmap -->

---

## 📂 Repository layout

```
client.py           # OpenRouter (OpenAI-compatible) client factory
coding_agent.py     # the harness: tools + tool schemas + the agent loop
frameworks/         # the same idea via CrewAI / LangGraph (framework hides the loop)
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
