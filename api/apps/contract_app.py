import logging
import json
import time
import uuid
from typing import List, Optional, Dict, Any, Type, Literal
from collections import OrderedDict
from enum import Enum

from flask import request
from flask_login import login_required, current_user
from pydantic import BaseModel, Field, model_validator

from api.db.services.file_service import FileService
from api.db.services.llm_service import LLMBundle
from api.db import LLMType
from api.apps.parser_app import IntelligentDocumentParser
from api.utils.api_utils import (
    get_json_result,
    get_data_error_result,
    server_error_response,
    validate_request
)
from api import settings

# Contract Models
class ContractComponentType(str, Enum):
    BASIC_INFO = "basic_info"
    PARTIES = "parties"
    SUBJECTS = "subjects"
    TERMS = "terms"
    CONTRACT = "contract"
    RISKS = "risks"

class ContractBasicInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="合同基本信息唯一标识符")
    title: str = Field(..., description="合同标题")
    contract_number: Optional[str] = Field(None, description="合同编号")
    contract_type: str = Field(..., description="合同类型，如'投资意向书'、'投资协议'、'租赁合同'、'销售合同'、'服务合同'等")

    signing_date: Optional[str] = Field(None, description="签订日期，格式为YYYY-MM-DD")
    effective_date: Optional[str] = Field(None, description="生效日期，格式为YYYY-MM-DD")
    expiration_date: Optional[str] = Field(None, description="到期日期，格式为YYYY-MM-DD")

    language: Optional[str] = Field(None, description="合同语言，使用ISO 639-1两字符语言码")
    country: Optional[str] = Field(None, description="合同适用国家，使用ISO 3166-1 alpha-2两字符国家码")

    summary: Optional[str] = Field(None, description="合同摘要")
    legal_basis: Optional[str] = Field(None, description="法律依据")
    signing_place: Optional[str] = Field(None, description="签订地点")

class ContractParty(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="合同方唯一标识符")
    name: str = Field(..., description="合同方名称，合同方是签署合同的实体，可以是公司、组织、个人等，但合同中出现的实体并不一定是合同方，合同方一般出现在合同的开头或结尾签署部分，如'甲方'、'乙方'、'卖方'、'买方'等")
    party_type: str = Field(..., description="合同方类型，如'个人'、'公司'、'政府'、'非盈利机构'等")
    role: Optional[str] = Field(None, description="在合同中的角色，如'买方'、'卖方'、'甲方'、'乙方'、'投资方'、'受资方'、'担保方'、'监理方'、'关联方'等")
    address: Optional[str] = Field(None, description="合同方地址")
    country: Optional[str] = Field(None, description="国家，使用ISO 3166-1 alpha-2两字符编码")
    province_state: Optional[str] = Field(None, description="省/市/州")
    contact: Optional[str] = Field(None, description="联系人")
    phone: Optional[str] = Field(None, description="联系电话")
    email: Optional[str] = Field(None, description="电子邮箱")
    representative: Optional[str] = Field(None, description="法定代表人")
    id_number: Optional[str] = Field(None, description="证件号码")

class ContractSubject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="标的唯一标识符")
    name: str = Field(..., description="标的名称，标的是合同中具体的交易对象，如货物、不动产、动产、股权、服务等")
    subject_type: str = Field(..., description="标的类型，如'货物'、'不动产'、'动产'、'股权'、'服务'或更为具体的'土地'、'机械设备'、'专利'等")
    description: str = Field(..., description="标的描述，标的的具体内容和特征，如货物的名称、规格、数量、质量、价格等")
    specification: Optional[str] = Field(None, description="规格参数")
    location: Optional[str] = Field(None, description="标的所在地或交付地点")
    transaction_price: Optional[str] = Field(None, description="交易价格，可能包含货币单位")

class ContractTerm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="条款唯一标识符")
    term_type: str = Field(..., description="条款类型，如'支付条款'、'排他性条款'、'交付条款'、'保密条款'等")
    excerpts: List[str] = Field(default_factory=list, description="条款内容摘录")

    @model_validator(mode='before')
    @classmethod
    def validate_excerpts(cls, data):
        if isinstance(data, dict) and data.get('excerpts') is None:
            data['excerpts'] = []
        return data

class ContractTerms(BaseModel):
    terms: List[ContractTerm] = Field(default_factory=list, description="条款列表")

class Contract(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="合同唯一标识符")
    basic_info: ContractBasicInfo = Field(..., description="合同基本信息")
    parties: List[ContractParty] = Field(..., description="合同方列表")
    subjects: List[ContractSubject] = Field(default_factory=list, description="合同标的列表")
    terms: ContractTerms = Field(..., description="合同条款和条件")
    raw_text: str = Field(..., description="原始合同文本")

class ContractRisk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="风险点唯一标识符")
    risk_type: str = Field(..., description="风险类型，如'付款风险'、'交付风险'、'违约风险'等")
    description: str = Field(..., description="风险描述")
    level: str = Field(..., description="风险等级，分为'高'、'中'、'低'三级")
    recommendation: Optional[str] = Field(None, description="风险处理建议")

class ContractRiskAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), exclude=True, description="合同风险列表唯一标识符")
    contract_id: str = Field(..., description="合同ID或标识")
    summary: Optional[str] = Field(None, description="风险分析总结")
    overall_risk_level: str = Field("中", description="整体风险等级，如'高'、'中'、'低'")
    analysis_date: Optional[str] = Field(None, description="分析时间，格式为YYYY-MM-DD")
    risks: List[ContractRisk] = Field(default_factory=list, description="风险点列表")

LanguageType = Literal["zh-CN", "zh-TW", "en", "ja", "ko", "fr", "de", "es", "ru"]

# Prompt Functions
def get_system_prompt() -> str:
    system_prompt = """
    You are **IridumAI**, a **professional legal contract reviewer** with extensive expertise in contract law and analysis.

    Your responsibilities include:
    1. Identifying key terms, clauses, and obligations in contracts
    2. Detecting potential risks and ambiguities in legal language
    3. Extracting structured information from contract documents
    4. Providing clear explanations of complex legal concepts
    5. Offering professional recommendations based on legal best practices

    Analyze all information objectively and provide accurate, helpful responses based on the contract content.
    Do not make assumptions beyond what is explicitly stated in the documents.

    ## GENERAL DATA FORMAT STANDARDS
    When extracting or analyzing information, adhere to these format standards:

    1. **Dates**:
       - Always use ISO 8601 format: YYYY-MM-DD (e.g., "2023-05-15")
       - For missing or unknown dates, use null instead of empty strings or placeholders
       - Do not validate or correct date values; preserve the original date as provided

    2. **Currency and Monetary Values**:
       - Preserve the original currency symbol or code as found in the document
       - Do not convert between currencies
       - For missing or unknown monetary values, use null
       - Maintain the original format of numbers (e.g., "50,000.00", "1,000,000")

    3. **Country and Language Codes**:
       - For countries: Use ISO 3166-1 alpha-2 two-letter country codes (e.g., "CN" for China, "US" for United States)
       - For languages: Use ISO 639-1 two-letter language codes with optional region subtags
         * For Chinese: Use "zh-CN" for Simplified Chinese, "zh-TW" for Traditional Chinese
         * For English: Use "en-US" for American English, "en-GB" for British English
         * For other languages: Use the base code (e.g., "fr" for French, "de" for German) unless regional distinction is important
       - If a country or language is mentioned but the code is uncertain, use the full name
       - For missing or unknown values, use null

    4. **Missing Information**:
       - Always use null for missing information, not empty strings, "N/A", or other placeholders
       - Do not attempt to infer missing information unless explicitly instructed

    ## FOLLOW JSON SCHEMA
    When a user is given a JSON schema, you have to follow it strictly, And pay attention to the following key details:

    1. **Extra content other than a valid JSON string is not allowed.**
        - Incorrect example(Extra double quotes): "The answer is {"key": "value"}"
        - Incorrect example(The extra three single quotes and json):  '''json {"key": "value"} '''
        - Incorrect example(Extra single quotes): '[ {"key": "value"} ]'

    2. **Double quotation marks are used**: All key names and string values must be in double quotation marks, and single quotation marks are prohibited. Numeric values, boolean values, and null do not require quotation marks.
        - Correct example: {"key": "value"}
        - Incorrect example: {'key': 'value'}

    3. **No extra fields**: The output must be strictly valid JSON without any extra text or comments.
        - Correct example: {"key": "value"}
        - Incorrect example: {"key": "value"} // This is a comment

    4. **Label closed**: Make sure that the opening and closing parentheses of the array and object match.
        - Correct example: [{"key1": "value1"}, {"key2": "value2"}]
        - Incorrect example: [{"key": "value"}, {"key": "value"}

    5. **Special values**: Use correct JSON representation for special values.
        - Correct example: {"value": null}
        - Incorrect example: {"value": undefined}

    6. **Empty structures**: Use {} or [] to identify null values, respectively.
        - Correct example: {"array": []}
        - Correct example: {"array": [], "object": {}}
        - Incorrect example: {"array": null, "object": null}

    7. **String escaping**: Properly escape special characters in strings.
        - Correct example: {"text": "Line 1\\nLine 2"}
        - Incorrect example: {"text": "Line 1
Line 2"}
        - Correct example: {"path": "C:\\\\Program Files\\\\App"}
        - Incorrect example: {"path": "C:\\Program Files\\App"}
    """
    return system_prompt.strip()

