# Task status

This tasks tool gives a direct read out of different Earth Engine tasks across different states currently running, cancelled, pending and failed tasks and requires no arguments. However you could pass the state and get stats like SUCCEEDED along with item description or path, number of attempts and time taken along with task ID as a JSON list. This could also simply be piped into a JSON file using ">"

![geeup_tasks_enhanced](https://user-images.githubusercontent.com/6677629/169737348-abf13334-e360-487e-b4ce-d25aa677404c.gif)

```
usage: geeup tasks [-h] [--state STATE]

optional arguments:
  -h, --help     show this help message and exit

Optional named arguments:
  --state STATE  Query by state type SUCCEEDED|PENDING|RUNNING|FAILED
```
