import os
import subprocess
import json
from textwrap import dedent

from openai import OpenAI
from client import get_client

client = get_client()

def execute_code(code:str):
    """
    Docstring for execute_code
    Execute python code and returs the output or error
    
    :param code: Description
    """

    try:
        with open("temp.py", "w") as f:
            f.write(code)

        result = subprocess.run(['python', 'temp.py'],capture_output=True, text=True, timeout=10)
        os.remove('temp.py')
        if result.returncode == 0:
            return {"output": result.stdout.strip(), "error": None}
        else:
            return {"output": None, "error": result.stderr.strip()}
        
    except Exception as e:
        return {"output": None, "error": str(e)}
    
def finish(answer: str):
    """Signals the task is complete with the final answer."""
    return {"final_answer": answer}



TOOLS = {
    "execute_code": execute_code,
    "finish": finish,
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code and return stdout or error.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute"
                    }
                },
                "required": ["code"],
                "additionalProperties": False   # ← good practice, prevents junk params
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Finish the task and return the final answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The final answer or result"
                    }
                },
                "required": ["answer"],
                "additionalProperties": False
            }
        }
    }
]


def run_agent(task: str, max_iterations: int = 8, model="openai/gpt-oss-120b"):
    messages = [
        {
            "role": "system",
            "content": dedent(
                """
                You are a coding agent.

                Rules:
                - Use tools when needed.
                - When the task is fully complete, call the finish tool exactly once.
                - Do not continue reasoning after calling finish.
                """
            ),
        },
        {"role": "user", "content": task},
    ]

    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.3,         
            max_tokens=2048,
        )

        if not response or not response.choices:
            raise RuntimeError(
                f"LLM returned empty response. "
                f"This usually means provider timeout or overload.\n"
                f"Raw response: {response}"
            )
        message = response.choices[0].message
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": message.tool_calls,   # keep if present
            }
        )
        # -------------------------
        # TOOL CALL HANDLING
        # -------------------------
        if message.tool_calls:
            messages.append(message)

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)

                result = TOOLS[tool_name](**args)

                # Immediately exit on finish
                if tool_name == "finish":
                    return result["final_answer"]

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result),
                    }
                )

        else:
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                }
            )

    raise RuntimeError("Max iterations reached without finishing the task.")
    


if __name__ == "__main__":
    task = "Write and execute a Python function for FizzBuzz up to 15. Return the output."
    result = run_agent(task)
    print("\nFinal Result:\n", result)