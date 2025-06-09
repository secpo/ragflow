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
合同风险分析服务，集成RAGFlow的LLM服务
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional

from api.db.services.llm_service import LLMBundle
from api.db import LLMType

# 使用相对导入来避免模块路径问题
try:
    from ..models.contract_models import (
        Contract, ContractRisk, ContractRiskAnalysis
    )
    from ..utils.prompts import format_risk_extraction_prompt, get_risk_analysis_system_prompt
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os

    # 添加contract模块路径到sys.path
    contract_path = os.path.dirname(os.path.dirname(__file__))
    if contract_path not in sys.path:
        sys.path.insert(0, contract_path)

    from models.contract_models import (
        Contract, ContractRisk, ContractRiskAnalysis
    )
    from utils.prompts import format_risk_extraction_prompt, get_risk_analysis_system_prompt


class RiskService:
    """合同风险分析服务"""
    
    def __init__(self, user_id: str):
        """
        初始化风险分析服务
        
        Args:
            user_id: 用户ID，用于LLM服务
        """
        self.user_id = user_id
        self.llm_bundle = LLMBundle(user_id, LLMType.CHAT)
    
    def analyze_risks(self, contract: Contract, analysis_type: str = "basic") -> Optional[ContractRiskAnalysis]:
        """
        分析合同风险
        
        Args:
            contract: 合同对象
            analysis_type: 分析类型 (basic, comprehensive)
            
        Returns:
            Optional[ContractRiskAnalysis]: 风险分析结果，失败时返回None
        """
        try:
            # 初始化风险分析对象
            risk_analysis = ContractRiskAnalysis(
                contract_id=contract.id,
                risks=[],
                summary="",
                overall_risk_level="低",
                analysis_date=time.strftime("%Y-%m-%d")
            )
            
            # 提取风险点
            logging.info("Starting risk extraction...")
            risks = self._extract_risks(contract)
            
            if not risks:
                logging.warning("No risks extracted from contract")
                return risk_analysis
            
            logging.info(f"Extracted {len(risks)} risk points")
            
            # 更新风险分析结果
            risk_analysis.risks = risks
            risk_analysis.overall_risk_level = self._evaluate_overall_risk_level(risks)
            risk_analysis.summary = self._generate_risk_summary(contract, risks)
            
            logging.info("Risk analysis completed successfully")
            return risk_analysis
            
        except Exception as e:
            logging.exception(f"Failed to analyze contract risks: {str(e)}")
            return None
    
    def _extract_risks(self, contract: Contract) -> List[ContractRisk]:
        """
        从合同中提取风险点
        
        Args:
            contract: 合同对象
            
        Returns:
            List[ContractRisk]: 风险点列表
        """
        try:
            # 构建提示词
            user_prompt = format_risk_extraction_prompt(contract, language="zh-CN")
            
            # 调用LLM
            risk_data = self._call_llm_for_risks(user_prompt)
            if not risk_data:
                return []
            
            # 解析风险数据
            risks = []
            try:
                if "risks" in risk_data and isinstance(risk_data["risks"], list):
                    risk_list = risk_data["risks"]
                elif isinstance(risk_data, list):
                    risk_list = risk_data
                else:
                    logging.error("Unable to parse risk data structure")
                    return []
                
                for risk_item in risk_list:
                    try:
                        risk = ContractRisk.model_validate(risk_item)
                        risks.append(risk)
                    except Exception as e:
                        logging.warning(f"Failed to validate risk item: {str(e)}")
                        continue
                        
            except Exception as e:
                logging.exception(f"Failed to parse risk data: {str(e)}")
                return []
            
            return risks
            
        except Exception as e:
            logging.exception(f"Failed to extract risks: {str(e)}")
            return []
    
    def _call_llm_for_risks(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用LLM进行风险分析

        Args:
            user_prompt: 用户提示词

        Returns:
            Optional[Dict[str, Any]]: LLM响应的JSON数据
        """
        try:
            # 使用专门的风险分析系统提示词
            system_prompt = get_risk_analysis_system_prompt()

            # 构建对话历史 - 只包含用户消息
            history = [{"role": "user", "content": user_prompt}]

            # 生成配置
            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 4096
            }

            # 调用RAGFlow的LLM服务
            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response for risk analysis")
                return None

            # 解析JSON响应
            return self._parse_llm_json_response(response)

        except Exception as e:
            logging.exception(f"Failed to call LLM for risk analysis: {str(e)}")
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
                    return {"risks": json.loads(array_match.group())}
                    
                logging.error(f"Failed to extract JSON from response: {response[:200]}...")
                return None
                
            except Exception as e:
                logging.exception(f"Failed to parse LLM JSON response: {str(e)}")
                return None
    
    def _generate_risk_summary(self, contract: Contract, risks: List[ContractRisk]) -> str:
        """
        生成风险分析摘要
        
        Args:
            contract: 合同对象
            risks: 风险点列表
            
        Returns:
            str: 风险分析摘要
        """
        try:
            high_risks = [risk for risk in risks if risk.level == "高"]
            medium_risks = [risk for risk in risks if risk.level == "中"]
            low_risks = [risk for risk in risks if risk.level == "低"]
            
            summary = f"本合同共识别出{len(risks)}个风险点，其中高风险{len(high_risks)}个，中风险{len(medium_risks)}个，低风险{len(low_risks)}个。"
            
            if high_risks:
                summary += "\n\n主要高风险点包括："
                for i, risk in enumerate(high_risks, 1):
                    summary += f"\n{i}. {risk.risk_type}：{risk.description}"
            
            if medium_risks and len(high_risks) == 0:
                summary += "\n\n主要中风险点包括："
                for i, risk in enumerate(medium_risks[:3], 1):  # 最多显示3个
                    summary += f"\n{i}. {risk.risk_type}：{risk.description}"
            
            return summary
            
        except Exception as e:
            logging.exception(f"Failed to generate risk summary: {str(e)}")
            return f"本合同共识别出{len(risks)}个风险点。"
    
    def _evaluate_overall_risk_level(self, risks: List[ContractRisk]) -> str:
        """
        评估整体风险等级
        
        Args:
            risks: 风险点列表
            
        Returns:
            str: 整体风险等级 (高/中/低)
        """
        try:
            high_risks = [risk for risk in risks if risk.level == "高"]
            medium_risks = [risk for risk in risks if risk.level == "中"]
            
            # 风险等级评估逻辑
            if len(high_risks) >= 3 or (len(high_risks) >= 1 and len(medium_risks) >= 3):
                return "高"
            elif len(high_risks) >= 1 or len(medium_risks) >= 2:
                return "中"
            else:
                return "低"
                
        except Exception as e:
            logging.exception(f"Failed to evaluate overall risk level: {str(e)}")
            return "中"  # 默认返回中等风险
