"""Tests for task definitions and registry."""

import tempfile
from pathlib import Path

import pytest
import yaml

from agentx.green_agent.tasks import (
    Task,
    TaskCategory,
    TaskDefinition,
    TaskDifficulty,
    TaskRegistry,
    TestCase,
)


class TestTaskDefinition:
    """Tests for TaskDefinition."""

    def test_create_task_definition(self):
        """Test creating a task definition."""
        task = TaskDefinition(
            task_id="test_task_001",
            name="Test Task",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="A test task",
        )

        assert task.task_id == "test_task_001"
        assert task.name == "Test Task"
        assert task.category == TaskCategory.CODE_GENERATION
        assert task.difficulty == TaskDifficulty.EASY
        assert task.max_score == 100.0

    def test_task_with_test_cases(self):
        """Test task definition with test cases."""
        public_test = TestCase(
            test_id="test_1",
            name="Basic test",
            input_data={"function": "add", "args": [1, 2]},
            expected_output=3,
        )

        hidden_test = TestCase(
            test_id="test_2",
            name="Hidden test",
            input_data={"function": "add", "args": [10, 20]},
            expected_output=30,
            is_hidden=True,
        )

        task = TaskDefinition(
            task_id="test_task_002",
            name="Addition Task",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Implement addition",
            public_tests=[public_test],
            hidden_tests=[hidden_test],
        )

        assert len(task.public_tests) == 1
        assert len(task.hidden_tests) == 1
        assert task.public_tests[0].expected_output == 3
        assert task.hidden_tests[0].is_hidden

    def test_task_fingerprint(self):
        """Test task fingerprint generation."""
        task = TaskDefinition(
            task_id="test_task",
            name="Test",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Test task",
        )

        fingerprint = task.get_fingerprint()
        assert len(fingerprint) == 16
        assert fingerprint.isalnum()

    def test_task_to_request_format(self):
        """Test converting task to request format."""
        task = TaskDefinition(
            task_id="test_task",
            name="Test",
            category=TaskCategory.BUG_FIX,
            difficulty=TaskDifficulty.MEDIUM,
            description="Fix the bug",
            context_files={"main.py": "buggy code"},
            evaluation_criteria=["Tests pass", "No regressions"],
        )

        request_format = task.to_task_request_format()

        assert request_format["task_type"] == "bug_fix"
        assert request_format["description"] == "Fix the bug"
        assert "main.py" in request_format["files"]
        assert "Tests pass" in request_format["evaluation_criteria"]


class TestTask:
    """Tests for Task runtime wrapper."""

    def test_task_wrapper(self):
        """Test Task wrapper functionality."""
        definition = TaskDefinition(
            task_id="wrapper_test",
            name="Wrapper Test",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Test wrapper",
            public_tests=[
                TestCase(test_id="t1", name="Test 1"),
            ],
            hidden_tests=[
                TestCase(test_id="t2", name="Test 2"),
            ],
        )

        task = Task(definition)

        assert task.task_id == "wrapper_test"
        assert len(task.all_tests) == 2

    def test_run_count(self):
        """Test task run count tracking."""
        definition = TaskDefinition(
            task_id="run_count_test",
            name="Run Count Test",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Test run counting",
        )

        task = Task(definition)

        assert task.increment_run() == 1
        assert task.increment_run() == 2
        assert task.increment_run() == 3


