import logging
import json
import os
from typing import List, Dict, Optional, Any
from rank_bm25 import BM25Okapi

from config import settings
from core.llm_service import LLMService
from core.embedding_service import EmbeddingService
from core.reranker_service import RerankerService
from core.document_processor import DocumentProcessor
from core.vector_store import VectorStore
from core.retrieval_service import RetrievalService
from core.workflow_state import WorkflowState, TASK_TYPE_PLAN_STRUCTURE
from core.orchestrator import Orchestrator

from agents.structure_planner_agent import StructurePlannerAgent
from agents.node_extractor_agent import NodeExtractorAgent
from agents.validator_agent import ValidatorAgent
from core.global_context_builder import GlobalContextBuilder
from core.graph_refiner import GraphRefiner

logger = logging.getLogger(__name__)

class ReportGenerationPipelineError(Exception):
    pass

class ReportGenerationPipeline:
    """
    Refactored Pipeline for Industry Chain Extraction.
    Inherits the name 'ReportGenerationPipeline' for compatibility with main.py,
    but performs industry extraction.
    """
    def __init__(self,
                 llm_service: LLMService,
                 embedding_service: EmbeddingService,
                 reranker_service: Optional[RerankerService] = None,
                 vector_store_path: str = settings.DEFAULT_VECTOR_STORE_PATH,
                 index_name: Optional[str] = None,
                 force_reindex: bool = False,
                 max_workflow_iterations: int = settings.DEFAULT_MAX_WORKFLOW_ITERATIONS,
                 # 索引参数
                 cli_overridden_parent_chunk_size: int = settings.DEFAULT_PARENT_CHUNK_SIZE,
                 cli_overridden_parent_chunk_overlap: int = settings.DEFAULT_PARENT_CHUNK_OVERLAP,
                 cli_overridden_child_chunk_size: int = settings.DEFAULT_CHILD_CHUNK_SIZE,
                 cli_overridden_child_chunk_overlap: int = settings.DEFAULT_CHILD_CHUNK_OVERLAP,
                 cli_overridden_vector_top_k: int = settings.DEFAULT_VECTOR_STORE_TOP_K,
                 # 忽略的参数保持签名兼容性，如果 main.py 适配了可以移除
                 **kwargs
                ):

        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.reranker_service = reranker_service
        
        self.vector_store_path = vector_store_path
        self.index_name = index_name
        self.force_reindex = force_reindex
        self.max_workflow_iterations = max_workflow_iterations

        self.parent_chunk_size = cli_overridden_parent_chunk_size
        self.parent_chunk_overlap = cli_overridden_parent_chunk_overlap
        self.child_chunk_size = cli_overridden_child_chunk_size
        self.child_chunk_overlap = cli_overridden_child_chunk_overlap

        # Initialize DocumentProcessor
        self.document_processor = DocumentProcessor(
            parent_chunk_size=self.parent_chunk_size,
            parent_chunk_overlap=self.parent_chunk_overlap,
            child_chunk_size=self.child_chunk_size,
            child_chunk_overlap=self.child_chunk_overlap
        )
        self.vector_store = VectorStore(embedding_service=self.embedding_service)
        self.bm25_index: Optional[BM25Okapi] = None
        self.all_child_chunks_for_bm25_mapping: List[Dict[str, Any]] = []

        self.workflow_state: Optional[WorkflowState] = None
        self.retrieval_service: Optional[RetrievalService] = None
        self.orchestrator: Optional[Orchestrator] = None
        
        # Agents
        self.structure_planner: Optional[StructurePlannerAgent] = None
        self.node_extractor: Optional[NodeExtractorAgent] = None
        self.validator_agent: Optional[ValidatorAgent] = None

        # New Components
        self.global_context_builder: Optional[GlobalContextBuilder] = None
        self.graph_refiner: Optional[GraphRefiner] = None

        logger.info("IndustryExtractionPipeline (named ReportGenerationPipeline) initialized.")

    def _initialize_components(self):
        if not self.workflow_state:
            raise ReportGenerationPipelineError("WorkflowState not initialized.")

        # Initialize Retrieval Service
        if not self.retrieval_service:
            self.retrieval_service = RetrievalService(
                vector_store=self.vector_store,
                bm25_index=self.bm25_index,
                all_child_chunks_for_bm25_mapping=self.all_child_chunks_for_bm25_mapping,
                reranker_service=self.reranker_service
            )
            self.workflow_state.log_event("RetrievalService initialized.")

        # Initialize Agents
        if not self.structure_planner:
            self.structure_planner = StructurePlannerAgent(
                llm_service=self.llm_service,
                retrieval_service=self.retrieval_service
            )
        
        if not self.node_extractor:
            self.node_extractor = NodeExtractorAgent(
                llm_service=self.llm_service,
                retrieval_service=self.retrieval_service
            )
            
            self.validator_agent = ValidatorAgent(
                llm_service=self.llm_service
            )

        # Initialize New Components
        if not self.global_context_builder:
            self.global_context_builder = GlobalContextBuilder(
                llm_service=self.llm_service,
                retrieval_service=self.retrieval_service
            )
        
        if not self.graph_refiner:
            self.graph_refiner = GraphRefiner(
                llm_service=self.llm_service
            )

        # Initialize Orchestrator
        if not self.orchestrator:
            self.orchestrator = Orchestrator(
                workflow_state=self.workflow_state,
                structure_planner=self.structure_planner,
                node_extractor=self.node_extractor,
                validator_agent=self.validator_agent,
                max_workflow_iterations=self.max_workflow_iterations
            )
            self.workflow_state.log_event("Orchestrator initialized.")

    def _process_and_load_data(self, data_path: str):
        # 复用现有的索引逻辑（为简洁起见，此处逻辑假设与之前相同）
        # 为了重构速度，我将复制核心逻辑但稍微精简日志。
        
        logger.info(f"正在处理数据: {data_path}")
        self.workflow_state.log_event(f"Processing data from: {data_path}")
        
        effective_index_name = self.index_name or (os.path.basename(os.path.normpath(data_path)) if data_path else "default_idx")
        vs_dir = os.path.abspath(self.vector_store_path)
        os.makedirs(vs_dir, exist_ok=True)
        
        faiss_path = os.path.join(vs_dir, f"{effective_index_name}.faiss")
        meta_path = os.path.join(vs_dir, f"{effective_index_name}.meta.json")
        
        loaded = False
        if not self.force_reindex and os.path.exists(faiss_path) and os.path.exists(meta_path):
            try:
                self.vector_store.load_store(faiss_path, meta_path)
                loaded = True
                self.workflow_state.log_event("Loaded existing index.")
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")

        if not loaded:
            # Process files
            chunks = []
            if data_path and os.path.isdir(data_path):
                for f in os.listdir(data_path):
                    fp = os.path.join(data_path, f)
                    if os.path.isfile(fp):
                        try:
                            text = self.document_processor.extract_text_from_file(fp)
                            if text.strip():
                                chunks.extend(self.document_processor.split_text_into_parent_child_chunks(text, f))
                        except Exception as e:
                            logger.error(f"Error processing {f}: {e}")
            
            if chunks:
                self.vector_store = VectorStore(self.embedding_service) # Reset
                self.vector_store.add_documents(chunks)
                self.vector_store.save_store(faiss_path, meta_path)
                self.workflow_state.log_event(f"Built new index with {len(chunks)} chunks.")
            else:
                 self.workflow_state.log_event("No data processed.", level="WARNING")

        # Build BM25
        self.all_child_chunks_for_bm25_mapping = [{"child_id": i['child_id'], "child_text": i['child_text']} for i in self.vector_store.document_store]
        if self.all_child_chunks_for_bm25_mapping:
            corpus = [i['child_text'].lower().split() for i in self.all_child_chunks_for_bm25_mapping]
            self.bm25_index = BM25Okapi(corpus)

    def run(self, user_topic: str, data_path: str, report_title: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        运行抽取流水线。返回产业链图谱的 JSON 字典。
        """
        self.workflow_state = WorkflowState(user_topic, report_title)
        self.workflow_state.log_event("流水线启动 (抽取模式)。")

        try:
            self._process_and_load_data(data_path)
            self._initialize_components()

            # 添加初始任务
            initial_payload = {'user_topic': user_topic}
            initial_payload.update(kwargs) # 传递 CLI 参数，如 max_recursion_depth
            
            # --- 1. 全局上下文构建 ---
            if self.global_context_builder:
                global_context = self.global_context_builder.build_context(user_topic)
                self.workflow_state.set_global_context(global_context)

            self.workflow_state.add_task(TASK_TYPE_PLAN_STRUCTURE, payload=initial_payload)
            
            # --- 2. 运行编排器 ---
            self.orchestrator.coordinate_workflow()
            
            # 剪枝：移除空节点或无证据的节点
            self.workflow_state.prune_industry_graph()
            
            # --- 3. 图谱优化 (中央控制) ---
            if self.graph_refiner:
                 self.workflow_state.industry_graph = self.graph_refiner.refine_graph(self.workflow_state.industry_graph)
                 self.workflow_state.log_event("图谱优化完成。")

            return self.workflow_state.industry_graph

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.workflow_state.log_event(f"Pipeline failed: {e}", level="ERROR")
            if self.workflow_state:
                return self.workflow_state.industry_graph # Return partial result if any
            return {"error": str(e)}
