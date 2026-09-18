import os
import subprocess
import json
from textwrap import dedent
import shlex
import subprocess
import os
from typing import Dict

from openai import OpenAI
from client import get_client, get_model
from permissions import PermissionChecker, cli_approver
from hooks import HookManager
from memory import Memory, SessionStore
from compaction import Compactor, llm_summarizer
from skills import SkillLibrary
import shutil
from pathlib import Path

# IMPORTANT: all file operations will happen here
WORKSPACE = Path("agent_workspace").resolve()
WORKSPACE.mkdir(exist_ok=True)

# Memory lives at the repo root (WORKSPACE's parent), NOT inside the agent's
# scratch workspace — so AGENTS.md / MEMORY.md are human-editable and persist.
PROJECT_ROOT = WORKSPACE.parent
MEMORY = Memory(PROJECT_ROOT)
SESSIONS = SessionStore(PROJECT_ROOT)
SKILLS = SkillLibrary(PROJECT_ROOT / "skills")

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

def remember(note: str) -> dict:
    """Save a note to persistent memory (MEMORY.md) so future runs recall it."""
    return MEMORY.remember(note)

def list_skills() -> dict:
    """List available skills (name + description). Cheap — no bodies loaded."""
    return {"skills": SKILLS.catalog()}

def load_skill(name: str) -> dict:
    """Load the full text of one skill on demand."""
    return SKILLS.load(name)

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
    

def bash(command: str, verbose: bool = True) -> Dict:
    """
    Safely execute a limited set of shell-like commands.

    This is a constrained command runner intended for AI agent tutorials.
    It does NOT execute through a shell and only allows explicit commands.
    """
    # Commands intentionally allowed for demonstration
    ALLOWED_COMMANDS = {
        "ls",
        "grep",
        "pip list",
        "pwd",
        "cat",
        "echo",
        "python",
        "python3",
        "pip",
    }

    try:
        if not command or not command.strip():
            return {"error": "Empty command not allowed"}

        # Parse like a shell, but DO NOT execute via shell
        try:
            args = shlex.split(command)
        except ValueError as e:
            return {"error": f"Invalid shell syntax: {e}"}

        cmd = args[0]

        # Enforce allowlist
        if cmd not in ALLOWED_COMMANDS:
            return {
                "error": "Command not allowed",
                "allowed_commands": sorted(ALLOWED_COMMANDS),
                "attempted": cmd,
            }

        # Prevent path traversal in arguments
        for a in args[1:]:
            if a.startswith("/") or ".." in a:
                return {
                    "error": "Absolute paths and parent directory access are not allowed",
                    "argument": a,
                }
        if verbose:
            print(f"Executing command: {args} in {WORKSPACE}")       
        result = subprocess.run(
            args,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=20,
            shell=False,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": WORKSPACE,
            },
        )

        return {
            "command": args,
            "stdout": result.stdout.strip() or "(no output)",
            "stderr": result.stderr.strip() or "(no error output)",
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }

    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    
def edit_file(filepath: str, search_text: str, replace_text: str) -> dict:
    """
    Replace a specific block of text in an existing file with new text.
    This is useful for precise edits without overwriting the entire file.
    
    - search_text: the exact existing text/block to find and replace
    - replace_text: the new text to insert in its place
    """
    try:
        full_path = (WORKSPACE / filepath).resolve()
        
        if not full_path.is_relative_to(WORKSPACE):
            return {"error": "Path must be inside workspace"}
        
        if not full_path.is_file():
            return {"error": f"File does not exist: {filepath}"}
        
        original_content = full_path.read_text(encoding="utf-8")
        
        if search_text not in original_content:
            return {
                "error": "search_text not found in the file",
                "filepath": filepath,
                "search_text_snippet": search_text[:100] + "..." if len(search_text) > 100 else search_text
            }
        
        # Replace only the first occurrence (to be safe and predictable)
        updated_content = original_content.replace(search_text, replace_text, 1)
        
        full_path.write_text(updated_content, encoding="utf-8")
        
        return {
            "status": "success",
            "filepath": filepath,
            "old_length": len(original_content),
            "new_length": len(updated_content),
            "change_delta": len(updated_content) - len(original_content),
            "replaced_block_length": len(search_text)
        }
    
    except Exception as e:
        return {"error": str(e)}
    


