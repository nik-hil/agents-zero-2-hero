import os
import subprocess
import json
from textwrap import dedent

from openai import OpenAI
from client import get_client

from pathlib import Path

# IMPORTANT: all file operations will happen here
WORKSPACE = Path("agent_workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)
os.chdir(WORKSPACE)
print(f"Changed working directory to: {os.getcwd()}")

# Optional: print current workspace so user knows where files are
print(f"Agent workspace: {WORKSPACE}")

client = get_client()

def execute_code(code: str) -> dict:
    """
    Docstring for execute_code
    Execute python code and returs the output or error
    
    :param code: Description
    """
    try:
        # Write temp file **inside** the workspace
        temp_path = WORKSPACE / "temp.py"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(code)

        # Run it with cwd = WORKSPACE
        result = subprocess.run(
            ['python', 'temp.py'],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=WORKSPACE          # ← this is the key line
        )

        # Clean up
        temp_path.unlink(missing_ok=True)

        if result.returncode == 0:
            return {"output": result.stdout.strip(), "error": None}
        else:
            return {"output": None, "error": result.stderr.strip()}

    except Exception as e:
        return {"output": None, "error": str(e)}
    
def finish(answer: str):
    """Signals the task is complete with the final answer."""
    return {"final_answer": answer}

def list_files(path: str = ".") -> dict:
    """
    List files and directories in the specified path (relative to workspace).
    Returns a dict with 'files' and 'directories' lists.
    
    :param path: Description
    :type path: str
    :return: Description
    :rtype: dict
    """

    try:
        target = (WORKSPACE/ path).resolve()

        # security : prevent going outsite the workspace
        if not target.is_relative_to(WORKSPACE):
            return {"error": "Path must be inside the workspace"}
    
        if not target.exists():
            return {"error": f"Path does not exist: {path}"}
        if not target.is_dir():
            return {"error": f"Not a directory: {path}"}

        items = []
        for item in sorted(target.iterdir()):
            rel_path = item.relative_to(WORKSPACE).as_posix()
            if item.is_dir():
                items.append(f"[DIR]  {rel_path}/")
            else:
                items.append(f"[FILE] {rel_path}")
        return {
            "path": path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {"error": str(e)}
    

def read_file(filepath: str) -> dict:
    """
    Read the content of a file in the workspace
    
    :param filepath: file path
    :type filepath: str
    :return: Description
    :rtype: dict
    """
    try:
        full_path = (WORKSPACE/ filepath).resolve()

        # Security check
        if not full_path.is_relative_to(WORKSPACE):
            return {"error": "Path must be inside workspace"}
        
        if not full_path.is_file():
            return {"error": f"Not a file or does not exist: {filepath}"}
        
        content = full_path.read_text(encoding="utf-8")
        return {
            "filepath": filepath,
            "content": content,
            "length": len(content)
        }
    except Exception as e:
        return {"error": str(e)}

def write_file(filepath: str, content: str, mode: str = "w") -> dict:
    """
    Write or append to a file in the workspace.
    mode: "w" = overwrite (default), "a" = append
    """
    try:
        if mode not in ("w", "a"):
            return {"error": 'mode must be "w" or "a"'}

        full_path = (WORKSPACE / filepath).resolve()
        
        # Security
        if not full_path.is_relative_to(WORKSPACE):
            return {"error": "Path must be inside workspace"}
        
        # Create parent directories if needed
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(full_path, mode=mode, encoding="utf-8") as f:
            f.write(content)
        
        return {
            "filepath": filepath,
            "action": "overwritten" if mode == "w" else "appended",
            "bytes_written": len(content)
        }
    except Exception as e:
        return {"error": str(e)}
    
TOOLS = {
    "execute_code": execute_code,
    "finish": finish,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
}


TOOL_SCHEMAS = [
    # Previous tools
    {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Execute Python code in a sandboxed environment and return stdout/stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Valid Python code to execute"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "finish",
            "description": "Call this when the task is fully solved. Provide the final answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The complete final answer to the user's task"
                    }
                },
                "required": ["answer"]
            }
        }
    },

    # 3 NEW TOOLS
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories in a given path inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path (default: current directory)",
                        "default": "."
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the full content of a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file"
                    }
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite/append to a file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path where to save the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["w", "a"],
                        "description": "'w' = overwrite, 'a' = append",
                        "default": "w"
                    }
                },
                "required": ["filepath", "content"]
            }
        }
    }
]


def run_agent(task: str, max_iterations: int = 8, model="x-ai/grok-4.1-fast", verbose=True):
    SYSTEM_PROMPT = """\
        You are an autonomous coding agent working inside a dedicated workspace folder.

        Available tools:
        - list_files(path=".")        → see what files/folders exist
        - read_file(filepath)         → read file content
        - write_file(filepath, content, mode="w") → create/overwrite/append file
        - execute_code(code)          → run Python code and see output
        - finish(answer)              → submit the final answer when done

        Rules:
        - ALWAYS explore the workspace first with list_files when starting a new task.
        - Use relative paths only (never absolute paths).
        - Read files before trying to modify or understand them.
        - Think step by step. Describe your plan before acting.
        - When the task is completely solved → call finish() with the answer.
        """
    messages = [
        {
            "role": "system",
            "content": dedent(SYSTEM_PROMPT),
        },
        {"role": "user", "content": task},
    ]

    for iteration in range(max_iterations):
        if verbose:
            print(f"\nIteration {iteration + 1}: Calling LLM...")
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
        if verbose and message.content:
            print(f"Assistant thinking: {message.content}")
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
                if verbose:
                    print(f"Tool call: {tool_name} with args: {args}")

                result = TOOLS[tool_name](**args)

                if verbose:
                    print(f"Tool result: {json.dumps(result, indent=2)}")

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
            if verbose:
                print("No tool calls this iteration.")
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                }
            )

    raise RuntimeError("Max iterations reached without finishing the task.")
    


if __name__ == "__main__":
    # List of demo tasks to showcase each tool
    demo_tasks = [
        # Demo 1: list_files
        "Explore the workspace with list_files and return the list of items as the final answer.",
        
        # Demo 2: write_file (overwrite/create)
        "Create a new file called demo.txt with the content 'Initial test content'. Then finish with 'File created successfully'.",
        
        # Demo 3: write_file (append)
        "Append ' Appended line' to demo.txt using mode='a'. Then finish with 'File appended successfully'.",
        
        # Demo 4: read_file
        "Read the content of demo.txt and return the full content as the final answer.",
        
        # Demo 5: execute_code
        "Execute Python code to calculate and print the sum of numbers from 1 to 10. Return the output.",
        
        # Demo 6: Combined (write + execute + finish)
        "Write a Python script to demo.py that prints FizzBuzz up to 10, execute it, and return the output."
    ]

    # Run each demo
    for i, task in enumerate(demo_tasks, 1):
        print(f"\n{'=' * 80}")
        print(f"DEMO {i}: Task = '{task}'")
        print(f"{'=' * 80}\n")
        
        try:
            result = run_agent(task, max_iterations=10, verbose=True)  # verbose=True for clear demo
            print(f"\nFinal Result for Demo {i}: {result}")
        except Exception as e:
            print(f"Error in Demo {i}: {str(e)}")

