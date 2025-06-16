import logging
import uuid
import json
import time
from enum import Enum
from typing import Optional, Dict, Any, List, Generator
from pydantic import BaseModel, Field
from flask import request, Response
from flask_login import login_required, current_user
from api.db.services.file_service import FileService
from api.db.services.llm_service import LLMBundle
from api.db import LLMType
from api.utils.api_utils import get_json_result, get_data_error_result, server_error_response
from api import settings

class DocumentType(str, Enum):
    BUSINESS_PLAN = "business_plan"
    INDUSTRY_REPORT = "industry_report"
    OTHER_REPORT = "other_report"

class AnalysisType(str, Enum):
    ANALYSIS = "analysis"
    HTML_CONVERSION = "html_conversion"

class DocumentAnalysisRequest(BaseModel):
    file_id: str = Field(..., description="文件ID")
    analysis_type: AnalysisType = Field(..., description="分析类型")
    document_type: DocumentType = Field(..., description="文档类型")
    file_content: Optional[str] = Field(None, description="文件内容")
    analysis_report: Optional[str] = Field(None, description="分析报告内容，用于HTML转换")

class DocumentAnalysisResponse(BaseModel):
    analysis_id: str = Field(..., description="分析ID")
    basic_analysis: Optional[str] = Field(None, description="基础分析结果")
    html_analysis: Optional[str] = Field(None, description="HTML分析结果")
    status: str = Field(..., description="分析状态")
    created_at: str = Field(..., description="创建时间")

def get_system_prompt(document_type: DocumentType) -> str:
    role_config = {
        DocumentType.BUSINESS_PLAN: {
            "title": "Business Plan Analyst",
            "background": "senior investment analyst and business consultant with 15+ years of experience in venture capital, private equity, and startup evaluation",
            "core_expertise": [
                "Investment due diligence and startup valuation methodologies",
                "Business model validation, optimization, and scalability assessment",
                "Market opportunity analysis and competitive positioning",
                "Financial modeling, projections, and investment return analysis",
                "Risk assessment and mitigation strategy development",
                "Entrepreneurial ecosystem and funding landscape knowledge"
            ],
            "analytical_focus": [
                "Evaluate from an investor's perspective with focus on viability, scalability, and ROI potential",
                "Apply rigorous due diligence standards and investment criteria",
                "Assess both opportunities and risks with balanced judgment",
                "Provide actionable insights for investment decision-making",
                "Consider market timing, competitive dynamics, and execution capabilities"
            ],
            "output_style": "professional, decisive analysis with clear investment recommendations based on industry best practices"
        },
        DocumentType.INDUSTRY_REPORT: {
            "title": "Industry Research Analyst",
            "background": "senior market research specialist with deep expertise in industry analysis, economic forecasting, and strategic market intelligence",
            "core_expertise": [
                "Macroeconomic and industry trend analysis with quantitative modeling",
                "Market sizing, segmentation, and growth trajectory assessment",
                "Competitive landscape mapping and strategic group analysis",
                "Technology innovation assessment and disruption impact analysis",
                "Policy and regulatory environment impact evaluation",
                "Investment flow analysis and market opportunity identification"
            ],
            "analytical_focus": [
                "Provide objective, data-driven insights with rigorous analytical methodology",
                "Focus on accuracy, evidence-based conclusions, and statistical validation",
                "Identify key trends, patterns, and inflection points in market dynamics",
                "Assess both current state and future projections with confidence intervals",
                "Consider multiple scenarios and risk factors in forecasting"
            ],
            "output_style": "comprehensive, research-grade analysis with clear methodology and supporting evidence"
        },
        DocumentType.OTHER_REPORT: {
            "title": "Document Analyst",
            "background": "professional information analyst with extensive expertise in document analysis, content evaluation, and knowledge extraction",
            "core_expertise": [
                "Document structure analysis and information architecture assessment",
                "Content quality evaluation and logical consistency verification",
                "Key information extraction and insight synthesis",
                "Cross-referencing and fact validation methodologies",
                "Information value assessment and practical application analysis",
                "Communication effectiveness and clarity evaluation"
            ],
            "analytical_focus": [
                "Maintain objectivity and neutrality in analysis without bias",
                "Focus on information completeness, accuracy, and logical coherence",
                "Extract actionable insights and practical value from content",
                "Identify gaps, inconsistencies, and areas for improvement",
                "Provide structured analysis with clear categorization and prioritization"
            ],
            "output_style": "thorough, systematic analysis with focus on information utility and practical application"
        }
    }

    config = role_config.get(document_type, role_config[DocumentType.OTHER_REPORT])

    system_prompt = f"""
    You are **IridumAI {config['title']}**, a {config['background']}.
    Your professional expertise includes:
    {chr(10).join(f"{i+1}. {expertise}" for i, expertise in enumerate(config['core_expertise']))}

    Your analytical approach:
    {chr(10).join(f"- {focus}" for focus in config['analytical_focus'])}

    Analyze all information objectively and provide accurate, helpful insights based on the document content.
    Do not make assumptions beyond what is explicitly stated in the documents.
    Always structure your analysis in a logical, professional manner with clear headings and detailed explanations.

    Deliver {config['output_style']}.
    """
    return system_prompt.strip()

