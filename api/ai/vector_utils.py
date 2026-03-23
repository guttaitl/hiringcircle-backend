import math
import json

def cosine_similarity(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x*x for x in a))
    norm_b = math.sqrt(sum(x*x for x in b))
    return dot / (norm_a * norm_b)


def load_embedding(embedding_json):
    if not embedding_json:
        return None

    if isinstance(embedding_json, list):
        return embedding_json

    return json.loads(embedding_json)