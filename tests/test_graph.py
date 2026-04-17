from app.agents.graph import AgentWorkflow, _next_after_review, _next_after_router
from app.schemas.request import TaskRequest
from app.schemas.response import ReviewResult, RouteDecision, TaskType


def test_agent_workflow_runs_for_general_task_without_database() -> None:
    workflow = AgentWorkflow()
    response = workflow.run(TaskRequest(requirement="你好"))

    assert response.route.task_type == TaskType.general
    assert response.analysis.summary
    assert response.plan.steps
    assert response.review.passed


def test_router_conditional_path_uses_task_type() -> None:
    assert _next_after_router({"requirement": "审查方案", "route": RouteDecision(task_type=TaskType.review, reason="x")}) == "review"
    assert _next_after_router({"requirement": "闲聊", "route": RouteDecision(task_type=TaskType.general, reason="x")}) == "analysis"
    assert _next_after_router({"requirement": "分析影响", "route": RouteDecision(task_type=TaskType.impact_analysis, reason="x")}) == "retrieval"


def test_review_conditional_path_loops_until_iteration_limit() -> None:
    state = {
        "review": ReviewResult(passed=False, comments=["missing"], missing_items=["实施步骤"]),
        "review_iterations": 1,
    }

    assert _next_after_review(state) == "planning"

    state["review_iterations"] = 2
    assert _next_after_review(state) == "end"
