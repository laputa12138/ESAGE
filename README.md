# E-SAGE: 基于多智能体协同的产业链结构化生成与演化引擎

# (E-SAGE: Evidence-based Structural Alignment and Graph Extraction)

## 项目简介

**E-SAGE** (Evidence-based Structural Alignment and Graph Extraction) 是一个基于多智能体协同（Multi-Agent Collaboration）和检索增强生成（RAG）技术的先进系统。旨在从大量非结构化文档（如行业报告、政策文件、PDF/Word）中，自动提取产业链结构，并生成包含节点详细信息及溯源证据的结构化图谱（Graph）。

本系统通过模拟人类专家的研究流程，实现了从**主题分析**、**结构规划**、**证据溯源**到**递归扩展**的全自动化工作流，有效解决了传统信息提取中的幻觉问题和结构混乱问题。

### 核心特性

* **多智能体协同架构**: 采用 `Orchestrator` 编排多个专业 Agent，模拟专家分工协作：
    * **StructurePlannerAgent (规划师)**: 宏观把控，生成产业骨架。
    * **NodeExtractorAgent (矿工)**: 深度挖掘节点详情与关系。
    * **QueryBuilderAgent (翻译官)**: 生成混合检索查询（Vector + BM25）。
    * **ValidatorAgent (质检员)**: 清洗图谱，合并同义词，剔除噪音。
* **后验证据验证 (Posterior Evidence Verification)**: 引入 **CSS (Composite Support Score)** 模型。
    *   **Top-K 聚焦**: 仅使用与生成实体最相关的 Top-K (默认 10) 个检索文档（包括生成依据的源文档）进行验证，大幅提升效率。
    *   **LLM 证据提取**: 摒弃基于规则的句子匹配，直接让 LLM 从 Top-K 文档中精确提取能够支撑生成的**原始关键句**，确保信息不失真。
* **Generalized Exact Match Boosting**: 针对实体（公司、技术、原料等）实施精确匹配增强策略，确保关键信息的召回率。
* **递归式图谱生长 (Recursive Tree-Growing)**: 系统不仅执行静态规划，还能在抽取过程中自动发现新的上游/下游节点，并动态扩展抽取范围，直至达到预设深度。
* **混合检索架构**: 
    * **Vector Queries**: 捕捉隐含语义（如“某环节的生产工艺”）。
    * **BM25 Queries**: 捕捉精确术语（如化学式、特定公司名）。
* **本地化隐私保护**: 深度集成 Xinference，支持本地部署 LLM 和 Embedding 模型，确保数据安全。

## 系统架构

系统基于动态任务驱动的工作流引擎运行，主要组件包括：

1. **WorkflowState (工作流状态)**: 作为系统的“短时记忆”，维护任务队列、动态图谱结构（Graph）和上下文信息。
2. **Orchestrator (编排器)**: 负责任务调度，根据当前状态动态分发任务给最合适的 Agent。
3. **关键 Agents**:
   * `StructurePlannerAgent`: **宏观规划者**。分析行业主题，定义初始的产业链上、中、下游骨架。
   * `QueryBuilderAgent`: **查询构建者**。为每个节点生成差异化的向量查询和关键词查询，确保检索内容的广度与精度。
   * `NodeExtractorAgent`: **微观探索与验证者**。针对具体节点抽取详细信息，并调用 `PosteriorVerifier` 进行证据注入，同时具备**自我扩展能力**。
   * `ValidatorAgent`: **图谱治理者**。在抽取结束后，对全图进行扫描，合并同义节点（如"光伏玻璃"与"太阳能玻璃"），删除非关联节点。
4. **PosteriorVerifier (后验验证器)**: 独立的验证模块，使用 LLM 对 Top-K 文档进行判别和原始证据提取，杜绝幻觉。
5. **RetrievalService (检索服务)**: 统一封装向量检索（FAISS）和关键词检索（BM25），提供高质量的上下文。

## 环境安装

本系统要求使用特定的 Conda 环境运行。

### 1. 环境依赖

* **操作系统**: Windows / Linux
* **Python**: 3.8+
* **Conda 环境名称**: `ym`

### 2. 安装步骤

```bash
# 激活 Conda 环境
conda activate ym

# 安装 Python 依赖
pip install -r requirements.txt
```

### 3. 模型服务

