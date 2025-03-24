import os
import re
from typing import Dict, List, Optional

from openai import OpenAI

from biz.llm.client.base import BaseClient
from biz.llm.types import NotGiven, NOT_GIVEN


class OpenAIClient(BaseClient):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com")
        if not self.api_key:
            raise ValueError("API key is required. Please provide it or set it in the environment variables.")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.default_model = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")

    def _extract_content(self, content: str) -> str:
        """
        从内容中提取<think>...</think>标签之外的部分。

        Args:
            content (str): 原始内容。

        Returns:
            str: 提取后的内容。
        """
        if "<think>" in content and "</think>" not in content:
            # 大模型回复的时候，思考链有可能截断，那么果断忽略回复，返回空
            return "COT ABORT!"
        elif "<think>" not in content and "</think>" in content:
            return content.split("</think>", 1)[1].strip()
        elif re.search(r'<think>.*?</think>', content, re.DOTALL):
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
        return content
    
    def completions(self,
                    messages: List[Dict[str, str]],
                    model: Optional[str] | NotGiven = NOT_GIVEN,
                    ) -> str:
        model = model or self.default_model
        stream = os.getenv("OPENAI_API_STREAM", "false").lower() == "true"
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=stream
        )
        if stream:
            content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content += chunk.choices[0].delta.content
            return self._extract_content(content)
        else:
            return self._extract_content(response.choices[0].message.content)

    def stream_completions(self,
                           messages: List[Dict[str, str]],
                           model: Optional[str] | NotGiven = NOT_GIVEN,
                           temperature: float = 0.7,
                           max_tokens: Optional[int] = None,
                           ) -> str:
        model = model or self.default_model
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=temperature,
                max_tokens=max_tokens
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            yield "抱歉，AI 服务出现错误，请稍后重试。"
