"""langgraph_agent.py

Creates a LangGraph-based agent that reuses the tools from `coding_agent.py`.

This file intentionally imports the tool implementations from `coding_agent.py`
instead of re-implementing them here. If the `langgraph` SDK isn't available
the file falls back to a local simulation mode for development and testing.
"""
import os
import sys
import json
from typing import Dict

# This file lives in frameworks/ but reuses the tools defined in the repo-root
# coding_agent.py. Add the repo root to sys.path so the import works no matter
# where you run this script from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import tools from coding_agent (user requested not to rewrite the tools)
from coding_agent import TOOLS as CODING_TOOLS

# Re-export the same TOOLS mapping so code that expects a TOOLS variable works
TOOLS = CODING_TOOLS

try:
    import langgraph
    LANGGRAPH_AVAILABLE = True
except Exception:
    LANGGRAPH_AVAILABLE = False


def run_agent(task: str, max_iterations: int = 8, model: str = "langgraph/gpt-5-mini", verbose: bool = True):
    """Run an autonomous agent loop using LangGraph when available.

    This function delegates tool execution to the functions imported from
    `coding_agent.py` via the `TOOLS` mapping. If `langgraph` is not installed
    the function prints a simulation summary and returns a placeholder result.
    """
    system_prompt = "You are an autonomous coding agent inside a workspace. Use available tools to complete tasks."

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    if LANGGRAPH_AVAILABLE:
        api_key = os.environ.get("LANGGRAPH_API_KEY")
        if not api_key:
            raise RuntimeError("LANGGRAPH_API_KEY is not set in environment")

        # NOTE: the exact LangGraph client interface may differ — this is a
        # conservative template showing how to integrate. Adapt to the real
        # SDK methods when wiring to your environment.
        client = langgraph.Client(api_key=api_key)

        for i in range(max_iterations):
            resp = client.chat.create(model=model, messages=messages, tools=list(TOOLS.keys()))
            message = getattr(resp, "message", None) or resp
            content = getattr(message, "content", None) or message.get("content")
            if verbose:
                print("Assistant:", content)

            # Process tool calls if provided by the SDK
            for call in getattr(message, "tool_calls", []) or []:
                name = call.name
                args = json.loads(call.arguments)
                result = TOOLS[name](**args)
                messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
                if name == "finish":
                    return result.get("final_answer")

            messages.append({"role": "assistant", "content": content})

        raise RuntimeError("Max iterations reached without finishing")
    else:
        # Local simulation fallback
        print("LangGraph SDK not available — running local simulation.")
        print("Task:", task)
        # Show available tools (from coding_agent)
        print("Available tools:", sorted(TOOLS.keys()))
        # Run a simple demonstration: list files
        if "list_files" in TOOLS:
            lf = TOOLS["list_files"]()
            print(json.dumps(lf, indent=2))
        return "(simulation) created LangGraph-style agent using tools from coding_agent.py"


if __name__ == "__main__":
    demo = "Find all places where \"print\" is used in Python files"
    print(run_agent(demo, max_iterations=4))
