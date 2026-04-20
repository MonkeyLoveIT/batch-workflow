"""
Workflow API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import yaml
import json
import os

from backend.models.database import get_db, Workflow, Execution, Folder

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

# Workflow storage directory
WORKFLOWS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "workflows")
os.makedirs(WORKFLOWS_DIR, exist_ok=True)


@router.get("", response_model=List[dict])
def list_workflows(db: Session = Depends(get_db)):
    """List all workflows."""
    workflows = db.query(Workflow).order_by(Workflow.updated_at.desc()).all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "folder": w.folder,
            "created_at": w.created_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workflows
    ]


@router.get("/folders", response_model=list)
def list_folders(db: Session = Depends(get_db)):
    """Get all unique folder paths as a tree structure."""
    # Get folders from Folder table
    folder_rows = db.query(Folder.path).distinct().all()
    folder_paths = set(f[0] for f in folder_rows if f[0])

    # Also get folders from workflows
    workflow_folders = db.query(Workflow.folder).distinct().all()
    folder_paths.update(f[0] for f in workflow_folders if f[0])

    folder_paths = sorted(folder_paths)

    # Build tree structure
    def build_tree(paths):
        tree = []
        for path in paths:
            parts = path.split("/")
            current = tree
            for i, part in enumerate(parts):
                # Find existing node
                existing = next((n for n in current if n["name"] == part), None)
                if not existing:
                    existing = {"name": part, "path": "/".join(parts[:i + 1]), "children": []}
                    current.append(existing)
                current = existing["children"]
        return tree

    return build_tree(folder_paths)


@router.post("/folders", response_model=dict)
def create_folder(data: dict, db: Session = Depends(get_db)):
    """Create a new folder."""
    path = data.get("path", "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="Folder path is required")

    # Check if folder already exists
    existing = db.query(Folder).filter(Folder.path == path).first()
    if existing:
        raise HTTPException(status_code=400, detail="Folder already exists")

    folder = Folder(path=path)
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return {"id": folder.id, "path": folder.path, "message": "Folder created successfully"}


@router.delete("/folders/{folder_path}", response_model=dict)
def delete_folder(folder_path: str, db: Session = Depends(get_db)):
    """Delete a folder and all its subfolders and workflows."""
    # Find the folder
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Delete all workflows in this folder and subfolders
    db.query(Execution).filter(Execution.workflow_id.in_(
        db.query(Workflow.id).filter(Workflow.folder.startswith(folder_path + "/"))
    )).delete(synchronize_session=False)
    db.query(Workflow).filter(Workflow.folder.startswith(folder_path + "/")).delete(synchronize_session=False)
    db.query(Workflow).filter(Workflow.folder == folder_path).delete(synchronize_session=False)

    # Delete all folders that start with this path (including subfolders)
    db.query(Folder).filter(Folder.path.startswith(folder_path + "/")).delete(synchronize_session=False)
    db.delete(folder)
    db.commit()

    return {"message": "Folder deleted successfully"}


@router.put("/folders/{folder_path}", response_model=dict)
def rename_folder(folder_path: str, data: dict, db: Session = Depends(get_db)):
    """Rename a folder and update all related paths."""
    new_name = data.get("new_name", "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="New folder name is required")

    # Find the folder
    folder = db.query(Folder).filter(Folder.path == folder_path).first()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")

    # Calculate new path
    if "/" in folder_path:
        parent_path = folder_path.rsplit("/", 1)[0]
        new_path = f"{parent_path}/{new_name}"
    else:
        new_path = new_name

    # Check if new path already exists
    existing = db.query(Folder).filter(Folder.path == new_path).first()
    if existing:
        raise HTTPException(status_code=400, detail="Folder already exists")

    # Update all subfolder paths
    subfolders = db.query(Folder).filter(Folder.path.startswith(folder_path + "/")).all()
    for subfolder in subfolders:
        subfolder.path = new_path + subfolder.path[len(folder_path):]

    # Update all workflow folders
    workflows = db.query(Workflow).filter(Workflow.folder.startswith(folder_path + "/")).all()
    for wf in workflows:
        wf.folder = new_path + wf.folder[len(folder_path):]

    # Update the folder itself
    folder.path = new_path

    db.commit()

    return {"message": f"Folder renamed to {new_path}"}


@router.get("/{workflow_id}", response_model=dict)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Get workflow by ID."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "folder": workflow.folder,
        "config": workflow.config,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


@router.post("", response_model=dict)
def create_workflow(data: dict, db: Session = Depends(get_db)):
    """Create a new workflow."""
    workflow = Workflow(
        name=data["name"],
        description=data.get("description", ""),
        folder=data.get("folder", ""),
        config=data["config"],
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    # Save as YAML file
    _save_workflow_yaml(workflow)

    return {
        "id": workflow.id,
        "name": workflow.name,
        "message": "Workflow created successfully",
    }


@router.put("/{workflow_id}", response_model=dict)
def update_workflow(workflow_id: int, data: dict, db: Session = Depends(get_db)):
    """Update a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow.name = data.get("name", workflow.name)
    workflow.description = data.get("description", workflow.description)
    workflow.folder = data.get("folder", workflow.folder)
    workflow.config = data.get("config", workflow.config)

    db.commit()
    db.refresh(workflow)

    # Update YAML file
    _save_workflow_yaml(workflow)

    return {
        "id": workflow.id,
        "name": workflow.name,
        "message": "Workflow updated successfully",
    }


