"""
Script to seed the benchmark registry with diverse software engineering tasks.
Run this to populate benchmarks/tasks/ with YAML definitions.
"""
import os
import yaml
from pathlib import Path

# Define tasks to generate
TASKS = [
    # --- Bug Fix Tasks ---
    {
        "task_id": "bug_fix_off_by_one",
        "name": "Fix Off-By-One Error",
        "category": "bug_fix",
        "difficulty": "easy",
        "description": "Fix a common off-by-one error in a range sum function.",
        "detailed_instructions": "The function `sum_range` is supposed to sum numbers from `start` to `end` (inclusive), but it's missing the last number. Fix it.",
        "starter_code": {
            "solution.py": "def sum_range(start, end):\n    total = 0\n    for i in range(start, end):\n        total += i\n    return total"
        },
        "reference_solution": {
            "solution.py": "def sum_range(start, end):\n    total = 0\n    for i in range(start, end + 1):\n        total += i\n    return total"
        },
        "public_tests": [
            {"test_id": "bf1_public", "name": "Small Range", "input_data": {"function": "sum_range", "args": [1, 3]}, "expected_output": 6, "weight": 1.0},
            {"test_id": "bf1_edge", "name": "Single Number", "input_data": {"function": "sum_range", "args": [5, 5]}, "expected_output": 5, "weight": 1.0}
        ],
        "hidden_tests": [
            {"test_id": "bf1_hidden", "name": "Larger Range", "input_data": {"function": "sum_range", "args": [1, 100]}, "expected_output": 5050, "weight": 2.0, "is_hidden": True}
        ],
        "evaluation_criteria": ["Correctly includes the end index"],
        "max_score": 100.0,
        "time_limit_seconds": 30,
        "allowed_languages": ["python"],
        "tags": ["loops", "bug_fix"]
    },
    {
        "task_id": "bug_fix_null_pointer",
        "name": "Handle None Input",
        "category": "bug_fix",
        "difficulty": "easy",
        "description": "Fix a function that crashes when input is None.",
        "detailed_instructions": "The function `process_data` crashes if the input list is None. Modify it to return an empty list in that case.",
        "starter_code": {
            "solution.py": "def process_data(items):\n    return [x * 2 for x in items]"
        },
        "reference_solution": {
            "solution.py": "def process_data(items):\n    if items is None:\n        return []\n    return [x * 2 for x in items]"
        },
        "public_tests": [
            {"test_id": "bf2_public", "name": "Valid Input", "input_data": {"function": "process_data", "args": [[1, 2]]}, "expected_output": [2, 4], "weight": 1.0}
        ],
        "hidden_tests": [
            {"test_id": "bf2_hidden", "name": "None Input", "input_data": {"function": "process_data", "args": [None]}, "expected_output": [], "weight": 2.0, "is_hidden": True}
        ],
        "evaluation_criteria": ["Robustly handles None input"],
        "max_score": 100.0,
        "time_limit_seconds": 30,
        "allowed_languages": ["python"],
        "tags": ["error_handling", "bug_fix"]
    },
    
    # --- Refactoring Tasks ---
    {
        "task_id": "refactor_simplify_conditional",
        "name": "Simplify Conditionals",
        "category": "refactoring",
        "difficulty": "medium",
        "description": "Refactor nested if/else statements into guard clauses.",
        "detailed_instructions": "Refactor `check_access` to use guard clauses (early returns) instead of nested logic. The behavior must remain exactly the same.",
        "starter_code": {
            "solution.py": "def check_access(user):\n    if user.get('is_active'):\n        if user.get('has_permission'):\n            if not user.get('is_locked'):\n                return True\n            else:\n                return False\n        else:\n            return False\n    else:\n        return False"
        },
        "reference_solution": {
            "solution.py": "def check_access(user):\n    if not user.get('is_active'):\n        return False\n    if not user.get('has_permission'):\n        return False\n    if user.get('is_locked'):\n        return False\n    return True"
        },
        "public_tests": [
            {"test_id": "rf1_public", "name": "Allowed User", "input_data": {"function": "check_access", "args": [{"is_active": True, "has_permission": True, "is_locked": False}]}, "expected_output": True, "weight": 1.0}
        ],
        "hidden_tests": [
             {"test_id": "rf1_hidden", "name": "Locked User", "input_data": {"function": "check_access", "args": [{"is_active": True, "has_permission": True, "is_locked": True}]}, "expected_output": False, "weight": 1.0, "is_hidden": True}
        ],
        "evaluation_criteria": ["Correct behavior preserved", "Code uses early returns"],
        "max_score": 100.0,
        "time_limit_seconds": 30,
        "allowed_languages": ["python"],
        "tags": ["refactoring", "clean_code"]
    },

    # --- Code Generation Tasks ---
    {
        "task_id": "code_gen_palindrome",
        "name": "Palindrome Checker",
        "category": "code_generation",
        "difficulty": "easy",
        "description": "Check if a string is a palindrome (ignoring case/spaces).",
        "detailed_instructions": "Implement `is_palindrome(s)` which returns True if string s is a palindrome, considering only alphanumeric characters and ignoring case.",
        "starter_code": {
            "solution.py": "def is_palindrome(s):\n    # TODO\n    pass"
        },
        "reference_solution": {
            "solution.py": "import re\ndef is_palindrome(s):\n    cleaned = ''.join(c.lower() for c in s if c.isalnum())\n    return cleaned == cleaned[::-1]"
        },
        "public_tests": [
            {"test_id": "cg1_public", "name": "Simple Palindrome", "input_data": {"function": "is_palindrome", "args": ["Racecar"]}, "expected_output": True, "weight": 1.0}
        ],
        "hidden_tests": [
            {"test_id": "cg1_hidden", "name": "Complex Palindrome", "input_data": {"function": "is_palindrome", "args": ["A man, a plan, a canal: Panama"]}, "expected_output": True, "weight": 1.5, "is_hidden": True},
            {"test_id": "cg1_hidden_fail", "name": "Not Palindrome", "input_data": {"function": "is_palindrome", "args": ["hello"]}, "expected_output": False, "weight": 1.0, "is_hidden": True}
        ],
        "evaluation_criteria": ["Correctness", "Handles non-alphanumeric chars"],
        "max_score": 100.0,
        "time_limit_seconds": 30,
        "allowed_languages": ["python"],
        "tags": ["strings", "algorithms"]
    },
    {
        "task_id": "code_gen_prime_factors",
        "name": "Prime Factorization",
        "category": "code_generation",
        "difficulty": "medium",
        "description": "Return a list of prime factors for a given integer.",
        "detailed_instructions": "Implement `get_prime_factors(n)` that returns a sorted list of prime factors of n. If n < 2, return [].",
        "starter_code": {
            "solution.py": "def get_prime_factors(n):\n    # TODO\n    pass"
        },
        "reference_solution": {
            "solution.py": "def get_prime_factors(n):\n    factors = []\n    d = 2\n    temp = n\n    while d * d <= temp:\n        while temp % d == 0:\n            factors.append(d)\n            temp //= d\n        d += 1\n    if temp > 1:\n        factors.append(temp)\n    return factors"
        },
        "public_tests": [
             {"test_id": "cg2_public", "name": "Factors of 12", "input_data": {"function": "get_prime_factors", "args": [12]}, "expected_output": [2, 2, 3], "weight": 1.0}
        ],
        "hidden_tests": [
             {"test_id": "cg2_hidden", "name": "Large Prime", "input_data": {"function": "get_prime_factors", "args": [97]}, "expected_output": [97], "weight": 1.0, "is_hidden": True},
             {"test_id": "cg2_hidden_2", "name": "Composite", "input_data": {"function": "get_prime_factors", "args": [100]}, "expected_output": [2, 2, 5, 5], "weight": 1.0, "is_hidden": True}
        ],
        "evaluation_criteria": ["Correctness", "Efficiency"],
        "max_score": 100.0,
        "time_limit_seconds": 30,
        "allowed_languages": ["python"],
        "tags": ["math", "algorithms"]
    }
]

def main():
    base_dir = Path("benchmarks/tasks")
    print(f"Seeding tasks into {base_dir.absolute()}...")
    
    for task in TASKS:
        category = task["category"]
        category_dir = base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Use simple filenames derived from task_id
        filename = task["task_id"].replace(f"{category}_", "") + ".yaml"
        file_path = category_dir / filename
        
        with open(file_path, "w") as f:
            yaml.dump(task, f, sort_keys=False, indent=2, width=1000)
        
        print(f"Created task: {task['task_id']} -> {file_path}")

if __name__ == "__main__":
    main()
