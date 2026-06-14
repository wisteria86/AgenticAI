import os
import shutil
import chromadb
from chromadb.config import Settings

class MemoryManager:
    """
    Manages long-term memory for the AI agent using ChromaDB (local vector database).
    """
    def __init__(self, db_path="./chroma_db"):
        self.db_path = db_path
        os.makedirs(self.db_path, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        # Create or get the collection for the agent's memories.
        # If the database is corrupted, delete and recreate it.
        try:
            self.collection = self.client.get_or_create_collection(
                name="agent_memory",
                metadata={"hnsw:space": "cosine"}
            )
            # Verify the collection is actually usable
            self.collection.count()
        except Exception as e:
            print(f"[Memory] WARNING: ChromaDB appears corrupted ({e}). Resetting database...")
            try:
                del self.client
                shutil.rmtree(self.db_path, ignore_errors=True)
                os.makedirs(self.db_path, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.db_path)
                self.collection = self.client.get_or_create_collection(
                    name="agent_memory",
                    metadata={"hnsw:space": "cosine"}
                )
                print("[Memory] Database reset successfully.")
            except Exception as e2:
                print(f"[Memory] FATAL: Could not reset database: {e2}")
                raise

    def store_memory(self, text: str, metadata: dict = None, memory_id: str = None):
        """
        Store a string in the vector database.
        
        Args:
            text: The text to remember.
            metadata: Optional dictionary of metadata.
            memory_id: Optional unique ID. If not provided, the text's hash can be used.
        """
        try:
            if memory_id is None:
                memory_id = str(hash(text))
                
            meta = metadata if metadata else {"source": "agent_memory"}
            self.collection.add(
                documents=[text],
                metadatas=[meta],
                ids=[memory_id]
            )
        except Exception as e:
            print(f"[Memory] Error storing memory: {e}")

    def retrieve_memory(self, query: str, n_results: int = 3) -> list[str]:
        """
        Retrieve relevant past memories based on a query.
        
        Args:
            query: The search query.
            n_results: Maximum number of results to return.
            
        Returns:
            A list of string documents.
        """
        try:
            # If the collection is empty, querying will throw an error, so handle it safely.
            if self.collection.count() == 0:
                return []
                
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents']:
                return []
                
            return results['documents'][0]
        except Exception as e:
            print(f"[Memory] Error retrieving memory: {e}")
            return []
