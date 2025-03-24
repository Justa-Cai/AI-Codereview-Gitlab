import os
import re
import yaml
import abc

from biz.utils.log import logger
from biz.llm.factory import Factory
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> dict:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        with open(prompt_templates_file, "r") as file:
            prompt_templates = yaml.safe_load(file)
            system_prompt = prompt_templates['system_prompt']
            user_prompt = prompt_templates['user_prompt']

        if not system_prompt or not user_prompt:
            logger.warning(f"未找到提示词配置{prompt_templates_file}")
            # 抛出异常
            raise Exception(f"未找到提示词配置{prompt_templates_file},或配置格式不正确")

        return {
            "code_review": {
                "system_message": {
                    "role": "system",
                    "content": system_prompt
                },
                "user_message": {
                    "role": "user",
                    "content": user_prompt
                }
            }
        }

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review代码，并返回结果"""
        prompts = self.prompts["code_review"]
        messages = [
            prompts["system_message"],
            {
                "role": "user",
                "content": prompts["user_message"]["content"].format(
                    diffs_text=diffs_text,
                    commits_text=commits_text
                )
            }
        ]
        return self.call_llm(messages)

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0

