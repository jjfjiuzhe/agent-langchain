from typing import TypedDict

from app.schemas.response import AnalysisResult, PlanningResult, RetrievedItem, ReviewResult, RouteDecision


class AgentState(TypedDict, total=False):
    requirement: str
    context: dict
    route: RouteDecision
    retrieved_items: list[RetrievedItem]
    analysis: AnalysisResult
    plan: PlanningResult
    review: ReviewResult
    review_iterations: int
