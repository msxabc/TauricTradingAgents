import json

import pytest

from tradingagents.research.config_loader import load_workflow_config


@pytest.mark.unit
class TestConfigLoader:
    def test_loads_default_job_config_without_file(self):
        config = load_workflow_config("daily_signal_research_book")

        assert config["job_name"] == "daily_signal_research_book"
        assert config["job"]["run"]["max_reports"] == 5
        assert config["job"]["social_scanner"]["endpoints"]["signals"] == "/v1/signals"
        assert config["llm_provider"] == "openai"

    def test_json_overlay_and_cli_overrides_apply_in_order(self, tmp_path):
        config_file = tmp_path / "daily.json"
        config_file.write_text(
            json.dumps(
                {
                    "llm_provider": "anthropic",
                    "daily_signal_research_book": {
                        "run": {"max_reports": 7},
                        "social_scanner": {"timeout_seconds": 20},
                    },
                }
            ),
            encoding="utf-8",
        )

        config = load_workflow_config(
            "daily_signal_research_book",
            config_path=str(config_file),
            cli_overrides={
                "llm_provider": "google",
                "job": {"run": {"max_reports": 3}},
            },
        )

        assert config["llm_provider"] == "google"
        assert config["job"]["run"]["max_reports"] == 3
        assert config["job"]["social_scanner"]["timeout_seconds"] == 20

    def test_env_placeholders_expand(self, tmp_path):
        config_file = tmp_path / "scanner.json"
        config_file.write_text(
            json.dumps(
                {
                    "manual_research_report": {
                        "social_scanner": {
                            "base_url": "${SOCIAL_SCANNER_BASE_URL}",
                            "api_key": "${SOCIAL_SCANNER_API_KEY}",
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        config = load_workflow_config(
            "manual_research_report",
            config_path=str(config_file),
            environ={
                "SOCIAL_SCANNER_BASE_URL": "http://127.0.0.1:3001",
                "SOCIAL_SCANNER_API_KEY": "scanner-secret",
            },
        )

        assert config["job"]["social_scanner"]["base_url"] == "http://127.0.0.1:3001"
        assert config["job"]["social_scanner"]["api_key"] == "scanner-secret"

    def test_alias_maps_to_canonical_job_name(self):
        config = load_workflow_config("daily_top5_social_research")
        assert config["job_name"] == "daily_signal_research_book"

    def test_unknown_job_raises(self):
        with pytest.raises(ValueError):
            load_workflow_config("unknown_job")

