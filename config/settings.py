import os

# ==============================================================================
# Xinference 服务配置 (Xinference Service Configuration)
# ==============================================================================
XINFERENCE_API_URL = os.getenv("XINFERENCE_API_URL", "http://180.163.192.103:1875") # Xinference API 服务器 URL

# ==============================================================================
# 大语言模型 (LLM) 配置 (Large Language Model Configuration)
# ==============================================================================
DEFAULT_LLM_MODEL_NAME = os.getenv("DEFAULT_LLM_MODEL_NAME", "qwen3") # 默认 LLM 模型名称
DEFAULT_LLM_MAX_TOKENS = int(os.getenv("DEFAULT_LLM_MAX_TOKENS", "50000")) # LLM 生成时最大 token 数量
DEFAULT_LLM_TEMPERATURE = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.6")) # LLM 生成温度
DEFAULT_LLM_TOP_P = float(os.getenv("DEFAULT_LLM_TOP_P", "0.95")) # LLM nucleus sampling (top-p) 参数
DEFAULT_LLM_ENABLE_THINKING = os.getenv("DEFAULT_LLM_ENABLE_THINKING", "True").lower() == "true" # 是否启用 LLM 的 "思考" 模式 (如果模型支持)
DEFAULT_LLM_TOP_K = int(os.getenv("DEFAULT_LLM_TOP_K", "20")) # LLM top-k 采样参数
DEFAULT_LLM_MIN_P = float(os.getenv("DEFAULT_LLM_MIN_P", "0")) # LLM min-p 采样参数 (一些模型可能支持)

# ==============================================================================
# 词嵌入模型配置 (Embedding Model Configuration)
# ==============================================================================
DEFAULT_EMBEDDING_MODEL_NAME = os.getenv("DEFAULT_EMBEDDING_MODEL_NAME", "Qwen3-Embedding-0.6B") # 默认词嵌入模型名称

# ==============================================================================
# Reranker 模型配置 (Reranker Model Configuration)
# ==============================================================================
DEFAULT_RERANKER_MODEL_NAME = os.getenv("DEFAULT_RERANKER_MODEL_NAME", "Qwen3-Reranker-0.6B") # 默认 Reranker 模型名称
DEFAULT_RERANKER_BATCH_SIZE = int(os.getenv("DEFAULT_RERANKER_BATCH_SIZE", "20")) # Reranker 处理文档时的批次大小 (调小默认值)
DEFAULT_RERANKER_MAX_TEXT_LENGTH = int(os.getenv("DEFAULT_RERANKER_MAX_TEXT_LENGTH", "32000")) # 发送给 Reranker 的文档最大字符长度 (调小默认值)
DEFAULT_RERANKER_INPUT_LIMIT = int(os.getenv("DEFAULT_RERANKER_INPUT_LIMIT", "40")) # 发送给 Reranker 的最大文档数量

# ==============================================================================
# 文档处理配置 (Document Processing Configuration)
# ==============================================================================
# --- 通用分块设置 (General Chunking Settings) ---
# (如果未使用父子分块，则为后备设置)
DEFAULT_CHUNK_SIZE = int(os.getenv("DEFAULT_CHUNK_SIZE", "500")) # 通用分块大小 (字符数)
DEFAULT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHUNK_OVERLAP", "100")) # 通用分块重叠大小 (字符数)

