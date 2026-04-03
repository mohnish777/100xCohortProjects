from typing import Any


MODEL_NAME = "all-MiniLM-L6-v2"
_model = None


def get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_embeddings(texts):
    normalized_texts = [str(text) for text in texts]
    return get_model().encode(normalized_texts)
