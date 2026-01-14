import argparse
import logging
import os
import sys
import json
from datetime import datetime
from typing import List, Optional as optional

# Ensure the project root is in PYTHONPATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import settings
from core.llm_service import LLMService
from core.embedding_service import EmbeddingService
from core.reranker_service import RerankerService
from pipelines.report_generation_pipeline import ReportGenerationPipeline, ReportGenerationPipelineError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_logging(log_level_str: str = 'INFO', debug_mode: bool = False, log_file_path: optional[str] = None):
    """Configures logging based on command-line arguments."""
    if debug_mode:
        effective_log_level = logging.DEBUG
    else:
        effective_log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.setLevel(effective_log_level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(effective_log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError:
                log_file_path = None

        if log_file_path:
            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG) # Always log debug to file
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

def main():
    """
    Main entry point for the Industry Chain Extraction System.
    """
    parser = argparse.ArgumentParser(
        description="Industry Chain Structured Extraction System (formerly Report Gen).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument("--topic", type=str, required=True, help="Industry topic.")
    parser.add_argument("--data_path", type=str, default="./data/v2", help="Source documents directory.")
    parser.add_argument("--output_path", type=str, default=f"output/graph_{args.topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", help="Path to save JSON output.")
        
    # Xinference
    parser.add_argument("--xinference_url", type=str, default=settings.XINFERENCE_API_URL)
    parser.add_argument("--llm_model", type=str, default=settings.DEFAULT_LLM_MODEL_NAME)
    parser.add_argument("--embedding_model", type=str, default=settings.DEFAULT_EMBEDDING_MODEL_NAME)
    parser.add_argument("--reranker_model", type=str, default=settings.DEFAULT_RERANKER_MODEL_NAME)

    # Retrieval
    # Updated default to my_vector_indexes as requested
    parser.add_argument("--vector_store_path", type=str, default="./my_vector_indexes/")
    parser.add_argument("--vector_top_k", type=int, default=settings.DEFAULT_VECTOR_STORE_TOP_K)
    parser.add_argument("--force_reindex", action='store_true', help="Force re-indexing documents.")
    

    # Logging
    parser.add_argument("--log_level", type=str, default=settings.LOG_LEVEL)
    parser.add_argument("--debug", action='store_true')
    parser.add_argument("--log_path", type=str, default="./logs/")

    args = parser.parse_args()

    log_file_name = f"extraction_{args.topic}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    full_log_file_path = os.path.join(args.log_path, log_file_name) if args.log_path else None
    setup_logging(log_level_str=args.log_level, debug_mode=args.debug, log_file_path=full_log_file_path)

    global logger
    logger = logging.getLogger(__name__)
    logger.info(f"正在启动产业链抽取系统，主题: {args.topic}") # Localized log
    logger.info(f"数据路径: {args.data_path}")
    logger.info(f"向量索引路径: {args.vector_store_path}")

    # Initialize Services
    try:
        logger.info("正在初始化 AI 服务...")
        llm_service = LLMService(api_url=args.xinference_url, model_name=args.llm_model)
        embedding_service = EmbeddingService(api_url=args.xinference_url, model_name=args.embedding_model)
        reranker_service = None
        if args.reranker_model and args.reranker_model.lower() != 'none':
            try:
                reranker_service = RerankerService(api_url=args.xinference_url, model_name=args.reranker_model)
                logger.info("Reranker 服务初始化成功。")
            except Exception as e:
                logger.warning(f"Reranker 初始化失败: {e}。将继续运行但不使用 Reranker。")
    except Exception as e:
        logger.error(f"核心 AI 服务初始化失败: {e}")
        sys.exit(1)

    # Run Pipeline
    try:
        logger.info("正在初始化抽取流水线...")
        pipeline = ReportGenerationPipeline(
            llm_service=llm_service,
            embedding_service=embedding_service,
            reranker_service=reranker_service,
            vector_store_path=args.vector_store_path,
            force_reindex=args.force_reindex,
            cli_overridden_vector_top_k=args.vector_top_k
        )

        logger.info("开始执行抽取任务...")
        output_graph = pipeline.run(user_topic=args.topic, data_path=args.data_path)

        # Save JSON
        output_dir = os.path.dirname(args.output_path)
        if output_dir: os.makedirs(output_dir, exist_ok=True)
        
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(output_graph, f, ensure_ascii=False, indent=2)
        
        logger.info(f"抽取完成！结果已保存至: {args.output_path}")
        print(f"抽取完成！结果文件: {args.output_path}")

    except Exception as e:
        logger.error(f"执行过程中发生错误: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