# --- 父子分块配置 (Parent-Child Chunking Configuration) ---
# 父块旨在包含更丰富的上下文 (例如段落)
DEFAULT_PARENT_CHUNK_SIZE = int(os.getenv("DEFAULT_PARENT_CHUNK_SIZE", "1000")) # 父块目标字符数
DEFAULT_PARENT_CHUNK_OVERLAP = int(os.getenv("DEFAULT_PARENT_CHUNK_OVERLAP", "200")) # 父块重叠字符数
# 子块旨在包含更小、更集中的片段 (例如句子或少量句子)
DEFAULT_CHILD_CHUNK_SIZE = int(os.getenv("DEFAULT_CHILD_CHUNK_SIZE", "100"))  # 子块目标字符数
DEFAULT_CHILD_CHUNK_OVERLAP = int(os.getenv("DEFAULT_CHILD_CHUNK_OVERLAP", "50"))   # 子块重叠字符数
# 注意: 分隔符可用于更语义化的分块 (例如, "\n\n" 代表段落)。
# 如果使用 NLTK 进行句子切分，这可能不直接用于子块，但可用于父块或作为后备。
# 为简单起见，目前主要依赖大小进行分块。

# --- 支持的文档类型 (Supported Document Types) ---
SUPPORTED_DOC_EXTENSIONS = [".pdf", ".docx", ".txt"] # 支持处理的文档扩展名

# ==============================================================================
# 向量存储配置 (Vector Store Configuration)
# ==============================================================================

DEFAULT_VECTOR_STORE_TOP_K = int(os.getenv("DEFAULT_VECTOR_STORE_TOP_K", "10")) # 向量搜索时检索的文档数量

DEFAULT_VECTOR_STORE_PATH = os.getenv("DEFAULT_VECTOR_STORE_PATH", "./my_vector_indexes") # 向量存储索引文件的默认保存路径

# ==============================================================================
# 混合搜索与检索配置 (Hybrid Search & Retrieval Configuration)
# ==============================================================================
# 用于混合向量搜索和关键字搜索分数的 Alpha 参数。
# Alpha = 1.0 表示纯向量搜索，Alpha = 0.0 表示纯关键字搜索。
# DEFAULT_HYBRID_SEARCH_ALPHA = float(os.getenv("DEFAULT_HYBRID_SEARCH_ALPHA", "0.5"))
# 融合前关键字搜索 (BM25) 的 Top K 数量。
DEFAULT_KEYWORD_SEARCH_TOP_K = int(os.getenv("DEFAULT_KEYWORD_SEARCH_TOP_K", "20"))
# RAG检索后，送入LLM生成答案的最终文档数量。
DEFAULT_RETRIEVAL_FINAL_TOP_N = int(os.getenv("DEFAULT_RETRIEVAL_FINAL_TOP_N", "40"))

# RERANKER 阈值
RERANKER_SCORE_THRESHOLD = float(os.getenv("RERANKER_SCORE_THRESHOLD", "0.6"))
VERIFICATION_THRESHOLD = float(os.getenv("VERIFICATION_THRESHOLD", "0.5"))

# --- Agent Specific Retrieval Settings ---
# For OutlineGeneratorAgent: Number of documents for initial outline context
DEFAULT_OUTLINE_GENERATION_RETRIEVAL_TOP_N = int(os.getenv("DEFAULT_OUTLINE_GENERATION_RETRIEVAL_TOP_N", "20"))
# For GlobalContentRetrieverAgent: Number of documents per chapter
DEFAULT_GLOBAL_RETRIEVAL_TOP_N_PER_CHAPTER = int(os.getenv("DEFAULT_GLOBAL_RETRIEVAL_TOP_N_PER_CHAPTER", "20")) # Reduced default

# ==============================================================================
# 后验验证器配置 (Posterior Verifier Configuration)
# ==============================================================================
# CSS (Composite Support Score) = Alpha * Lexical + Beta * NLI
# 计算公式：Score = Alpha * LexicalOverlap + Beta * NLI_Probability
POSTERIOR_VERIFIER_ALPHA = float(os.getenv("POSTERIOR_VERIFIER_ALPHA", "0.6")) # 字面刚性约束权重 (防止实体胡编)
POSTERIOR_VERIFIER_BETA = float(os.getenv("POSTERIOR_VERIFIER_BETA", "0.4"))   # 语义柔性约束权重 (确保逻辑支撑)
POSTERIOR_VERIFIER_THRESHOLD = float(os.getenv("POSTERIOR_VERIFIER_THRESHOLD", "0.6")) # 验证通过的最小 CSS 分数阈值
POSTERIOR_VERIFICATION_TOP_K = int(os.getenv("POSTERIOR_VERIFICATION_TOP_K", "10")) # 后验验证仅使用 Top K 个最相关文档 (性能优化)
POSTERIOR_VERIFIER_EPSILON = 1e-6 # 防止分母为零的小数

