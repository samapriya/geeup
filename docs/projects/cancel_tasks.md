# Cancel Tasks tool

The Cancel Tasks tool in geeup is a powerful utility designed to streamline task management within Google Earth Engine (GEE). This tool provides users with precise control over task cancellation, allowing for the cancellation of various task types based on specific criteria. Whether you need to cancel all tasks, terminate running tasks, clear pending tasks, or selectively cancel a single task using its unique task ID, the Cancel Tasks tool has you covered.

#### Key Features

- **Efficient Task Cancellation**: The Cancel Tasks tool simplifies the process of terminating GEE tasks, ensuring efficient resource management.

- **Cancel All Tasks**: Users can opt to cancel all active tasks, providing a quick and comprehensive way to clear ongoing processes.

- **Terminate Running Tasks**: For situations requiring the immediate cessation of running tasks, this tool enables the cancellation of running tasks specifically.

- **Clear Pending Tasks**: Pending tasks can be removed in one fell swoop, ensuring that resources are not tied up unnecessarily.

- **Selective Task Cancellation**: Users have the flexibility to target a single task for cancellation by providing its unique task ID.

#### Usage

Utilizing the Cancel Tasks tool is straightforward, and it provides fine-grained control over task cancellation.

```bash
geeup cancel -h
usage: geeup cancel [-h] --tasks TASKS

optional arguments:
  -h, --help     show this help message and exit

Required named arguments.:
  --tasks TASKS  You can provide tasks as running or pending or all or even a
                 single task id
```

- `state`: (Optional) Specifies the state of tasks to cancel (e.g., 'RUNNING' for running tasks, 'READY' for pending tasks).

- `task_id`: (Optional) The unique identifier of the task you want to cancel.

#### Example

Here's an example demonstrating how to use the Cancel Tasks tool to efficiently manage Earth Engine tasks:


![geeup_tasks_cancel](https://user-images.githubusercontent.com/6677629/114294403-04086c00-9a64-11eb-9f43-a80522de159d.gif)
