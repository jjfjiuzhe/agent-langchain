from app.agents.langchain_utils import build_structured_chain, dump_for_prompt, invoke_structured
from app.schemas.response import AnalysisResult, PlanStep, PlanningResult, ReviewResult


class PlanningAgent:
    """Generates an implementation plan from analysis results."""

    def __init__(self, chain=None, chat_model=None) -> None:
        self.chain = chain or build_structured_chain(
            system_prompt=(
                "你是研发实施方案 Agent。请根据分析结果和可选审查反馈，输出结构化实施策略与步骤。"
            ),
            human_prompt="分析结果：{analysis}\n审查反馈：{review_feedback}",
            output_schema=PlanningResult,
            chat_model=chat_model,
        )

    def run(self, analysis: AnalysisResult, review_feedback: ReviewResult | None = None) -> PlanningResult:
        planned = invoke_structured(
            self.chain,
            {
                "analysis": dump_for_prompt(analysis),
                "review_feedback": dump_for_prompt(review_feedback) if review_feedback else "无",
            },
            PlanningResult,
        )
        if planned is not None:
            return planned
        return self._fallback(review_feedback)

    def _fallback(self, review_feedback: ReviewResult | None = None) -> PlanningResult:
        feedback_step = []
        if review_feedback and review_feedback.missing_items:
            feedback_step.append(
                PlanStep(
                    title="补齐审查缺口",
                    description=f"根据审查反馈补齐：{', '.join(review_feedback.missing_items)}。",
                    deliverables=["修订后的分析结论", "修订后的实施方案"],
                )
            )

        return PlanningResult(
            strategy="采用分层 Agent 架构：Router 决策入口，Retrieval 补充上下文，Analysis 输出影响分析，Planning 生成实施步骤，Review 做最终质量门禁。",
            steps=[
                *feedback_step,
                PlanStep(
                    title="接入真实检索源",
                    description="完善 DocRetriever、CodeRetriever 和 PGVectorStore，实现文档库、代码库与 PostgreSQL + PGVector 的真实检索。",
                    deliverables=["文档检索器", "代码检索器", "向量存储适配器"],
                ),
                PlanStep(
                    title="完善 Agent 提示词与模型调用",
                    description="使用 LangChain PromptTemplate 和 ChatModel 封装每个 Agent 的推理逻辑。",
                    deliverables=["Agent prompt", "LLM client 配置", "结构化输出解析"],
                ),
                PlanStep(
                    title="强化 LangGraph 工作流",
                    description="补充条件边、错误处理、审查失败后的回退修改路径。",
                    deliverables=["状态图", "条件路由", "回归测试"],
                ),
            ],
        )