# ==============================================================================
# Quert Builder Configuration
# ==============================================================================
DEFAULT_QUERY_BUILDER_PROMPT = """你是一个专业的搜索查询构建专家。你的任务是为给定的产业链环节生成两类检索查询，以确保从文档库中召回最相关的内容。

产业链环节名称：'{node_name}'
行业背景：'{user_topic}'

请生成以下两组查询：
1. **vector_queries (基于向量的语义检索生成)**:
   - 目标：捕捉该环节的功能、上下游关系、工艺动作等隐含语义。
   - 形式：长句或短语，包含动词和描述性词汇。
   - 数量：3-5条。
   - 示例："光伏玻璃的生产工艺流程"、"生产太阳能电池组件所需的原材料"、"单晶硅片的上游供应环节"。

2. **bm25_queries (基于关键词的精确匹配)**:
   - 目标：捕捉专有名词、特定型号、化学式或行业术语。
   - 形式：关键词列表，尽量使用行业内特定的实体名，以及**包含“企业”、“公司”、“上市公司”、“龙头”等后缀的查询**。
   - 数量：3-5条。
   - 示例："光伏玻璃"、"超白压延玻璃"、"光伏玻璃企业"、"光伏玻璃龙头股"。

输出必须是严格的 JSON 格式：
{{
  "vector_queries": ["...", "..."],
  "bm25_queries": ["...", "..."]
}}
"""

# --- Query Generation/Expansion Settings ---
# Max expanded queries from TopicAnalyzerAgent (LLM prompt also guides this)
DEFAULT_MAX_EXPANDED_QUERIES_TOPIC = int(os.getenv("DEFAULT_MAX_EXPANDED_QUERIES_TOPIC", "20"))
# Max heuristic queries for GlobalContentRetrieverAgent per chapter
DEFAULT_MAX_CHAPTER_QUERIES_GLOBAL_RETRIEVAL = int(os.getenv("DEFAULT_MAX_CHAPTER_QUERIES_GLOBAL_RETRIEVAL", "20"))
# Max heuristic queries for ContentRetrieverAgent per chapter
DEFAULT_MAX_CHAPTER_QUERIES_CONTENT_RETRIEVAL = int(os.getenv("DEFAULT_MAX_CHAPTER_QUERIES_CONTENT_RETRIEVAL", "20"))

# --- Iterative Retrieval Settings ---
# used in agents/topic_analyzer_agent.py
# Global retrieval during topic analysis
GLOBAL_RETRIEVAL_MAX_ITERATIONS = int(os.getenv("GLOBAL_RETRIEVAL_MAX_ITERATIONS", "2"))
GLOBAL_RETRIEVAL_QUERIES_PER_ITERATION = int(os.getenv("GLOBAL_RETRIEVAL_QUERIES_PER_ITERATION", "5"))
GLOBAL_RETRIEVAL_TOP_N_PER_ITERATION = int(os.getenv("GLOBAL_RETRIEVAL_TOP_N_PER_ITERATION", "10"))

# Per-chapter retrieval
CHAPTER_RETRIEVAL_MAX_ITERATIONS = int(os.getenv("CHAPTER_RETRIEVAL_MAX_ITERATIONS", "2"))
CHAPTER_RETRIEVAL_QUERIES_PER_ITERATION = int(os.getenv("CHAPTER_RETRIEVAL_QUERIES_PER_ITERATION", "3"))



