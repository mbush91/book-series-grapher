from book_series_grapher.settings import Settings


def test_agent_model_settings_exposes_provider_portable_effort() -> None:
    settings = Settings(model_name="openai:gpt-5.6-sol", model_effort="high", _env_file=None)

    assert settings.agent_model_settings() == {"thinking": "high"}
