---
trigger: always_on
---

# Python Environment Configuration

This project requires a specific local Conda environment to run correctly. The Agent must strictly follow these execution rules to access necessary packages (like pandas, etc.).

## 1. Python Executable Path
* **Environment Name:** ym
* **Executable Path:** `E:\miniconda\envs\ym\python.exe`

## 2. Execution Protocol
When generating commands to run Python scripts (in Planning or Execution phases):
* **NEVER** use the generic `python` command.
* **NEVER** rely on `conda activate` inside the agent's shell.
* **ALWAYS** use the full absolute path.

### Correct Example:
`E:\miniconda\envs\ym\python.exe scripts/data_analysis.py`

### Incorrect Example:
`python scripts/data_analysis.py`