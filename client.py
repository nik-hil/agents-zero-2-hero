"""client.py — one OpenAI-compatible client, two providers.

Both OpenRouter and DigitalOcean's Serverless Inference expose an
**OpenAI-compatible** API. That means the *same* `openai` SDK works for both —
the only things that change are:

    1. base_url   (where requests go)
    2. api_key    (which credential to send)
    3. model slug (each provider names models differently)

So "support both providers" is really just "pick one config bundle". We select
it with the LLM_PROVIDER env var and keep everything else identical.

    LLM_PROVIDER=openrouter   -> https://openrouter.ai/api/v1
    LLM_PROVIDER=digitalocean -> https://inference.do-ai.run/v1

Optionally override the model with LLM_MODEL (otherwise the provider default is
used).
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Each provider is just a bundle of (endpoint, which key to read, default model).
PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        # GPT-5.6 Luna: fast, cost-efficient, good for agentic/tool-calling loops.
        "default_model": "openai/gpt-5.6-luna",
    },
    "digitalocean": {
        # DigitalOcean Serverless Inference, OpenAI-compatible.
        # Key = a "model access key" created in the DO Control Panel.
        # NOTE: DO model IDs use hyphens, not slashes. Pick a model that supports
        # Chat Completions + tool calling (some newer DO models are Responses-API
        # only). Luna qualifies. Full catalog:
        # https://docs.digitalocean.com/products/inference/details/models/
        "base_url": "https://inference.do-ai.run/v1",
        "api_key_env": "DIGITALOCEAN_INFERENCE_KEY",
        # Same model as OpenRouter above, so switching providers changes only plumbing.
        "default_model": "openai-gpt-5.6-luna",
    },
}


def get_provider() -> str:
    """Which provider this run — default OpenRouter for backward compatibility."""
    return os.getenv("LLM_PROVIDER", "openrouter").lower()


def _config() -> dict:
    provider = get_provider()
    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown LLM_PROVIDER={provider!r}. "
            f"Choose one of: {', '.join(PROVIDERS)}"
        )
    return PROVIDERS[provider]


def get_model() -> str:
    """The model slug to use: explicit LLM_MODEL wins, else the provider default."""
    return os.getenv("LLM_MODEL") or _config()["default_model"]


def get_client() -> OpenAI:
    """An OpenAI SDK client pointed at the selected provider."""
    cfg = _config()
    api_key = os.getenv(cfg["api_key_env"])
    if not api_key:
        raise ValueError(
            f"{cfg['api_key_env']} is not set. "
            f"LLM_PROVIDER={get_provider()} needs it in your environment or .env file."
        )
    return OpenAI(
        base_url=cfg["base_url"],
        api_key=api_key,
        default_headers={"X-Title": "Agents Zero 2 Hero"},
    )


if __name__ == "__main__":
    print(f"Provider: {get_provider()}  |  Model: {get_model()}")
    response = get_client().chat.completions.create(
        model=get_model(),
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Say hello from {get_provider()}!"},
        ],
        temperature=0.7,
        max_tokens=100,
    )
    print(response.choices[0].message.content)
