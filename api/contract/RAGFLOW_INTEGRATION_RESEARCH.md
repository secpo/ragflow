# RAGFlow Graph & ES 功能调研报告

## 📋 调研目标
为合同风险图数据库的未来扩展，调研RAGFlow现有的Graph和ES功能接口，评估复用可行性。

## 🔍 Graph功能调研

### 1. 现有Graph架构

#### **核心组件**
- **GraphRAG模块**: `graphrag/` 目录，基于Microsoft GraphRAG和LightRAG
- **图数据结构**: 使用NetworkX (`nx.Graph`)
- **存储方式**: 图数据序列化后存储在ES中，使用`knowledge_graph_kwd`字段标识

#### **关键API接口**

**知识图谱API** (`api/apps/kb_app.py`):
```python
# 获取知识图谱
GET /v1/kb/<kb_id>/knowledge_graph
# 删除知识图谱  
DELETE /v1/kb/<kb_id>/knowledge_graph
```

**核心工具函数** (`graphrag/utils.py`):
```python
# 图操作
async def get_graph(tenant_id, kb_id, exclude_rebuild=None)
async def set_graph(tenant_id, kb_id, embd_mdl, graph, change, callback)
def graph_merge(g1, g2, change)

# 实体和关系检索
def get_relation(tenant_id, kb_id, from_ent_name, to_ent_name, size=1)
async def graph_node_to_chunk(kb_id, embd_mdl, ent_name, meta, chunks)
async def graph_edge_to_chunk(kb_id, embd_mdl, from_ent_name, to_ent_name, meta, chunks)
```

#### **数据模型**
```python
# 图变更跟踪
@dataclasses.dataclass
class GraphChange:
    removed_nodes: Set[str]
    added_updated_nodes: Set[str] 
    removed_edges: Set[Tuple[str, str]]
    added_updated_edges: Set[Tuple[str, str]]

# 图数据存储格式
{
    "knowledge_graph_kwd": "graph|entity|relation|subgraph",
    "content_with_weight": "JSON序列化的图数据",
    "entity_kwd": "实体名称",
    "from_entity_kwd": "关系源实体",
    "to_entity_kwd": "关系目标实体"
}
```

### 2. Graph功能特点

#### **优势**
✅ **成熟的图处理**: 基于NetworkX，支持复杂图操作
✅ **ES集成**: 图数据直接存储在ES中，便于检索
✅ **实体解析**: 支持实体消歧和合并
✅ **增量更新**: 支持图的增量构建和更新
✅ **多租户**: 完整的租户隔离机制
✅ **缓存优化**: Redis缓存LLM调用和嵌入结果

#### **适用场景**
- 实体关系抽取和存储
- 知识图谱构建和查询
- 图数据的可视化展示
- 基于图的检索增强

## 🔍 ES功能调研

### 1. ES架构概览

#### **核心组件**
- **连接层**: `rag/utils/es_conn.py` - ES连接和基础操作
- **搜索层**: `rag/nlp/search.py` - 高级搜索和检索
- **文档服务**: `api/db/services/document_service.py` - 文档索引管理

#### **关键接口**

**ES连接类** (`ESConnection`):
```python
# 索引管理
def createIdx(indexName, knowledgebaseId, vectorSize)
def deleteIdx(indexName, knowledgebaseId) 
def indexExist(indexName, knowledgebaseId)

# CRUD操作
def search(selectFields, highlightFields, condition, matchExprs, orderBy, offset, limit, indexNames, knowledgebaseIds)
def insert(documents, indexName, knowledgebaseId)
def delete(condition, indexName, knowledgebaseId)
```

**搜索服务** (`Dealer`):
```python
# 检索接口
def search(req, idx_names, kb_ids, emb_mdl, highlight, rank_feature)
def retrieval(question, embd_mdl, tenant_ids, kb_ids, page, page_size, similarity_threshold)

# 向量搜索
def get_vector(text, emb_mdl, topk, similarity_threshold)
```

#### **数据结构**
```python
# 文档chunk结构
{
    "id": "chunk_id",
    "content_with_weight": "文档内容", 
    "content_ltks": "分词结果",
    "q_<dim>_vec": "向量嵌入",
    "kb_id": "知识库ID",
    "doc_id": "文档ID",
    "knowledge_graph_kwd": "类型标识",
    "entity_kwd": "实体关键词",
    "important_kwd": "重要关键词"
}
```

### 2. ES功能特点

#### **优势**
✅ **混合检索**: 支持文本+向量混合搜索
✅ **多模态**: 支持文本、图片等多种数据类型
✅ **高性能**: 分布式架构，支持大规模数据
✅ **灵活查询**: 支持复杂的过滤和聚合查询
✅ **实时索引**: 支持文档的实时索引和更新

#### **适用场景**
- 大规模文档检索
- 语义相似性搜索
- 多条件组合查询
- 实时数据分析

