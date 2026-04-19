# Batch Workflow Framework

A lightweight workflow execution framework with plugin support for task orchestration.

## Features

- **Plugin-based architecture**: All tools (scripts, CLI, notifications) are unified as plugins
- **DAG-based scheduling**: Configure task dependencies, parallel execution supported
- **Built-in plugins**: Script execution, command execution, HTTP requests, WeChat Work, DingTalk, Email, Alert tools
- **Notification system**: Get notified at different stages (workflow start, task success/failure)
- **YAML configuration**: Easy-to-read workflow definitions

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Define a workflow in YAML

```yaml
name: "My Workflow"

tasks:
  - id: task1
    plugin: command
    config:
      cmd: echo
      args: ["Hello from task1"]

  - id: task2
    plugin: command
    config:
      cmd: echo
      args: ["Hello from task2"]
    depends_on:
      - task1
```

### 2. Run the workflow

```bash
python -m core.engine --config config/workflows/my_workflow.yaml
```

Or programmatically:

```python
from core import WorkflowEngine
import plugins  # Load all plugins

engine = WorkflowEngine(workflow_config)
context = engine.run()
```

## Workflow Configuration

### Task Definition

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique task identifier |
| `name` | string | Human-readable task name |
| `plugin` | string | Plugin name to use |
| `config` | dict | Plugin-specific configuration |
| `depends_on` | list | List of task IDs this task depends on |
| `retry` | int | Number of retries on failure (default: 0) |
| `continue_on_failure` | bool | Continue workflow if this task fails (default: false) |

### Example DAG

```
task1 ─┬─> task2 ─┐
       └─> task3 ─┼─> task4
```

YAML:

```yaml
tasks:
  - id: task1
    plugin: command
    config: {cmd: echo, args: [step1]}

  - id: task2
    plugin: command
    config: {cmd: echo, args: [step2]}
    depends_on: [task1]

  - id: task3
    plugin: command
    config: {cmd: echo, args: [step3]}
    depends_on: [task1]

  - id: task4
    plugin: command
    config: {cmd: echo, args: [step4]}
    depends_on: [task2, task3]
```

## Available Plugins

### Built-in Plugins

| Plugin | Description | Key Config |
|--------|-------------|------------|
| `script` | Execute shell scripts | `script`: path, `interpreter`: auto/bash/python |
| `command` | Execute CLI commands | `cmd`: command, `args`: list |
| `http` | Make HTTP requests | `url`, `method`, `headers`, `body` |

### Notification Plugins

| Plugin | Description | Key Config |
|--------|-------------|------------|
| `wechat_work` | WeChat Work webhooks | `webhook_url`, `message` |
| `dingtalk` | DingTalk webhooks | `webhook_url`, `message` |
| `email` | SMTP email | `smtp_host`, `from_addr`, `to_addrs` |

### Alert Plugins

| Plugin | Description | Key Config |
|--------|-------------|------------|
| `alert` | Generic alert backend | `url`, `type`, `level`, `title` |

## Notification Events

Configure notifications in your workflow:

```yaml
notifications:
  - event: workflow_start
    plugin: wechat_work
    config:
      webhook_url: "https://..."
      message: "Workflow started"

  - event: task_failure
    plugin: wechat_work
    config:
      webhook_url: "https://..."
      message: "Task {task_id} failed"
```

Available events:
- `workflow_start` / `workflow_complete` / `workflow_failed`
- `task_start` / `task_success` / `task_failure` / `task_retry`

## Creating Custom Plugins

```python
from core.plugin import Plugin, register_plugin

@register_plugin("my_plugin")
class MyPlugin(Plugin):
    name = "my_plugin"

    def validate(self, config):
        return "param" in config

    def execute(self, context):
        param = context.get("param")
        # Do something
        return {"result": "done"}
```

## Project Structure

```
batch-workflow/
├── core/               # Core framework
│   ├── engine.py       # Workflow engine
│   ├── scheduler.py   # DAG scheduler
│   ├── plugin.py      # Plugin base class
│   ├── context.py     # Execution context
│   └── notification.py # Notification manager
├── plugins/            # Built-in plugins
│   ├── builtin/       # Script, command, HTTP plugins
│   ├── notification/  # WeChat, DingTalk, Email plugins
│   └── alert/         # Alert plugin
├── config/workflows/  # Example workflows
└── examples/          # Usage examples
```
