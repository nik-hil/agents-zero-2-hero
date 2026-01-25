import os
from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
OPENROUTER_MODEL="x-ai/grok-4.1-fast"
# OPENROUTER_MODEL="openai/gpt-oss-120b"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set in environment variables.")

def get_client():
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        # Optional — helps with rankings on their leaderboard
        default_headers={
            # "HTTP-Referer": "https://your-app-or-github-link.com",  # ← change or remove
            "X-Title": "My Coding Agent Tutorial",
        }
    )
    return client

if __name__ == "__main__":
    response = get_client().chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello from Grok 4.1 Fast!"}
        ],
        temperature=0.7,
        max_tokens=100,
    )
    print(response.choices[0].message.content)