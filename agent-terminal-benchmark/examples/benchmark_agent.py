"""Copy to my_agent.py and connect YOUR harness; this is not a solved agent.

Keep input fixtures unchanged. Work only inside workspace. Do not give your
agent grader code, reference solutions, cache files, or previous task answers.
"""
from pathlib import Path


async def solve_task(instruction: str, workspace: Path, logs_dir: Path, options: dict) -> dict:
    """Run your agent, await completion, and report what actually happened.

    instruction: prepared task text, including local file paths.
    workspace: isolated trial directory (not an OS sandbox).
    logs_dir: location for your agent logs; do not record credentials.
    options: provider, model, max_steps, max_seconds, command_timeout, task_cwd.

    Return {"status": "completed", "answer": "...", "metrics": {...}} only
    after your real run completes. Other statuses may be timeout/step_limit/
    failed. Omit unknown metrics; do not invent token use or costs. The evaluator
    determines correctness independently from the files your agent produces.
    """
    raise NotImplementedError("Connect your own harness here before evaluation")
