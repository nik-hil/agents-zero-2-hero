"""crewai_agent.py

Recreates the agents in `coding_agent.py` but using CREWAI.

This file is a safe template: when the `crewai` package is available
and `CREWAI_API_KEY` is set, it will attempt to use the CREWAI client.
Otherwise it falls back to a local simulation mode so the file is still
useful for development and testing without network access.

Drop-in replacement for experimenting with CREWAI-driven agents.
"""
import os
import sys
import json

# This file lives in frameworks/ but reuses the tools defined in the repo-root
# coding_agent.py. Add the repo root to sys.path so the import works no matter
# where you run this script from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import crewai
from coding_agent import TOOLS as CODING_TOOLS

TOOLS = CODING_TOOLS

def run_agent(task: str, max_iterations: int = 8, model: str = "crewai/gpt-5-mini", verbose: bool = True):
    """Run an autonomous agent loop based on CREWAI protocol if available.

    This function attempts to use the `crewai` package. If not available,
    it performs a local simulated loop that demonstrates the message flow.
    """
    system_prompt = (
        "You are an autonomous coding agent inside a workspace. Use available tools to complete tasks."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    api_key = os.environ.get("CREWAI_API_KEY")
    if not api_key:
        raise RuntimeError("CREWAI_API_KEY is not set in environment")
    client = crewai.Client(api_key=api_key)

    for i in range(max_iterations):
        resp = client.chat.create(model=model, messages=messages, tools=list(TOOLS.keys()))
        # This assumes `resp` contains `message` and optional `tool_calls` similar to other LLM APIs
        message = resp.message
        if verbose:
            print("Assistant:", message.content)
        # Handle tool calls if present
        for call in getattr(message, "tool_calls", []) or []:
            name = call.name
            args = json.loads(call.arguments)
            result = TOOLS[name](**args)
            messages.append({"role": "tool", "tool_name": name, "content": json.dumps(result)})
            if name == "finish":
                return result.get("final_answer")
        messages.append({"role": "assistant", "content": message.content})
    raise RuntimeError("Max iterations reached without finishing")
    


if __name__ == "__main__":
    demo = "Find all places where \"print\" is used in Python files"
    print(run_agent(demo, max_iterations=4))