def get_risk_analysis_system_prompt(perspective: str = "Neutral party") -> str:
    system_prompt = f"""
    You are **IridumAI**, a **senior lawyer employed by {perspective}**, your role is to identify commercial contract risks, realise employer value and avoid losses, otherwise you will be fired and disqualified from practising.

    Your specialized responsibilities include:
    1. Identifying potential legal, commercial, operational, and financial risks in contracts
    2. Evaluating risk severity and likelihood of occurrence
    3. Analyzing contract clauses for potential vulnerabilities and ambiguities
    4. Providing detailed risk descriptions and mitigation recommendations
    5. Assessing overall contract risk levels based on identified risk factors

    **Analysis Perspective**: You are conducting this analysis **specifically from the perspective of {perspective}**. Focus on identifying risks that could negatively impact {perspective}'s interests, rights, obligations, and potential liabilities."""

    system_prompt += """

    Focus on comprehensive risk identification including:
    - Legal compliance risks (regulatory violations, jurisdictional issues)
    - Commercial risks (payment defaults, performance failures, market changes)
    - Operational risks (delivery delays, quality issues, resource constraints)
    - Financial risks (currency fluctuations, cost overruns, liability exposure)

    For each identified risk, provide:
    - Clear risk categorization and type identification
    - Detailed description of the risk and its potential impact
    - Accurate risk level assessment (高/中/低)
    - Practical recommendations for risk mitigation or management

    Analyze all contract information objectively and provide thorough risk assessments based on the contract content and structure.
    Do not make assumptions beyond what is explicitly stated in the documents.

    ## GENERAL DATA FORMAT STANDARDS
    When analyzing and reporting risks, adhere to these format standards:

    1. **Risk Levels**:
       - Use only "高", "中", "低" for risk level classification
       - Base assessments on both severity and likelihood of occurrence

    2. **Risk Types**:
       - Use clear, specific risk type names (e.g., "合规风险", "付款风险", "交付风险")
       - Avoid generic or overly broad categorizations

    3. **Missing Information**:
       - Always use null for missing information, not empty strings, "N/A", or other placeholders
       - Do not attempt to infer missing information unless explicitly instructed

    ## FOLLOW JSON SCHEMA
    When a user is given a JSON schema, you have to follow it strictly, And pay attention to the following key details:

    1. **Extra content other than a valid JSON string is not allowed.**
        - Incorrect example(Extra double quotes): "The answer is {"key": "value"}"
        - Incorrect example(The extra three single quotes and json):  '''json {"key": "value"} '''
        - Incorrect example(Extra single quotes): '[ {"key": "value"} ]'

    2. **Double quotation marks are used**: All key names and string values must be in double quotation marks, and single quotation marks are prohibited. Numeric values, boolean values, and null do not require quotation marks.
        - Correct example: {"key": "value"}
        - Incorrect example: {'key': 'value'}
        - Correct example: [{"key1": "value1"}, {"key2": "value2"}]
        - Incorrect example: [{'key1': 'value1'}, {'key2': 'value2'}]

    3. **No extra fields**: The output must be strictly valid JSON without any extra text or comments.
        - Correct example: {"key": "value"}
        - Incorrect example: {"key": "value"} // This is a comment

    4. **Label closed**: Make sure that the opening and closing parentheses of the array and object match.
        - Correct example: [{"key1": "value1"}, {"key2": "value2"}]
        - Incorrect example: [{"key": "value"}, {"key": "value"}
        - Correct example: {"key": ["value1", "value2"]}
        - Incorrect example: {"key": ["value1", "value2"}

    5. **Special values**: Use correct JSON representation for special values.
        - Correct example: {"value": null}
        - Incorrect example: {"value": undefined}
        - Correct example: {"value": 0}
        - Incorrect example: {"value": NaN}

    6. **Empty structures**: Use {} or [] to identify null values, respectively.
        - Correct example: {"array": []}
        - Correct example: {"array": [], "object": {}}
        - Incorrect example: {"array": null, "object": null}

    7. **String escaping**: Properly escape special characters in strings.
        - Correct example: {"text": "Line 1\nLine 2"}
        - Incorrect example: {"text": "Line 1
Line 2"}
        - Correct example: {"path": "C:\\\\Program Files\\\\App"}
        - Incorrect example: {"path": "C:\\Program Files\\App"}
        """
    return system_prompt.strip()

def set_language(language: LanguageType = "zh-CN") -> str:
    language_prompts = {
        "zh-CN": "请使用简体中文回答问题。",
        "zh-TW": "請使用繁體中文回答問題。",
        "en": "Please answer the following questions in English.",
        "ja": "以下の質問に日本語で答えてください。",
        "ko": "다음 질문에 한국어로 답변해 주세요.",
        "fr": "Veuillez répondre aux questions suivantes en français.",
        "de": "Bitte beantworten Sie die folgenden Fragen auf Deutsch.",
        "es": "Por favor, responda a las siguientes preguntas en español.",
        "ru": "Пожалуйста, ответьте на следующие вопросы на русском языке."
    }
    return language_prompts.get(language, language_prompts["zh-CN"])

