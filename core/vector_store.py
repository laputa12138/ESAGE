import logging
import faiss
import numpy as np
import os
import contextlib
from typing import List, Tuple, Optional, Dict, Any
from core.embedding_service import EmbeddingService, EmbeddingServiceError
from config.settings import DEFAULT_VECTOR_STORE_TOP_K

# Configure logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') # Configured in main
logger = logging.getLogger(__name__)

class VectorStoreError(Exception):
    """Custom exception for VectorStore errors."""
    pass

@contextlib.contextmanager
def temporary_cwd(path):
    """
    Context manager to temporarily change the current working directory.
    This is useful for handling tools (like FAISS on Windows) that struggle with
    absolute paths containing non-ASCII characters.
    """
    old_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(old_cwd)

class VectorStore:
    """
    A class for creating, managing, and searching a FAISS-based vector store.
    It uses an EmbeddingService to convert text to vectors.
    This version is adapted for parent-child chunking.
    """

    def __init__(self, embedding_service: EmbeddingService, dimension: Optional[int] = None):
        """
        Initializes the VectorStore.

        Args:
            embedding_service (EmbeddingService): An instance of EmbeddingService.
            dimension (Optional[int]): The dimension of the embedding vectors.
                                       If None, it will be inferred.
        """
        self.embedding_service = embedding_service
        self.index: Optional[faiss.Index] = None

        # self.documents list will now store dictionaries for each child chunk,
        # including its text, its parent's text, and relevant IDs.
        # Format: {'child_id': str, 'child_text': str, 'parent_id': str, 'parent_text': str,
        #          'source_document_name': str} 
        # The FAISS index will map to the index of this list.
        self.document_store: List[Dict[str, Any]] = []

        self.dimension = dimension
        self._is_initialized = False
        logger.info("VectorStore initialized for parent-child chunking.")

    def _initialize_index(self, first_embedding_vector: np.ndarray):
        """Helper to initialize FAISS index once dimension is known."""
        if not self.dimension:
            self.dimension = first_embedding_vector.shape[-1] # Get dimension from the embedding vector
            logger.info(f"Inferred embedding dimension: {self.dimension}")

        if self.dimension is None or self.dimension <= 0:
            raise VectorStoreError("Embedding dimension must be a positive integer.")

        self.index = faiss.IndexFlatL2(self.dimension)
        # For production, consider IndexIDMap to map FAISS indices to our child_ids directly.
        # self.index = faiss.IndexIDMap(faiss.IndexFlatL2(self.dimension)) -> then use index.add_with_ids
        self._is_initialized = True
        logger.info(f"FAISS index initialized with dimension {self.dimension} using IndexFlatL2.")

    def add_documents(self, parent_child_data: List[Dict[str, Any]]):
        """
        Adds documents, structured as parent and child chunks, to the vector store.
        Embeddings are generated only for the child chunks.
        """
        if not parent_child_data:
            logger.warning("add_documents called with empty parent_child_data.")
            return

        logger.info(f"Adding {len(parent_child_data)} parent documents (with their children) to the vector store.")

        child_texts_for_embedding: List[str] = []
        child_metadata_for_store: List[Dict[str, Any]] = []

        for parent_info in parent_child_data:
            parent_id = parent_info.get('parent_id')
            parent_text = parent_info.get('parent_text')

            if not parent_id or not parent_text:
                logger.warning(f"Skipping parent_info due to missing 'parent_id' or 'parent_text'. Data: {str(parent_info)[:200]}")
                continue

            source_doc_name = parent_info.get('source_document_name')
            if not source_doc_name:
                logger.warning(f"Missing 'source_document_name' for parent_id: {parent_id}. Using default value 'Unknown Source Document'.")
                source_doc_name = 'Unknown Source Document' 

            for child_info in parent_info.get('children', []):
                child_id = child_info.get('child_id')
                child_text = child_info.get('child_text') 

                if not child_id:
                    logger.warning(f"Skipping child_info due to missing 'child_id' in parent {parent_id}. Data: {str(child_info)[:200]}")
                    continue

                if not child_text or not child_text.strip():
                    logger.debug(f"Skipping empty or missing child_text for child_id {child_id} from parent {parent_id}.")
                    continue

                child_texts_for_embedding.append(child_text)
                child_metadata_for_store.append({
                    'child_id': child_id,
                    'child_text': child_text,
                    'parent_id': parent_id,
                    'parent_text': parent_text, 
                    'source_document_name': source_doc_name 
                })

        if not child_texts_for_embedding:
            logger.warning("No valid child texts found in parent_child_data to embed.")
            return

        logger.info(f"Extracted {len(child_texts_for_embedding)} child chunks for embedding.")

        try:
            # Generate embeddings for all child texts in batch
            child_embeddings_list = self.embedding_service.create_embeddings(child_texts_for_embedding)

            if not child_embeddings_list or len(child_embeddings_list) != len(child_texts_for_embedding):
                logger.error("Mismatch between number of child texts and generated embeddings, or empty embeddings list.")
                raise VectorStoreError("Embedding service did not return expected embeddings for all child chunks.")

            child_embeddings_np = np.array(child_embeddings_list, dtype='float32')
            if child_embeddings_np.ndim == 1 and child_embeddings_np.size > 0: # Single embedding
                 child_embeddings_np = np.expand_dims(child_embeddings_np, axis=0)

            if child_embeddings_np.size == 0:
                logger.error("Embeddings array is empty after processing child texts.")
                raise VectorStoreError("No valid embeddings generated for child chunks.")

            if not self._is_initialized:
                self._initialize_index(child_embeddings_np[0]) 

            if self.index is None:
                raise VectorStoreError("FAISS index is not initialized (should have been by _initialize_index).")

            # Add embeddings to FAISS index
            self.index.add(child_embeddings_np)

            # Add corresponding metadata to our document_store
            self.document_store.extend(child_metadata_for_store)

            logger.info(f"Successfully added {len(child_texts_for_embedding)} child_chunk embeddings to FAISS. "
                        f"Total child chunks in store: {len(self.document_store)} (FAISS ntotal: {self.index.ntotal}).")

        except EmbeddingServiceError as e:
            logger.error(f"Failed to generate embeddings for child documents: {e}")
            raise VectorStoreError(f"Child chunk embedding generation failed: {e}")
        except Exception as e:
            logger.error(f"Failed to add child documents to FAISS index: {e}")
            raise VectorStoreError(f"FAISS index add operation for child chunks failed: {e}")

    def search(self, query_text: str, k: int = None) -> List[Dict[str, Any]]:
        """
        Searches the vector store for child chunks similar to the query text.
        """
        if not self._is_initialized or self.index is None:
            raise VectorStoreError("Search attempted on uninitialized or empty vector store.")

        if not self.document_store: 
            logger.warning("Search attempted on an empty document_store (no child/parent metadata).")
            return []

        k_to_use = k if k is not None else DEFAULT_VECTOR_STORE_TOP_K
        k_to_use = min(k_to_use, self.index.ntotal)

        if k_to_use <= 0 :
            return []

        logger.info(f"Searching for top {k_to_use} child chunks similar to query: '{query_text[:100]}...'")
        try:
            query_embedding_list = self.embedding_service.create_embeddings([query_text])
            if not query_embedding_list or not query_embedding_list[0]:
                raise VectorStoreError("Query embedding generation returned empty result.")

            query_embedding_np = np.array(query_embedding_list, dtype='float32')
            if query_embedding_np.ndim == 1: 
                query_embedding_np = np.expand_dims(query_embedding_np, axis=0)

            distances, indices = self.index.search(query_embedding_np, k_to_use)

            results = []
            if indices.size > 0:
                for i in range(indices.shape[1]):
                    doc_index_in_store = indices[0, i]
                    if 0 <= doc_index_in_store < len(self.document_store):
                        retrieved_item_meta = self.document_store[doc_index_in_store]
                        result_entry = {
                            'child_id': retrieved_item_meta['child_id'],
                            'child_text': retrieved_item_meta['child_text'],
                            'parent_id': retrieved_item_meta['parent_id'],
                            'parent_text': retrieved_item_meta['parent_text'],
                            'source_document_name': retrieved_item_meta.get('source_document_name', 'Unknown Source Document'),
                            'score': float(distances[0, i]) # L2 distance
                        }
                        results.append(result_entry)
                    else:
                        logger.warning(f"Search returned invalid document index: {doc_index_in_store} Skipping.")
            return results

        except EmbeddingServiceError as e:
            logger.error(f"Failed to generate embedding for query: {e}")
            raise VectorStoreError(f"Query embedding generation failed: {e}")
        except Exception as e:
            logger.error(f"FAISS search operation failed: {e}")
            raise VectorStoreError(f"FAISS search operation failed: {e}")

    def save_store(self, index_path: str, metadata_path: str):
        """Saves the FAISS index and the document metadata store."""
        if not self._is_initialized or self.index is None:
            raise VectorStoreError("Cannot save uninitialized index.")
        logger.info(f"Saving FAISS index to {index_path} and metadata to {metadata_path}")
        
        # Determine directory and filename for FAISS index 
        # to handle potential Windows non-ASCII path issues in FAISS C++ writer
        index_dir = os.path.dirname(os.path.abspath(index_path))
        index_file = os.path.basename(index_path)
        
        if not os.path.exists(index_dir):
            try:
                os.makedirs(index_dir, exist_ok=True)
            except Exception as e:
                 logger.error(f"Failed to create directory {index_dir}: {e}")
                 raise VectorStoreError(f"Failed to create directory: {e}")

        try:
            # Context manager to switch CWD to index_dir so we can write to just the filename (ASCII safe-ish)
            # This bypasses full path encoding issues in C++ backend
            with temporary_cwd(index_dir):
                 faiss.write_index(self.index, index_file)
        except Exception as e:
            # Fallback to absolute path try if CWD trick fails for some reason
            logger.warning(f"Save with CWD trick failed: {e}. Retrying with absolute path.")
            try:
                faiss.write_index(self.index, index_path)
            except Exception as inner_e:
                logger.error(f"Failed to save FAISS index: {inner_e}")
                raise VectorStoreError(f"Failed to save index: {inner_e}")

        try:
            import json
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "document_store": self.document_store,
                    "dimension": self.dimension
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata store to {metadata_path}: {e}")
            raise VectorStoreError(f"Failed to save metadata: {e}")

    def load_store(self, index_path: str, metadata_path: str):
        """Loads the FAISS index and the document metadata store."""
        logger.info(f"Loading FAISS index from {index_path} and metadata from {metadata_path}")
        
        index_dir = os.path.dirname(os.path.abspath(index_path))
        index_file = os.path.basename(index_path)
        
        try:
            # Use same CWD trick for loading
            with temporary_cwd(index_dir):
                if os.path.exists(index_file):
                    self.index = faiss.read_index(index_file)
                else:
                    # If CWD didn't work to find file (maybe unexpected path), try full path
                    # This branch is just a fallback logic check
                    raise FileNotFoundError("Index file not found in CWD")
        except Exception as e:
             logger.warning(f"Load with CWD trick failed or file not local: {e}. Retrying with absolute path.")
             try:
                 self.index = faiss.read_index(index_path)
             except Exception as inner_e:
                 logger.error(f"Failed to load FAISS index: {inner_e}")
                 raise VectorStoreError(f"Failed to load index: {inner_e}")

        try:
            import json
            with open(metadata_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.document_store = data.get("document_store", [])
                loaded_dimension = data.get("dimension")
            
            # --- Metadata Compatibility Check ---
            # (Keeping original logic for compatibility check)
            migrated_count = 0
            defaulted_count = 0
            if self.document_store:
                for item_meta in self.document_store:
                    if 'source_document_name' not in item_meta or not item_meta['source_document_name']:
                        old_key_name = 'doc_name'
                        if old_key_name in item_meta and item_meta[old_key_name]:
                            item_meta['source_document_name'] = item_meta[old_key_name]
                            del item_meta[old_key_name]
                            migrated_count += 1
                        else:
                            item_meta['source_document_name'] = 'Unknown Source Document (Loaded)'
                            defaulted_count += 1
            if migrated_count > 0:
                logger.info(f"Successfully migrated 'source_document_name' for {migrated_count} items during load.")
            # ---------------------------

            if loaded_dimension is not None and self.index.d != loaded_dimension:
                logger.warning(f"Dimension mismatch: FAISS index ({self.index.d}) vs metadata ({loaded_dimension}).")
            self.dimension = self.index.d
            self._is_initialized = True
            
        except FileNotFoundError:
            logger.error(f"Could not find index file or metadata file.")
            raise VectorStoreError(f"Index or metadata file not found during load.")
        except Exception as e:
            logger.error(f"Failed to load FAISS index or metadata: {e}")
            raise VectorStoreError(f"Failed to load store: {e}")

    @property
    def count_child_chunks(self) -> int:
        return len(self.document_store) if self.index else 0

    def get_all_child_texts(self) -> List[str]:
        return [item['child_text'] for item in self.document_store]
