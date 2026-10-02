"""Pydantic input/output contracts for dataset requests."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.request import RequestStatus

class RequestCreate(BaseModel):
    """Fields a client sends when asking for a dataset."""

    task_name: str = Field(..., min_length=1, max_length=255)
    episodes_requested: int = Field(..., gt=0)
    deadline: date
    notes: Optional[str] = None

class RequestUpdateStatus(BaseModel):
    """Fields sent when asking the API to move a request to another state."""

    status: RequestStatus 
    note: Optional[str] = None

    
class RequestResponse(BaseModel):
    """Fields returned to clients and staff after reading or changing a request."""

    id: int
    client_id: int
    client_name: Optional[str] = None
    task_name: str
    episodes_requested: int
    assigned_count: int = 0
    deadline: date
    notes: Optional[str] = None
    status: RequestStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RequestDetailResponse(RequestResponse):
    """Extended response for screens that need to show fulfillment progress."""

    assigned_count: int = 0  # Number of linked episodes; default is useful for empty requests.


class StatusHistoryResponse(BaseModel):
    """One row of a request's status history."""

    id: int
    from_status: Optional[RequestStatus] = None
    to_status: RequestStatus
    changed_by_id: Optional[int] = None
    changed_at: datetime
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


