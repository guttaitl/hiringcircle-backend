import logging
from api.services.embedding_service import get_text_embedding
from api.utils.file_parser import extract_text  # adjust if needed

logger = logging.getLogger(__name__)


def chunk_text(text, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def process_resume(file_path, db, file_hash):
    try:
        logger.info(f"📄 Processing resume: {file_path}")

        # 1. Extract text
        text = extract_text(file_path)

        if not text:
            logger.warning(f"⚠️ No text extracted: {file_path}")
            return

        # 2. Chunk text
        chunks = chunk_text(text)

        logger.info(f"🧩 Chunks created: {len(chunks)}")

        # 3. Generate embeddings + store
        for chunk in chunks:
            embedding = get_text_embedding(chunk)

            if not embedding:
                continue

            db.execute("""
                INSERT INTO resume_embeddings (file_name, file_hash, content, embedding)
                VALUES (:file_name, :file_hash, :content, :embedding)
            """, {
                "file_name": file_path,
                "file_hash": file_hash,
                "content": chunk,
                "embedding": embedding
            })

        db.commit()

        logger.info(f"✅ Resume indexed: {file_path}")

    except Exception as e:
        logger.error(f"❌ Error processing {file_path}: {e}")
        db.rollback()