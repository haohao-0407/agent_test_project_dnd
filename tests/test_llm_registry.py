import unittest

from playscript_agent.llm.registry import resolve_llm_config


class LlmRegistryTest(unittest.TestCase):
    def test_resolves_openai_compatible_config_from_env(self) -> None:
        config = {
            "models": {
                "player": {
                    "model": "openai:deepseek-chat",
                    "api_key_env": "DEEPSEEK_API_KEY",
                    "base_url_env": "DEEPSEEK_BASE_URL",
                    "temperature": 0.8,
                    "kwargs": {"timeout": 30},
                }
            }
        }
        env = {
            "DEEPSEEK_API_KEY": "sk-test",
            "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
        }

        model, kwargs = resolve_llm_config("player", config, env)

        self.assertEqual(model, "openai:deepseek-chat")
        self.assertEqual(kwargs["api_key"], "sk-test")
        self.assertEqual(kwargs["base_url"], "https://api.deepseek.com")
        self.assertEqual(kwargs["temperature"], 0.8)
        self.assertEqual(kwargs["timeout"], 30)

    def test_supports_legacy_string_config(self) -> None:
        model, kwargs = resolve_llm_config(
            "dm",
            {"models": {"dm": "anthropic:claude-sonnet-4-5"}},
            {},
        )

        self.assertEqual(model, "anthropic:claude-sonnet-4-5")
        self.assertEqual(kwargs, {})

    def test_falls_back_to_default_role(self) -> None:
        model, kwargs = resolve_llm_config(
            "summarizer",
            {
                "models": {
                    "default": {
                        "model": "openai:gpt-4o-mini",
                        "api_key_env": "OPENAI_API_KEY",
                    }
                }
            },
            {"OPENAI_API_KEY": "sk-default"},
        )

        self.assertEqual(model, "openai:gpt-4o-mini")
        self.assertEqual(kwargs["api_key"], "sk-default")

    def test_resolves_dollar_env_references_in_values(self) -> None:
        model, kwargs = resolve_llm_config(
            "dm",
            {
                "models": {
                    "dm": {
                        "model": "${DM_MODEL}",
                        "base_url": "$DM_BASE_URL",
                    }
                }
            },
            {
                "DM_MODEL": "openai:custom-model",
                "DM_BASE_URL": "https://llm-gateway.example/v1",
            },
        )

        self.assertEqual(model, "openai:custom-model")
        self.assertEqual(kwargs["base_url"], "https://llm-gateway.example/v1")


if __name__ == "__main__":
    unittest.main()
