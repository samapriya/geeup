# Tasks tool

The Tasks tool in geeup provides a streamlined approach to monitor and manage tasks within Google Earth Engine (GEE). It offers comprehensive insights into the status of ongoing tasks, including those that are running, cancelled, pending, and failed. Additionally, the tool allows for detailed task-specific information retrieval by providing either the task state or a specific task ID.

#### Key Features

- **Task Status Overview**: The Tasks tool offers a quick summary of tasks currently in progress, cancelled, pending, and those that have encountered failures. This enables users to effectively track the progress and status of their Earth Engine tasks.

- **Detailed Task Information**: Users have the ability to retrieve detailed information about a specific task by providing either the task state or a unique task ID. This information includes task descriptions, URIs, and the resources (EECUs) utilized by the task.

#### Usage

Using the Tasks tool is straightforward. You can either get an overview of all tasks or retrieve specific information about a particular task.


![geeup_tasks_enhanced](https://user-images.githubusercontent.com/6677629/169737348-abf13334-e360-487e-b4ce-d25aa677404c.gif)

```
usage: geeup tasks [-h] [--state STATE]

optional arguments:
  -h, --help     show this help message and exit

Optional named arguments:
  --state STATE  Query by state type SUCCEEDED|PENDING|RUNNING|FAILED
```
