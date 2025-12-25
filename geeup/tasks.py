"""
Task discovery logic for geeup (Python 3.10+)
Updated to align with geeadd.py tasks functionality
"""

from datetime import datetime
import ee


def _epoch_convert_time(epoch_timestamp: int) -> str:
    """Convert epoch timestamp to formatted datetime string."""
    dt_object = datetime.fromtimestamp(epoch_timestamp / 1000)
    formatted_date_time = dt_object.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return formatted_date_time


def _runtime_ms(start_ms: int, end_ms: int) -> str:
    """Calculate runtime from start and end timestamps."""
    date_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    start = datetime.strptime(_epoch_convert_time(start_ms), date_format)
    end = datetime.strptime(_epoch_convert_time(end_ms), date_format)
    return str(end - start)


def fetch_tasks(
    *,
    state: str | None = None,
    task_id: str | None = None,
) -> list[dict]:
    """
    Fetch task details from Earth Engine.

    Args:
        state: Filter tasks by state (e.g., 'COMPLETED', 'RUNNING', 'FAILED')
        task_id: Get details of a specific task ID

    Returns:
        List of task dictionaries with detailed information
    """
    tasks = ee.data.getTaskList()

    # Filter by state if provided
    if state:
        tasks = [t for t in tasks if t["state"] == state.upper()]

    # Filter by task_id if provided
    if task_id:
        tasks = [t for t in tasks if t["id"] == task_id]

    output: list[dict] = []

    for t in tasks:
        item = {
            "task_id": t["id"],
            "operation_type": t.get("task_type"),
            "description": t.get("description", "").split(":")[0],
            "attempt": t.get("attempt"),
            "state": t.get("state"),
        }

        # Calculate runtime if timestamps are available
        if "start_timestamp_ms" in t and "update_timestamp_ms" in t:
            item["run_time"] = _runtime_ms(
                t["start_timestamp_ms"],
                t["update_timestamp_ms"],
            )

        # Extract destination path if available
        if "destination_uris" in t:
            item["item_path"] = t["destination_uris"][0].replace(
                "https://code.earthengine.google.com/?asset=", ""
            )

        # Include EECU usage if available
        if "batch_eecu_usage_seconds" in t:
            item["eecu_usage"] = t["batch_eecu_usage_seconds"]

        output.append(item)

    return output


def summarize_tasks() -> dict[str, int]:
    """
    Return a summary count of tasks by state.

    Returns:
        Dictionary with state names as keys and counts as values
    """
    states = [t["state"] for t in ee.data.getTaskList()]

    return {
        "RUNNING": states.count("RUNNING"),
        "READY": states.count("READY"),
        "COMPLETED": states.count("COMPLETED") + states.count("SUCCEEDED"),
        "FAILED": states.count("FAILED"),
        "CANCELLED": states.count("CANCELLED") + states.count("CANCELLING"),
    }


def cancel_tasks(target: str) -> dict[str, int | str]:
    """
    Cancel Earth Engine tasks.

    Args:
        target: What to cancel - 'all', 'running', 'pending', or a specific task ID

    Returns:
        Dictionary with cancellation results
    """
    result = {"cancelled": 0, "errors": 0, "message": ""}

    try:
        if target == "all":
            statuses = ee.data.getTaskList()
            for status in statuses:
                state = status["state"]
                task_id = status["id"]

                if state in ["READY", "RUNNING"]:
                    try:
                        ee.data.cancelTask(task_id)
                        result["cancelled"] += 1
                    except ee.EEException:
                        result["errors"] += 1

            if result["cancelled"] > 0:
                result["message"] = f"Successfully cancelled {result['cancelled']} tasks"
            else:
                result["message"] = "No running or pending tasks found to cancel"

        elif target == "running":
            statuses = ee.data.getTaskList()
            running_tasks = [s for s in statuses if s["state"] == "RUNNING"]

            for status in running_tasks:
                try:
                    ee.data.cancelTask(status["id"])
                    result["cancelled"] += 1
                except ee.EEException:
                    result["errors"] += 1

            result["message"] = (
                f"Successfully cancelled {result['cancelled']} running tasks"
                if running_tasks
                else "No running tasks found"
            )

        elif target == "pending":
            statuses = ee.data.getTaskList()
            pending_tasks = [s for s in statuses if s["state"] == "READY"]

            for status in pending_tasks:
                try:
                    ee.data.cancelTask(status["id"])
                    result["cancelled"] += 1
                except ee.EEException:
                    result["errors"] += 1

            result["message"] = (
                f"Successfully cancelled {result['cancelled']} pending tasks"
                if pending_tasks
                else "No pending tasks found"
            )

        else:
            # Assume it's a task ID
            statuses = ee.data.getTaskStatus([target])
            if not statuses:
                result["message"] = f"Task {target} not found"
                return result

            status = statuses[0]
            state = status["state"]

            if state == "UNKNOWN":
                result["message"] = f"Unknown task ID: {target}"
            elif state in ["READY", "RUNNING"]:
                ee.data.cancelTask(target)
                result["cancelled"] = 1
                result["message"] = f"Successfully cancelled task {target}"
            else:
                result["message"] = (
                    f"Task {target} is already in state '{state}' and cannot be cancelled"
                )

    except Exception as e:
        result["message"] = f"Error in cancel_tasks: {e}"
        result["errors"] += 1

    return result
