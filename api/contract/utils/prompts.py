"""
提示词模块，包含各种提示词生成函数
"""
import json
from typing import Dict, Any, List, Optional, Literal

try:
    from ..models.contract_models import (
        Contract, ContractComponentType, ContractRisk
    )
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    import sys
    import os
    contract_path = os.path.dirname(os.path.dirname(__file__))
    if contract_path not in sys.path:
        sys.path.insert(0, contract_path)

    from models.contract_models import (
        Contract, ContractComponentType, ContractRisk
    )

LanguageType = Literal["zh-CN", "zh-TW", "en", "ja", "ko", "fr", "de", "es", "ru"]


def get_system_prompt() -> str:
    """获取合同信息提取的系统提示词"""
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


def get_risk_analysis_system_prompt() -> str:
    """获取合同风险分析的系统提示词"""
    system_prompt = """
    You are **IridumAI**, a **professional legal contract risk analyzer** with extensive expertise in contract law, risk assessment, and legal compliance.

    Your specialized responsibilities include:
    1. Identifying potential legal, commercial, operational, and financial risks in contracts
    2. Evaluating risk severity and likelihood of occurrence
    3. Analyzing contract clauses for potential vulnerabilities and ambiguities
    4. Providing detailed risk descriptions and mitigation recommendations
    5. Assessing overall contract risk levels based on identified risk factors

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


def set_language(language: LanguageType = "zh-CN") -> str:
    """
    设置响应语言

    Args:
        language: 语言类型

    Returns:
        str: 语言设置提示词
    """
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

    # 向后兼容处理
    if language == "zh":
        language = "zh-CN"

    return language_prompts.get(language, language_prompts["zh-CN"])


def format_contract_extraction(
    contract_text: str,
    schema: Dict[str, Any],
    component_type: ContractComponentType,
    language: LanguageType = "zh-CN"
) -> str:
    """
    格式化合同组件提取提示词

    Args:
        contract_text: 合同文本
        schema: 组件的JSON Schema
        component_type: 组件类型
        language: 响应语言

    Returns:
        str: 格式化后的用户提示词
    """
    # 针对特定组件的提示词
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
    
    # 移除不需要的字段
    fields_to_remove = ["id", "start_position", "end_position"]
    if "properties" in schema:
        schema["properties"] = {k: v for k, v in schema["properties"].items() if k not in fields_to_remove}

    # 构建用户提示词
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
    """
    格式化风险提取提示词
    Args:
        contract: 合同对象
        language: 响应语言

    Returns:
        str: 格式化后的用户提示词
    """
    contract_text = contract.raw_text
    contract_json = {
        "basic_info": contract.basic_info.model_dump(),
        "parties": [party.model_dump() for party in contract.parties],
        "subjects": [subject.model_dump() for subject in contract.subjects],
        "terms": {
            "terms": [term.model_dump() for term in contract.terms.terms]
        }
    }

    # 获取风险模型的schema，移除id字段
    schema = ContractRisk.model_json_schema()
    if "properties" in schema and "id" in schema["properties"]:
        schema["properties"].pop("id", None)

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
    {json.dumps(schema, ensure_ascii=False, indent=2)}
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
