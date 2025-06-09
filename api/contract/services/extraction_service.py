#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
合同信息抽取服务，集成RAGFlow的LLM服务
"""
import json
import logging
from typing import Optional, Dict, Any, List, Type
from collections import OrderedDict

from api.db.services.llm_service import LLMBundle
from api.db import LLMType

# 使用相对导入来避免模块路径问题
try:
    from ..models.contract_models import (
        Contract, ContractBasicInfo, ContractParty, ContractSubject,
        ContractTerms, ContractTerm, ContractComponentType
    )
    from ..utils.prompts import (
        get_system_prompt, format_contract_extraction
    )
    from ..utils.document_loader import ContractDocumentLoader
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os

    # 添加contract模块路径到sys.path
    contract_path = os.path.dirname(os.path.dirname(__file__))
    if contract_path not in sys.path:
        sys.path.insert(0, contract_path)

    from models.contract_models import (
        Contract, ContractBasicInfo, ContractParty, ContractSubject,
        ContractTerms, ContractTerm, ContractComponentType
    )
    from utils.prompts import (
        get_system_prompt, format_contract_extraction
    )
    from utils.document_loader import ContractDocumentLoader


class ExtractionService:
    """合同信息抽取服务"""
    
    def __init__(self, user_id: str):
        """
        初始化抽取服务
        
        Args:
            user_id: 用户ID，用于LLM服务和文件访问
        """
        self.user_id = user_id
        self.llm_bundle = LLMBundle(user_id, LLMType.CHAT)
        self.document_loader = ContractDocumentLoader(user_id)
    
    def extract_from_file(self, file_id: str, extraction_type: str = "basic") -> Optional[Contract]:
        """
        从文件ID提取合同信息
        
        Args:
            file_id: RAGFlow文件ID
            extraction_type: 提取类型 (basic, detailed, custom)
            
        Returns:
            Optional[Contract]: 提取的合同对象，失败时返回None
        """
        try:
            # 加载文档内容
            contract_text = self.document_loader.load_from_file_id(file_id)
            if not contract_text:
                logging.error(f"Failed to load document content from file {file_id}")
                return None
            
            # 提取合同信息
            return self.extract_from_text(contract_text, extraction_type)
            
        except Exception as e:
            logging.exception(f"Failed to extract contract from file {file_id}: {str(e)}")
            return None
    
    def extract_from_text(self, contract_text: str, extraction_type: str = "basic") -> Optional[Contract]:
        """
        从文本提取合同信息
        
        Args:
            contract_text: 合同文本
            extraction_type: 提取类型 (basic, detailed, custom)
            
        Returns:
            Optional[Contract]: 提取的合同对象，失败时返回None
        """
        try:
            # 定义组件提取顺序
            component_config = OrderedDict([
                (ContractComponentType.BASIC_INFO, ContractBasicInfo),
                (ContractComponentType.PARTIES, List[ContractParty]),
                (ContractComponentType.SUBJECTS, List[ContractSubject]),
                (ContractComponentType.TERMS, ContractTerms)
            ])
            
            extracted_components = {}
            
            # 逐步提取各个组件
            for step, (component_type, model_type) in enumerate(component_config.items(), 1):
                component_name = component_type.value
                logging.info(f"Step {step}: Extracting {component_name}...")
                
                component = self._extract_component(
                    text=contract_text,
                    component_type=model_type,
                    component_enum=component_type
                )
                
                if component is None:
                    if component_type == ContractComponentType.BASIC_INFO:
                        logging.error(f"Failed to extract {component_name}, cannot continue")
                        return None
                    elif component_type == ContractComponentType.PARTIES:
                        logging.warning(f"Failed to extract {component_name}, using empty list")
                        component = []
                    elif component_type == ContractComponentType.SUBJECTS:
                        logging.warning(f"Failed to extract {component_name}, using empty list")
                        component = []
                    elif component_type == ContractComponentType.TERMS:
                        logging.warning(f"Failed to extract {component_name}, using empty object")
                        component = ContractTerms()
                
                extracted_components[component_name] = component
                
                # 记录提取结果
                if component_type == ContractComponentType.BASIC_INFO:
                    logging.info(f"Successfully extracted basic info: {component.title}")
                elif component_type == ContractComponentType.PARTIES:
                    logging.info(f"Successfully extracted parties: {len(component)} parties")
                elif component_type == ContractComponentType.SUBJECTS:
                    logging.info(f"Successfully extracted subjects: {len(component)} subjects")
                elif component_type == ContractComponentType.TERMS:
                    logging.info(f"Successfully extracted terms: {len(component.terms)} term types")
            
            # 构建完整的合同对象
            contract = Contract(
                basic_info=extracted_components["basic_info"],
                parties=extracted_components["parties"],
                subjects=extracted_components["subjects"],
                terms=extracted_components["terms"],
                raw_text=contract_text
            )
            
            logging.info("Contract extraction completed successfully")
            return contract
            
        except Exception as e:
            logging.exception(f"Failed to extract contract from text: {str(e)}")
            return None
    
    def _extract_component(
        self,
        text: str,
        component_type: Type,
        component_enum: ContractComponentType
    ) -> Any:
        """
        提取单个组件
        
        Args:
            text: 合同文本
            component_type: 组件类型
            component_enum: 组件枚举
            
        Returns:
            Any: 提取的组件对象
        """
        try:
            # 构建schema
            if hasattr(component_type, "__origin__") and component_type.__origin__ is list:
                element_schema = component_type.__args__[0].model_json_schema()
                
                if component_enum in [ContractComponentType.PARTIES, ContractComponentType.SUBJECTS]:
                    schema = {
                        "type": "object",
                        "properties": {
                            component_enum.value: {
                                "type": "array",
                                "items": element_schema
                            }
                        },
                        "required": [component_enum.value]
                    }
                else:
                    schema = {"type": "array", "items": element_schema}
            else:
                schema = component_type.model_json_schema()
            
            # 构建提示词
            system_prompt = get_system_prompt()
            user_prompt = format_contract_extraction(
                contract_text=text,
                schema=schema,
                component_type=component_enum,
                language="zh-CN"
            )
            
            # 调用LLM
            component_data = self._call_llm(system_prompt, user_prompt)
            if not component_data:
                return None
            
            # 处理响应数据
            component_data = self._process_component_data(component_data, component_enum)
            
            # 验证并构建对象
            if hasattr(component_type, "__origin__") and component_type.__origin__ is list:
                element_type = component_type.__args__[0]
                return [element_type.model_validate(item) for item in component_data]
            else:
                return component_type.model_validate(component_data)
                
        except Exception as e:
            logging.exception(f"Failed to extract component {component_enum.value}: {str(e)}")
            return None
    
    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用RAGFlow的LLM服务

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            Optional[Dict[str, Any]]: LLM响应的JSON数据
        """
        try:
            # 构建对话历史 - 只包含用户消息，系统消息会由LLMBundle自动处理
            history = [{"role": "user", "content": user_prompt}]

            # 生成配置 - 设置较低温度以获得更稳定的JSON输出
            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 4096
            }

            # 调用RAGFlow的LLM服务
            # system_prompt: 系统提示词（独立参数）
            # history: 对话历史（用户和助手消息列表）
            # gen_conf: 生成配置（温度、最大token等）
            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response")
                return None

            # 解析JSON响应
            return self._parse_llm_json_response(response)

        except Exception as e:
            logging.exception(f"Failed to call LLM: {str(e)}")
            return None
    
    def _parse_llm_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """
        解析LLM的JSON响应
        
        Args:
            response: LLM响应文本
            
        Returns:
            Optional[Dict[str, Any]]: 解析的JSON数据
        """
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # 尝试提取JSON部分
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                
                # 尝试提取数组
                array_match = re.search(r'\[.*\]', response, re.DOTALL)
                if array_match:
                    return json.loads(array_match.group())
                    
                logging.error(f"Failed to extract JSON from response: {response[:200]}...")
                return None
                
            except Exception as e:
                logging.exception(f"Failed to parse LLM JSON response: {str(e)}")
                return None

    def _process_component_data(self, component_data: Any, component_enum: ContractComponentType) -> Any:
        """
        处理组件数据，确保格式正确

        Args:
            component_data: 原始组件数据
            component_enum: 组件类型枚举

        Returns:
            Any: 处理后的组件数据
        """
        try:
            if component_enum == ContractComponentType.BASIC_INFO:
                # 处理基本信息的特殊字段
                if isinstance(component_data, dict):
                    # 处理日期字段
                    if "dates" in component_data and isinstance(component_data["dates"], dict):
                        dates = component_data["dates"]
                        date_fields = ["signing_date", "effective_date", "expiration_date"]
                        for field in date_fields:
                            if field in dates and dates[field] is not None:
                                component_data[field] = dates[field]
                        del component_data["dates"]

                    # 移除位置信息
                    if "positions" in component_data:
                        del component_data["positions"]

                return component_data

            elif component_enum in [ContractComponentType.PARTIES, ContractComponentType.SUBJECTS]:
                component_key = component_enum.value

                # 如果是包装在对象中的数组，提取数组
                if isinstance(component_data, dict) and component_key in component_data:
                    component_data = component_data[component_key]

                # 确保是数组格式
                if not isinstance(component_data, list):
                    if isinstance(component_data, dict):
                        # 检查是否是单个对象
                        typical_fields = ["name"]
                        if component_enum == ContractComponentType.SUBJECTS:
                            typical_fields.append("description")
                        if component_enum == ContractComponentType.PARTIES:
                            typical_fields.append("role")

                        if any(key in component_data for key in typical_fields):
                            component_data = [component_data]
                        else:
                            # 尝试从字典值中提取对象
                            items = []
                            for key, value in component_data.items():
                                if isinstance(value, dict) and "name" in value:
                                    items.append(value)
                            component_data = items if items else []
                    else:
                        logging.warning(f"Unexpected {component_key} data type: {type(component_data)}")
                        component_data = []

                return component_data

            else:
                # 其他组件类型直接返回
                return component_data

        except Exception as e:
            logging.exception(f"Failed to process component data for {component_enum.value}: {str(e)}")
            return component_data