def get_business_plan_analysis_prompt(file_content: str) -> str:
    from datetime import datetime
    current_time = datetime.now().strftime("%Y年%m月%d日")
    user_prompt = f"""
请基于{current_time}的市场环境，对以下商业计划书进行专业投资分析。

**重要输出要求：**
- 直接输出Markdown格式的分析报告
- 不要使用代码块包裹整个报告
- 不要添加任何前缀说明或后缀总结
- 严格按照以下结构组织内容

**必须按照以下结构输出：**

## 📋 文档摘要
- 项目名称与核心业务
- 目标市场与客户群体
- 商业模式概述
- 融资需求与用途

## 🔍 重点发现
- 核心竞争优势
- 关键成功因素
- 主要风险点
- 市场机会

## ⚠️ 重点关注
- 需要验证的关键假设
- 潜在的执行风险
- 财务可持续性问题
- 竞争威胁

## 💼 投资分析

### 商业模式评估
- 收入模式可行性
- 成本结构合理性
- 盈利能力预测

### 市场与竞争
- 市场规模与增长潜力
- 竞争格局分析
- 差异化优势

### 团队与执行
- 团队能力评估
- 执行计划可行性
- 里程碑设置

### 财务预测
- 收入增长预期
- 现金流状况
- 投资回报预测

## 🎯 投资建议
- 整体投资价值评估
- 建议投资策略
- 关键改进建议

**待分析的商业计划书内容：**

{file_content}

**请严格按照上述结构，用中文输出完整的Markdown格式投资分析报告。**
    """
    return user_prompt.strip()


def get_industry_report_analysis_prompt(file_content: str) -> str:
    from datetime import datetime
    current_time = datetime.now().strftime("%Y年%m月%d日")
    user_prompt = f"""
请基于{current_time}的宏观环境，对以下行业研究报告进行深度分析。

**重要输出要求：**
- 直接输出Markdown格式的分析报告
- 不要使用代码块包裹整个报告
- 不要添加任何前缀说明或后缀总结
- 严格按照以下结构组织内容

**必须按照以下结构输出：**

## 📊 报告摘要
- 行业名称与定义
- 报告时间范围
- 核心数据概览
- 主要结论

## 🔍 重点发现
- 关键市场趋势
- 重要数据指标
- 突出变化点
- 新兴机会

## ⚠️ 重点关注
- 风险因素识别
- 不确定性分析
- 政策影响评估
- 技术变革影响

## 📈 行业分析

### 市场现状
- 市场规模与增长
- 区域分布特征
- 发展阶段判断

### 竞争格局
- 市场集中度
- 主要参与者
- 竞争态势

### 技术趋势
- 技术发展水平
- 创新驱动因素
- 技术壁垒

### 政策环境
- 相关政策梳理
- 政策影响分析
- 未来政策预期

## 🎯 投资与发展
- 投资机会识别
- 风险评估
- 发展建议

**待分析的行业研究报告内容：**

{file_content}

**请严格按照上述结构，用中文输出完整的Markdown格式行业分析报告。**
    """
    return user_prompt.strip()

def get_other_report_analysis_prompt(file_content: str) -> str:
    """获取其他文档分析提示词"""
    from datetime import datetime
    current_time = datetime.now().strftime("%Y年%m月%d日")

    user_prompt = f"""
请基于{current_time}的背景，对以下文档进行全面分析以生成markdown格式的分析报告。

**重要输出要求：**
- 直接输出Markdown格式的分析报告
- 不要使用代码块包裹整个报告
- 不要添加任何前缀说明或后缀总结
- 严格按照以下结构组织内容

**必须按照以下结构输出：**

## 📄 文档摘要
- 文档类型与性质
- 主要内容概述
- 核心观点提炼
- 文档结构特征

## 🔍 重点发现
- 关键信息点
- 重要数据指标
- 核心结论
- 创新观点

## ⚠️ 重点关注
- 逻辑一致性问题
- 数据可靠性疑点
- 论证不足之处
- 潜在偏见或局限

## 📊 内容分析

### 信息质量
- 数据完整性
- 来源可靠性
- 时效性评估

### 逻辑结构
- 论证逻辑
- 结构合理性
- 内容连贯性

### 实用价值
- 应用场景
- 操作指导性
- 参考价值

## 🎯 应用建议
- 使用建议
- 注意事项
- 改进方向

**待分析的文档内容：**

{file_content}

请遵循上述结构，用中文输出，可使用表格，不要有任何解释或多余内容、包裹元素。
    """
    return user_prompt.strip()

