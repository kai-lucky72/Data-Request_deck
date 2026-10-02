"""Tests for CSV episode import functionality."""

import pytest

from app.services.import_episodes import import_episodes


def test_csv_import_reports_bad_rows_and_is_idempotent(db, tmp_path):
    """A repeat import skips an existing ID and malformed rows are explained."""
    csv_file = tmp_path / "episodes.csv"
    csv_file.write_text(
        "episode_id,robot_id,task_name,recorded_at,duration_seconds,operator_name,quality\n"
        "EP-1,arm-1,pick cup,2026-09-01T00:00:00,20,Ada,GOOD\n"
        "EP-2,arm-1,,2026-09-01T00:00:00,20,Ada,usable\n",
        encoding="utf-8",
    )
    first = import_episodes(db, csv_file)
    second = import_episodes(db, csv_file)
    assert first["imported"] == 1 and first["skipped"] == 1
    assert "task_name" in first["issues"][0]["reason"]
    assert second["imported"] == 0
    assert "duplicate episode_id" in second["issues"][0]["reason"]