def format_contract_extraction(
    contract_text: str,
    schema: Dict[str, Any],
    component_type: ContractComponentType,
    language: LanguageType = "zh-CN"
) -> str:
    instructions = {
        ContractComponentType.BASIC_INFO: """
    ##**任务**
    根据指定的JSON Schema从以下合同文本中提取基本信息。

    ##**指南**
    1. 专注于提取合同的基本信息，包括：
       - 标题(title)：合同的完整标题
       - 合同编号(contract_number)：唯一标识合同的编号
       - 合同类型(contract_type)：如"销售合同"、"租赁合同"、"服务合同"等
       - 签订日期(signing_date)：合同签订的日期
       - 生效日期(effective_date)：合同生效的日期
       - 到期日期(expiration_date)：合同到期的日期
       - 语言(language)：合同语言，使用ISO 639-1两字符语言码
       - 国家(country)：合同适用国家，使用ISO 3166-1 alpha-2两字符国家码
       - 摘要(summary)：合同的简要描述或主要内容概述
       - 法律依据(legal_basis)：合同引用的法律法规
       - 签订地点(signing_place)：合同签订的地点
    2. 特别注意合同的标题、开头部分和结尾部分，这些信息通常在这些位置。
    3. 提取的信息应尽可能详细和准确。
    """,

        ContractComponentType.PARTIES: """
    ##**任务**
    根据指定的JSON Schema从以下合同文本中提取所有相关方的信息。

    ##**指南**
    1. 专注于识别合同中提到的所有相关方（个人、公司、组织）。
    2. 对于每个相关方，提取以下信息：
       - 名称(name)：相关方的全称
       - 类型(party_type)：如"公司"、"个人"、"政府机构"等
       - 角色(role)：如"卖方"、"买方"、"投资方"、"受资方"等
       - 地址(address)：相关方的详细地址
       - 国家(country)：相关方所在国家
       - 省/市/州(province_state)：相关方所在省/市/州
       - 联系人(contact)：联系人姓名
       - 电话(phone)：联系电话
       - 电子邮件(email)：电子邮件地址
       - 代表人(representative)：法定代表人或授权代表
       - 证件号码(id_number)：如营业执照号、身份证号等
    3. 这些信息通常在合同的开头部分、序言部分和签名部分。
    4. 提取的信息应尽可能详细和准确。
    5. 确保返回的是一个包含"parties"键的对象，该键对应一个数组。
    """,

        ContractComponentType.SUBJECTS: """
    ##**任务**
    根据指定的JSON Schema从以下合同文本中提取合同标的信息。

    ##**指南**
    1. 专注于识别在此合同中交换、销售、购买或以其他方式交易的内容。
    2. 对于每个标的，提取以下信息：
       - 名称(name)：标的的名称
       - 类型(subject_type)：如"商品"、"不动产"、"知识产权"等
       - 描述(description)：标的的详细描述
       - 规格参数(specification)：标的的规格或参数
       - 所在地(location)：标的所在地或交付地点
       - 交易价格(transaction_price)：交易价格
    3. 这些信息通常在合同的主体部分，经常在专门讨论商品或服务的章节中。
    4. 提取的信息应尽可能详细和准确。
    5. 确保返回的是一个包含"subjects"键的对象，该键对应一个数组。
    """,

        ContractComponentType.TERMS: """
    ##**任务**
    根据指定 JSON Schema 从给定的合同文本中提取条款和条件。

    ##**指南**
    1. 从专业法律角度出发，识别合同文本中实际存在的条款内容。
    2. 对于每个识别到的条款，提供以下信息：
       - 条款类型(term_type)：如"支付条款"、"交付条款"、"保密条款"等
       - 条款内容摘录(excerpts)：从合同文本中提取的相关段落

    3. 条款识别原则：以内容为准
       - 条款识别必须基于文本内容的实质和法律意义
       - 即使某段内容没有明确的标题、编号，只要其内容实质符合某种条款类型，也应将其识别为相应条款
       - 一个条款可能分散在合同的不同部分，应根据内容相关性将其归为同一类型

    4. 示例条款类型：
       - 权利义务条款、履约条件条款、排他性条款、竞业限制条款
       - 交易与付款条款、交付条款、质量保证条款、服务条款
       - 违约责任条款、争议解决条款、保密条款、不可抗力条款
       - 合同变更条款、合同终止条款、知识产权条款

    5. 提取的信息应尽可能详细和准确，必须提供准确的文本摘录。
    6. **重要**：只提取合同中实际存在的条款，不要标记不存在的条款。
    """
    }

    instruction = instructions.get(component_type, instructions[ContractComponentType.TERMS])

    fields_to_remove = ["id", "start_position", "end_position"]
    if "properties" in schema:
        schema["properties"] = {k: v for k, v in schema["properties"].items() if k not in fields_to_remove}
    user_prompt = f"""
    {instruction}

    ##**指定JSON Schema**
    指定JSON Schema包含在<schema></schema>标签中：
    <schema>
    {json.dumps(schema, ensure_ascii=False, indent=2)}
    </schema>

    ##**给定的合同文本**
    给定的合同文本包含在<contract></contract>标签中：
    <contract>
    {contract_text}
    </contract>

    **{set_language(language)}**
    """
    return user_prompt.strip()

