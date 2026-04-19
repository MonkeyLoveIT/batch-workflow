# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Batch Workflow Framework - A lightweight Python workflow execution engine with plugin support. Designed for task orchestration on internal servers, supporting parallel execution, DAG-based scheduling, and notification integration.

## Quick Start

```bash
# Start Web Management Console (recommended)
cd backend && uvicorn main:app --reload --port 8000
# Then open http://localhost:3000

# Or run workflow via CLI
python -m core.engine --config config/workflows/example.yaml
```

## Architecture

### Web Management Console (Recommended)
- **Frontend**: React + Vite + ReactFlow (DAG visualization)
- **Backend**: FastAPI + SQLAlchemy (SQLite)
- **Start**: `cd backend && uvicorn main:app --reload --port 8000`

### Core Components

- **`core/engine.py`**: `WorkflowEngine` - Main entry point, orchestrates task execution
- **`core/scheduler.py`**: `DAGScheduler` - Resolves task dependencies, topological sorting, parallel execution
- **`core/plugin.py`**: `Plugin` base class + `@register_plugin` decorator + `PluginRegistry`
- **`core/context.py`**: `WorkflowContext` - Thread-safe shared state during execution
- **`core/notification.py`**: `NotificationManager` - Dispatches notifications on workflow events

### Plugin System

All tools inherit from `Plugin` base class and register via `@register_plugin("name")` decorator:

```python
@register_plugin("my_plugin")
class MyPlugin(Plugin):
    name = "my_plugin"

    def execute(self, context: dict) -> dict:
        # Return {"success": bool, ...}
        pass
```

### DAG Execution Flow

1. `WorkflowEngine.run()` loads config, creates `DAGScheduler`
2. `DAGScheduler.get_execution_order()` returns levels of parallelizable tasks
3. Each level executes in `ThreadPoolExecutor` (max_workers configurable)
4. `NotificationManager` triggers on events: `workflow_start/complete/failed`, `task_start/success/failure/retry`

## Key Files

### Core
| File | Purpose |
|------|---------|
| `core/plugin.py` | `Plugin` abstract class, `@register_plugin` decorator, `PluginRegistry` |
| `core/scheduler.py` | `DAGScheduler` - dependency resolution, topological sort |
| `core/engine.py` | `WorkflowEngine` - workflow execution coordinator |
| `core/context.py` | `WorkflowContext` - thread-safe shared state |

### Backend (Web API)
| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI application entry point |
| `backend/api/workflow.py` | Workflow CRUD API endpoints |
| `backend/api/execute.py` | Workflow execution API |
| `backend/api/history.py` | Execution history API |
| `backend/models/database.py` | SQLAlchemy database models |

### Frontend (Web UI)
| File | Purpose |
|------|---------|
| `frontend/src/App.jsx` | Main application component |
| `frontend/src/views/WorkflowEditor.jsx` | DAG visual editor (ReactFlow) |
| `frontend/src/views/WorkflowList.jsx` | Workflow list and management |
| `frontend/src/views/History.jsx` | Execution history and stats |

### Plugins
| File | Purpose |
|------|---------|
| `plugins/builtin/command_plugin.py` | Execute shell commands |
| `plugins/builtin/script_plugin.py` | Execute script files |
| `plugins/builtin/exec_flow.py` | Execute custom flow tool |
| `plugins/notification/push_wxchat.py` | WeChat push notification |
| `plugins/notification/alert_ims.py` | IMS alert notification |
| `plugins/alert/alert_ims.py` | Alert tool integration |

## Commands

```bash
# Web Management Console
cd backend && uvicorn main:app --reload --port 8000
# Frontend: cd frontend && npm install && npm run dev

# Run workflow from YAML config
python -m core.engine --config config/workflows/example.yaml

# Run example programmatically
python examples/run_workflow.py

# List available plugins
python -c "import plugins; from core.plugin import PluginRegistry; print(PluginRegistry.list_plugins())"

# Run tests
pytest tests/ -v

# Validate plugins
python tools/validate_plugin.py --all

# Validate workflow
python tools/validate_workflow.py config/workflows/example.yaml --check-deps --visualize
```

## Environment Variables

- `WECOM_WEBHOOK_URL`: WeChat Work webhook URL for notifications
- `NOTIFY_API_URL`: Custom notification API endpoint
- `TOOLS_DIR`: Path to custom tools directory (default: `/Users/eddy/tools`)

## Testing

- `tests/test_scheduler.py`: DAG validation, topological sort, dependency resolution
- `tests/test_plugin.py`: Plugin registration and creation
- `tests/test_engine.py`: Workflow execution logic
