from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agentsystem.container import AppContainer
from agentsystem.domain import ApprovalDecision, ApprovalPolicy, StepStatus, TaskCreate, TaskStatus


def run_case(case: dict[str, str]) -> dict[str, object]:
    container = AppContainer()
    view = container.workflow.create_task(
        TaskCreate(
            repo_id=case["repo_id"],
            prompt=case["prompt"],
            approval_policy=ApprovalPolicy(case["approval_policy"]),
        )
    )

    while view.task.status == TaskStatus.AWAITING_APPROVAL:
        pending = [item for item in view.approvals if item.status == StepStatus.AWAITING_APPROVAL]
        if not pending:
            raise AssertionError("Task awaits approval but no pending approval exists")
        view = container.workflow.approve(
            view.task.id,
            ApprovalDecision(approval_id=pending[0].id, approved=True, actor="eval"),
        )

    return {
        "name": case["name"],
        "task_id": view.task.id,
        "status": view.task.status,
        "trace_id": view.task.trace_id,
        "pr_url": view.task.pr_url,
    }


def main() -> int:
    cases_path = ROOT / "evals" / "cases.jsonl"
    results_dir = ROOT / "evals" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []

    for line in cases_path.read_text().splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        result = run_case(case)
        expected = case["expected_status"]
        if result["status"] != expected:
            failures.append({"case": case["name"], "expected": expected, "actual": result["status"]})
        results.append(result)

    output = {"results": results, "failures": failures}
    (results_dir / "latest.json").write_text(json.dumps(output, indent=2, default=str) + "\n")
    print(json.dumps(output, indent=2, default=str))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
