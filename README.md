# E-SAGE: 基于多智能体协同的产业链结构化生成与演化引擎

# (E-SAGE: Evidence-based Structural Alignment and Graph Extraction)

## 项目简介

**E-SAGE** (Evidence-based Structural Alignment and Graph Extraction) 是一个基于多智能体协同（Multi-Agent Collaboration）和检索增强生成（RAG）技术的先进系统。旨在从大量非结构化文档（如行业报告、政策文件、PDF/Word）中，自动提取产业链结构，并生成包含节点详细信息及溯源证据的结构化图谱（Graph）。

本系统通过模拟人类专家的研究流程，实现了从**主题分析**、**结构规划**、**证据溯源**到**递归扩展**的全自动化工作流，有效解决了传统信息提取中的幻觉问题和结构混乱问题。

### 核心特性

* **多智能体协同架构**: 采用 `Orchestrator` (系统编排器) 动态调度多个专业 Agent，模拟专家分工协作：
  * **StructurePlannerAgent (结构化规划Agent)**: 负责宏观层面的产业骨架规划与构建。
  * **NodeExtractorAgent (节点抽取Agent)**: 负责微观层面的节点信息深度挖掘与关系抽取。
  * **QueryBuilderAgent (语义查询构建Agent)**: 负责生成基于向量 (Vector) 和关键词 (BM25) 的混合检索查询。
  * **ValidatorAgent (一致性验证Agent)**: 负责图谱的清洗、实体对齐及噪音剔除。
* **后验证据验证 (Posterior Evidence Verification)**: 引入 **CSS (Composite Support Score)** 模型。
  * **Top-K 聚焦**: 仅使用与生成实体最相关的 Top-K (默认 10) 个检索文档进行验证。
  * **LLM 证据提取**: 利用大语言模型从文档中精确提取支持性原文证据，确保可追溯性。
* **混合检索架构**: 结合语义检索 (捕捉隐含关系) 与精确匹配检索 (捕捉专有名词)。
* **递归式图谱生长 (Recursive Tree-Growing)**: 支持从初始骨架出发，动态发现并扩展新的上下游节点。
* **可视化交互**: 基于 React + Cytoscape.js 的交互式前端，支持图谱的动态展示与细节查看。

## 系统架构

系统基于动态任务驱动的工作流引擎运行，主要组件包括：

1. **WorkflowState (工作流状态)**: 维护任务队列、动态图谱结构（Graph）和全局上下文信息。
2. **Orchestrator (系统编排器)**: 负责任务调度与资源分配，根据当前状态动态激活相应的 Agent。
3. **关键 Agents**:
   * `StructurePlannerAgent`: **结构化规划Agent**。分析行业主题，定义初始的产业链上、中、下游层级结构。
   * `QueryBuilderAgent`: **语义查询构建Agent**。为特定节点生成高精度的多样化查询请求。
   * `NodeExtractorAgent`: **节点抽取Agent**。执行具体的信息抽取任务，并调用验证模块进行证据注入与自我扩展。
   * `ValidatorAgent`: **一致性验证Agent**。执行图谱治理，合并同义实体，确保知识库的整洁与一致性。
4. **PosteriorVerifier (后验验证模块)**: 独立的验证组件，基于 CSS 模型对提取信息进行真值判别与证据关联。
5. **RetrievalService (混合检索模块)**: 封装向量检索与关键词检索，提供统一的高质量上下文召回服务。

## 可视化 (Visualization)

本项目包含一个基于 **React** 和 **Cytoscape.js** 的前端可视化模块，位于 `bio-chain-vis` 目录下。该模块旨在直观地展示生成的产业链图谱，支持：

- **层级展示**: 清晰呈现上游、中游、下游的结构关系。
- **节点交互**: 点击节点即可在侧边栏查看详细信息（投入要素、产出产品、关键技术、代表企业及溯源证据）。
- **动态布局**: 基于 Dagre 算法的自动布局，支持缩放和平移。
- **现代化 UI**: 采用 Glassmorphism 设计风格，提供优质的用户体验。

## 安装说明

本系统包含后端（Python）和前端（Node.js）两部分。

### 1. 后端环境 (Python)

**前提条件**:

- 已安装 Anaconda 或 Miniconda。
- 操作系统: Windows / Linux。

**安装步骤**:

```bash
# 激活指定环境 (环境名称: ym)
conda activate ym

# 安装依赖
pip install -r requirements.txt
```

### 2. 前端环境 (Node.js)

**前提条件**:

- 已安装 Node.js (建议 v16+)。

**安装步骤**:

```bash
# 进入可视化项目目录
cd bio-chain-vis

# 安装依赖
npm install
```

### 3. 模型服务

确保本地已启动 [Xinference](https://github.com/xorbitsai/inference) 服务，并部署了 `config/settings.py` 中配置的模型（LLM, Embedding, Reranker）。

## 使用指南

### 1. 运行后端抽取

使用 `main.py` 启动产业链抽取任务。建议使用完整的 Python 解释器路径。

**基本命令**:

```bash
E:\miniconda\envs\ym\python.exe main.py --topic "低空经济"
```

**常用参数**:

- `--topic`: (必选) 行业主题名称。
- `--output_path`: 结果 JSON 保存路径 (默认为 `output/graph_{topic}_{time}.json`)。
- `--max_recursion_depth`: 递归扩展深度 (默认为 2)。

**示例**:

```bash
E:\miniconda\envs\ym\python.exe main.py --topic "生物医药" --max_recursion_depth 2
```

### 2. 运行前端可视化

在后端生成 JSON 数据后，启动前端查看图谱。

**启动服务**:

```bash
cd bio-chain-vis
npm run dev
```

**访问页面**:
服务启动后，在浏览器中访问终端输出的地址 (通常为 `http://localhost:5173`)。您需要手动加载后端生成的 JSON 文件（通常位于 `../output/` 目录下）进行展示。

## 关键代码文件说明

| 路径                  | 文件名                         | 作用与职责                                                      |
| :-------------------- | :----------------------------- | :-------------------------------------------------------------- |
| **`core/`**   | `workflow_state.py`          | **系统状态管理**。维护图谱数据结构与任务流状态。          |
|                       | `orchestrator.py`            | **系统编排器**。系统的核心调度引擎。                      |
|                       | `posterior_verifier.py`      | **后验验证模块**。基于 Lexical + NLI 的证据验证核心逻辑。 |
|                       | `retrieval_service.py`       | **混合检索模块**。集成向量与关键词检索的统一服务层。      |
| **`agents/`** | `structure_planner_agent.py` | **结构化规划Agent**。生成宏观产业架构。                   |
|                       | `query_builder_agent.py`     | **语义查询构建Agent**。生成高召回率的检索查询。           |
|                       | `node_extractor_agent.py`    | **节点抽取Agent**。执行微观信息抽取与递归扩展。           |
|                       | `validator_agent.py`         | **一致性验证Agent**。执行图谱的合并与清洗。               |
| **根目录**      | `main.py`                    | **程序入口**。参数解析与系统启动脚本。                    |