确保本地已启动 [Xinference](https://github.com/xorbitsai/inference) 服务，并部署了在 `config/settings.py` 中配置的模型（LLM, Embedding, Reranker）。

## 使用指南

请务必使用项目指定的 Python 解释器路径运行脚本。

### 基本用法

使用 `main.py` 启动抽取任务。你需要指定**行业主题** (`--topic`)。

```bash
E:\miniconda\envs\ym\python.exe main.py --topic "低空经济"
```

### 常用参数

| 参数                    | 说明                                                     | 默认值                               |
| :---------------------- | :------------------------------------------------------- | :----------------------------------- |
| `--topic`             | **(必选)** 行业主题名称，如 "低空经济"、"商业航天" | 无                                   |
| `--data_path`         | 源文档目录路径                                           | `./data`                        |
| `--output_path`       | 结果 JSON 保存路径                                       | `output/graph_{topic}_{time}.json` |
| `--max_recursion_depth` | **(新增)** 递归扩展深度。0=仅静态规划，>0=允许动态发现新节点 | `2`                                  |
| `--vector_store_path` | 向量索引保存/加载路径                                    | `./my_vector_indexes/`             |
| `--force_reindex`     | 是否强制重新构建向量索引                                 | `False`                            |

### 运行示例

**示例 1：标准抽取（带自动扩展）**
处理 `./data` 下的文档，生成 "生物医药" 产业链图谱，允许向下扩展 2 层。

```bash
E:\miniconda\envs\ym\python.exe main.py --topic "生物医药" --data_path "./data" --output_path 'output/bio.json' --max_recursion_depth 2
```

**示例 2：仅静态规划（无递归）**
如果只想获取最顶层的规划结构，不进行深度挖掘：

```bash
E:\miniconda\envs\ym\python.exe main.py --topic "光伏产业" --max_recursion_depth 0
```

### 输出结果

脚本运行完成后，将在 `output/` 目录下生成一个 JSON 文件，包含完整的产业链图谱结构：

```json
{
  "root_topic": "低空经济",
  "structure": {
    "upstream": ["碳纤维", "航空发动机", ...],
    "midstream": [...],
    "downstream": [...]
  },
  "node_details": {
    "碳纤维": {
      "entity_name": "碳纤维",
      "description": "...",
      "input_elements": ["聚丙烯腈"], // 可能触发递归抽取
      "output_products": ["机身复合材料"],
      "representative_companies": ["光威复材", "中简科技"],
      "evidence_refs": { // 溯源证据
         "representative_companies": {
             "光威复材": {
                 "source_id": "XX研报_2024.pdf",
                 "key_evidence": "光威复材作为国内碳纤维龙头企业...",
                 "score": 0.95
             }
         }
      }
    }
  }
}
```

## 核心机制详解：E-SAGE 进化版

本系统实现了自动化产业链扩展与高精度验证。

### 1. 种子阶段：宏观规划 (Seed Generation)
**负责角色**: `StructurePlannerAgent`
*   LLM 分析全局上下文，生成**初始骨架**（例如：上游-抗生素原料，中游-化学制药）。

### 2. 生长阶段：循环迭代与闭环验证 (Iterative Extraction & Verification)
**负责角色**: `Orchestrator`, `NodeExtractorAgent`, `QueryBuilderAgent`

1.  **混合查询构建**: `QueryBuilderAgent` 针对当前节点生成语义查询（捕捉隐含关系）和精准关键词（捕捉实体）。
2.  **信息抽取**: LLM 从文档中提取结构化信息。
3.  **后验证据注入 (Posterior Evidence Injection)**:
    *   **PosteriorVerifier** 对提取的每一条信息（Claim）进行验证。
    *   **范围锁定**: 仅对 **Top-K** (默认 10) 个最相关文档进行深度检查。
    *   **原句提取**: 调用 LLM 判断支持性，并**提取原文证据句**（必须与文档完全一致）。
    *   **CSS 评分**: 结合 **NLI 分数 (语义支持)** 和 **Lexical 预过滤 (实体匹配)**，精确匹配的实体给予额外加分。JSON 输出中将详细展示 `entity_match_score` 和 `nli_score` 分项。
    *   只有 CSS 分数高于阈值的信息才会被保留并注入证据 (低分证据保留在 `filtered_items` 以供复核)。
4.  **递归扩展**: 验证通过的新节点（如原材料、产成品）将被加入任务队列，触发下一轮抽取。

### 3. 收敛阶段：图谱治理 (Graph Governance)
**负责角色**: `ValidatorAgent`, `WorkflowState`
*   **僵尸节点过滤**: 实施严格的清理策略，移除虽然包含描述但无任何实质结构化信息（上/下游、技术、公司全为空）的节点，保持图谱纯净。
*   **同义词合并**: `ValidatorAgent` 扫描全图，识别并合并同义词节点（如 "EVA胶膜" 与 "光伏胶膜"）。
*   **噪音剔除**: 剔除语义上不属于产业链物理环节的噪音节点。

---

## 关键代码文件说明

| 路径 | 文件名 | 作用与职责 |
| :--- | :--- | :--- |
| **`core/`** | `workflow_state.py` | **系统大脑/记忆**。维护图谱结构、任务队列和全局状态。 |
| | `orchestrator.py` | **指挥官**。负责主循环，协调所有 Agent。 |
| | `posterior_verifier.py` | **(核心) 验证器**。实现 CSS 评分逻辑 (Lexical + NLI) 和 Exact Match Boosting。 |
| | `retrieval_service.py` | **检索中台**。提供统一的混合检索接口。 |
| **`agents/`** | `structure_planner_agent.py` | **宏观规划师**。生成产业链初始骨架。 |
| | `query_builder_agent.py` | **查询构建者**。生成 Vector 和 BM25 查询。 |
| | `node_extractor_agent.py` | **微观矿工**。负责信息抽取、调用验证器、触发递归。**关键逻辑 `execute_task` 在此**。 |
| | `validator_agent.py` | **质检员**。负责图谱清洗和节点合并。 |
| **`pipelines/`** | `report_generation_pipeline.py` | **组装线**。组装各组件，提供统一运行入口。 |
| **根目录** | `main.py` | **程序入口**。处理参数并启动系统。 |
