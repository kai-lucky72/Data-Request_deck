from fastapi import HTTPException,status
from sqlalchemy.orm import Session

from app.models.user import UserRole,User
from app.models.request import Request,RequestStatus,RequestStatusHistory

# A directed workflow map: current state -> proposed next state -> allowed roles.
# For example, only an operator/admin can move submitted to in_progress.
ALLOWED_TRANSITIONS={
    """Map of allowed state transitions by role"""
    RequestStatus.submitted:{
        RequestStatus.in_progress:{UserRole.operator,UserRole.admin},
    },
    RequestStatus.in_progress:{
        RequestStatus.delivered:{UserRole.operator,UserRole.admin},
    },
    RequestStatus.delivered:{
        RequestStatus.accepted:{UserRole.client},
        RequestStatus.rejected:{UserRole.client},
    },
    RequestStatus.rejected:{
        RequestStatus.in_progress:{UserRole.operator,UserRole.admin},
    },
    RequestStatus.accepted:{},
}

def change_request_status(
    db: Session,
    request: Request,
    new_status:RequestStatus,
    user:User,
    note:Optional[str]=None,
)->Request:
    """Validate authorization, record the audit row, then persist the new status."""
    # Save the old state before changing the ORM object so history has both values.
    current=request.status
    
    # If this state pair is absent, the workflow does not allow the requested move.
    allowed = ALLOWED_TRANSITIONS.get(current,{})
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot transition from '{current.value}' to '{new_status.value}'"
        )
        
    # A valid state change can still be forbidden to a role that does not own it.
    if user.role not in allowed[new_status]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role.value}' cannot perform this transition",
        )
        
    # Role permission alone is insufficient for clients: they may act only on
    # requests whose owner ID matches their authenticated database user ID.
    if user.role == UserRole.client and request.client_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own requests",
        )

    # Delivery is only valid after operations attached the requested quantity.
    if new_status == RequestStatus.delivered:
        from app.models.assignment import Assignment
        # Count in SQL instead of loading every assignment row into Python.
        assigned_count = db.query(Assignment.id).filter(Assignment.request_id == request.id).count()
        if assigned_count < request.episodes_requested:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Assign at least {request.episodes_requested} episodes before delivery (currently {assigned_count})",
            )
        
    # The audit row and current request update are committed in one transaction.
    history = RequestStatusHistory(
        request_id=request.id,
        from_status=current,
        to_status=new_status,
        changed_by_id=user.id,
        note=note
    )
    
    db.add(history)
    
    request.status= new_status
    db.add(request)
    db.commit()
    db.refresh(request)
    
    
    return request