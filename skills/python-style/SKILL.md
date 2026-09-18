---
name: python-style
description: How to write clean, idiomatic Python for this project.
---
# Python style

Follow these when writing or editing Python in this repo:

- Use `snake_case` for functions and variables, `CapWords` for classes.
- Give every function a short docstring saying what it does.
- Prefer f-strings (`f"{x}"`) over `%` or `.format()`.
- Keep functions small and single-purpose; extract helpers when one grows.
- Add type hints where they clarify intent (args and return types).
- Guard runnable scripts with `if __name__ == "__main__":`.