@router.delete("/{workflow_id}", response_model=dict)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Delete a workflow."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Delete related executions first
    db.query(Execution).filter(Execution.workflow_id == workflow_id).delete()

    # Delete YAML file
    yaml_path = os.path.join(WORKFLOWS_DIR, f"workflow_{workflow_id}.yaml")
    if os.path.exists(yaml_path):
        os.remove(yaml_path)

    db.delete(workflow)
    db.commit()

    return {"message": "Workflow deleted successfully"}


@router.post("/import", response_model=dict)
async def import_workflow(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Import workflow from YAML file."""
    content = await file.read()

    try:
        config = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

    if not config.get("name"):
        raise HTTPException(status_code=400, detail="Workflow name is required")
    if not config.get("tasks"):
        raise HTTPException(status_code=400, detail="Workflow tasks are required")

    # Get folder from config, default to empty
    folder = config.get("folder", "")

    # Check for duplicate name within same folder
    existing = db.query(Workflow).filter(
        Workflow.name == config["name"],
        Workflow.folder == folder
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Workflow with name '{config['name']}' already exists in folder '{folder or 'root'}")

    # Create folder if it doesn't exist
    if folder:
        existing_folder = db.query(Folder).filter(Folder.path == folder).first()
        if not existing_folder:
            new_folder = Folder(path=folder)
            db.add(new_folder)
            db.commit()

    workflow = Workflow(
        name=config["name"],
        description=config.get("description", ""),
        folder=folder,
        config=config,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)

    _save_workflow_yaml(workflow)

    return {
        "id": workflow.id,
        "name": workflow.name,
        "folder": workflow.folder,
        "message": "Workflow imported successfully",
    }


@router.get("/export/{workflow_id}")
def export_workflow(workflow_id: int, db: Session = Depends(get_db)):
    """Export workflow as YAML."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Add folder to config for export
    export_config = {**workflow.config, "folder": workflow.folder or ""}
    yaml_content = yaml.dump(export_config, allow_unicode=True, default_flow_style=False)

    return {
        "name": workflow.name,
        "folder": workflow.folder or "",
        "yaml": yaml_content,
    }


def _save_workflow_yaml(workflow: Workflow):
    """Save workflow config as YAML file."""
    yaml_path = os.path.join(WORKFLOWS_DIR, f"workflow_{workflow.id}.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(workflow.config, f, allow_unicode=True, default_flow_style=False)
