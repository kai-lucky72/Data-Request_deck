"""CSV parser and idempotent database importer for recording-system exports."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.models.episode import Episode, Quality


def _clean(value: Any) -> str:
    """Trim whitespace and normalize null-like CSV values to an empty string."""
    if value is None:
        return ""
    cleaned = str(value).strip()
    return "" if cleaned.lower() in {"", "na", "n/a", "null", "none", "-"} else cleaned


def _parse_time(value: str) -> datetime:
    """Parse ISO timestamps, including a trailing Z, and normalize to UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def import_episodes(db: Session, csv_path: str | Path) -> dict[str, Any]:
    """Import valid unique rows and return counts plus a reason for every skip.

    A unique database constraint is the final protection against duplicate IDs;
    this importer also checks existing rows first so repeat imports are readable.
    """
    imported = 0
    issues: list[dict[str, Any]] = []
    path = Path(csv_path)

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if not reader.fieldnames:
            return {"imported": 0, "skipped": 0, "issues": []}

        # Normalize headers because human-edited exports often vary in case/spacing.
        for row_number, raw in enumerate(reader, start=2):
            row = {str(key).strip().lower(): value for key, value in raw.items() if key}
            episode_id = _clean(row.get("episode_id"))
            try:
                required = ["episode_id", "robot_id", "task_name", "recorded_at", "duration_seconds", "quality"]
                missing = [key for key in required if not _clean(row.get(key))]
                if missing:
                    raise ValueError("missing required value(s): " + ", ".join(missing))
                if db.query(Episode.id).filter(Episode.episode_id == episode_id).first():
                    raise ValueError("duplicate episode_id already exists in database")

                # Normalize common inconsistent capitalization and extra spaces.
                quality_text = _clean(row["quality"]).lower()
                quality = Quality(quality_text)
                duration = int(float(_clean(row["duration_seconds"])))
                if duration <= 0:
                    raise ValueError("duration_seconds must be greater than zero")
                task_name = " ".join(_clean(row["task_name"]).split())

                # A savepoint isolates this row: a bad record cannot erase earlier good rows.
                with db.begin_nested():
                    db.add(Episode(
                        episode_id=episode_id,
                        robot_id=_clean(row["robot_id"]).upper(),
                        task_name=task_name,
                        recorded_at=_parse_time(_clean(row["recorded_at"])),
                        duration_seconds=duration,
                        operator_name=_clean(row.get("operator_name")) or None,
                        quality=quality,
                    ))
                    db.flush()
                imported += 1
            except (ValueError, TypeError, KeyError) as error:
                issues.append({"row": row_number, "episode_id": episode_id or None, "reason": str(error)})
            except Exception as error:
                # The nested transaction above rolls back only this row.
                issues.append({"row": row_number, "episode_id": episode_id or None, "reason": f"database error: {error}"})

    # Persist any rows that were successfully flushed after row-level validation.
    db.commit()
    return {"imported": imported, "skipped": len(issues), "issues": issues}
