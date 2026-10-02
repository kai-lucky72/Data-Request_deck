"""Database-side summary queries for episode and request operations."""

from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, cast, Integer, func
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.episode import Episode, Quality
from app.models.request import Request, RequestStatus, RequestStatusHistory
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# GET reads data and does not mutate rows; operators/admins only may request it.
@router.get("")
def get_analytics(
    db: Annotated[Session, Depends(get_db)],  # Inject one database session for all grouped queries.
    _user: Annotated[User, Depends(require_roles(UserRole.operator, UserRole.admin))],  # Enforce role access before querying.
    start_date: date = Query(...),  # Required URL parameter, parsed as a calendar date.
    end_date: date = Query(...),  # Required and inclusive; reversed ranges return HTTP 400.
):
    """Return grouped counts and median delivery time for an inclusive date range.

    Aggregation and grouping run in SQL so the API does not load millions of rows
    into Python. Indexes on recorded_at, status, and history request_id help these
    queries; at very large scale, time partitioning and pre-aggregated daily tables
    would keep dashboard reads fast.
    """
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be on or after start_date")
    
    # Convert the inclusive calendar dates to a half-open timestamp range:
    # start <= recorded_at < midnight after end_date. This includes all of end_date.
    start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    # SQLite's CAST(... AS DATE) has different return behavior from PostgreSQL;
    # date() gives the same YYYY-MM-DD grouping key on both supported engines.
    day_expression = func.date(Episode.recorded_at)
    per_day_robot = db.query(
        day_expression.label("day"),
        Episode.robot_id,
        func.count(Episode.id).label("count"),
    ).filter(Episode.recorded_at >= start, Episode.recorded_at < end).group_by(
        day_expression, Episode.robot_id
    ).order_by(day_expression, Episode.robot_id).all()

    # Group request rows in the database; the range refers to when each request began.
    status_counts = db.query(Request.status, func.count(Request.id)).filter(
        Request.created_at >= start, Request.created_at < end
    ).group_by(Request.status).all()
    
    # Build one SQL subquery with each request's first delivered timestamp.
    # CASE returns the timestamp only on delivered-history rows; MIN ignores NULLs.
    delivered = db.query(
        Request.id.label("request_id"),
        func.min(case((RequestStatusHistory.to_status == RequestStatus.delivered, RequestStatusHistory.changed_at))).label("delivered_at"),
    ).join(RequestStatusHistory, RequestStatusHistory.request_id == Request.id).filter(
        Request.created_at >= start, Request.created_at < end
    ).group_by(Request.id).subquery()
    
    # A matching subquery gets the original submitted event for each request.
    submitted_times = db.query(
        Request.id.label("request_id"),
        func.min(case((RequestStatusHistory.to_status == RequestStatus.submitted, RequestStatusHistory.changed_at))).label("submitted_at"),
    ).join(RequestStatusHistory, RequestStatusHistory.request_id == Request.id).filter(
        Request.created_at >= start, Request.created_at < end
    ).group_by(Request.id).subquery()
    if db.get_bind().dialect.name == "sqlite":
        # SQLite lacks percentile_cont, so calculate the middle row(s) with window
        # functions. The durations and median still stay inside the database.
        duration_seconds = (
            func.julianday(delivered.c.delivered_at) - func.julianday(submitted_times.c.submitted_at)
        ) * 86400
        ranked_durations = db.query(
            duration_seconds.label("seconds"),
            func.row_number().over(order_by=duration_seconds).label("row_number"),
            func.count().over().label("row_count"),
        ).join(submitted_times, submitted_times.c.request_id == delivered.c.request_id).subquery()
        
        # For an odd number of rows, both bounds select the same middle row. For
        # an even number, the bounds select the two middle rows and AVG combines them.
        middle_lower = cast((ranked_durations.c.row_count + 1) / 2, Integer)
        middle_upper = cast(ranked_durations.c.row_count / 2, Integer) + 1
        median_delivery_seconds = db.query(func.avg(ranked_durations.c.seconds)).filter(
            ranked_durations.c.row_number >= middle_lower,
            ranked_durations.c.row_number <= middle_upper,
        ).scalar()
    else:
        # PostgreSQL provides an ordered-set aggregate for an exact median.
        # PostgreSQL can subtract timestamps and calculate an exact median directly.
        duration_seconds = func.extract("epoch", delivered.c.delivered_at - submitted_times.c.submitted_at)
        median_delivery_seconds = db.query(func.percentile_cont(0.5).within_group(duration_seconds)).join(
            submitted_times, submitted_times.c.request_id == delivered.c.request_id
        ).scalar()

    # Count only good episodes in SQL, sort largest task counts first, and keep five.
    top_tasks = db.query(Episode.task_name, func.count(Episode.id).label("count")).filter(
        Episode.quality == Quality.good, Episode.recorded_at >= start, Episode.recorded_at < end
    ).group_by(Episode.task_name).order_by(func.count(Episode.id).desc()).limit(5).all()

    return {
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "episodes_per_day_per_robot": [
            {"date": row.day.isoformat() if hasattr(row.day, "isoformat") else str(row.day),
             "robot_id": row.robot_id, "count": row.count} for row in per_day_robot
        ],
        "requests_by_status": {status.value: count for status, count in status_counts},
        "median_submitted_to_delivered_seconds": float(median_delivery_seconds) if median_delivery_seconds is not None else None,
        "top_5_good_episode_tasks": [{"task_name": task, "count": count} for task, count in top_tasks],
    }
