from app.agents.langchain_utils import build_structured_chain, dump_for_prompt, invoke_structured
from app.schemas.response import AnalysisResult, RetrievedItem, RouteDecision


class AnalysisAgent:
    """Builds requirement and impact analysis from retrieved context."""

    def __init__(self, chain=None, chat_model=None) -> None:
        self.chain = chain or build_structured_chain(
            system_prompt=(
                "你是研发任务分析 Agent。请基于需求、路由结果和检索上下文，输出结构化的需求理解、"
                "影响范围、风险和关键假设。"
            ),
            human_prompt=(
                "需求：{requirement}\n"
                "路由结果：{route}\n"
                "检索上下文：{retrieved_items}"
            ),
            output_schema=AnalysisResult,
            chat_model=chat_model,
        )

    def run(self, requirement: str, route: RouteDecision, retrieved_items: list[RetrievedItem]) -> AnalysisResult:
        analyzed = invoke_structured(
            self.chain,
            {
                "requirement": requirement,
                "route": dump_for_prompt(route),
                "retrieved_items": dump_for_prompt(retrieved_items),
            },
            AnalysisResult,
        )
        if analyzed is not None:
            return analyzed
        return self._fallback(route, retrieved_items)

    def _fallback(self, route: RouteDecision, retrieved_items: list[RetrievedItem]) -> AnalysisResult:
        sources = ", ".join(sorted({item.source for item in retrieved_items})) or "no external context"
        return AnalysisResult(
            summary=f"任务类型为 {route.task_type}。结合 {sources}，需要先明确业务目标、技术边界、影响范围和验收标准。",
            risks=[
                "检索结果质量依赖文档库和代码索引覆盖度，需结合真实业务上下文进一步确认影响范围。",
                "需求若缺少验收标准，后续方案可能难以审查完整性。",
            ],
            impacted_areas=["API 层", "Agent 工作流", "检索模块", "向量存储"],
            assumptions=[
                "系统会使用 LangGraph 编排多 Agent 工作流。",
                "文档和代码会被统一索引到可检索的数据源。",
            ],
        )
