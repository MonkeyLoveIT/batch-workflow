"""
Tool discovery and schema API.
"""

import os
import yaml
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/tools", tags=["tools"])

# Default tools directory
DEFAULT_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools")


def get_tools_dir() -> str:
    """Get the tools directory from environment or default."""
    return os.environ.get("TOOLS_DIR", DEFAULT_TOOLS_DIR)


def load_tool_schema(tool_name: str) -> Optional[Dict[str, Any]]:
    """Load tool schema from .tool.yaml file."""
    tools_dir = get_tools_dir()
    schema_file = os.path.join(tools_dir, tool_name, f"{tool_name}.tool.yaml")

    if not os.path.exists(schema_file):
        return None

    with open(schema_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def discover_tools() -> List[Dict[str, str]]:
    """Discover all available tools in the tools directory."""
    tools_dir = get_tools_dir()
    tools = []

    if not os.path.exists(tools_dir):
        return tools

    for item in os.listdir(tools_dir):
        item_path = os.path.join(tools_dir, item)
        if os.path.isdir(item_path):
            schema = load_tool_schema(item)
            if schema:
                tools.append({
                    "name": schema.get("name", item),
                    "description": schema.get("description", ""),
                })

    return tools


class ToolParameter(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""
    flag: str = ""  # CLI flag like -p or --param


class ToolSchema(BaseModel):
    name: str
    description: str = ""
    parameters: List[ToolParameter] = []


@router.get("", response_model=List[Dict[str, str]])
def list_tools():
    """Get all available tools."""
    return discover_tools()


@router.get("/{tool_name}/schema", response_model=ToolSchema)
def get_tool_schema(tool_name: str):
    """Get schema for a specific tool."""
    schema = load_tool_schema(tool_name)

    if not schema:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    # Convert parameters to include flag if not specified
    parameters = []
    for p in schema.get("parameters", []):
        param = ToolParameter(
            name=p.get("name", ""),
            type=p.get("type", "string"),
            required=p.get("required", False),
            default=p.get("default"),
            description=p.get("description", ""),
            flag=p.get("flag", f"-{p.get('name', '')}"),
        )
        parameters.append(param)

    return ToolSchema(
        name=schema.get("name", tool_name),
        description=schema.get("description", ""),
        parameters=parameters,
    )