def format_risk_extraction_prompt(
    contract: Contract,
    language: LanguageType = "zh-CN"
) -> str:
    contract_text = contract.raw_text
    contract_json = {
        "basic_info": contract.basic_info.model_dump(),
        "parties": [party.model_dump() for party in contract.parties],
        "subjects": [subject.model_dump() for subject in contract.subjects],
        "terms": {
            "terms": [term.model_dump() for term in contract.terms.terms]
        }
    }

    # 正确处理schema - 先获取完整schema，再移除id字段
    schema = ContractRisk.model_json_schema()
    if "properties" in schema and "id" in schema["properties"]:
        del schema["properties"]["id"]

    # 构建数组schema
    array_schema = {
        "type": "array",
        "items": schema
    }

    user_prompt = f"""
    ##**任务**
    根据指定的 JSON Schema 分析合同中的风险点。

    ##**指南**
    1. 仔细分析合同文本和结构化信息，识别可能存在的法律风险、商业风险和操作风险。
    2. 对于每个风险点，提供以下信息：
       - 风险类型(risk_type)：如"合规风险"、"付款风险"、"交付风险"、"违约风险"等
       - 风险描述(description)：详细描述风险的具体内容和可能的后果
       - 风险等级(level)：评估风险的严重程度，可选值为"高"、"中"、"低"
       - 风险处理建议(recommendation)：针对该风险的处理建议
    3. 以下为示例风险点：
       - 不符合、不适用法律规定
       - 不一致甚至矛盾的内容
       - 明显超出或低于行业标准
       - 条款缺失或不完整
       - 条款表述不明确或存在歧义
       - 权利义务不对等
       - 责任划分不清晰
       - 违约责任不明确或过轻/过重
       - 争议解决机制不完善
    4. 返回的风险点应按风险等级从高到低排序。

    ##**指定的JSON Schema**
    指定的 JSON Schema 包含在<schema></schema>标签中：
    <schema>
    {json.dumps(array_schema, ensure_ascii=False, indent=2)}
    </schema>

    ##**给定的合同**
    给定合同的内容包含在<contract></contract>标签中：
    <contract>
    {contract_text}
    </contract>

    ##**给定的合同结构化信息**
    给定的合同结构化信息包含在<contract_info></contract_info>标签中：
    <contract_info>
    {json.dumps(contract_json, ensure_ascii=False, indent=2)}
    </contract_info>

    **{set_language(language)}**
    """
    return user_prompt.strip()

def format_risk_review_prompt(contract: Contract, initial_risks: List[ContractRisk], language: LanguageType = "zh-CN") -> str:
    contract_text = contract.raw_text
    contract_json = {
        "basic_info": contract.basic_info.model_dump(),
        "parties": [party.model_dump() for party in contract.parties],
        "subjects": [subject.model_dump() for subject in contract.subjects],
        "terms": {
            "terms": [term.model_dump() for term in contract.terms.terms]
        }
    }

    initial_data = [risk.model_dump() for risk in initial_risks]
    # 正确处理schema - 先获取完整schema，再移除id字段
    schema = ContractRisk.model_json_schema()
    if "properties" in schema and "id" in schema["properties"]:
        del schema["properties"]["id"]

    # 构建数组schema
    array_schema = {
        "type": "array",
        "items": schema
    }

    user_prompt = f"""
    ##**任务**
    根据指定的 JSON Schema，对初步识别的风险点进行审查校验，确保风险分析的全面性、准确性和一致性。

    ##**指南**
    1. 仔细分析合同文本、结构化信息和初步识别的风险点。
    2. 执行以下审查校验任务：
       - **检查遗漏**：识别可能被忽略的重要风险点，特别是与合同类型相关的典型风险
       - **检查错误**：修正风险描述、等级或其他信息中的错误
       - **检查重复**：识别并合并描述相似或重复的风险点
       - **优化建议**：改进风险处理建议，使其更具体、可操作
       - **一致性检查**：确保风险等级评估的一致性，高风险应该真正影响合同的核心利益
    3. 对于每个风险点，确保包含以下信息：
       - 风险类型(risk_type)：如"付款风险"、"交付风险"、"违约风险"、"法律合规风险"等
       - 风险描述(description)：详细描述风险的具体内容和可能的后果
       - 风险等级(level)：评估风险的严重程度，可选值为"高"、"中"、"低"
       - 风险处理建议(recommendation)：针对该风险的处理建议
    4. 返回的风险点应按风险等级从高到低排序。
    5. 如果初步风险列表已经全面且准确，可以保留原有风险点，但应确保描述和建议的质量。

    ##**指定的 JSON Schema**
    指定的 JSON Schema 包含在<schema></schema>标签中：
    <schema>
    {json.dumps(array_schema, ensure_ascii=False, indent=2)}
    </schema>

    ##**给定的合同**
    给定的合同完整内容包含在<contract></contract>标签中：
    <contract>
    {contract_text}
    </contract>

    ##**给定的合同结构化信息**
    给定的合同结构化信息包含在<contract_info></contract_info>标签中：
    <contract_info>
    {json.dumps(contract_json, ensure_ascii=False, indent=2)}
    </contract_info>

    ##**初步识别的风险点**
    初步识别的风险点包含在<initial_risks></initial_risks>标签中：
    <initial_risks>
    {json.dumps(initial_data, ensure_ascii=False, indent=2)}
    </initial_risks>

    **{set_language(language)}**
    """
    return user_prompt.strip()

