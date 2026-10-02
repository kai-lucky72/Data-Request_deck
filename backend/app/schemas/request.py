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

    id: int  # Database request identifier, used in routes such as /requests/{id}.
    client_id: int  # Owner's database ID; clients only receive their own records.
    task_name: str  # What kind of robot task the requested dataset should contain.
    episodes_requested: int  # Required delivery quantity.
    deadline: date  # Requested completion date.
    notes: Optional[str]  # Optional instructions supplied during creation.
    status: RequestStatus  # Current workflow state, not the full state history.
    created_at: datetime  # When the request was first saved.
    updated_at: datetime  # Most recent database update time.
    
    # Pydantic reads these output fields from the SQLAlchemy model attributes.
    model_config = ConfigDict(from_attributes=True)


class RequestDetailResponse(RequestResponse):
    """Extended response for screens that need to show fulfillment progress."""

    assigned_count: int = 0  # Number of linked episodes; default is useful for empty requests.