def code_search(pattern: str, file_pattern: str = "*.py", context_lines: int = 2) -> dict:
    """
    Search for a pattern across files in the workspace.
    
    Uses ripgrep (rg) if available, otherwise falls back to simple grep-like search.
    
    Args:
        pattern:        The search string / regex to look for
        file_pattern:   Glob pattern of files to search (default: "*.py")
        context_lines:  Number of context lines to show around matches
    """
    try:
        # Check if ripgrep is available
        rg_available = shutil.which("rg") is not None

        if rg_available:
            # Use ripgrep - fast and powerful
            cmd = [
                "rg",
                "--color=never",
                f"--context={context_lines}",
                "--glob", file_pattern,
                pattern,
                "."
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=WORKSPACE,
                timeout=20
            )
            
            output = result.stdout.strip()
            if not output:
                output = "(no matches found)"
                
            return {
                "method": "ripgrep",
                "pattern": pattern,
                "file_pattern": file_pattern,
                "results": output,
                "match_count": output.count("\n") // (2 * context_lines + 1) if output else 0
            }
        
        else:
            # Fallback: simple Python-based search
            from pathlib import Path
            matches = []
            
            for file_path in WORKSPACE.rglob(file_pattern):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if pattern in line:
                            start = max(0, i - context_lines)
                            end = min(len(lines), i + context_lines + 1)
                            context = "\n".join(lines[start:end])
                            rel_path = file_path.relative_to(WORKSPACE).as_posix()
                            matches.append(f"File: {rel_path}\nLine {i+1}:\n{context}\n{'-'*60}")
                except Exception:
                    pass  # skip unreadable files
            
            result_text = "\n".join(matches) if matches else "(no matches found)"
            
            return {
                "method": "python_fallback",
                "pattern": pattern,
                "file_pattern": file_pattern,
                "results": result_text,
                "match_count": len(matches)
            }
    
    except subprocess.TimeoutExpired:
        return {"error": "Search timed out"}
    except Exception as e:
        return {"error": str(e)}
    

TOOLS = {
    "execute_code": execute_code,
    "finish": finish,
    "remember": remember,
    "list_skills": list_skills,
    "load_skill": load_skill,
    "list_files": list_files,
    "read_file": read_file,
    "write_file": write_file,
    "bash": bash,
    "edit_file": edit_file,
    "code_search": code_search,
}


TOOL_SCHEMAS = [
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
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": (
                "Save a short note to persistent memory (MEMORY.md) so it is "
                "available in future runs. Use for durable facts, preferences, or "
                "decisions worth recalling later."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "note": {
                        "type": "string",
                        "description": "The fact or note to remember (one short sentence)"
                    }
                },
                "required": ["note"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_skills",
            "description": (
                "List available skills (name + description). Skills are on-demand "
                "knowledge; call this to see what guidance you can load."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": (
                "Load the full text of one skill by name. Do this when a task "
                "matches a skill's description, then follow its guidance."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "The skill name from list_skills"}
                },
                "required": ["name"]
            }
        }
    },
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
    },
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command inside the workspace directory. "
                "Useful for git operations, listing files with options, running tests, "
                "simple greps, checking environment, etc. "
                "Dangerous or destructive commands are blocked."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute (e.g. 'ls -la', 'git status', 'pytest', 'grep -r TODO .')"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace a specific block of text in an existing file with new text. "
                "Use this for precise, targeted code edits instead of overwriting the whole file. "
                "The search_text must match exactly (including indentation)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path to the file to edit"
                    },
                    "search_text": {
                        "type": "string",
                        "description": "The exact existing text/block to find and replace (case-sensitive, whitespace-sensitive)"
                    },
                    "replace_text": {
                        "type": "string",
                        "description": "The new text to insert in place of search_text"
                    }
                },
                "required": ["filepath", "search_text", "replace_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "code_search",
            "description": (
                "Search for a text pattern or regex across files in the workspace. "
                "Uses ripgrep (rg) if installed, otherwise a simple Python-based search. "
                "Great for finding function definitions, usages, TODOs, variable names, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "The string or regex pattern to search for"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern of files to include (default: '*.py')",
                        "default": "*.py"
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Number of context lines around each match (default: 2)",
                        "default": 2
                    }
                },
                "required": ["pattern"]
            }
        }
    }
]


