from app.agents.langchain_utils import build_structured_chain, invoke_structured
from app.schemas.response import RouteDecision, TaskType


class RouterAgent:
    """Classifies an incoming requirement and selects the first workflow intent."""

    def __init__(self, chain=None, chat_model=None) -> None:
        self.chain = chain or build_structured_chain(
            system_prompt=(
                "你是研发任务路由 Agent。请根据用户需求判断任务类型，只能选择 "
                "requirement_analysis、impact_analysis、planning、review 或 general。"
            ),
            human_prompt="用户需求：{requirement}",
            output_schema=RouteDecision,
            chat_model=chat_model,
        )

    def run(self, requirement: str) -> RouteDecision:
        routed = invoke_structured(self.chain, {"requirement": requirement}, RouteDecision)
        if routed is not None:
            return routed
        return self._fallback(requirement)

    def _fallback(self, requirement: str) -> RouteDecision:
        text = requirement.lower()
        if any(keyword in text for keyword in ["review", "审查", "评审", "检查方案"]):
            return RouteDecision(task_type=TaskType.review, reason="Requirement asks for a plan or design review.")
        if any(keyword in text for keyword in ["影响", "impact", "风险", "依赖"]):
            return RouteDecision(task_type=TaskType.impact_analysis, reason="Requirement focuses on impact, risk, or dependencies.")
        if any(keyword in text for keyword in ["方案", "计划", "拆解", "plan", "实施"]):
            return RouteDecision(task_type=TaskType.planning, reason="Requirement asks for implementation planning.")
        if any(keyword in text for keyword in ["需求", "分析", "requirement"]):
            return RouteDecision(task_type=TaskType.requirement_analysis, reason="Requirement asks for requirement analysis.")
        return RouteDecision(task_type=TaskType.general, reason="No specific intent keyword found; using general analysis.")