def get_html_conversion_prompt(analysis_report: str) -> str:
    """获取HTML转换提示词"""
    user_prompt = f"""
请将以下报告转换为一个单一的完整HTML页面。

**重要输出要求：**
- 直接输出完整的HTML代码
- 不要使用代码块包裹HTML代码
- 不要添加任何前缀说明或后缀总结
- 确保HTML代码可以直接在浏览器中显示

**HTML要求：**
1. 包含完整的HTML文档结构（DOCTYPE、html、head、body）
2. 采用卡片式布局
3. 使用现代CSS样式，确保页面美观、专业
4. 保持原有的Markdown结构和内容
5. 添加适当的颜色、字体、间距等样式
6. 响应式设计，适配不同设备
7. 使用中文字体和适合中文阅读的样式

**待转换的分析报告：**

{analysis_report}

**请直接输出完整的单一HTML文件，不要有任何解释或多余内容、包裹元素。**
    """
    return user_prompt.strip()

class DocumentAnalysisService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm_bundle = LLMBundle(user_id, LLMType.CHAT)



    def analyze_document(self, file_id: str, document_type: DocumentType, file_content: str) -> Optional[str]:
        """分析文档内容"""
        try:
            system_prompt = get_system_prompt(document_type)

            if document_type == DocumentType.BUSINESS_PLAN:
                user_prompt = get_business_plan_analysis_prompt(file_content)
            elif document_type == DocumentType.INDUSTRY_REPORT:
                user_prompt = get_industry_report_analysis_prompt(file_content)
            else:  # OTHER_REPORT
                user_prompt = get_other_report_analysis_prompt(file_content)

            history = [{"role": "user", "content": user_prompt}]

            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 8192
            }

            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response for document analysis")
                return None

            return response.strip()

        except Exception as e:
            logging.exception(f"Failed to analyze document: {str(e)}")
            return None

    def analyze_document_stream(self, file_id: str, document_type: DocumentType, file_content: str) -> Generator[str, None, None]:
        """流式分析文档内容"""
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': '开始分析文档...', 'timestamp': time.time()})}\n\n"

            system_prompt = get_system_prompt(document_type)
            if document_type == DocumentType.BUSINESS_PLAN:
                user_prompt = get_business_plan_analysis_prompt(file_content)
            elif document_type == DocumentType.INDUSTRY_REPORT:
                user_prompt = get_industry_report_analysis_prompt(file_content)
            else:  # OTHER_REPORT
                user_prompt = get_other_report_analysis_prompt(file_content)

            yield f"data: {json.dumps({'type': 'progress', 'message': '正在调用AI模型进行分析...', 'timestamp': time.time()})}\n\n"

            history = [{"role": "user", "content": user_prompt}]

            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 8192
            }

            try:
                # 检查LLM是否支持流式输出
                if hasattr(self.llm_bundle, 'chat_stream'):
                    # 使用流式API
                    accumulated_content = ""
                    for chunk in self.llm_bundle.chat_stream(system_prompt, history, gen_conf):
                        if chunk:
                            accumulated_content += chunk
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'accumulated': accumulated_content, 'timestamp': time.time()})}\n\n"

                    if accumulated_content:
                        # 直接返回累积内容，不进行清理
                        yield f"data: {json.dumps({'type': 'complete', 'content': accumulated_content.strip(), 'timestamp': time.time()})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'AI模型返回空内容', 'timestamp': time.time()})}\n\n"
                else:
                    # 回退到普通API，模拟流式输出
                    yield f"data: {json.dumps({'type': 'progress', 'message': '正在生成分析报告...', 'timestamp': time.time()})}\n\n"

                    response = self.llm_bundle.chat(system_prompt, history, gen_conf)

                    if response:
                        # 直接使用响应内容，不进行清理
                        response_content = response.strip()

                        # 模拟分块输出
                        chunk_size = 100
                        for i in range(0, len(response_content), chunk_size):
                            chunk = response_content[i:i + chunk_size]
                            accumulated = response_content[:i + chunk_size]
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk, 'accumulated': accumulated, 'timestamp': time.time()})}\n\n"
                            time.sleep(0.05)  # 模拟流式延迟

                        yield f"data: {json.dumps({'type': 'complete', 'content': response_content, 'timestamp': time.time()})}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': 'AI模型返回空内容', 'timestamp': time.time()})}\n\n"

            except Exception as llm_error:
                logging.exception(f"LLM error during streaming: {str(llm_error)}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'AI模型调用失败: {str(llm_error)}', 'timestamp': time.time()})}\n\n"

        except Exception as e:
            logging.exception(f"Failed to analyze document in stream mode: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'分析失败: {str(e)}', 'timestamp': time.time()})}\n\n"

    def convert_to_html(self, analysis_report: str) -> Optional[str]:
        """将分析报告转换为HTML"""
        try:
            # HTML转换使用通用文档分析师角色
            system_prompt = get_system_prompt(DocumentType.OTHER_REPORT)
            user_prompt = get_html_conversion_prompt(analysis_report)

            history = [{"role": "user", "content": user_prompt}]

            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 8192
            }

            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response for HTML conversion")
                return None

            # 直接返回响应内容，不进行清理
            return response.strip()

        except Exception as e:
            logging.exception(f"Failed to convert to HTML: {str(e)}")
            return None


# API Endpoints
@manager.route("/analyze", methods=["POST"])
@login_required
def analyze_document():
    """
    文档分析接口
    ---
    tags:
      - Document Extract
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            file_id:
              type: string
              description: 文件ID
            analysis_type:
              type: string
              enum: [analysis, html_conversion]
              description: 分析类型
            document_type:
              type: string
              enum: [business_plan, industry_report, other_report]
              description: 文档类型
            file_content:
              type: string
              description: 文件内容（用于analysis类型）
            analysis_report:
              type: string
              description: 分析报告内容（用于html_conversion类型）
    responses:
      200:
        description: 分析成功
        schema:
          type: object
          properties:
            code:
              type: integer
            message:
              type: string
            data:
              type: object
              properties:
                analysis_id:
                  type: string
                basic_analysis:
                  type: string
                html_analysis:
                  type: string
                status:
                  type: string
                created_at:
                  type: string
    """
    try:
        req = request.json
        if not req:
            return get_data_error_result(message="Request body is required!")

        # 验证必需参数
        file_id = req.get("file_id")
        analysis_type = req.get("analysis_type")
        document_type = req.get("document_type")

        if not all([file_id, analysis_type, document_type]):
            return get_data_error_result(message="file_id, analysis_type, and document_type are required!")

        # 验证文件权限
        e, file = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message="File not found!")
        if file.tenant_id != current_user.id:
            return get_json_result(
                data=False,
                message='No authorization to access this file.',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )

        analysis_service = DocumentAnalysisService(current_user.id)
        analysis_id = str(uuid.uuid4())

        # 检查是否请求流式输出
        stream_mode = req.get("stream", False)

        if analysis_type == AnalysisType.ANALYSIS:
            file_content = req.get("file_content")
            if not file_content:
                return get_data_error_result(message="file_content is required for analysis type!")

            # 如果请求流式输出
            if stream_mode:
                def generate():
                    yield f"data: {json.dumps({'type': 'init', 'analysis_id': analysis_id, 'timestamp': time.time()})}\n\n"

                    try:
                        for chunk in analysis_service.analyze_document_stream(file_id, document_type, file_content):
                            yield chunk
                    except Exception as e:
                        logging.exception(f"Stream analysis failed: {str(e)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'流式分析失败: {str(e)}', 'timestamp': time.time()})}\n\n"

                    yield f"data: {json.dumps({'type': 'end', 'timestamp': time.time()})}\n\n"

                return Response(
                    generate(),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'Connection': 'keep-alive',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Cache-Control'
                    }
                )
            else:
                # 普通模式
                basic_analysis = analysis_service.analyze_document(file_id, document_type, file_content)
                if not basic_analysis:
                    return get_data_error_result(message="Document analysis failed.")

                response_data = DocumentAnalysisResponse(
                    analysis_id=analysis_id,
                    basic_analysis=basic_analysis,
                    status="completed",
                    created_at=str(uuid.uuid4())  # 简化实现，实际应该是时间戳
                )

        elif analysis_type == AnalysisType.HTML_CONVERSION:
            analysis_report = req.get("analysis_report")
            if not analysis_report:
                return get_data_error_result(message="analysis_report is required for html_conversion type!")

            html_analysis = analysis_service.convert_to_html(analysis_report)
            if not html_analysis:
                return get_data_error_result(message="HTML conversion failed.")

            response_data = DocumentAnalysisResponse(
                analysis_id=analysis_id,
                html_analysis=html_analysis,
                status="completed",
                created_at=str(uuid.uuid4())  # 简化实现，实际应该是时间戳
            )

        else:
            return get_data_error_result(message="Invalid analysis_type!")

        return get_json_result(data=response_data.model_dump())

    except Exception as e:
        logging.exception(f"Document analysis failed: {str(e)}")
        return server_error_response(e)
