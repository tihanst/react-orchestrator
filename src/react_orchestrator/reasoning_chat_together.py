from typing import Any, ClassVar

from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from langchain_together import ChatTogether


class ReasoningChatTogether(ChatTogether):
    REASONING_FIELDS: ClassVar[tuple[str, ...]] = (
        "reasoning_content",
        "reasoning",
    )

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation = super()._convert_chunk_to_generation_chunk(
            chunk,
            default_chunk_class,
            base_generation_info,
        )

        if generation is None:
            return None

        if not isinstance(generation.message, AIMessageChunk):
            return generation

        choices = chunk.get("choices", []) or chunk.get("chunk", {}).get(
            "choices",
            [],
        )

        if not choices:
            return generation

        delta = choices[0].get("delta") or {}

        for field in self.REASONING_FIELDS:
            if field in delta and delta[field] is not None:
                generation.message.additional_kwargs[field] = delta[field]

        return generation

    def _get_request_payload(
        self,
        input_: Any,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        messages = self._convert_input(input_).to_messages()

        payload = super()._get_request_payload(
            input_,
            stop=stop,
            **kwargs,
        )

        api_messages = payload.get("messages")

        if not isinstance(api_messages, list):
            return payload

        for message, api_message in zip(messages, api_messages):
            if not isinstance(message, AIMessage):
                continue

            for field in self.REASONING_FIELDS:
                if field in message.additional_kwargs:
                    api_message[field] = message.additional_kwargs[field]

        return payload
