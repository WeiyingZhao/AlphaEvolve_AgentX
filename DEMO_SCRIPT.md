# AgentBeats Demo Script

**Time Limit**: 3 Minutes
**Goal**: Demonstrate the Green Agent's capabilities, reproducibility, and the visual leaderboard.

## Scene 1: Introduction (0:00 - 0:30)
- **Visual**: Show the GitHub Repository README.
- **Narration**: 
  "Welcome to AlphaEvolve AgentX, a robust Green Agent for the AgentBeats competition. AgentX is designed for reliability, security, and 100% reproducibility in evaluating software agents."

## Scene 2: Task Diversity (0:30 - 1:00)
- **Visual**: Show VS Code with `benchmarks/tasks/` open. Scroll through `bug_fix` and `refactoring` folders.
- **Action**: Run the task lister.
  ```bash
  agentx list-tasks
  ```
- **Narration**: 
  "We go beyond simple code generation. AgentX supports bug fixing, refactoring, and code review tasks. Each task defines clear success criteria, hidden test cases, and efficiency constraints."

## Scene 3: The Evaluation (1:00 - 2:00)
- **Visual**: Split screen terminal.
- **Action**: Run a live evaluation with 3 runs to show reproducibility.
  ```bash
  # Trigger the evaluation flow
  agentx evaluate --runs 3 --seed 42
  ```
- **Narration**:
  "Watch as we evaluate a standard Purple Agent. We run the evaluation three times with a fixed seed. Our Dockerized environment ensures total isolation—the agent cannot tamper with the scorer. Notice how the scores are identical across runs."

## Scene 4: Results & Leaderboard (2:00 - 2:45)
- **Visual**: Open the generated `results/leaderboard.html` in a browser.
- **Action**: Generate the leaderboard.
  ```bash
  python scripts/render_leaderboard.py
  ```
- **Narration**:
  "Finally, we generate a comprehensive leaderboard. It tracks not just the average score, but the standard deviation, giving us a 'Confidence Score' for every entry. AgentX doesn't just rank agents; it certifies them."

## Scene 5: Conclusion (2:45 - 3:00)
- **Visual**: Show the "Reproducibility Verified" badge or the GitHub Action green checkmark.
- **Narration**:
  "Secure. Reproducible. Multi-faceted. This is AlphaEvolve AgentX."
