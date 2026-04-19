"""
Execute API endpoints.
"""

import threading
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models.database import get_db, Workflow, Execution
from core.engine import WorkflowEngine
import plugins

router = APIRouter(prefix="/api/workflows", tags=["execute"])

# Store running executions
running_executions = {}


@router.post("/{workflow_id}/execute", response_model=dict)
def execute_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Execute a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if already running
    if workflow_id in running_executions and running_executions[workflow_id].is_alive():
        raise HTTPException(status_code=400, detail="Workflow is already running")

    # Create execution record
    execution = Execution(
        workflow_id=workflow_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    execution_id = execution.id

    # Run in background thread
    def run_workflow():
        try:
            engine = WorkflowEngine(workflow.config)
            context = engine.run()

            # Update execution record
            results = context.get_all_results()
            statuses = [r.status.value for r in results.values()]
            overall_status = "failed" if "failed" in statuses else "success"

            from datetime import datetime
            finished_at = datetime.utcnow()
            duration = int((finished_at - execution.started_at).total_seconds())

            db_exec = db.query(Execution).filter(Execution.id == execution_id).first()
            db_exec.status = overall_status
            db_exec.finished_at = finished_at
            db_exec.duration = duration
            db_exec.result = {
                "tasks": {
                    tid: {
                        "status": r.status.value,
                        "duration": r.duration,
                        "error": r.error,
                    }
                    for tid, r in results.items()
                }
            }
            db.commit()

        except Exception as e:
            db_exec = db.query(Execution).filter(Execution.id == execution_id).first()
            db_exec.status = "failed"
            db_exec.finished_at = datetime.utcnow()
            db_exec.result = {"error": str(e)}
            db.commit()

        finally:
            running_executions.pop(workflow_id, None)

    thread = threading.Thread(target=run_workflow)
    running_executions[workflow_id] = thread
    thread.start()

    return {
        "execution_id": execution_id,
        "status": "started",
        "message": f"Workflow execution started (ID: {execution_id})",
    }


@router.get("/{workflow_id}/status", response_model=dict)
def get_workflow_status(workflow_id: int, db: Session = Depends(get_db)):
    """Get current execution status for a workflow."""
    execution = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id)
        .order_by(Execution.started_at.desc())
        .first()
    )

    if not execution:
        return {"status": "not_run", "message": "Workflow has not been executed yet"}

    return {
        "execution_id": execution.id,
        "status": execution.status,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        "duration": execution.duration,
    }


@router.post("/{workflow_id}/stop", response_model=dict)
def stop_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Stop a running workflow."""
    if workflow_id not in running_executions:
        raise HTTPException(status_code=400, detail="Workflow is not running")

    # Note: This doesn't actually stop the thread, just marks it
    execution = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id, Execution.status == "running")
        .first()
    )
    if execution:
        execution.status = "cancelled"
        execution.finished_at = datetime.utcnow()
        db.commit()

    return {"message": "Stop requested"}
