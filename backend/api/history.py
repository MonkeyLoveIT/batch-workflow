"""
History API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.models.database import get_db, Execution, Workflow

router = APIRouter(prefix="/api/history", tags=["history"])


@router.get("", response_model=List[dict])
def list_executions(
    limit: int = 50,
    workflow_id: int = None,
    db: Session = Depends(get_db)
):
    """List execution history."""
    query = db.query(Execution)

    if workflow_id:
        query = query.filter(Execution.workflow_id == workflow_id)

    executions = query.order_by(Execution.started_at.desc()).limit(limit).all()

    result = []
    for e in executions:
        workflow = db.query(Workflow).filter(Workflow.id == e.workflow_id).first()
        result.append({
            "id": e.id,
            "workflow_id": e.workflow_id,
            "workflow_name": workflow.name if workflow else "Unknown",
            "status": e.status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "finished_at": e.finished_at.isoformat() if e.finished_at else None,
            "duration": e.duration,
        })

    return result


@router.get("/stats", response_model=dict)
def get_stats(db: Session = Depends(get_db)):
    """Get execution statistics."""
    # Total executions
    total = db.query(Execution).count()

    # By status
    success = db.query(Execution).filter(Execution.status == "success").count()
    failed = db.query(Execution).filter(Execution.status == "failed").count()
    running = db.query(Execution).filter(Execution.status == "running").count()

    # Recent trend (last 7 days)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent = db.query(Execution).filter(Execution.started_at >= seven_days_ago).all()

    daily_stats = {}
    for e in recent:
        day = e.started_at.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = {"success": 0, "failed": 0}
        if e.status in ("success", "failed"):
            daily_stats[day][e.status] += 1

    return {
        "total": total,
        "success": success,
        "failed": failed,
        "running": running,
        "success_rate": round(success / total * 100, 1) if total > 0 else 0,
        "daily_stats": daily_stats,
    }


@router.get("/{execution_id}", response_model=dict)
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    """Get execution details."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Execution not found")

    workflow = db.query(Workflow).filter(Workflow.id == execution.workflow_id).first()

    return {
        "id": execution.id,
        "workflow_id": execution.workflow_id,
        "workflow_name": workflow.name if workflow else "Unknown",
        "status": execution.status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "duration": execution.duration,
        "result": execution.result,
        "logs": execution.logs,
    }