# ==============================================================================
# 日志配置 (Logging Configuration)
# ==============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper() # 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)

# ==============================================================================
# Agent 默认 Prompt 模板 (Agent Default Prompt Templates)
# ==============================================================================

# --- TopicAnalyzerAgent ---
DEFAULT_TOPIC_ANALYZER_PROMPT = """你是一个深度主题分析专家。请严格按照任务指令分析用户主题。

任务指令：
1.  泛化用户主题，分别提供中文和英文版本。
2.  提取与用户主题最相关的3-5个核心关键词（中文和英文）。
3.  识别1-3个核心研究问题（中文）。
4.  推断1-2种潜在研究方法或视角（中文）。
5.  生成{max_expanded_queries}个相关的、多样化的搜索查询建议（中文或英文）。

用户主题：'{user_topic}'

输出格式要求：
必须严格按照以下JSON结构返回结果。不要添加任何额外的解释、注释或说明文字。
确保所有键名（例如 "generalized_topic_cn"）都用双引号括起来。
确保所有字符串值（例如泛化主题、关键词、问题、方法、查询）都用双引号括起来。
确保列表类型的字段（例如 "keywords_cn", "core_research_questions_cn", "potential_methodologies_cn", "expanded_queries"）的值是JSON数组格式（例如 ["示例1", "示例2"]）。
不要生成任何未在以下JSON格式定义中出现的键名。

JSON输出格式定义：
{{
  "generalized_topic_cn": "此处填写泛化后的中文主题",
  "generalized_topic_en": "Fill generalized English topic here",
  "keywords_cn": ["关键词一", "关键词二"],
  "keywords_en": ["Keyword One", "Keyword Two"],
  "core_research_questions_cn": ["核心研究问题一？", "核心研究问题二？"],
  "potential_methodologies_cn": ["潜在研究方法一", "潜在研究方法二"],
  "expanded_queries": ["扩展查询一", "扩展查询二", "扩展查询三"]
}}
"""


# --- StructurePlannerAgent (Renamed from TopicAnalyzer) ---
INDUSTRY_STRUCTURE_PLANNER_PROMPT = """你是一个产业研究专家。你的任务是根据检索到的文档摘要，分析该产业的宏观产业链结构。
请识别该产业的“上游（Upstream）”、“中游（Midstream）”、“下游（Downstream）”分类，并列出每个分类下包含的具体“环节名称”。

产业大类：'{user_topic}'

输出要求：
1. 必须严格按照下面的JSON格式返回。
2. 不要包含Markdown格式（如 ```json ... ```）。
3. 确保环节名称准确、专业。
4. "upstream", "midstream", "downstream" 对应的值必须是字符串列表。

JSON输出格式：
{{
  "upstream": ["原材料A", "原材料B", "关键设备C"],
  "midstream": ["核心部件制造", "组装加工"],
  "downstream": ["应用领域X", "终端产品Y"]
}}
"""

# --- NodeExtractorAgent (Renamed from ChapterWriter) ---
NODE_EXTRACTOR_PROMPT = """你是一个产业数据抽取助手。你的任务是针对给定的“产业链环节”，从参考文档中提取详细的结构化信息。

产业链环节名称：'{node_name}'

参考文档：
---
{retrieved_content}
---

请提取以下字段的信息：
1. entity_name: 环节的标准名称（通常与输入的环节名称一致，或是更具体的名称）。
2. input_elements: 该环节的关键投入要素（如原材料、零部件、上游设备）。返回列表。
3. output_products: 该环节的关键产出（如产品、服务、中间件）。返回列表。
4. key_technologies: 该环节涉及的关键工艺或技术关键词。返回列表。
5. representative_companies: 该环节的国内外代表性企业。返回列表。**请尽可能多地列出文中明确提及的企业名称，不要遗漏。**
6. description: 对该环节的简短描述（50字以内）。

输出要求：
1. 必须严格以JSON格式返回。
2. 若文档中未提及某字段信息，请在该字段填入空列表 [] 或 null，不要编造。
3. 必须使用 `response_format={{"type": "json_object"}}` 提示（如果适用）。

JSON输出格式：
{{
  "entity_name": "环节名称",
  "input_elements": ["投入1", "投入2"],
  "output_products": ["产出1", "产出2"],
  "key_technologies": ["技术1", "技术2"],
  "representative_companies": ["企业A", "企业B", "企业C"],
  "description": "简短描述..."
}}
"""

