import os
from pathlib import Path
import logging
from api.db import get_db_conn

logger = logging.getLogger("resume_importer")

BASE_DIR = Path(__file__).resolve().parent
RESUME_FOLDER = BASE_DIR / "uploads" / "resumes"


def import_resumes():

    conn = get_db_conn()
    cur = conn.cursor()

    imported = 0

    try:

        for file in RESUME_FOLDER.iterdir():

            if not file.name.lower().endswith((".pdf", ".docx", ".txt")):
                continue

            file_path = str(file)

            cur.execute(
                "SELECT id FROM candidate_resumes WHERE file_path=%s",
                (file_path,)
            )

            if cur.fetchone():
                continue

            cur.execute(
                """
                INSERT INTO candidate_resumes
                (file_path, parsed_successfully)
                VALUES (%s, false)
                """,
                (file_path,)
            )

            imported += 1

        conn.commit()

    finally:
        cur.close()
        conn.close()

    if imported > 0:
        logger.info(f"Imported {imported} new resumes")

    return imported


if __name__ == "__main__":
    import_resumes()