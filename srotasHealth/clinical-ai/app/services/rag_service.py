from typing import List

from app.config import supabase
from app.services.embedding_service import get_embeddings
import faiss
import numpy as np

def chunk_text(text: str, chunk_size=500, overlap=50)-> list[str]:
    """Keep this function - it's still needed"""
    chunk = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk.append(text[start:end])
        start += chunk_size - overlap

    return chunk

trial_vector_store ={}

def create_faiss_index(trial_id, chunks: List[str]):
    """
    Deprecated: Embeddings are now stored in Supabase.
    This function is kept for backward compatibility only.
    """
    print(f"⚠️ create_faiss_index() is deprecated. Embeddings are stored in Supabase.")
    pass

    embeddings = get_embeddings(chunks)
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    trial_vector_store[trial_id] = {
        "index": index,
        "chunks": chunks
    }

def search(trial_id, query_embedding, k=50):
    trial_data = trial_vector_store[trial_id]
    index = trial_data["index"]
    chunks = trial_data["chunks"]
    D, I = index.search(np.array([query_embedding]), k)
    return [chunks[i] for i in I[0]]

def retrieve_relevant_context(trial_id: str, query: str, k: int = 5):
    """
    Retrieve relevant chunks from Supabase using vector similarity search.
    
    Args:
        trial_id: UUID of the trial
        query: Search query (e.g., "inclusion criteria")
        k: Number of top chunks to retrieve
        
    Returns:
        Concatenated text of relevant chunks
    """
    query_embedding = get_embeddings([query])[0].tolist()
    # Call Supabase RPC function for vector search
    try:
        result = supabase.rpc(
            'match_trial_chunks',
            {
                'query_embedding': query_embedding,
                'match_trial_id': trial_id,
                'match_count': k
            }
        ).execute()
        
        if not result.data:
            print(f"⚠️ No chunks found for trial {trial_id}")
            return ""
        
        # Extract and join chunk texts
        chunks = [row['chunk_text'] for row in result.data]
        return "\n".join(chunks)
    
    except Exception as e:
        print(f"❌ Error retrieving context from Supabase: {e}")
        return ""
    