# E-SAGE: 基于多智能体协同的产业链结构化生成与演化引擎

# (E-SAGE: Evidence-based Structural Alignment and Graph Extraction)

## 项目简介

**E-SAGE** (Evidence-based Structural Alignment and Graph Extraction) 是一个基于多智能体协同（Multi-Agent Collaboration）和检索增强生成（RAG）技术的先进系统。旨在从大量非结构化文档（如行业报告、政策文件、PDF/Word）中，自动提取产业链结构，并生成包含节点详细信息及溯源证据的结构化图谱（Graph）。

本系统通过模拟人类专家的研究流程，实现了从**主题分析**、**结构规划**、**证据溯源**到**递归扩展**的全自动化工作流，有效解决了传统信息提取中的幻觉问题和结构混乱问题。

### 核心特性

* **多智能体协同架构**: 采用 `Orchestrator` 编排多个专业 Agent（如结构规划、节点提取），模拟专家分工协作。
* **递归式图谱生长 (Recursive Tree-Growing)**: 系统不仅执行静态规划，还能在抽取过程中自动发现新的上游/下游节点，并动态扩展抽取范围，直至达到预设深度。
* **证据驱动 (Evidence-based)**: 所有提取的节点和关系均强关联至原始文档片段，确保信息可追溯、可验证。
* **混合检索与父子分块**: 结合向量检索与 BM25 关键词检索，利用 Parent-Child Chunking 策略兼顾检索精度与上下文完整性。
* **本地化隐私保护**: 深度集成 Xinference，支持本地部署 LLM 和 Embedding 模型，确保数据安全。

## 系统架构

系统基于动态任务驱动的工作流引擎运行，主要组件包括：

1. **WorkflowState (工作流状态)**: 作为系统的“短时记忆”，维护任务队列、动态图谱结构（Graph）和上下文信息。
2. **Orchestrator (编排器)**: 负责任务调度，根据当前状态动态分发任务给最合适的 Agent。
3. **核心 Agents**:
   * `StructurePlannerAgent`: **宏观规划者**。分析行业主题，定义初始的产业链上、中、下游骨架。
   * `NodeExtractorAgent`: **微观探索者**。针对具体节点抽取详细信息，并具备**自我扩展能力**——能够从抽取内容中识别新的关联节点（如原材料、产成品），触发递归抽取。
4. **RetrievalService (检索服务)**: 统一封装向量检索（FAISS）和关键词检索（BM25），提供高质量的上下文。

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
      "evidence_refs": { ... }
    }
  }
}
```

## 核心机制详解：从“种子”到“森林”的递归抽取

本系统实现了自动化产业链扩展，其过程类似植物生长。

### 1. 种子阶段：宏观规划 (Seed Generation)
**负责角色**: `StructurePlannerAgent`

*   **初始检索**: 全局检索主题（如“生物医药”），获取宏观背景。
*   **结构生成**:  LLM 分析后生成**初始骨架**（例如：上游-抗生素原料，中游-化学制药）。
*   **任务播种**: 这些初始节点被作为第一批任务加入队列，深度标记为 `depth=0`。

### 2. 生长阶段：循环迭代 (Iterative Extraction)
**负责角色**: `Orchestrator` & `NodeExtractorAgent`

系统进入持续循环：取出任务 -> 处理 -> 发现新线索 -> 裂变新任务。

1.  **针对性检索**: 智能体为当前节点（如“抗生素原料”）生成特定查询词（“生物医药 抗生素原料 详细信息”），挖掘细节。
2.  **信息抽取**: LLM 从文档中提取结构化信息，包括 `input_elements`（上游线索）和 `output_products`（下游线索）。
3.  **递归扩展 (Recursive Expansion)**:
    *   **扫描**: 检查提取出的输入/输出要素（如发现上游原料“玉米发酵液”）。
    *   **验证**: 确认当前深度未超限 (`depth < MAX_DEPTH`) 且该节点未在图谱中存在。
    *   **裂变**: 将新发现的节点（“玉米发酵液”）加入图谱，并创建新任务推入队列 (`depth=1`)。

### 3. 结果汇总
通过这种机制，系统从根主题出发，自动挖掘出骨架之下更细微的“毛细血管”（具体原料、细分部件），形成一棵完整的产业链树。

---

## 关键代码文件说明

| 路径 | 文件名 | 作用与职责 |
| :--- | :--- | :--- |
| **`core/`** | `workflow_state.py` | **系统大脑/记忆**。维护图谱结构（Graph）、任务队列（Queue）和全局状态。新增了 `add_node_to_structure` 用于动态扩展。 |
| | `orchestrator.py` | **指挥官**。负责主循环，监控队列状态，将任务分发给 Agent，并管理系统的生命周期。 |
| | `retrieval_service.py` | **检索中台**。封装了 FAISS 向量检索和 BM25 关键词检索，向 Agent 提供统一的 `retrieve()` 接口。 |
| **`agents/`** | `structure_planner_agent.py` | **宏观规划师**。负责第一阶段，从 0 到 1 生成产业链的初始骨架。 |
| | `node_extractor_agent.py` | **微观矿工**。负责第二阶段，深入挖掘每个节点的信息。**关键逻辑 `_expand_nodes` 在此实现**，负责发现新节点并触发递归。 |
| **`pipelines/`** | `report_generation_pipeline.py` | **组装线**。将 LLM、Retrieval、Orchestrator 等组件组装在一起，对外提供 `run()` 入口。 |
| **根目录** | `main.py` | **程序入口**。处理命令行参数（如 `--topic`, `--max_recursion_depth`），初始化服务并启动 Pipeline。 |
