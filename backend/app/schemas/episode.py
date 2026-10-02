"""Validated API shapes for imported and searchable episode records."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.episode import Quality

class EpisodeResponse(BaseModel):
    """Fields the API returns when operators browse episodes or requests."""

    id:int
    episode_id:str
    robot_id:str
    task_name: str
    recorded_at: datetime
    duration_seconds: int
    operator_name: str | None
    quality: Quality
    assigned: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    """Small JSON request body for assigning one episode to a request."""

    episode_id: int  # Internal Episode.id, rather than the source system's text ID.

class AssignmentResponse(BaseModel):
    """Safe output fields describing who assigned an episode and when."""

    id: int
    request_id: int
    episode_id: int
    assigned_by_id: int # user who performed the action
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ImportIssue(BaseModel):
    """One skipped CSV row and a human-readable reason for skipping it."""

    row: int  # Physical CSV row number, including the header as row 1.
    episode_id: str | None = None  # Best-effort ID from that row, if present.
    reason: str  # Validation or database explanation suitable for operator feedback.

class ImportReport(BaseModel):
    """Complete summary returned after attempting a CSV import."""

    imported: int  # Number of rows successfully added during this run.
    skipped: int  # Number of rows not added, including duplicates and invalid data.
    issues: list[ImportIssue]  # Detail for each skipped row, so operators can repair the file.
