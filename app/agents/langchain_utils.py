import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.config import settings

StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


def create_chat_model():
    """Creates the configured OpenAI-compatible ChatModel when available."""
    if not settings.openai_api_key:
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    kwargs: dict[str, Any] = {
        "model": settings.llm_model_name,
        "api_key": settings.openai_api_key,
        "temperature": 0,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**kwargs)


def build_structured_chain(system_prompt: str, human_prompt: str, output_schema: type[StructuredModel], chat_model=None):
    """Builds a PromptTemplate -> ChatModel -> Pydantic structured output chain."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    model = chat_model or create_chat_model()
    if model is None or not hasattr(model, "with_structured_output"):
        return None

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", human_prompt),
        ]
    )
    return prompt | model.with_structured_output(output_schema)


def invoke_structured(chain, inputs: dict[str, Any], output_schema: type[StructuredModel]) -> StructuredModel | None:
    """Invokes a LangChain Runnable and normalizes the result into a Pydantic model."""
    if chain is None:
        return None

    result = chain.invoke(inputs)
    if isinstance(result, output_schema):
        return result
    if isinstance(result, dict):
        if hasattr(output_schema, "model_validate"):
            return output_schema.model_validate(result)
        return output_schema.parse_obj(result)
    return None


def dump_for_prompt(value: Any) -> str:
    """Serializes Pydantic models and lists into compact prompt-friendly text."""
    if isinstance(value, BaseModel):
        if hasattr(value, "model_dump"):
            return json.dumps(value.model_dump(mode="json"), ensure_ascii=False)
        return value.json(ensure_ascii=False)
    if isinstance(value, list):
        return "\n".join(dump_for_prompt(item) for item in value)
    return str(value)
