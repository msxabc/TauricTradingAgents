import json

import pytest

from tradingagents.archive.archive_writer import ArchiveWriter, slugify


@pytest.mark.unit
class TestArchiveWriter:
    def test_daily_run_dirs_increment_without_overwrite(self, tmp_path):
        writer = ArchiveWriter(str(tmp_path / "research_archive"))

        first = writer.create_daily_run_dir("2026-05-11")
        second = writer.create_daily_run_dir("2026-05-11")

        assert first.name == "run_001"
        assert second.name == "run_002"

    def test_manual_run_dirs_append_suffix_on_collision(self, tmp_path):
        writer = ArchiveWriter(str(tmp_path / "research_archive"))

        first = writer.create_manual_run_dir(
            "2026-05-11",
            "GOOGL",
            "google report",
            run_stamp="143022",
        )
        second = writer.create_manual_run_dir(
            "2026-05-11",
            "GOOGL",
            "google report",
            run_stamp="143022",
        )

        assert first.name == "143022_GOOGL_google-report"
        assert second.name == "143022_GOOGL_google-report_02"

    def test_write_json_is_deterministic(self, tmp_path):
        writer = ArchiveWriter(str(tmp_path / "research_archive"))
        output = writer.write_json(tmp_path / "bundle" / "artifact.json", {"z": 1, "a": {"d": 4, "b": 2}})

        assert output.exists()
        parsed = json.loads(output.read_text(encoding="utf-8"))
        assert parsed == {"a": {"b": 2, "d": 4}, "z": 1}

    def test_slugify_falls_back_when_empty(self):
        assert slugify("  ") == "item"