# Document Loader Class
class ContractDocumentLoader:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.parser = IntelligentDocumentParser(
            user_id=user_id,
            strategy="auto",
            extract_tables=False,
            extract_images=False
        )

    def load_from_file_id(self, file_id: str) -> Optional[str]:
        try:
            result = self.parser.parse_file(file_id)
            if result is None:
                logging.error(f"Failed to parse document from file {file_id}")
                return None
            logging.info(f"Document parsed successfully: {file_id}")
            return result["content"]
        except Exception as e:
            logging.exception(f"Failed to load document from file {file_id}: {str(e)}")
            return None

    def get_parse_info(self, file_id: str) -> Optional[dict]:
        try:
            result = self.parser.parse_file(file_id)
            if result is None:
                return None
            return {
                "file_id": result["file_id"],
                "file_name": result["file_name"],
                "file_type": result["file_type"],
                "file_size": result["file_size"],
                "parser_used": result["parser_used"],
                "metadata": result["metadata"]
            }

        except Exception as e:
            logging.exception(f"Failed to get parse info for file {file_id}: {str(e)}")
            return None

    def preview_document(self, file_id: str, max_length: int = 500) -> Optional[str]:
        try:
            result = self.parser.preview_file(file_id, max_length)

            if result is None:
                return None

            return result["preview_content"]

        except Exception as e:
            logging.exception(f"Failed to preview document {file_id}: {str(e)}")
            return None


# Extraction Service Class
class ExtractionService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm_bundle = LLMBundle(user_id, LLMType.CHAT)
        self.document_loader = ContractDocumentLoader(user_id)

    def extract_from_file(self, file_id: str, extraction_type: str = "basic") -> Optional[Contract]:
        try:
            contract_text = self.document_loader.load_from_file_id(file_id)
            if not contract_text:
                logging.error(f"Failed to load document content from file {file_id}")
                return None
            return self.extract_from_text(contract_text, extraction_type)
        except Exception as e:
            logging.exception(f"Failed to extract contract from file {file_id}: {str(e)}")
            return None

    def extract_from_text(self, contract_text: str, extraction_type: str = "basic") -> Optional[Contract]:
        try:
            component_config = OrderedDict([
                (ContractComponentType.BASIC_INFO, ContractBasicInfo),
                (ContractComponentType.PARTIES, List[ContractParty]),
                (ContractComponentType.SUBJECTS, List[ContractSubject]),
                (ContractComponentType.TERMS, ContractTerms)
            ])

            extracted_components = {}

            for step, (component_type, model_type) in enumerate(component_config.items(), 1):
                component_name = component_type.value

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

            contract = Contract(
                basic_info=extracted_components["basic_info"],
                parties=extracted_components["parties"],
                subjects=extracted_components["subjects"],
                terms=extracted_components["terms"],
                raw_text=contract_text
            )

            logging.info("Contract extraction completed")
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
        try:
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

            system_prompt = get_system_prompt()
            user_prompt = format_contract_extraction(
                contract_text=text,
                schema=schema,
                component_type=component_enum,
                language="zh-CN"
            )

            component_data = self._call_llm(system_prompt, user_prompt)
            if not component_data:
                return None

            component_data = self._process_component_data(component_data, component_enum)

            if hasattr(component_type, "__origin__") and component_type.__origin__ is list:
                element_type = component_type.__args__[0]
                return [element_type.model_validate(item) for item in component_data]
            else:
                return component_type.model_validate(component_data)

        except Exception as e:
            logging.exception(f"Failed to extract component {component_enum.value}: {str(e)}")
            return None

    def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        try:
            history = [{"role": "user", "content": user_prompt}]

            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 4096
            }

            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response")
                return None

            return self._parse_llm_json_response(response)

        except Exception as e:
            logging.exception(f"Failed to call LLM: {str(e)}")
            return None

    def _parse_llm_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                import re
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())

                array_match = re.search(r'\[.*\]', response, re.DOTALL)
                if array_match:
                    return json.loads(array_match.group())

                logging.error(f"Failed to extract JSON from response")
                return None

            except Exception as e:
                logging.exception(f"Failed to parse LLM JSON response: {str(e)}")
                return None

    def _process_component_data(self, component_data: Any, component_enum: ContractComponentType) -> Any:
        try:
            if component_enum == ContractComponentType.BASIC_INFO:
                if isinstance(component_data, dict):
                    if "dates" in component_data and isinstance(component_data["dates"], dict):
                        dates = component_data["dates"]
                        date_fields = ["signing_date", "effective_date", "expiration_date"]
                        for field in date_fields:
                            if field in dates and dates[field] is not None:
                                component_data[field] = dates[field]
                        del component_data["dates"]

                    if "positions" in component_data:
                        del component_data["positions"]

                return component_data

            elif component_enum in [ContractComponentType.PARTIES, ContractComponentType.SUBJECTS]:
                component_key = component_enum.value

                if isinstance(component_data, dict) and component_key in component_data:
                    component_data = component_data[component_key]

                if not isinstance(component_data, list):
                    if isinstance(component_data, dict):
                        typical_fields = ["name"]
                        if component_enum == ContractComponentType.SUBJECTS:
                            typical_fields.append("description")
                        if component_enum == ContractComponentType.PARTIES:
                            typical_fields.append("role")

                        if any(key in component_data for key in typical_fields):
                            component_data = [component_data]
                        else:
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
                return component_data

        except Exception as e:
            logging.exception(f"Failed to process component data for {component_enum.value}: {str(e)}")
            return component_data