# --- Query Expansion Prompts ---
QUERY_EXPANSION_PROMPT = """你是一名资深研究员，正在为一个关于“{topic}”的报告收集资料。
你已经有了一些初步的检索查询：
{existing_queries}

并且已经通过这些查询找到了一些相关内容：
--- 开始 ---
{retrieved_content}
--- 结束 ---

你的任务是基于以上信息，进行头脑风暴，提出 {num_new_queries} 个全新的、更深入的、或者不同角度的检索查询。

请遵循以下原则：
1.  **避免重复**：不要提出与已有查询 ({existing_queries}) 过于相似的查询。
2.  **探索性**：新查询应该能帮助我们探索未知领域、发现新的子主题、或者挖掘更具体的细节。
3.  **多样性**：尝试从不同角度提问，例如：技术细节、应用案例、未来趋势、相关挑战、不同实体之间的关系等。
4.  **简洁高效**：查询应简洁明了，适合搜索引擎。

请以 JSON 格式返回你的建议，格式如下：
{{
  "new_queries": [
    "查询1",
    "查询2",
    "..."
  ]
}}
"""

CHAPTER_QUERY_EXPANSION_PROMPT = """你是一名资深研究员，正在为一个报告中的具体章节：“{topic}” 收集资料。
你已经有了一些初步的检索查询：
{existing_queries}

并且已经通过这些查询找到了一些相关内容：
--- 开始 ---
{retrieved_content}
--- 结束 ---

你的任务是基于以上信息，进行头脑风暴，提出 {num_new_queries} 个全新的、更深入的、或者不同角度的检索查询，以确保章节内容全面而深入。

请遵循以下原则：
1.  **聚焦章节**：所有新查询必须严格围绕章节标题 “{topic}” 相关。
2.  **避免重复**：不要提出与已有查询 ({existing_queries}) 过于相似的查询。
3.  **探索性**：新查询应该能帮助我们探索未知领域、发现新的子主题、或者挖掘更具体的细节。
4.  **多样性**：尝试从不同角度提问，例如：技术细节、应用案例、未来趋势、相关挑战、不同实体之间的关系等。
5.  **简洁高效**：查询应简洁明了，适合搜索引擎。

请以 JSON 格式返回你的建议，格式如下：
{{
  "new_queries": [
    "查询1",
    "查询2",
    "..."
  ]
}}
"""



