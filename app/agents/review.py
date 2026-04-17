from app.agents.langchain_utils import build_structured_chain, dump_for_prompt, invoke_structured
from app.schemas.response import AnalysisResult, PlanningResult, ReviewResult


class ReviewAgent:
    """Reviews whether the generated plan is complete enough to execute."""

    def __init__(self, chain=None, chat_model=None) -> None:
        self.chain = chain or build_structured_chain(
            system_prompt=(
                "你是方案审查 Agent。请审查分析结果和实施方案是否完整、合理、可执行，"
                "并输出 passed、comments、missing_items。"
            ),
            human_prompt="分析结果：{analysis}\n实施方案：{plan}",
            output_schema=ReviewResult,
            chat_model=chat_model,
        )

    def run(self, analysis: AnalysisResult, plan: PlanningResult) -> ReviewResult:
        reviewed = invoke_structured(
            self.chain,
            {
                "analysis": dump_for_prompt(analysis),
                "plan": dump_for_prompt(plan),
            },
            ReviewResult,
        )
        if reviewed is not None:
            return reviewed
        return self._fallback(analysis, plan)

    def _fallback(self, analysis: AnalysisResult, plan: PlanningResult) -> ReviewResult:
        missing_items: list[str] = []
        if not analysis.summary:
            missing_items.append("分析摘要")
        if not analysis.impacted_areas:
            missing_items.append("影响范围")
        if not plan.strategy:
            missing_items.append("实施策略")
        if not plan.steps:
            missing_items.append("实施步骤")
        if not analysis.risks:
            missing_items.append("风险说明")

        comments = ["方案包含需求分析、检索上下文、实施步骤和审查结果。"]
        if missing_items:
            comments.append("仍需补齐关键内容后再进入开发。")

        return ReviewResult(passed=not missing_items, comments=comments, missing_items=missing_items)
