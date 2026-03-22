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

index = None
stored_chunks = []

def create_faiss_index(embeddings):
    global index
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))

def search(query_embedding, k=3):
    D, I = index.search(np.array([query_embedding]), k)
    return [stored_chunks[i] for i in I[0]]