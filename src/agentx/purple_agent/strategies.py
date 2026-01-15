"""
Task-solving strategies for Purple Agent.

This module provides different strategies for handling various types
of software engineering tasks.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from agentx.a2a.protocol import TaskRequest


class BaseStrategy(ABC):
    """Base class for task-solving strategies."""

    @property
    @abstractmethod
    def supported_task_types(self) -> list[str]:
        """List of task types this strategy can handle."""
        pass

    @abstractmethod
    async def solve(
        self,
        task: TaskRequest,
    ) -> dict[str, str]:
        """
        Attempt to solve the task.

        Args:
            task: The task request to solve

        Returns:
            Dict mapping filename to content
        """
        pass

    def can_handle(self, task_type: str) -> bool:
        """Check if this strategy can handle the given task type."""
        return task_type in self.supported_task_types


class CodeGenerationStrategy(BaseStrategy):
    """Strategy for code generation tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["code_generation", "api_design"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Generate code based on task description."""
        # Extract function signature hints from description
        description = task.description
        test_cases = task.test_cases

        # Build a basic solution scaffold
        code_lines = []
        code_lines.append('"""')
        code_lines.append(f"Auto-generated solution for: {task.task_id}")
        code_lines.append(description[:200] + "..." if len(description) > 200 else description)
        code_lines.append('"""')
        code_lines.append("")

        # Try to extract function signatures from test cases
        functions_to_implement = set()
        for test in test_cases:
            input_data = test.get("input_data", {})
            if "function" in input_data:
                func_name = input_data["function"]
                args = input_data.get("args", [])
                functions_to_implement.add((func_name, len(args)))

        # Generate function stubs
        for func_name, num_args in functions_to_implement:
            arg_names = [f"arg{i}" for i in range(num_args)]
            code_lines.append(f"def {func_name}({', '.join(arg_names)}):")
            code_lines.append("    # TODO: Implement this function")
            code_lines.append("    pass")
            code_lines.append("")

        # If no functions found, create a basic template
        if not functions_to_implement:
            code_lines.append("def main():")
            code_lines.append("    # TODO: Implement solution")
            code_lines.append("    pass")
            code_lines.append("")
            code_lines.append('if __name__ == "__main__":')
            code_lines.append("    main()")

        return {"solution.py": "\n".join(code_lines)}


class DebugStrategy(BaseStrategy):
    """Strategy for debugging/bug fix tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["bug_fix", "debugging"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Attempt to fix bugs in provided code."""
        output_files = {}

        for filename, content in task.files.items():
            if filename.endswith(".py"):
                fixed_content = self._apply_common_fixes(content)
                output_files[filename] = fixed_content
            else:
                output_files[filename] = content

        # If no Python files, create a placeholder
        if not any(f.endswith(".py") for f in output_files):
            output_files["solution.py"] = "# No Python files found to fix\npass"

        return output_files

    def _apply_common_fixes(self, code: str) -> str:
        """Apply common bug fixes to code."""
        fixed = code

        # Fix common Python mistakes
        # 1. Replace = with == in comparisons (naive)
        # This is a simplified example - real bug fixing would be more sophisticated

        # 2. Fix missing colons in control structures
        lines = fixed.split("\n")
        fixed_lines = []
        for line in lines:
            stripped = line.rstrip()
            # Check for control structures missing colons
            if re.match(r"^\s*(if|elif|else|for|while|def|class|try|except|finally|with)\s+.+[^:]$", stripped):
                if not stripped.endswith(":"):
                    stripped += ":"
            fixed_lines.append(stripped)
        fixed = "\n".join(fixed_lines)

        # 3. Fix indentation issues (basic)
        # This would need more sophisticated handling in practice

        return fixed


class RefactoringStrategy(BaseStrategy):
    """Strategy for code refactoring tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["refactoring", "optimization"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Refactor provided code."""
        output_files = {}

        for filename, content in task.files.items():
            if filename.endswith(".py"):
                refactored = self._refactor_code(content)
                output_files[filename] = refactored
            else:
                output_files[filename] = content

        return output_files

    def _refactor_code(self, code: str) -> str:
        """Apply basic refactoring to code."""
        refactored = code

        # 1. Remove trailing whitespace
        lines = refactored.split("\n")
        lines = [line.rstrip() for line in lines]

        # 2. Add docstrings to functions without them
        result_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            result_lines.append(line)

            # Check if this is a function definition
            if re.match(r"^\s*def\s+\w+\s*\(", line):
                # Check if next non-empty line is a docstring
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    result_lines.append(lines[next_idx])
                    next_idx += 1

                if next_idx < len(lines):
                    next_line = lines[next_idx].strip()
                    if not (next_line.startswith('"""') or next_line.startswith("'''")):
                        # Add a placeholder docstring
                        indent = len(line) - len(line.lstrip()) + 4
                        result_lines.append(" " * indent + '"""TODO: Add docstring."""')

            i += 1

        return "\n".join(result_lines)


class TestWritingStrategy(BaseStrategy):
    """Strategy for test writing tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["test_writing"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Generate test cases for provided code."""
        # Analyze the code to find functions to test
        functions = []
        for filename, content in task.files.items():
            if filename.endswith(".py"):
                # Extract function definitions
                func_matches = re.findall(r"def\s+(\w+)\s*\(([^)]*)\)", content)
                for func_name, args in func_matches:
                    if not func_name.startswith("_"):  # Skip private functions
                        functions.append((func_name, args))

        # Generate test file
        test_lines = [
            '"""Auto-generated test cases."""',
            "import pytest",
            "",
        ]

        # Try to import from solution
        test_lines.append("# Import the module to test")
        for filename in task.files:
            if filename.endswith(".py"):
                module_name = filename[:-3]
                test_lines.append(f"from {module_name} import *")
        test_lines.append("")

        # Generate test cases
        for func_name, args in functions:
            test_lines.append(f"def test_{func_name}():")
            test_lines.append(f"    # TODO: Implement test for {func_name}")
            test_lines.append(f"    # Function signature: {func_name}({args})")
            test_lines.append("    pass")
            test_lines.append("")

        if not functions:
            test_lines.append("def test_placeholder():")
            test_lines.append("    # No functions found to test")
            test_lines.append("    pass")

        return {"test_solution.py": "\n".join(test_lines)}


class MultiStepPlanningStrategy(BaseStrategy):
    """Strategy for multi-step planning tasks requiring decomposition."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["multi_step_planning"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Solve multi-step planning tasks by implementing all stages."""
        output_files = {}

        # Start with any provided starter code
        for filename, content in task.files.items():
            output_files[filename] = content

        # If there's a solution.py template, enhance it
        if "solution.py" in output_files:
            content = output_files["solution.py"]
            # Try to implement the methods marked with TODO
            content = self._implement_todos(content, task)
            output_files["solution.py"] = content

        return output_files

    def _implement_todos(self, code: str, task: TaskRequest) -> str:
        """Attempt to implement TODO sections based on task context."""
        # For baseline, return the code as-is
        # A more advanced agent would implement the actual logic
        return code


class APIIntegrationStrategy(BaseStrategy):
    """Strategy for API integration tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["api_integration"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Solve API integration tasks."""
        output_files = {}

        # Start with any provided starter code
        for filename, content in task.files.items():
            output_files[filename] = content

        # If there's a solution.py template, enhance it
        if "solution.py" in output_files:
            content = output_files["solution.py"]
            content = self._implement_api_client(content, task)
            output_files["solution.py"] = content

        return output_files

    def _implement_api_client(self, code: str, task: TaskRequest) -> str:
        """Attempt to implement API client methods."""
        # For baseline, return the code as-is
        # A more advanced agent would implement the actual logic
        return code


class MLEngineeringStrategy(BaseStrategy):
    """Strategy for ML engineering tasks."""

    @property
    def supported_task_types(self) -> list[str]:
        return ["ml_engineering"]

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Solve ML engineering tasks."""
        output_files = {}

        # Start with any provided starter code
        for filename, content in task.files.items():
            output_files[filename] = content

        return output_files


class CompositeStrategy(BaseStrategy):
    """Composite strategy that delegates to appropriate sub-strategies."""

    def __init__(self):
        self.strategies: list[BaseStrategy] = [
            CodeGenerationStrategy(),
            DebugStrategy(),
            RefactoringStrategy(),
            TestWritingStrategy(),
            MultiStepPlanningStrategy(),
            APIIntegrationStrategy(),
            MLEngineeringStrategy(),
        ]

    @property
    def supported_task_types(self) -> list[str]:
        types = []
        for strategy in self.strategies:
            types.extend(strategy.supported_task_types)
        return list(set(types))

    async def solve(self, task: TaskRequest) -> dict[str, str]:
        """Delegate to the appropriate strategy."""
        for strategy in self.strategies:
            if strategy.can_handle(task.task_type):
                return await strategy.solve(task)

        # Fallback: return files as-is with a placeholder
        if task.files:
            return dict(task.files)
        return {"solution.py": "# No suitable strategy found\npass"}
