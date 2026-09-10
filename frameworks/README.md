# frameworks/

The rest of this repo builds a coding-agent **harness by hand** so the raw
mechanics (the loop, tool schemas, tool execution, permissions, memory…) are
visible. These files show the *same idea* implemented with an off-the-shelf
framework instead — the framework hides the loop, you just register tools.

Both files **reuse the exact tools** from the root `coding_agent.py` (they
import `TOOLS`) so the only thing that changes is who drives the loop.

| File | Framework | Notes |
|------|-----------|-------|
| `crewai_agent.py` | CrewAI | Falls back to a local simulation if `crewai` / `CREWAI_API_KEY` are absent. |
| `langgraph_agent.py` | LangGraph | Falls back to a local simulation if `langgraph` / `LANGGRAPH_API_KEY` are absent. |

Run from the repo root:

```bash
python frameworks/crewai_agent.py
python frameworks/langgraph_agent.py
```
