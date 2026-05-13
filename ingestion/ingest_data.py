"""
Data Ingestion Pipeline

Loads documentation files and embeds them into ChromaDB for retrieval.
"""

import os
import logging
from pathlib import Path
from typing import List

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """Ingests documentation into ChromaDB for RAG"""

    def __init__(self, docs_path: str, vector_db_path: str):
        self.docs_path = Path(docs_path)
        self.vector_db_path = Path(vector_db_path)
        self.vector_db_path.mkdir(parents=True, exist_ok=True)

        # Initialize Ollama embeddings
        logger.info("Initializing Ollama embeddings...")
        from langchain_ollama import OllamaEmbeddings
        from config import OLLAMA_BASE_URL, EMBEDDINGS_MODEL
        self.embeddings = OllamaEmbeddings(
            model=EMBEDDINGS_MODEL,
            base_url=OLLAMA_BASE_URL
        )

        # Initialize ChromaDB with new API
        from config import CHROMA_HOST, CHROMA_PORT
        if CHROMA_HOST:
            self.chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        else:
            self.chroma_client = chromadb.PersistentClient(path=str(self.vector_db_path))

    def load_documents(self) -> List:
        """Load all text documents from docs folder"""
        documents = []

        logger.info(f"Loading documents from {self.docs_path}")
        for file_path in self.docs_path.glob("*.txt"):
            try:
                logger.info(f"Loading {file_path.name}")
                loader = TextLoader(str(file_path), encoding="utf-8")
                docs = loader.load()
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"Loaded {len(documents)} documents")
        return documents

    def split_documents(self, documents: List) -> List:
        """Split documents into chunks"""
        logger.info("Splitting documents into chunks...")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        chunks = splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    def ingest_to_chromadb(self, chunks: List):
        """Ingest chunks into ChromaDB"""
        logger.info("Ingesting chunks into ChromaDB...")

        # Get or create collection
        collection = self.chroma_client.get_or_create_collection(
            name="devops_docs",
            metadata={"hnsw:space": "cosine"},
        )

        # Clear existing data
        try:
            collection.delete(where={})
        except Exception:
            pass

        # Add documents with embeddings
        for i, chunk in enumerate(chunks):
            if i % 10 == 0:
                logger.info(f"Processing chunk {i}/{len(chunks)}")

            # Generate embedding
            embedding = self.embeddings.embed_query(chunk.page_content)

            # Determine document type and category from source file
            source = chunk.metadata.get("source", "unknown")

            # Enhanced metadata extraction (minimum 3 tags per Lab 2 requirements)
            if "docker" in source.lower():
                doc_type = "docker"
                error_category = "containerization"
                priority_level = "high"
            elif "linux" in source.lower():
                doc_type = "linux"
                error_category = "system"
                priority_level = "high"
            elif "python" in source.lower():
                doc_type = "python"
                error_category = "application"
                priority_level = "medium"
            else:
                doc_type = "general"
                error_category = "miscellaneous"
                priority_level = "medium"

            # Add to collection with enriched metadata
            collection.add(
                ids=[f"doc_{i}"],
                embeddings=[embedding],
                documents=[chunk.page_content],
                metadatas=[{
                    "source": source,
                    "chunk_index": str(i),
                    "doc_type": doc_type,                    # Tag 1: Document type
                    "error_category": error_category,        # Tag 2: Error category
                    "priority_level": priority_level,        # Tag 3: Priority level
                    "last_updated": "2026-03-08",           # Tag 4: Update date
                }],
            )

        logger.info("Ingestion complete!")

    def run(self):
        """Execute full ingestion pipeline"""
        documents = self.load_documents()
        chunks = self.split_documents(documents)
        self.ingest_to_chromadb(chunks)
        logger.info(f"Successfully ingested {len(chunks)} chunks into ChromaDB")


def main():
    """Main ingestion entry point"""
    current_dir = Path(__file__).parent.parent
    docs_path = current_dir / "data" / "docs"
    vector_db_path = current_dir / "vector_db"

    pipeline = DataIngestionPipeline(
        docs_path=str(docs_path),
        vector_db_path=str(vector_db_path),
    )
    pipeline.run()


if __name__ == "__main__":
    main()
