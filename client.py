import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-5.6-luna")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def get_client() -> OpenAI:
    """Create an OpenRouter client using the OpenAI-compatible API."""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. Create a local .env file or export it in your shell."
        )

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "X-Title": "Agents Zero 2 Hero",
        },
    )


if __name__ == "__main__":
    response = get_client().chat.completions.create(
        model=OPENROUTER_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello from GPT-5.6 Luna via OpenRouter!"},
        ],
        temperature=0.7,
        max_tokens=100,
    )
    print(response.choices[0].message.content)
