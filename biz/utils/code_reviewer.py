import os
import re
import yaml
import abc
import json
from typing import Dict, List, Optional
import traceback

from biz.utils.log import logger
from biz.llm.factory import Factory
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.agents = self._load_agents()

    def _load_agents(self) -> Dict[str, Dict]:
        """加载所有启用的Agent配置"""
        agents = {}
        agents_dir = "conf/agents"
        
        # 确保agents目录存在
        if not os.path.exists(agents_dir):
            logger.warning(f"Agents directory {agents_dir} does not exist")
            return agents
            
        # 从环境变量获取启用的Agent列表
        enabled_agents = os.getenv('ENABLED_AGENTS', '').split(',')
        enabled_agents = [agent.strip() for agent in enabled_agents if agent.strip()]
        
        if not enabled_agents:
            logger.warning("No agents enabled in .env configuration")
            # 如果没有配置启用的Agent，加载默认的code_review配置
            return self._load_default_config()
            
        # 遍历启用的Agent
        for agent_name in enabled_agents:
            agent_dir = os.path.join(agents_dir, agent_name)
            if not os.path.isdir(agent_dir):
                logger.warning(f"Agent directory {agent_dir} does not exist")
                continue
                
            # 加载agent的提示词配置
            prompt_file = os.path.join(agent_dir, "prompt_templates.yml")
            if not os.path.exists(prompt_file):
                logger.warning(f"Prompt templates file not found for agent {agent_name}")
                continue
                
            try:
                with open(prompt_file, "r", encoding='utf-8') as file:
                    prompt_templates = yaml.safe_load(file)
                    system_prompt = prompt_templates.get('system_prompt')
                    user_prompt = prompt_templates.get('user_prompt')
                    
                    if not system_prompt or not user_prompt:
                        logger.warning(f"Invalid prompt templates for agent {agent_name}")
                        continue
                        
                    agents[agent_name] = {
                        "system_message": {
                            "role": "system",
                            "content": system_prompt
                        },
                        "user_message": {
                            "role": "user",
                            "content": user_prompt
                        }
                    }
            except Exception as e:
                logger.error(f"Error loading agent {agent_name}: {str(e)}")
                continue
                
        # 如果没有成功加载任何Agent，加载默认配置
        if not agents:
            logger.warning("No agents loaded successfully, falling back to default configuration")
            return self._load_default_config()
                
        return agents

    def _load_default_config(self) -> Dict[str, Dict]:
        """加载默认的code_review配置"""
        try:
            with open("conf/prompt_templates.yml", "r", encoding='utf-8') as file:
                prompt_templates = yaml.safe_load(file)
                system_prompt = prompt_templates.get('system_prompt')
                user_prompt = prompt_templates.get('user_prompt')
                
                if system_prompt and user_prompt:
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
                else:
                    logger.error("Invalid default prompt templates configuration")
        except Exception as e:
            logger.error(f"Error loading default configuration: {str(e)}")
        return {}

    def review_code(self, diffs_text: str, commits_text: str = '', system_prompt: str = None, user_prompt: str = None) -> str:
        """
        评审代码
        :param diffs_text: 代码变更内容
        :param commits_text: 提交信息
        :param system_prompt: 系统提示词
        :param user_prompt: 用户提示词
        :return: 评审结果
        """
        try:
            # 尝试解析 diffs_text
            try:
                if isinstance(diffs_text, str):
                    # 尝试解析 JSON 字符串
                    diffs_data = json.loads(diffs_text)
                else:
                    diffs_data = diffs_text
            except json.JSONDecodeError:
                # 如果 JSON 解析失败，保持原始字符串
                diffs_data = diffs_text

            # 处理完整文件内容
            if isinstance(diffs_data, list):
                formatted_changes = []
                for change in diffs_data:
                    if isinstance(change, dict):
                        formatted_change = {
                            'file_path': change.get('new_path', change.get('old_path', '')),
                            'change_type': change.get('change_type', 'modified'),
                            'diff': change.get('diff', ''),
                            'full_content': change.get('full_content', '')
                        }
                        formatted_changes.append(formatted_change)
                diffs_data = formatted_changes

            # 确保 diffs_text 是字符串格式
            if isinstance(diffs_data, (list, dict)):
                diffs_text = json.dumps(diffs_data, ensure_ascii=False, indent=2)

            # 构建发送给大模型的消息
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_prompt:
                messages.append({"role": "user", "content": user_prompt.format(
                    diffs_text=diffs_text,
                    commits_text=commits_text
                )})

            # 打印发送给大模型的数据
            logger.info("=== 发送给大模型的数据 ===")
            logger.info(f"Messages: {messages}")
            logger.info("==========================")

            # 调用大模型
            response = self.call_llm(messages)
            
            # 打印大模型返回的结果
            logger.info("=== 大模型返回结果 ===")
            logger.info(f"Response: {response}")
            logger.info("==========================")
            
            return response

        except Exception as e:
            logger.error(f"Error in review_code: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"代码评审失败: {str(e)}"

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0


class CodeReviewer(BaseReviewer):
    """代码审查实现类"""
    
    def __init__(self):
        super().__init__("code_review")
        
    def call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        调用大模型
        :param messages: 消息列表
        :return: 大模型返回的结果
        """
        try:
            # 打印发送给大模型的数据
            logger.info("=== 发送给大模型的数据 ===")
            logger.info(f"Messages: {messages}")
            logger.info("==========================")

            # 调用大模型
            response = self.client.completions(
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )

            # 打印大模型返回的结果
            logger.info("=== 大模型返回结果 ===")
            logger.info(f"Response: {response}")
            logger.info("==========================")

            return response

        except Exception as e:
            logger.error(f"Error in call_llm: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"调用大模型失败: {str(e)}"

    def review_and_strip_code(self, diffs_text: str, commits_text: str = '') -> str:
        """
        评审代码并处理完整文件内容
        :param diffs_text: 代码变更内容
        :param commits_text: 提交信息
        :return: 评审结果
        """
        try:
            # 尝试解析 diffs_text
            try:
                if isinstance(diffs_text, str):
                    # 尝试解析 JSON 字符串
                    diffs_data = json.loads(diffs_text)
                else:
                    diffs_data = diffs_text
            except json.JSONDecodeError:
                # 如果 JSON 解析失败，保持原始字符串
                diffs_data = diffs_text

            # 处理完整文件内容
            if isinstance(diffs_data, list):
                for change in diffs_data:
                    if isinstance(change, dict) and 'full_content' in change:
                        # 将完整内容添加到 diff 中
                        change['diff'] = f"完整文件内容:\n{change['full_content']}\n\n变更部分:\n{change.get('diff', '')}"

            # 确保 diffs_text 是字符串格式
            if isinstance(diffs_data, (list, dict)):
                diffs_text = json.dumps(diffs_data, ensure_ascii=False)

            # 加载默认配置
            config = self._load_default_config()
            if not config:
                return "无法加载默认配置"

            # 构建消息
            messages = []
            system_message = config.get('code_review', {}).get('system_message')
            user_message = config.get('code_review', {}).get('user_message')
            
            if system_message:
                messages.append(system_message)
            if user_message:
                messages.append({
                    "role": "user",
                    "content": user_message['content'].format(
                        diffs_text=diffs_text,
                        commits_text=commits_text
                    )
                })

            # 调用大模型
            return self.call_llm(messages)

        except Exception as e:
            logger.error(f"Error in review_and_strip_code: {str(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return f"代码评审失败: {str(e)}"