# Risk Service Class
class RiskService:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.llm_bundle = LLMBundle(user_id, LLMType.CHAT)

    def analyze_risks(self, contract: Contract, analysis_type: str = "basic", perspective: str = "Neutral party") -> Optional[ContractRiskAnalysis]:
        try:
            risk_analysis = ContractRiskAnalysis(
                contract_id=contract.id,
                risks=[],
                summary="",
                overall_risk_level="低",
                analysis_date=time.strftime("%Y-%m-%d")
            )

            initial_risks = self._extract_risks(contract, perspective)

            if not initial_risks:
                logging.warning("No initial risks extracted from contract")
                return risk_analysis

            risk_analysis.risks = initial_risks
            risk_analysis.overall_risk_level = self._evaluate_overall_risk_level(initial_risks)
            risk_analysis.summary = self._generate_risk_summary(contract, initial_risks)

            final_risks = self._review_risks(contract, initial_risks, perspective)

            if not final_risks:
                logging.warning("Risk review failed, using initial risks")
                final_risks = initial_risks
            else:
                risk_analysis.risks = final_risks
                risk_analysis.overall_risk_level = self._evaluate_overall_risk_level(final_risks)
                risk_analysis.summary = self._generate_risk_summary(contract, final_risks)

            logging.info(f"Risk analysis completed: {len(final_risks)} risk points")
            return risk_analysis

        except Exception as e:
            logging.exception(f"Failed to analyze contract risks: {str(e)}")
            return None

    def _extract_risks(self, contract: Contract, perspective: str = "Neutral party") -> List[ContractRisk]:
        try:
            user_prompt = format_risk_extraction_prompt(contract, language="zh-CN")

            risk_data = self._call_llm_for_risks(user_prompt, perspective)
            if not risk_data:
                logging.error("LLM returned no data for risk extraction")
                return []

            risks = []
            try:
                # 支持直接数组格式（原始设计）
                if isinstance(risk_data, list):
                    risk_list = risk_data
                elif "risks" in risk_data and isinstance(risk_data["risks"], list):
                    risk_list = risk_data["risks"]
                else:
                    logging.error(f"Unable to parse risk data structure")
                    return []

                for i, risk_item in enumerate(risk_list):
                    try:
                        risk = ContractRisk.model_validate(risk_item)
                        risks.append(risk)
                    except Exception as e:
                        logging.warning(f"Failed to validate risk item {i+1}: {str(e)}")
                        continue

            except Exception as e:
                logging.exception(f"Failed to parse risk data: {str(e)}")
                return []

            return risks

        except Exception as e:
            logging.exception(f"Failed to extract risks: {str(e)}")
            return []

    def _review_risks(self, contract: Contract, initial_risks: List[ContractRisk], perspective: str = "Neutral party") -> List[ContractRisk]:
        try:
            if not initial_risks:
                logging.warning("Initial risks list is empty, skipping review")
                return []

            user_prompt = format_risk_review_prompt(contract, initial_risks, language="zh-CN")

            reviewed_risk_data = self._call_llm_for_risks(user_prompt, perspective)
            if not reviewed_risk_data:
                logging.warning("Risk review failed, returning initial risks")
                return initial_risks

            reviewed_risks = []
            try:
                # 优先解析数组格式（与第一轮保持一致）
                if isinstance(reviewed_risk_data, list):
                    risk_list = reviewed_risk_data
                elif "risks" in reviewed_risk_data and isinstance(reviewed_risk_data["risks"], list):
                    risk_list = reviewed_risk_data["risks"]
                else:
                    logging.error(f"Unable to parse reviewed risk data structure")
                    return initial_risks

                for i, risk_item in enumerate(risk_list):
                    try:
                        risk = ContractRisk.model_validate(risk_item)
                        reviewed_risks.append(risk)
                    except Exception as e:
                        logging.warning(f"Failed to validate reviewed risk item {i+1}: {str(e)}")
                        continue

            except Exception as e:
                logging.exception(f"Failed to parse reviewed risk data: {str(e)}")
                return initial_risks

            return reviewed_risks

        except Exception as e:
            logging.exception(f"Failed to review risks: {str(e)}")
            return initial_risks

    def _call_llm_for_risks(self, user_prompt: str, perspective: str = "Neutral party") -> Optional[Dict[str, Any]]:
        try:
            system_prompt = get_risk_analysis_system_prompt(perspective)

            history = [{"role": "user", "content": user_prompt}]

            gen_conf = {
                "temperature": 0.1,
                "max_tokens": 4096
            }

            response = self.llm_bundle.chat(system_prompt, history, gen_conf)

            if not response:
                logging.error("LLM returned empty response for risk analysis")
                return None

            return self._parse_llm_json_response(response)

        except Exception as e:
            logging.exception(f"Failed to call LLM for risk analysis: {str(e)}")
            return None

    def _parse_llm_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM的JSON响应，使用更健壮的解析逻辑"""
        # 首先清理响应，移除markdown代码块标记
        cleaned_response = response.strip()
        if cleaned_response.startswith('```json'):
            cleaned_response = cleaned_response[7:]  # 移除 ```json
        if cleaned_response.startswith('```'):
            cleaned_response = cleaned_response[3:]   # 移除 ```
        if cleaned_response.endswith('```'):
            cleaned_response = cleaned_response[:-3]  # 移除结尾的 ```
        cleaned_response = cleaned_response.strip()

        try:
            # 首先尝试直接解析清理后的响应
            data = json.loads(cleaned_response)
            return data

        except json.JSONDecodeError:
            pass

        try:
            import re

            # 优先尝试提取JSON数组（因为我们期望的是数组格式）
            array_match = re.search(r'\[.*\]', cleaned_response, re.DOTALL)
            if array_match:
                array_str = array_match.group()
                try:
                    array_data = json.loads(array_str)
                    return array_data
                except json.JSONDecodeError:
                    pass

            # 如果数组解析失败，再尝试提取JSON对象
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    data = json.loads(json_str)
                    return data
                except json.JSONDecodeError:
                    pass

            logging.error("No valid JSON found in response")
            return None

        except Exception as e:
            logging.exception(f"Failed to parse LLM JSON response: {str(e)}")
            return None

    def _generate_risk_summary(self, contract: Contract, risks: List[ContractRisk]) -> str:
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
                for i, risk in enumerate(medium_risks[:3], 1):
                    summary += f"\n{i}. {risk.risk_type}：{risk.description}"

            return summary

        except Exception as e:
            logging.exception(f"Failed to generate risk summary: {str(e)}")
            return f"本合同共识别出{len(risks)}个风险点。"

    def _evaluate_overall_risk_level(self, risks: List[ContractRisk]) -> str:
        try:
            high_risks = [risk for risk in risks if risk.level == "高"]
            medium_risks = [risk for risk in risks if risk.level == "中"]

            if len(high_risks) >= 3 or (len(high_risks) >= 1 and len(medium_risks) >= 3):
                return "高"
            elif len(high_risks) >= 1 or len(medium_risks) >= 2:
                return "中"
            else:
                return "低"

        except Exception as e:
            logging.exception(f"Failed to evaluate overall risk level: {str(e)}")
            return "中"

@manager.route('/extract', methods=['POST'])  # noqa: F821
@login_required
@validate_request("file_id")
def extract_contract():
    req = request.json
    file_id = req["file_id"]
    extraction_type = req.get("extraction_type", "basic")

    try:
        e, file = FileService.get_by_id(file_id)
        if not e:
            return get_data_error_result(message="File not found!")
        if file.tenant_id != current_user.id:
            return get_json_result(
                data=False,
                message='No authorization to access this file.',
                code=settings.RetCode.AUTHENTICATION_ERROR
            )

        extraction_service = ExtractionService(current_user.id)
        contract = extraction_service.extract_from_file(file_id, extraction_type)

        if not contract:
            return get_data_error_result(message="Contract extraction failed.")
        return get_json_result(data=contract.model_dump())

    except Exception as e:
        logging.exception(f"Contract extraction failed: {str(e)}")
        return server_error_response(e)

@manager.route('/analyze_risk', methods=['POST'])  # noqa: F821
@login_required
@validate_request("contract_data")
def analyze_risk():
    req = request.json
    contract_data = req["contract_data"]
    analysis_type = req.get("analysis_type", "basic")
    perspective = req.get("perspective", "Neutral party")

    try:
        contract = Contract.model_validate(contract_data)

        risk_service = RiskService(current_user.id)
        risk_analysis = risk_service.analyze_risks(contract, analysis_type, perspective)

        if not risk_analysis:
            return get_data_error_result(message="Risk analysis failed.")

        return get_json_result(data=risk_analysis.model_dump())

    except Exception as e:
        logging.exception(f"Risk analysis failed: {str(e)}")
        return server_error_response(e)