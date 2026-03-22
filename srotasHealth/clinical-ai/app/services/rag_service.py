from app.services.embedding_service import get_embeddings
import faiss
import numpy as np

def chunk_text(text: str, chunk_size=500, overlap=50)-> list[str]:
    chunk = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk.append(text[start:end])
        start += chunk_size - overlap

    return chunk

trial_vector_store ={}
stored_chunks = []

def create_faiss_index(trial_id, embeddings):
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    trial_vector_store[trial_id] = {
        "index": index,
        "chunks": stored_chunks
    }

def search(trial_id, query_embedding, k=20):
    trial_data = trial_vector_store[trial_id]
    D, I = trial_data["index"].search(np.array([query_embedding]), k)
    return [stored_chunks[i] for i in I[0]]

def retrieve_relevant_context(trial_id, query):
    query_embeddings = get_embeddings([query])[0]
    relevant_chunks = search(trial_id, query_embeddings)
    return "\n".join(relevant_chunks)