if __name__ == '__main__':
    print("--- Xinference 服务配置 ---")
    print(f"XINFERENCE_API_URL: {XINFERENCE_API_URL}")

    print("\n--- 大语言模型 (LLM) 配置 ---")
    print(f"DEFAULT_LLM_MODEL_NAME: {DEFAULT_LLM_MODEL_NAME}")
    print(f"DEFAULT_LLM_MAX_TOKENS: {DEFAULT_LLM_MAX_TOKENS}")
    print(f"DEFAULT_LLM_TEMPERATURE: {DEFAULT_LLM_TEMPERATURE}")
    print(f"DEFAULT_LLM_TOP_P: {DEFAULT_LLM_TOP_P}")
    print(f"DEFAULT_LLM_ENABLE_THINKING: {DEFAULT_LLM_ENABLE_THINKING}")
    print(f"DEFAULT_LLM_TOP_K: {DEFAULT_LLM_TOP_K}")
    print(f"DEFAULT_LLM_MIN_P: {DEFAULT_LLM_MIN_P}")

    print("\n--- 词嵌入模型配置 ---")
    print(f"DEFAULT_EMBEDDING_MODEL_NAME: {DEFAULT_EMBEDDING_MODEL_NAME}")

    print("\n--- Reranker 模型配置 ---")
    print(f"DEFAULT_RERANKER_MODEL_NAME: {DEFAULT_RERANKER_MODEL_NAME}")
    print(f"DEFAULT_RERANKER_BATCH_SIZE: {DEFAULT_RERANKER_BATCH_SIZE}")
    print(f"DEFAULT_RERANKER_MAX_TEXT_LENGTH: {DEFAULT_RERANKER_MAX_TEXT_LENGTH}")

    print("\n--- 文档处理配置 ---")
    print(f"DEFAULT_CHUNK_SIZE (通用): {DEFAULT_CHUNK_SIZE}")
    print(f"DEFAULT_CHUNK_OVERLAP (通用): {DEFAULT_CHUNK_OVERLAP}")
    print(f"DEFAULT_PARENT_CHUNK_SIZE: {DEFAULT_PARENT_CHUNK_SIZE}")
    print(f"DEFAULT_PARENT_CHUNK_OVERLAP: {DEFAULT_PARENT_CHUNK_OVERLAP}")
    print(f"DEFAULT_CHILD_CHUNK_SIZE: {DEFAULT_CHILD_CHUNK_SIZE}")
    print(f"DEFAULT_CHILD_CHUNK_OVERLAP: {DEFAULT_CHILD_CHUNK_OVERLAP}")
    print(f"SUPPORTED_DOC_EXTENSIONS: {SUPPORTED_DOC_EXTENSIONS}")

    print("\n--- 向量存储配置 ---")
    print(f"DEFAULT_VECTOR_STORE_TOP_K: {DEFAULT_VECTOR_STORE_TOP_K}")
    print(f"DEFAULT_VECTOR_STORE_PATH: {DEFAULT_VECTOR_STORE_PATH}")

    print("\n--- 混合搜索与检索配置 ---")
    # print(f"DEFAULT_HYBRID_SEARCH_ALPHA: {DEFAULT_HYBRID_SEARCH_ALPHA}")
    print(f"DEFAULT_KEYWORD_SEARCH_TOP_K: {DEFAULT_KEYWORD_SEARCH_TOP_K}")
    print(f"DEFAULT_RETRIEVAL_FINAL_TOP_N: {DEFAULT_RETRIEVAL_FINAL_TOP_N}")
    print(f"DEFAULT_RETRIEVAL_MIN_SCORE_THRESHOLD: {DEFAULT_RETRIEVAL_MIN_SCORE_THRESHOLD}")




    print("\n--- Agent Specific Retrieval Settings ---")
    print(f"DEFAULT_OUTLINE_GENERATION_RETRIEVAL_TOP_N: {DEFAULT_OUTLINE_GENERATION_RETRIEVAL_TOP_N}")
    print(f"DEFAULT_GLOBAL_RETRIEVAL_TOP_N_PER_CHAPTER: {DEFAULT_GLOBAL_RETRIEVAL_TOP_N_PER_CHAPTER}")

    print("\n--- Query Generation/Expansion Settings ---")
    print(f"DEFAULT_MAX_EXPANDED_QUERIES_TOPIC: {DEFAULT_MAX_EXPANDED_QUERIES_TOPIC}")
    print(f"DEFAULT_MAX_CHAPTER_QUERIES_GLOBAL_RETRIEVAL: {DEFAULT_MAX_CHAPTER_QUERIES_GLOBAL_RETRIEVAL}")
    print(f"DEFAULT_MAX_CHAPTER_QUERIES_CONTENT_RETRIEVAL: {DEFAULT_MAX_CHAPTER_QUERIES_CONTENT_RETRIEVAL}")

