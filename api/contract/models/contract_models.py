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

from typing import List, Optional
import uuid
from enum import Enum
from pydantic import BaseModel, Field, model_validator


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
    name: str = Field(..., description="合同方名称")
    party_type: str = Field(..., description="合同方类型，如'个人'、'公司'、'政府'、'非盈利机构'等")
    role: Optional[str] = Field(None, description="在合同中的角色，如'买方'、'卖方'、'甲方'、'乙方'等")
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
    name: str = Field(..., description="标的名称")
    subject_type: str = Field(..., description="标的类型，如'货物'、'不动产'、'动产'、'股权'、'服务'等")
    description: str = Field(..., description="标的描述")
    specification: Optional[str] = Field(None, description="规格参数")
    location: Optional[str] = Field(None, description="标的所在地或交付地点")
    transaction_price: Optional[str] = Field(None, description="交易价格，可能包含货币单位")


class ContractTerm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="条款唯一标识符")
    term_type: str = Field(..., description="条款类型，如'支付条款'、'排他性条款'、'交付条款'、'保密条款'等")
    excerpts: List[str] = Field(default_factory=list, description="条款内容摘录，可能包含多个相关段落")

    @model_validator(mode='before')
    @classmethod
    def validate_excerpts(cls, data):
        if isinstance(data, dict) and data.get('excerpts') is None:
            data['excerpts'] = []
        return data


class ContractTerms(BaseModel):
    terms: List[ContractTerm] = Field(default_factory=list, description="条款列表，每个条款包含类型、内容摘录等信息")


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
    level: str = Field(..., description="风险等级，如'高'、'中'、'低'")
    recommendation: Optional[str] = Field(None, description="风险处理建议")


class ContractRiskAnalysis(BaseModel):
    """
    合同风险分析
    独立于合同结构，但引用合同中的元素进行风险分析
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), exclude=True, description="合同风险列表唯一标识符")
    contract_id: str = Field(..., description="合同ID或标识")
    summary: Optional[str] = Field(None, description="风险分析总结")
    overall_risk_level: str = Field("中", description="整体风险等级，如'高'、'中'、'低'")
    analysis_date: Optional[str] = Field(None, description="分析时间，格式为YYYY-MM-DD")
    risks: List[ContractRisk] = Field(default_factory=list, description="风险点列表")
