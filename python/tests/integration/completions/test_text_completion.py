# Copyright (c) Microsoft. All rights reserved.

import platform
import sys
from functools import partial, reduce
from typing import Any

import pytest
from openai import AsyncAzureOpenAI

from semantic_kernel.connectors.ai.bedrock.bedrock_prompt_execution_settings import BedrockTextPromptExecutionSettings
from semantic_kernel.connectors.ai.bedrock.services.bedrock_text_completion import BedrockTextCompletion
from semantic_kernel.connectors.ai.google.google_ai.google_ai_prompt_execution_settings import (
    GoogleAITextPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.google.google_ai.services.google_ai_text_completion import GoogleAITextCompletion
from semantic_kernel.connectors.ai.google.vertex_ai.services.vertex_ai_text_completion import VertexAITextCompletion
from semantic_kernel.connectors.ai.google.vertex_ai.vertex_ai_prompt_execution_settings import (
    VertexAITextPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.hugging_face.hf_prompt_execution_settings import HuggingFacePromptExecutionSettings
from semantic_kernel.connectors.ai.hugging_face.services.hf_text_completion import HuggingFaceTextCompletion
from semantic_kernel.connectors.ai.ollama.ollama_prompt_execution_settings import OllamaTextPromptExecutionSettings
from semantic_kernel.connectors.ai.ollama.services.ollama_text_completion import OllamaTextCompletion
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import (
    OpenAITextPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.open_ai.services.azure_text_completion import AzureTextCompletion
from semantic_kernel.connectors.ai.open_ai.services.open_ai_text_completion import OpenAITextCompletion
from semantic_kernel.connectors.ai.open_ai.settings.azure_open_ai_settings import AzureOpenAISettings
from semantic_kernel.connectors.ai.text_completion_client_base import TextCompletionClientBase
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.text_content import TextContent

if sys.version_info >= (3, 12):
    from typing import override  # pragma: no cover
else:
    from typing_extensions import override  # pragma: no cover

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from tests.integration.completions.completion_test_base import CompletionTestBase, ServiceType
from tests.integration.completions.test_utils import is_service_setup_for_testing, retry

ollama_setup: bool = is_service_setup_for_testing("OLLAMA_MODEL")
google_ai_setup: bool = is_service_setup_for_testing("GOOGLE_AI_API_KEY")
vertex_ai_setup: bool = is_service_setup_for_testing("VERTEX_AI_PROJECT_ID")
onnx_setup: bool = is_service_setup_for_testing("ONNX_GEN_AI_TEXT_MODEL_FOLDER")

skip_on_mac_available = platform.system() == "Darwin"
if not skip_on_mac_available:
    from semantic_kernel.connectors.ai.onnx import OnnxGenAIPromptExecutionSettings, OnnxGenAITextCompletion


pytestmark = pytest.mark.parametrize(
    "service_id, execution_settings_kwargs, inputs, kwargs",
    [
        pytest.param(
            "openai",
            {},
            ["Repeat the word Hello once"],
            {},
            id="openai_text_completion",
        ),
        pytest.param(
            "azure",
            {},
            ["Repeat the word Hello once"],
            {},
            id="azure_text_completion",
        ),
        pytest.param(
            "hf_t2t",
            {},
            ["translate English to Dutch: Hello"],
            {},
            id="huggingface_text_completion_translation",
        ),
        pytest.param(
            "hf_summ",
            {},
            [
                """Summarize: Whales are fully aquatic, open-ocean animals:
        they can feed, mate, give birth, suckle and raise their young at sea.
        Whales range in size from the 2.6 metres (8.5 ft) and 135 kilograms (298 lb)
        dwarf sperm whale to the 29.9 metres (98 ft) and 190 tonnes (210 short tons) blue whale,
        which is the largest known animal that has ever lived. The sperm whale is the largest
        toothed predator on Earth. Several whale species exhibit sexual dimorphism,
        in that the females are larger than males."""
            ],
            {},
            id="huggingface_text_completion_summarization",
        ),
        pytest.param(
            "hf_gen",
            {},
            ["Hello, I like sleeping and "],
            {},
            id="huggingface_text_completion_generation",
        ),
        pytest.param(
            "ollama",
            {},
            ["Repeat the word Hello once"],
            {},
            marks=pytest.mark.skipif(not ollama_setup, reason="Need local Ollama setup"),
            id="ollama_text_completion",
        ),
        pytest.param(
            "google_ai",
            {},
            ["Repeat the word Hello once"],
            {},
            marks=pytest.mark.skip(reason="Skipping due to 429s from Google AI."),
            id="google_ai_text_completion",
        ),
        pytest.param(
            "vertex_ai",
            {},
            ["Repeat the word Hello once"],
            {},
            marks=pytest.mark.skipif(not vertex_ai_setup, reason="Need VertexAI setup"),
            id="vertex_ai_text_completion",
        ),
        pytest.param(
            "onnx_gen_ai",
            {},
            ["<|user|>Repeat the word Hello<|end|><|assistant|>"],
            {},
            marks=pytest.mark.skipif(not onnx_setup, reason="Need local Onnx setup"),
            id="onnx_gen_ai_text_completion",
        ),
        pytest.param(
            "bedrock_amazon_titan",
            {},
            ["Repeat the word Hello once"],
            {},
            id="bedrock_amazon_titan_text_completion",
        ),
        pytest.param(
            "bedrock_anthropic_claude",
            {},
            ["Repeat the word Hello once"],
            {"streaming": False},  # Streaming is not supported for models from this provider
            id="bedrock_anthropic_claude_text_completion",
        ),
        pytest.param(
            "bedrock_cohere_command",
            {},
            ["Repeat the word Hello once"],
            {"streaming": False},  # Streaming is not supported for models from this provider
            id="bedrock_cohere_command_text_completion",
        ),
        pytest.param(
            "bedrock_ai21labs",
            {},
            ["Repeat the word Hello once"],
            {"streaming": False},  # Streaming is not supported for models from this provider
            id="bedrock_ai21labs_text_completion",
        ),
        pytest.param(
            "bedrock_meta_llama",
            {},
            ["Repeat the word Hello once"],
            {"streaming": False},  # Streaming is not supported for models from this provider
            id="bedrock_meta_llama_text_completion",
        ),
        pytest.param(
            "bedrock_mistralai",
            {},
            ["Repeat the word Hello once"],
            {"streaming": False},  # Streaming is not supported for models from this provider
            id="bedrock_mistralai_text_completion",
        ),
    ],
)


@pytest.mark.asyncio(scope="module")
class TestTextCompletion(CompletionTestBase):
    """Test class for text completion"""

    @override
    @pytest.fixture(scope="class")
    def services(self) -> dict[str, tuple[ServiceType, type[PromptExecutionSettings]]]:
        azure_openai_settings = AzureOpenAISettings.create()
        endpoint = azure_openai_settings.endpoint
        deployment_name = azure_openai_settings.text_deployment_name
        ad_token = azure_openai_settings.get_azure_openai_auth_token()
        api_version = azure_openai_settings.api_version
        azure_custom_client = AzureTextCompletion(
            async_client=AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                azure_deployment=deployment_name,
                azure_ad_token=ad_token,
                api_version=api_version,
                default_headers={"Test-User-X-ID": "test"},
            ),
        )

        return {
            "openai": (OpenAITextCompletion(), OpenAITextPromptExecutionSettings),
            "azure": (AzureTextCompletion(), OpenAITextPromptExecutionSettings),
            "azure_custom_client": (azure_custom_client, OpenAITextPromptExecutionSettings),
            "ollama": (OllamaTextCompletion() if ollama_setup else None, OllamaTextPromptExecutionSettings),
            "google_ai": (GoogleAITextCompletion() if google_ai_setup else None, GoogleAITextPromptExecutionSettings),
            "vertex_ai": (VertexAITextCompletion() if vertex_ai_setup else None, VertexAITextPromptExecutionSettings),
            "hf_t2t": (
                HuggingFaceTextCompletion(
                    service_id="patrickvonplaten/t5-tiny-random",
                    ai_model_id="patrickvonplaten/t5-tiny-random",
                    task="text2text-generation",
                ),
                HuggingFacePromptExecutionSettings,
            ),
            "hf_summ": (
                HuggingFaceTextCompletion(
                    service_id="jotamunz/billsum_tiny_summarization",
                    ai_model_id="jotamunz/billsum_tiny_summarization",
                    task="summarization",
                ),
                HuggingFacePromptExecutionSettings,
            ),
            "hf_gen": (
                HuggingFaceTextCompletion(
                    service_id="HuggingFaceM4/tiny-random-LlamaForCausalLM",
                    ai_model_id="HuggingFaceM4/tiny-random-LlamaForCausalLM",
                    task="text-generation",
                ),
                HuggingFacePromptExecutionSettings,
            ),
            "onnx_gen_ai": (
                OnnxGenAITextCompletion() if onnx_setup else None,
                OnnxGenAIPromptExecutionSettings if not skip_on_mac_available else None,
            ),
            # Amazon Bedrock supports models from multiple providers but requests to and responses from the models are
            # inconsistent. So we need to test each model separately.
            "bedrock_amazon_titan": (
                BedrockTextCompletion(model_id="amazon.titan-text-premier-v1:0"),
                BedrockTextPromptExecutionSettings,
            ),
            "bedrock_anthropic_claude": (
                BedrockTextCompletion(model_id="anthropic.claude-v2"),
                BedrockTextPromptExecutionSettings,
            ),
            "bedrock_cohere_command": (
                BedrockTextCompletion(model_id="cohere.command-text-v14"),
                BedrockTextPromptExecutionSettings,
            ),
            "bedrock_ai21labs": (
                BedrockTextCompletion(model_id="ai21.j2-mid-v1"),
                BedrockTextPromptExecutionSettings,
            ),
            "bedrock_meta_llama": (
                BedrockTextCompletion(model_id="meta.llama3-70b-instruct-v1:0"),
                BedrockTextPromptExecutionSettings,
            ),
            "bedrock_mistralai": (
                BedrockTextCompletion(model_id="mistral.mistral-7b-instruct-v0:2"),
                BedrockTextPromptExecutionSettings,
            ),
        }

    async def get_text_completion_response(
        self,
        service: TextCompletionClientBase,
        execution_settings: PromptExecutionSettings,
        prompt: str,
        stream: bool,
    ) -> Any:
        """Get response from the service

        Args:
            kernel (Kernel): Kernel instance.
            service (ChatCompletionClientBase): Chat completion service.
            execution_settings (PromptExecutionSettings): Execution settings.
            prompt (str): Input string.
            stream (bool): Stream flag.
        """
        if stream:
            response = service.get_streaming_text_content(
                prompt=prompt,
                settings=execution_settings,
            )
            parts = [part async for part in response]
            if parts:
                response = reduce(lambda p, r: p + r, parts)
            else:
                raise AssertionError("No response")
        else:
            response = await service.get_text_content(
                prompt=prompt,
                settings=execution_settings,
            )

        return response

    @override
    async def test_completion(
        self,
        kernel: Kernel,
        service_id: str,
        services: dict[str, tuple[ServiceType, type[PromptExecutionSettings]]],
        execution_settings_kwargs: dict[str, Any],
        inputs: list[str | ChatMessageContent | list[ChatMessageContent]],
        kwargs: dict[str, Any],
    ) -> None:
        await self._test_helper(service_id, services, execution_settings_kwargs, inputs, False)

    @override
    async def test_streaming_completion(
        self,
        kernel: Kernel,
        service_id: str,
        services: dict[str, tuple[ServiceType, type[PromptExecutionSettings]]],
        execution_settings_kwargs: dict[str, Any],
        inputs: list[str | ChatMessageContent | list[ChatMessageContent]],
        kwargs: dict[str, Any],
    ):
        if "streaming" in kwargs and not kwargs["streaming"]:
            pytest.skip("Skipping streaming test")

        await self._test_helper(service_id, services, execution_settings_kwargs, inputs, True)

    @override
    def evaluate(self, test_target: Any, **kwargs):
        print(test_target)
        if isinstance(test_target, TextContent):
            # Test is considered successful if the test_target is not empty
            assert test_target.text, "Error: Empty test target"
            return
        raise AssertionError(f"Unexpected output: {test_target}, type: {type(test_target)}")

    async def _test_helper(
        self,
        service_id: str,
        services: dict[str, tuple[ServiceType, type[PromptExecutionSettings]]],
        execution_settings_kwargs: dict[str, Any],
        inputs: list[str],
        stream: bool,
    ):
        service, settings_type = services[service_id]

        for test_input in inputs:
            response = await retry(
                partial(
                    self.get_text_completion_response,
                    service=service,
                    execution_settings=settings_type(**execution_settings_kwargs),
                    prompt=test_input,
                    stream=stream,
                ),
                retries=5,
            )
            self.evaluate(response)
