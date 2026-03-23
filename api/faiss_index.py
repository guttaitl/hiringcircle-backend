import faiss
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ResumeVectorIndex:
    def __init__(self):
        self.index = None
        self.resume_ids = []

    def build(self, embeddings: list, resume_ids: list):
        """
        embeddings: list of list[float]
        resume_ids: list of resume database IDs (same order)
        """

        logger.info("Building FAISS index...")

        vectors = np.array(embeddings).astype("float32")

        # normalize for cosine similarity
        faiss.normalize_L2(vectors)

        dim = vectors.shape[1]

        # Exact cosine similarity index (fast enough for 100K+)
        self.index = faiss.IndexFlatIP(dim)

        self.index.add(vectors)
        self.resume_ids = resume_ids

        logger.info(f"FAISS index built with {self.index.ntotal} vectors")

    def search(self, query_embedding, top_k=50):
        """
        Returns top matching resume IDs
        """

        query = np.array([query_embedding]).astype("float32")
        faiss.normalize_L2(query)

        scores, indices = self.index.search(query, top_k)

        matched_ids = [
            self.resume_ids[i]
            for i in indices[0]
            if i < len(self.resume_ids)
        ]

        return matched_ids