## 🚀 合同风险图数据库设计方案

### 1. 架构设计

#### **数据模型**
```python
# 合同实体
{
    "knowledge_graph_kwd": "contract_entity",
    "entity_type_kwd": "contract|party|clause|risk",
    "entity_kwd": "实体名称",
    "content_with_weight": {
        "entity_name": "合同名称",
        "entity_type": "contract", 
        "contract_type": "投资协议",
        "risk_level": "高",
        "description": "实体描述"
    }
}

# 风险关系
{
    "knowledge_graph_kwd": "contract_relation", 
    "from_entity_kwd": "合同A",
    "to_entity_kwd": "风险点B",
    "relation_type_kwd": "has_risk|similar_to|caused_by",
    "content_with_weight": {
        "relation_type": "has_risk",
        "description": "关系描述",
        "confidence": 0.85,
        "risk_propagation": "传播路径"
    }
}
```

#### **服务层设计**
```python
# 合同图服务
class ContractGraphService:
    def build_contract_graph(contract, risks) -> nx.Graph
    def add_contract_entity(contract) -> str
    def add_risk_entities(risks) -> List[str] 
    def create_risk_relationships(contract_id, risk_ids) -> List[Tuple]
    def find_similar_contracts(contract) -> List[str]
    def analyze_risk_propagation(risk_id) -> Dict

# 合同检索服务  
class ContractSearchService:
    def search_similar_risks(risk_description, contract_type) -> List[Dict]
    def search_contracts_by_risk(risk_type, risk_level) -> List[Dict]
    def get_risk_statistics(tenant_id, time_range) -> Dict
```

### 2. 实施路径

#### **阶段1: 基础图构建**
1. **复用Graph工具**: 使用`graphrag/utils.py`中的图操作函数
2. **扩展实体类型**: 在现有entity基础上添加合同特定实体
3. **定义关系类型**: 设计合同-风险、风险-条款等关系

#### **阶段2: 检索增强**
1. **复用ES检索**: 使用`rag/nlp/search.py`的检索能力
2. **自定义过滤器**: 添加合同类型、风险等级等过滤条件
3. **相似性搜索**: 基于向量嵌入找相似合同和风险

#### **阶段3: 高级分析**
1. **风险传播分析**: 基于图结构分析风险传播路径
2. **模式识别**: 识别常见的风险模式和组合
3. **预测分析**: 基于历史数据预测潜在风险

### 3. 技术实现

#### **复用现有接口**
```python
# 图操作
from graphrag.utils import get_graph, set_graph, graph_merge
from graphrag.search import KGSearch

# ES检索
from rag.nlp.search import Dealer
from api.db.services.document_service import DocumentService

# 合同图服务实现
class ContractGraphService:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.kg_search = KGSearch(settings.docStoreConn)
        self.dealer = Dealer(settings.docStoreConn)
    
    async def build_contract_graph(self, contract: Contract, risks: List[ContractRisk]):
        # 创建图对象
        graph = nx.Graph()
        
        # 添加合同节点
        contract_node = {
            "entity_name": contract.basic_info.title,
            "entity_type": "contract",
            "description": contract.basic_info.summary or "",
            "source_id": [contract.id]
        }
        graph.add_node(contract.id, **contract_node)
        
        # 添加风险节点和关系
        for risk in risks:
            risk_node = {
                "entity_name": risk.risk_type,
                "entity_type": "risk", 
                "description": risk.description,
                "risk_level": risk.level,
                "source_id": [contract.id]
            }
            graph.add_node(risk.id, **risk_node)
            
            # 添加合同-风险关系
            graph.add_edge(contract.id, risk.id, 
                          relation_type="has_risk",
                          description=f"合同存在{risk.risk_type}",
                          weight=1.0 if risk.level == "高" else 0.5,
                          source_id=[contract.id])
        
        # 保存到ES
        change = GraphChange()
        change.added_updated_nodes = set(graph.nodes())
        change.added_updated_edges = set(graph.edges())
        
        await set_graph(self.tenant_id, "contract_kb", embd_mdl, graph, change, None)
        return graph
```

## 📊 可行性评估

### ✅ 高度可行
1. **技术成熟**: RAGFlow的Graph和ES功能已经在生产环境验证
2. **接口完整**: 提供了完整的图操作和检索接口
3. **扩展性强**: 支持自定义实体类型和关系
4. **性能优秀**: 基于ES的分布式架构，支持大规模数据

### 🎯 推荐方案
1. **短期**: 直接复用现有Graph和ES接口构建合同风险图
2. **中期**: 基于图数据实现风险分析和相似性检索
3. **长期**: 构建完整的合同风险知识图谱和预测系统

### 📝 下一步行动
1. **原型开发**: 基于现有接口开发合同图构建原型
2. **性能测试**: 验证大规模合同数据的处理能力
3. **功能扩展**: 根据业务需求扩展图分析功能