SPAWN_SCHEMA = {
    "type": "function",
    "function": {
        "name": "spawn_subagent",
        "description": (
            "Delegate a self-contained subtask to a fresh subagent that has its own "
            "clean context and the same tools. Returns the subagent's final answer. "
            "Use for well-scoped sub-jobs (e.g. 'research X', 'refactor file Y') so "
            "their detail doesn't clutter your own context."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "task": {"type": "string",
                         "description": "A complete, standalone instruction for the subagent"}
            },
            "required": ["task"],
        },
    },
}


def run_agent(task: str, max_iterations: int = 8, model=None, verbose=True,
              permissions=None, hooks=None, memory=None, session=None, resume=False,
              compactor=None, extra_tools=None, extra_schemas=None,
              depth=0, max_depth=1):
    # Default to whichever provider/model client.py selected (OpenRouter or DO).
    model = model or get_model()
    # Merge in any externally provided tools (e.g. from an MCP server) so they
    # sit alongside the built-in ones with no special-casing in the loop.
    tools_map = {**TOOLS, **(extra_tools or {})}
    schemas = TOOL_SCHEMAS + list(extra_schemas or [])
    # Every tool call is gated by this checker. Mode comes from AGENT_PERMISSION_MODE
    # (auto | default | plan); auto keeps the earlier demos running unattended.
    if permissions is None:
        permissions = PermissionChecker(
            mode=os.getenv("AGENT_PERMISSION_MODE", "auto"),
            approver=cli_approver,
        )
    # Lifecycle hooks around each tool call. Default: no hooks (a no-op manager).
    if hooks is None:
        hooks = HookManager()
    # Memory: project context (AGENTS.md) + persistent notes (MEMORY.md).
    if memory is None:
        memory = MEMORY
    # Compaction: summarize old turns when the history exceeds the char budget.
    # Threshold from AGENT_MAX_CONTEXT_CHARS; summaries produced by the LLM.
    if compactor is None:
        compactor = Compactor(
            max_chars=int(os.getenv("AGENT_MAX_CONTEXT_CHARS", "8000")),
            summarizer=llm_summarizer(client, model),
        )

    # Subagents: let this agent delegate a scoped subtask to a fresh child agent.
    # The child gets its OWN clean message history (isolated context) but shares
    # the same policy (permissions/hooks/memory) and workspace. Bounded by
    # max_depth so agents can't spawn endlessly.
    def _spawn_subagent(task, **_ignore):
        if depth >= max_depth:
            return {"error": "subagent depth limit reached — do this task yourself"}
        if verbose:
            print(f"[subagent] depth {depth + 1}: {task[:70]}")
        answer = run_agent(
            task, max_iterations=max_iterations, model=model, verbose=verbose,
            permissions=permissions, hooks=hooks, memory=memory,
            depth=depth + 1, max_depth=max_depth,
        )
        return {"subagent_result": answer}

    if depth < max_depth:
        tools_map["spawn_subagent"] = _spawn_subagent
        schemas = schemas + [SPAWN_SCHEMA]
    SYSTEM_PROMPT = """\
        You are an autonomous coding agent working inside a dedicated workspace folder.

        Available tools:
        - list_files(path=".")        → see what files/folders exist
        - read_file(filepath)         → read file content
        - write_file(filepath, content, mode="w") → create/overwrite/append file
        - execute_code(code)          → run Python code and see output
        - bash(command)               → run a shell command inside the workspace (git, tests, grep, ls with options, etc.). Dangerous commands are blocked.
        - edit_file(filepath, search_text, replace_text) → replace a specific block of text in a file with new text (precise edits)
        - code_search(pattern, file_pattern="*.py", context_lines=2) → search for a pattern across files (uses ripgrep if available)
        - remember(note)              → save a durable note to persistent memory (MEMORY.md)
        - list_skills()               → list available skills (name + description)
        - load_skill(name)            → load a skill's full guidance on demand
        - spawn_subagent(task)        → delegate a self-contained subtask to a fresh subagent
        - finish(answer)              → submit the final answer when done

        Rules:
        - ALWAYS explore the workspace first with list_files when starting a new task.
        - If a skill's description matches the task, load_skill() it and follow its guidance.
        - Use relative paths only (never absolute paths).
        - Read files before trying to modify or understand them.
        - Think step by step. Describe your plan before acting.
        - A permission layer may block a tool call; if a result says "permission denied",
          adjust your approach instead of retrying the same call.
        - When the task is completely solved → call finish() with the answer.
        """
    # Inject project context + remembered notes into the system prompt.
    system_content = dedent(SYSTEM_PROMPT)
    addendum = memory.system_addendum()
    if addendum:
        system_content += "\n\n# Memory\n" + addendum
        if verbose:
            print(f"[memory] injected {len(addendum)} chars of context/notes")
    # Inject the cheap skills catalog (names + descriptions only — bodies stay
    # on disk until load_skill pulls one in). This is the "on-demand" part.
    catalog = SKILLS.catalog_text()
    if catalog:
        system_content += "\n\n# Available skills (load with load_skill)\n" + catalog
        if verbose:
            print(f"[skills] {len(SKILLS.names())} available: {', '.join(SKILLS.names())}")

    messages = [{"role": "system", "content": system_content}]

    # Optionally resume: replay a prior session's transcript as context.
    transcript = []
    if session and resume:
        prior = SESSIONS.load(session)
        if prior:
            transcript = list(prior)
            messages.append({
                "role": "user",
                "content": "Here is our earlier session for context:\n\n"
                           + SESSIONS.as_text(prior),
            })
            if verbose:
                print(f"[session] resumed '{session}' ({len(prior)} entries)")

    messages.append({"role": "user", "content": task})
    transcript.append({"role": "user", "content": task})

    for iteration in range(max_iterations):
        # Keep the context under budget before every model call.
        messages, compacted = compactor.maybe_compact(messages)
        if compacted and verbose:
            print(f"[compaction] history summarized -> now {len(messages)} messages, "
                  f"~{sum(len(m.get('content') or '') for m in messages)} chars")

        if verbose:
            print(f"\nIteration {iteration + 1}: Calling LLM...")
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=schemas,
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
        if message.content:
            transcript.append({"role": "assistant", "content": message.content})
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

                # 1) Permission gate: hard allow/deny before anything runs.
                decision = permissions.check(tool_name, args)
                blocked = not decision.allowed
                if blocked:
                    result = {"error": "permission denied", "reason": decision.reason}
                    if verbose:
                        print(f"Permission denied: {decision.reason}")
                else:
                    # 2) PreToolUse hooks: may rewrite args or block the call.
                    allowed, reason, args = hooks.run_pre(tool_name, args)
                    if not allowed:
                        blocked = True
                        result = {"error": "blocked by hook", "reason": reason}
                        if verbose:
                            print(f"Hook blocked: {reason}")
                    elif tool_name not in tools_map:
                        # Model asked for a tool that isn't available here (e.g.
                        # spawn beyond max_depth). Return an error, don't crash.
                        blocked = True
                        result = {"error": f"unknown tool: {tool_name}"}
                        if verbose:
                            print(f"Unknown tool: {tool_name}")
                    else:
                        # 3) Execute, then PostToolUse hooks may rewrite the result.
                        result = tools_map[tool_name](**args)
                        result = hooks.run_post(tool_name, args, result)

                if verbose:
                    print(f"Tool result: {json.dumps(result, indent=2)}")

                # Record a compact transcript entry for session resume.
                transcript.append({"role": "assistant", "content": f"called {tool_name}({args})"})
                transcript.append({"role": "tool", "content": json.dumps(result)[:400]})

                # Immediately exit on finish
                if not blocked and tool_name == "finish":
                    transcript.append({"role": "assistant", "content": result["final_answer"]})
                    if session:
                        path = SESSIONS.save(session, transcript)
                        if verbose:
                            print(f"[session] saved -> {path}")
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

    if session:
        SESSIONS.save(session, transcript)
    raise RuntimeError("Max iterations reached without finishing the task.")
    


