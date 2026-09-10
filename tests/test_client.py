"""Unit tests for client.py — the provider/model selection layer.

These run fully offline: no API key, no network. We only check that the right
base_url / model / errors come out for each LLM_PROVIDER + LLM_MODEL combo.

Run:
    python -m unittest discover -s tests
"""
import os
import unittest
from unittest import mock

import client


class ProviderSelection(unittest.TestCase):
    def _run(self, overrides):
        # Blank the four vars, then set only what the test wants.
        to_clear = ["LLM_PROVIDER", "LLM_MODEL",
                    "OPENROUTER_API_KEY", "DIGITALOCEAN_INFERENCE_KEY"]
        with mock.patch.dict(os.environ, {}, clear=False):
            for k in to_clear:
                os.environ.pop(k, None)
            os.environ.update(overrides)
            return client.get_provider(), client.get_model()

    def test_default_provider_is_openrouter(self):
        provider, model = self._run({"OPENROUTER_API_KEY": "x"})
        self.assertEqual(provider, "openrouter")
        self.assertEqual(model, "openai/gpt-5.6-luna")

    def test_digitalocean_selected(self):
        provider, model = self._run({
            "LLM_PROVIDER": "digitalocean",
            "DIGITALOCEAN_INFERENCE_KEY": "x",
        })
        self.assertEqual(provider, "digitalocean")
        self.assertEqual(model, "openai-gpt-5.6-luna")

    def test_llm_model_override_wins(self):
        _, model = self._run({
            "LLM_PROVIDER": "digitalocean",
            "LLM_MODEL": "glm-5.2",
            "DIGITALOCEAN_INFERENCE_KEY": "x",
        })
        self.assertEqual(model, "glm-5.2")

    def test_unknown_provider_raises(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "bogus"}, clear=False):
            with self.assertRaises(ValueError):
                client.get_model()


class ClientConstruction(unittest.TestCase):
    def test_openrouter_base_url_and_key(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_PROVIDER", None)
            os.environ["OPENROUTER_API_KEY"] = "sk-test"
            c = client.get_client()
        self.assertEqual(str(c.base_url).rstrip("/"), "https://openrouter.ai/api/v1")

    def test_digitalocean_base_url(self):
        with mock.patch.dict(os.environ, {
            "LLM_PROVIDER": "digitalocean",
            "DIGITALOCEAN_INFERENCE_KEY": "do-test",
        }, clear=False):
            c = client.get_client()
        self.assertEqual(str(c.base_url).rstrip("/"), "https://inference.do-ai.run/v1")

    def test_missing_key_raises_with_helpful_message(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "digitalocean"}, clear=False):
            os.environ.pop("DIGITALOCEAN_INFERENCE_KEY", None)
            with self.assertRaises(ValueError) as ctx:
                client.get_client()
        self.assertIn("DIGITALOCEAN_INFERENCE_KEY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
