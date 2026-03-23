from api.utils.openai_client import create_embedding


def get_text_embedding(text: str):
    """
    Generate embedding vector for given text.
    """

    if not text:
        return None

    try:
        return create_embedding(text)
    except Exception as e:
        raise RuntimeError(f"Embedding generation failed: {e}")