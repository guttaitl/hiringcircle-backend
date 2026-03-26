import os
import faiss
import numpy as np
import logging

logger = logging.getLogger(__name__)

INDEX_FILE = "faiss_resume.index"
META_FILE = "faiss_resume_ids.npy"


class ResumeVectorIndex:
    def __init__(self):
        self.index = None
        self.resume_ids = []
        self.dimension = None

    # ==========================================================
    # BUILD INDEX (IVF FOR SCALING)
    # ==========================================================
    def build(self, embeddings: list, resume_ids: list):
        logger.info("Building FAISS index...")

        if not embeddings or not resume_ids:
            logger.warning("No embeddings provided. Skipping FAISS build.")
            self.index = None
            self.resume_ids = []
            return

        try:
            vectors = np.array(embeddings, dtype="float32")

            if vectors.ndim != 2:
                raise ValueError("Embeddings must be 2D array")

            faiss.normalize_L2(vectors)

            dim = vectors.shape[1]
            self.dimension = dim

            num_vectors = len(vectors)

            if num_vectors < 100:
                nlist = max(1, num_vectors // 2)
            else:
                nlist = 100

            quantizer = faiss.IndexFlatIP(dim)
            index = faiss.IndexIVFFlat(quantizer, dim, nlist)

            logger.info("Training FAISS IVF index...")
            index.train(vectors)

            index.add(vectors)
            index.nprobe = 10  # search accuracy vs speed tradeoff

            self.index = index
            self.resume_ids = list(resume_ids)

            logger.info(f"FAISS index built with {self.index.ntotal} vectors")

            self.save()

        except Exception:
            logger.exception("FAISS build failed")
            self.index = None
            self.resume_ids = []

    # ==========================================================
    # ADD EMBEDDINGS (INCREMENTAL UPDATE)
    # ==========================================================
    def add_embeddings(self, new_embeddings, new_ids):
        if not new_embeddings:
            return

        try:
            vectors = np.array(new_embeddings, dtype="float32")
            faiss.normalize_L2(vectors)

            if self.index is None:
                logger.info("Index empty → building fresh index")
                self.build(new_embeddings, new_ids)
                return

            self.index.add(vectors)
            self.resume_ids.extend(new_ids)

            logger.info(f"Added {len(new_ids)} embeddings to FAISS")

            self.save()

        except Exception:
            logger.exception("Failed to add embeddings")

    # ==========================================================
    # SEARCH
    # ==========================================================
    def search(self, query_embedding, top_k=50):
        if self.index is None:
            logger.warning("FAISS index is empty")
            return []

        if not self.resume_ids:
            return []

        try:
            query = np.array([query_embedding], dtype="float32")

            if query.ndim != 2:
                raise ValueError("Query must be 2D")

            if self.dimension and query.shape[1] != self.dimension:
                raise ValueError(
                    f"Dimension mismatch: expected {self.dimension}, got {query.shape[1]}"
                )

            faiss.normalize_L2(query)

            top_k = min(top_k, len(self.resume_ids))

            scores, indices = self.index.search(query, top_k)

            matched_ids = []
            for i in indices[0]:
                if 0 <= i < len(self.resume_ids):
                    matched_ids.append(self.resume_ids[i])

            return matched_ids

        except Exception:
            logger.exception("FAISS search failed")
            return []

    # ==========================================================
    # SAVE INDEX
    # ==========================================================
    def save(self):
        try:
            if self.index is None:
                return

            faiss.write_index(self.index, INDEX_FILE)
            np.save(META_FILE, np.array(self.resume_ids))

            logger.info("FAISS index saved")

        except Exception:
            logger.exception("Failed to save FAISS index")

    # ==========================================================
    # LOAD INDEX
    # ==========================================================
    def load(self):
        try:
            if not os.path.exists(INDEX_FILE):
                logger.warning("No FAISS index file found")
                return

            self.index = faiss.read_index(INDEX_FILE)
            self.resume_ids = np.load(META_FILE).tolist()
            self.dimension = self.index.d

            logger.info(f"FAISS index loaded ({len(self.resume_ids)} vectors)")

        except Exception:
            logger.exception("Failed to load FAISS index")
            self.index = None
            self.resume_ids = []

    # ==========================================================
    # RESET
    # ==========================================================
    def reset(self):
        logger.info("Resetting FAISS index")
        self.index = None
        self.resume_ids = []
        self.dimension = None

    # ==========================================================
    # STATUS CHECK
    # ==========================================================
    def is_ready(self):
        return self.index is not None and len(self.resume_ids) > 0