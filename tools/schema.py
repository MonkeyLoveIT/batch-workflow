"""
Workflow schema for validation.
"""

WORKFLOW_SCHEMA = {
    "type": "object",
    "required": ["name", "tasks"],
    "properties": {
        "name": {
            "type": "string",
            "description": "Workflow name"
        },
        "description": {
            "type": "string",
            "description": "Workflow description"
        },
        "config": {
            "type": "object",
            "properties": {
                "max_workers": {"type": "integer", "minimum": 1},
                "stop_on_failure": {"type": "boolean"},
            }
        },
        "tasks": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id", "plugin"],
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[a-zA-Z0-9_]+$",
                        "description": "Unique task identifier"
                    },
                    "name": {
                        "type": "string",
                        "description": "Human-readable task name"
                    },
                    "plugin": {
                        "type": "string",
                        "description": "Plugin name to execute"
                    },
                    "config": {
                        "type": "object",
                        "description": "Plugin-specific configuration"
                    },
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of task IDs this task depends on"
                    },
                    "retry": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 0
                    },
                    "continue_on_failure": {
                        "type": "boolean",
                        "default": False
                    },
                    "notify_on": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["start", "success", "failure"]
                        }
                    }
                }
            }
        },
        "notifications": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["event", "plugin"],
                "properties": {
                    "event": {
                        "type": "string",
                        "enum": [
                            "workflow_start", "workflow_complete", "workflow_failed",
                            "task_start", "task_success", "task_failure", "task_retry"
                        ]
                    },
                    "plugin": {"type": "string"},
                    "config": {"type": "object"}
                }
            }
        }
    }
}

TASK_DEPENDENCY_SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "depends_on": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }
}