if __name__ == "__main__":
    mode = os.getenv("AGENT_PERMISSION_MODE", "auto")
    session = os.getenv("AGENT_SESSION", "demo")
    resume = os.getenv("AGENT_RESUME") == "1"

    use_mcp = os.getenv("AGENT_MCP") == "1"
    use_subagent = os.getenv("AGENT_SUBAGENT") == "1"

    # Default task exercises skills. AGENT_MCP=1 uses an external MCP tool;
    # AGENT_SUBAGENT=1 delegates a subtask to a child agent.
    if use_subagent:
        task = ("Delegate to a subagent the task of creating greet.txt containing "
                "'hi from the subagent'. When it reports done, finish with its result.")
    elif use_mcp:
        task = "Use the mcp__add tool to add 21 and 21, then finish with the result."
    else:
        task = (
            "List your available skills, then load the 'python-style' skill and create "
            "greet.py with a function that returns a greeting, following that skill. "
            "Finish when done."
        )

    print(f"\n{'=' * 80}")
    print(f"Permission mode: {mode}   (AGENT_PERMISSION_MODE=auto|default|plan)")
    print(f"Session: {session}   resume={resume}   (AGENT_SESSION=name AGENT_RESUME=1)")
    print(f"Context budget: {os.getenv('AGENT_MAX_CONTEXT_CHARS', '8000')} chars "
          f"(try AGENT_MAX_CONTEXT_CHARS=5000 to see compaction; keep it above the "
          f"~3000-char system+memory floor)")
    print(f"Task: {task}")
    print(f"{'=' * 80}\n")

    # Start clean so the outcome reflects THIS run's mode, not a leftover file.
    (WORKSPACE / "greet.py").unlink(missing_ok=True)

    # Attach lifecycle hooks: a timing logger (pre+post) and a usage counter (post).
    from hooks import HookManager, TimingLogger, make_counter
    timer = TimingLogger()
    tool_counts = {}
    hooks = HookManager(
        pre=[timer.pre],
        post=[timer.post, make_counter(tool_counts)],
    )

    # Optionally connect an external MCP server and mount its tools.
    extra_tools, extra_schemas, mcp = None, None, None
    if use_mcp:
        import sys
        from mcp_client import MCPClient, to_openai_schemas, make_proxies
        mcp = MCPClient([sys.executable, str(PROJECT_ROOT / "mcp_servers" / "echo_server.py")]).start()
        mcp_tools = mcp.list_tools()
        print(f"[mcp] connected; tools: {[t['name'] for t in mcp_tools]}")
        extra_schemas = to_openai_schemas(mcp_tools)
        extra_tools = make_proxies(mcp, mcp_tools)

    try:
        result = run_agent(task, max_iterations=8, verbose=True, hooks=hooks,
                           session=session, resume=resume,
                           extra_tools=extra_tools, extra_schemas=extra_schemas)
        print(f"\nFinal result: {result}")
    except Exception as e:
        print(f"\nError: {e}")
    finally:
        if mcp:
            mcp.stop()

    print(f"Tool usage (from counter hook): {tool_counts}")
    created = (WORKSPACE / "greet.py").exists()
    print(f"greet.py created? {created}   (expected: False in plan mode, True in auto)")

    # Show that memory persisted to disk between runs.
    print(f"\nMEMORY.md now contains:\n{MEMORY.load_memory() or '(empty)'}")