class TestTaskRegistry:
    """Tests for TaskRegistry."""

    def test_register_task(self):
        """Test registering a task."""
        registry = TaskRegistry()
        task = TaskDefinition(
            task_id="reg_test",
            name="Registry Test",
            category=TaskCategory.CODE_GENERATION,
            difficulty=TaskDifficulty.EASY,
            description="Test registration",
        )

        registry.register(task)

        assert len(registry) == 1
        assert registry.get("reg_test") is not None
        assert registry.get("nonexistent") is None

    def test_list_tasks_no_filter(self):
        """Test listing tasks without filters."""
        registry = TaskRegistry()

        for i in range(3):
            registry.register(
                TaskDefinition(
                    task_id=f"task_{i}",
                    name=f"Task {i}",
                    category=TaskCategory.CODE_GENERATION,
                    difficulty=TaskDifficulty.EASY,
                    description=f"Task {i}",
                )
            )

        tasks = registry.list_tasks()
        assert len(tasks) == 3

    def test_list_tasks_with_category_filter(self):
        """Test listing tasks with category filter."""
        registry = TaskRegistry()

        registry.register(
            TaskDefinition(
                task_id="gen_task",
                name="Gen Task",
                category=TaskCategory.CODE_GENERATION,
                difficulty=TaskDifficulty.EASY,
                description="Gen task",
            )
        )
        registry.register(
            TaskDefinition(
                task_id="fix_task",
                name="Fix Task",
                category=TaskCategory.BUG_FIX,
                difficulty=TaskDifficulty.EASY,
                description="Fix task",
            )
        )

        gen_tasks = registry.list_tasks(category=TaskCategory.CODE_GENERATION)
        assert len(gen_tasks) == 1
        assert gen_tasks[0].task_id == "gen_task"

    def test_list_tasks_with_difficulty_filter(self):
        """Test listing tasks with difficulty filter."""
        registry = TaskRegistry()

        registry.register(
            TaskDefinition(
                task_id="easy_task",
                name="Easy Task",
                category=TaskCategory.CODE_GENERATION,
                difficulty=TaskDifficulty.EASY,
                description="Easy",
            )
        )
        registry.register(
            TaskDefinition(
                task_id="hard_task",
                name="Hard Task",
                category=TaskCategory.CODE_GENERATION,
                difficulty=TaskDifficulty.HARD,
                description="Hard",
            )
        )

        hard_tasks = registry.list_tasks(difficulty=TaskDifficulty.HARD)
        assert len(hard_tasks) == 1
        assert hard_tasks[0].task_id == "hard_task"

    def test_load_from_yaml_file(self):
        """Test loading task from YAML file."""
        registry = TaskRegistry()

        task_yaml = """
task_id: yaml_task
name: YAML Task
category: code_generation
difficulty: medium
description: Task loaded from YAML
max_score: 50.0
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(task_yaml)
            f.flush()

            task = registry.load_from_file(Path(f.name))

            assert task.task_id == "yaml_task"
            assert task.name == "YAML Task"
            assert task.category == TaskCategory.CODE_GENERATION
            assert task.difficulty == TaskDifficulty.MEDIUM
            assert task.max_score == 50.0

    def test_load_from_directory(self):
        """Test loading tasks from directory."""
        registry = TaskRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create multiple task files
            for i in range(2):
                task_yaml = f"""
task_id: dir_task_{i}
name: Directory Task {i}
category: code_generation
difficulty: easy
description: Task {i}
"""
                (tmppath / f"task_{i}.yaml").write_text(task_yaml)

            tasks = registry.load_from_directory(tmppath)

            assert len(tasks) == 2
            assert len(registry) == 2


class TestTestCase:
    """Tests for TestCase."""

    def test_create_test_case(self):
        """Test creating a test case."""
        test = TestCase(
            test_id="test_001",
            name="Basic Test",
            description="A basic test case",
            input_data={"x": 1, "y": 2},
            expected_output=3,
            weight=2.0,
        )

        assert test.test_id == "test_001"
        assert test.name == "Basic Test"
        assert test.input_data == {"x": 1, "y": 2}
        assert test.expected_output == 3
        assert test.weight == 2.0
        assert not test.is_hidden

    def test_hidden_test_case(self):
        """Test creating a hidden test case."""
        test = TestCase(
            test_id="hidden_test",
            name="Hidden Test",
            is_hidden=True,
        )

        assert test.is_hidden
