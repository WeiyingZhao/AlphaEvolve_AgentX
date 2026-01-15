import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path("src").absolute()))

from agentx.green_agent.tasks import TaskRegistry, TaskCategory
from agentx.green_agent.tools.kaggle import KaggleToolkit
from agentx.green_agent.scoring import ScoringEngine

def test_load_ml_task():
    print("Testing ML Task Loading...")
    registry = TaskRegistry()
    registry.load_from_directory(Path("benchmarks/tasks"))
    
    tasks = registry.list_tasks(category=TaskCategory.ML_ENGINEERING)
    if len(tasks) == 0:
        print("FAIL: No ML tasks found")
        sys.exit(1)
    
    task = tasks[0]
    print(f"PASS: Loaded task {task.task_id} with metric {task.evaluation_metric}")

def test_kaggle_toolkit():
    print("Testing Kaggle Toolkit...")
    work_dir = Path("/tmp/agent_test/kaggle_work")
    toolkit = KaggleToolkit(work_dir)
    data_dir = toolkit.download_competition_data("titanic")
    
    if os.path.exists(os.path.join(data_dir, "train.csv")):
        print("PASS: Kaggle data downloaded")
    else:
        print("FAIL: Data missing")
        sys.exit(1)

def main():
    try:
        test_load_ml_task()
        test_kaggle_toolkit()
        print("All checks passed!")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
