# E-SAGE: 基于多智能体协同的产业链结构化生成与演化引擎
# (E-SAGE: Evidence-based Structural Alignment and Graph Extraction)

## 项目简介

**E-SAGE** (Evidence-based Structural Alignment and Graph Extraction) 是一个基于多智能体协同（Multi-Agent Collaboration）和检索增强生成（RAG）技术的先进系统。旨在从大量非结构化文档（如行业报告、政策文件、PDF/Word）中，自动提取产业链结构，并生成包含节点详细信息及溯源证据的结构化图谱（Graph）。

本系统通过模拟人类专家的研究流程，实现了从**主题分析**、**结构规划**到**证据溯源**的全自动化工作流，有效解决了传统信息提取中的幻觉问题和结构混乱问题。

### 核心特性

*   **多智能体协同架构**: 采用 `Orchestrator` 编排多个专业 Agent（如结构规划、节点提取），模拟专家分工协作。
*   **证据驱动 (Evidence-based)**: 所有提取的节点和关系均强关联至原始文档片段，确保信息可追溯、可验证。
*   **动态图谱构建**: 支持通过 `StructurePlannerAgent` 自主规划产业链层级与节点，并由 `NodeExtractorAgent` 填充细节。
*   **混合检索与父子分块**: 结合向量检索与 BM25 关键词检索，利用 Parent-Child Chunking 策略兼顾检索精度与上下文完整性。
*   **本地化隐私保护**: 深度集成 Xinference，支持本地部署 LLM 和 Embedding 模型，确保数据安全。

## 系统架构

系统基于动态任务驱动的工作流引擎运行，主要组件包括：

1.  **WorkflowState (工作流状态)**: 作为系统的“短时记忆”，维护任务队列、图谱数据（Graph）和上下文信息。
2.  **Orchestrator (编排器)**: 负责任务调度，根据当前状态动态分发任务给最合适的 Agent。
3.  **核心 Agents**:
    *   `StructurePlannerAgent`: 负责“宏观规划”，分析行业主题，定义产业链的上、中、下游结构及关键节点名称。
    *   `NodeExtractorAgent`: 负责“微观提取”，针对规划出的节点，从文档中检索具体信息（如市场规模、核心企业），并关联原文证据。
4.  **RetrievalService (检索服务)**: 统一封装向量检索（FAISS）和关键词检索（BM25），提供高质量的上下文。

## 环境安装

本系统要求使用特定的 Conda 环境运行。

### 1. 环境依赖
*   **操作系统**: Windows / Linux
*   **Python**: 3.8+
*   **Conda 环境名称**: `ym`

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

| 参数 | 说明 | 默认值 |
| :--- | :--- | :--- |
| `--topic` | **(必选)** 行业主题名称，如 "低空经济"、"商业航天" | 无 |
| `--data_path` | 源文档目录路径 | `./data/v2` |
| `--output_path` | 结果 JSON 保存路径 | `output/graph_{topic}_{time}.json` |
| `--vector_store_path` | 向量索引保存/加载路径 | `./my_vector_indexes/` |
| `--force_reindex` | 是否强制重新构建向量索引 | `False` |
| `--log_level` | 日志级别 (DEBUG, INFO) | `INFO` |

### 运行示例

**示例 1：标准抽取**
处理 `./data/v2` 下的文档，生成 "低空经济" 产业链图谱。
```bash
E:\miniconda\envs\ym\python.exe main.py --topic "低空经济" --data_path "./data/v2"
```

**示例 2：强制重新索引**
如果添加了新文档，需加上 `--force_reindex` 标志。
```bash
E:\miniconda\envs\ym\python.exe main.py --topic "商业航天" --data_path "./data/aerospace" --force_reindex
```

### 输出结果

脚本运行完成后，将在 `output/` 目录下生成一个 JSON 文件，包含完整的产业链图谱结构：
```json
{
  "root": "低空经济",
  "layers": [
    {
      "name": "上游：原材料与核心零部件",
      "nodes": [
        {
          "name": "碳纤维",
          "details": "...",
          "evidence": "..."
        }
      ]
    },
    ...
  ]
}
```

## 文件结构

```text
.
├── agents/                     # [核心] 各类 AI 智能体实现
│   ├── structure_planner_agent.py   # 结构规划
│   ├── node_extractor_agent.py      # 节点内容提取
│   └── ...
├── core/                       # [核心] 基础服务模块
│   ├── orchestrator.py         # 任务编排
│   ├── workflow_state.py       # 状态管理
│   ├── retrieval_service.py    # 检索逻辑
│   └── ...
├── pipelines/                  # 业务流水线
│   └── report_generation_pipeline.py  # 产业链抽取主流程
├── data/                       # 输入数据目录
├── output/                     # 输出结果目录
├── main.py                     # 程序入口
├── requirements.txt            # 项目依赖
└── README.md                   # 项目说明
```
