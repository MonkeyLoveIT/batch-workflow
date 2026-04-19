"""
Workflow Engine - Main entry point for workflow execution.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
import concurrent.futures
import threading

from core.plugin import Plugin, PluginRegistry
from core.scheduler import DAGScheduler, DAGValidationError
from core.context import WorkflowContext, TaskResult, TaskStatus
from core.notification import NotificationManager, NotificationEvent

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Main workflow execution engine.
    Coordinates task scheduling, plugin execution, and notifications.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the workflow engine.

        Args:
            config: Workflow configuration containing:
                - name: Workflow name
                - tasks: List of task configurations
                - config: Global configuration
                - notifications: Notification settings
        """
        self.config = config
        self.workflow_name = config.get("name", "unnamed")
        self.scheduler = DAGScheduler(config.get("tasks", []))
        self.notification_manager = NotificationManager.from_config(config)
        self.context = WorkflowContext(config)

        self._max_workers = config.get("max_workers", 4)
        self._stop_on_failure = config.get("stop_on_failure", False)
        self._running = False
        self._lock = threading.Lock()

    def run(self) -> WorkflowContext:
        """
        Execute the workflow.

        Returns:
            WorkflowContext with all task results
        """
        with self._lock:
            self._running = True

        logger.info(f"Starting workflow: {self.workflow_name}")
        self.notification_manager.notify(
            NotificationEvent.WORKFLOW_START,
            {"workflow_name": self.workflow_name}
        )

        try:
            self._execute_workflow()
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            self.notification_manager.notify(
                NotificationEvent.WORKFLOW_FAILED,
                {"workflow_name": self.workflow_name, "error": str(e)}
            )
            raise
        finally:
            with self._lock:
                self._running = False

        # Check final status
        if self.scheduler.has_failures(self.context):
            self.notification_manager.notify(
                NotificationEvent.WORKFLOW_FAILED,
                {"workflow_name": self.workflow_name}
            )
        else:
            self.notification_manager.notify(
                NotificationEvent.WORKFLOW_COMPLETE,
                {"workflow_name": self.workflow_name}
            )

        logger.info(f"Workflow completed: {self.workflow_name}")
        return self.context

    def _execute_workflow(self) -> None:
        """Execute all tasks according to DAG order."""
        execution_order = self.scheduler.get_execution_order()

        for level, task_ids in enumerate(execution_order):
            logger.debug(f"Executing level {level}: {task_ids}")

            # Execute tasks at this level in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {}
                for task_id in task_ids:
                    future = executor.submit(self._execute_task, task_id)
                    futures[future] = task_id

                # Wait for all tasks at this level to complete
                for future in concurrent.futures.as_completed(futures):
                    task_id = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Task {task_id} raised exception: {e}")
                        if self._stop_on_failure:
                            raise

    def _execute_task(self, task_id: str) -> None:
        """
        Execute a single task.

        Args:
            task_id: ID of the task to execute
        """
        task = self.scheduler.get_task(task_id)
        if not task:
            logger.error(f"Task not found: {task_id}")
            return

        start_time = datetime.now()

        # Create task context
        task_context = {
            **task.get("config", {}),
            "task_id": task_id,
            "workflow_name": self.workflow_name,
            "workflow_context": self.context,
        }

        # Notify task start
        self.notification_manager.notify(
            NotificationEvent.TASK_START,
            {"task_id": task_id, "task_name": task.get("name", task_id)}
        )

        # Get plugin
        plugin_name = task.get("plugin")
        plugin = PluginRegistry.create(plugin_name)

        if not plugin:
            error = f"Plugin not found: {plugin_name}"
            self._handle_task_failure(task_id, task, Exception(error), start_time)
            return

        # Initialize plugin if needed
        if not plugin._initialized:
            plugin.initialize(task.get("config", {}))

        # Execute with retries
        max_retries = task.get("retry", 0)
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = plugin.execute(task_context)

                # Check if plugin reported failure via return value
                if isinstance(result, dict) and not result.get("success", True):
                    error_msg = result.get("error", "Task failed with success=False")
                    raise Exception(error_msg)

                # Task succeeded
                self._handle_task_success(task_id, task, result, start_time, task_context)
                return

            except Exception as e:
                last_error = e
                logger.warning(f"Task {task_id} failed (attempt {attempt + 1}/{max_retries + 1}): {e}")

                if attempt < max_retries:
                    self.notification_manager.notify(
                        NotificationEvent.TASK_RETRY,
                        {"task_id": task_id, "attempt": attempt + 1, "error": str(e)}
                    )

        # All retries exhausted
        self._handle_task_failure(task_id, task, last_error, start_time)

    def _handle_task_success(
        self,
        task_id: str,
        task: Dict[str, Any],
        result: Dict[str, Any],
        start_time: datetime,
        task_context: Dict[str, Any]
    ) -> None:
        """Handle successful task completion."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.SUCCESS,
            result=result,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )

        self.context.set_task_result(task_id, task_result)

        # Store result data in context for dependent tasks
        if result:
            self.context.set_data(f"task.{task_id}.result", result)

        logger.info(f"Task {task_id} completed in {duration:.2f}s")

        # Notify success
        self.notification_manager.notify(
            NotificationEvent.TASK_SUCCESS,
            {
                "task_id": task_id,
                "task_name": task.get("name", task_id),
                "duration": duration,
                "result": result
            }
        )

        # Call plugin callback
        plugin_name = task.get("plugin")
        plugin = PluginRegistry.create(plugin_name)
        if plugin:
            plugin.on_success(task_context, result)

    def _handle_task_failure(
        self,
        task_id: str,
        task: Dict[str, Any],
        error: Exception,
        start_time: datetime
    ) -> None:
        """Handle task failure."""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=str(error),
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )

        self.context.set_task_result(task_id, task_result)

        logger.error(f"Task {task_id} failed after {duration:.2f}s: {error}")

        # Notify failure
        self.notification_manager.notify(
            NotificationEvent.TASK_FAILURE,
            {
                "task_id": task_id,
                "task_name": task.get("name", task_id),
                "duration": duration,
                "error": str(error)
            }
        )

        # Check if we should continue workflow
        if not task.get("continue_on_failure", False) and self._stop_on_failure:
            raise error


def load_workflow_from_file(file_path: str) -> Dict[str, Any]:
    """Load workflow configuration from a YAML file."""
    import yaml
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def run_workflow(config_path: str, **kwargs) -> WorkflowContext:
    """
    Run a workflow from a configuration file.

    Args:
        config_path: Path to workflow YAML file
        **kwargs: Additional config overrides

    Returns:
        WorkflowContext with results
    """
    config = load_workflow_from_file(config_path)

    # Apply overrides
    for key, value in kwargs.items():
        if key in config:
            if isinstance(config[key], dict) and isinstance(value, dict):
                config[key].update(value)
            else:
                config[key] = value

    engine = WorkflowEngine(config)
    return engine.run()


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="Batch Workflow Engine")
    parser.add_argument("--config", required=True, help="Path to workflow config YAML")
    args = parser.parse_args()

    try:
        context = run_workflow(args.config)
        # Exit with error code if any task failed
        failed = context.get_task_ids_by_status(TaskStatus.FAILED)
        sys.exit(1 if failed else 0)
    except Exception as e:
        logger.error(f"Workflow failed: {e}")
        sys.exit(1)
