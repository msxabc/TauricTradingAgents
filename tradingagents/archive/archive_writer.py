"""Archive writer for daily and manual research workflows."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Optional

from tradingagents.research.serialization import stable_json_dumps


def slugify(value: str, *, fallback: str = "item") -> str:
    lowered = (value or "").strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return cleaned or fallback


class ArchiveWriter:
    """Create deterministic archive layouts and write stable artifacts."""

    def __init__(self, base_path: str = "research_archive"):
        self.base_path = Path(base_path)

    def create_daily_run_dir(
        self,
        report_date: str,
        *,
        overwrite_existing_run: bool = False,
    ) -> Path:
        root = self.base_path / "daily" / report_date
        root.mkdir(parents=True, exist_ok=True)

        if overwrite_existing_run:
            return self._ensure_dir(root / "run_001")

        run_index = 1
        while True:
            candidate = root / f"run_{run_index:03d}"
            if not candidate.exists():
                return self._ensure_dir(candidate)
            run_index += 1

    def create_manual_run_dir(
        self,
        report_date: str,
        ticker: str,
        slug: str,
        *,
        run_stamp: str,
        overwrite_existing_run: bool = False,
    ) -> Path:
        root = self.base_path / "manual" / report_date
        root.mkdir(parents=True, exist_ok=True)

        safe_ticker = slugify(ticker, fallback="ticker").upper()
        safe_slug = slugify(slug, fallback="report")
        base_name = f"{run_stamp}_{safe_ticker}_{safe_slug}"
        candidate = root / base_name

        if overwrite_existing_run:
            return self._ensure_dir(candidate)

        if not candidate.exists():
            return self._ensure_dir(candidate)

        suffix = 2
        while True:
            alt_candidate = root / f"{base_name}_{suffix:02d}"
            if not alt_candidate.exists():
                return self._ensure_dir(alt_candidate)
            suffix += 1

    def write_json(self, path: str | Path, payload: Any) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(stable_json_dumps(payload) + "\n", encoding="utf-8")
        return target

    def write_markdown(self, path: str | Path, content: str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_text(self, path: str | Path, content: str) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def write_artifact_bundle(
        self,
        run_dir: str | Path,
        *,
        json_artifacts: Optional[dict[str, Any]] = None,
        markdown_artifacts: Optional[dict[str, str]] = None,
        text_artifacts: Optional[dict[str, str]] = None,
    ) -> None:
        root = Path(run_dir)
        if json_artifacts:
            for relative_path, payload in json_artifacts.items():
                self.write_json(root / relative_path, payload)
        if markdown_artifacts:
            for relative_path, content in markdown_artifacts.items():
                self.write_markdown(root / relative_path, content)
        if text_artifacts:
            for relative_path, content in text_artifacts.items():
                self.write_text(root / relative_path, content)

    @staticmethod
    def _ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        return path
