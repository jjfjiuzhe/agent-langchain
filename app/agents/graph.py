from app.agents.analysis import AnalysisAgent
from app.agents.planning import PlanningAgent
from app.agents.retrieval import RetrievalAgent
from app.agents.review import ReviewAgent
from app.agents.router import RouterAgent
from app.agents.state import AgentState
from app.schemas.request import TaskRequest
from app.schemas.response import AnalysisResult, PlanningResult, ReviewResult, RouteDecision, TaskAnalysisResponse, TaskType

MAX_REVIEW_ITERATIONS = 2


def _route(state: AgentState) -> AgentState:
    state["route"] = RouterAgent().run(state["requirement"])
    return state


def _retrieve(state: AgentState) -> AgentState:
    state["retrieved_items"] = RetrievalAgent().run(state["requirement"])
    return state


def _analyze(state: AgentState) -> AgentState:
    route = _ensure_route(state)
    state["analysis"] = AnalysisAgent().run(
        state["requirement"],
        route,
        state.get("retrieved_items", []),
    )
    return state


def _plan(state: AgentState) -> AgentState:
    analysis = _ensure_analysis(state)
    state["plan"] = PlanningAgent().run(analysis, state.get("review"))
    return state


def _review(state: AgentState) -> AgentState:
    analysis = _ensure_analysis(state)
    plan = _ensure_plan(state, analysis)
    state["review"] = ReviewAgent().run(analysis, plan)
    state["review_iterations"] = state.get("review_iterations", 0) + 1
    return state


def _ensure_route(state: AgentState) -> RouteDecision:
    if "route" not in state:
        state["route"] = RouterAgent().run(state["requirement"])
    return state["route"]


def _ensure_analysis(state: AgentState) -> AnalysisResult:
    if "analysis" not in state:
        state["analysis"] = AnalysisAgent().run(
            state["requirement"],
            _ensure_route(state),
            state.get("retrieved_items", []),
        )
    return state["analysis"]


def _ensure_plan(state: AgentState, analysis: AnalysisResult) -> PlanningResult:
    if "plan" not in state:
        state["plan"] = PlanningAgent().run(analysis, state.get("review"))
    return state["plan"]


def _next_after_router(state: AgentState) -> str:
    task_type = _ensure_route(state).task_type
    if task_type == TaskType.review:
        return "review"
    if task_type == TaskType.general:
        return "analysis"
    return "retrieval"


def _next_after_review(state: AgentState) -> str:
    review = state.get("review")
    if review is None or review.passed:
        return "end"
    if state.get("review_iterations", 0) >= MAX_REVIEW_ITERATIONS:
        return "end"
    missing = ", ".join(review.missing_items) or "审查意见"
    state["review"] = ReviewResult(
        passed=False,
        comments=[*review.comments, f"进入第 {state.get('review_iterations', 0) + 1} 轮方案修订。"],
        missing_items=[missing],
    )
    return "planning"


def _run_sequential(state: AgentState) -> AgentState:
    state = _route(state)
    next_step = _next_after_router(state)

    if next_step == "retrieval":
        state = _retrieve(state)
        state = _analyze(state)
        state = _plan(state)
    elif next_step == "analysis":
        state = _analyze(state)
        state = _plan(state)
    elif next_step == "review":
        pass

    while True:
        state = _review(state)
        if _next_after_review(state) == "end":
            return state
        state = _plan(state)


def build_graph():
    """Builds the LangGraph workflow with conditional routing and review loops."""
    try:
        from langgraph.graph import END, StateGraph
    except ImportError:
        return None

    workflow = StateGraph(AgentState)
    workflow.add_node("router", _route)
    workflow.add_node("retrieval", _retrieve)
    workflow.add_node("analysis", _analyze)
    workflow.add_node("planning", _plan)
    workflow.add_node("review", _review)

    workflow.set_entry_point("router")
    workflow.add_conditional_edges(
        "router",
        _next_after_router,
        {
            "retrieval": "retrieval",
            "analysis": "analysis",
            "review": "review",
        },
    )
    workflow.add_edge("retrieval", "analysis")
    workflow.add_edge("analysis", "planning")
    workflow.add_edge("planning", "review")
    workflow.add_conditional_edges(
        "review",
        _next_after_review,
        {
            "planning": "planning",
            "end": END,
        },
    )
    return workflow.compile()


class AgentWorkflow:
    """Facade used by the API and tests to execute the multi-agent workflow."""

    def __init__(self) -> None:
        self.graph = build_graph()

    def run(self, request: TaskRequest) -> TaskAnalysisResponse:
        initial_state: AgentState = {
            "requirement": request.requirement,
            "context": request.context,
            "review_iterations": 0,
        }
        final_state = self.graph.invoke(initial_state) if self.graph else _run_sequential(initial_state)
        return TaskAnalysisResponse(
            route=final_state["route"],
            retrieved_items=final_state.get("retrieved_items", []),
            analysis=final_state["analysis"],
            plan=final_state["plan"],
            review=final_state["review"],
        )
