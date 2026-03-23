import os
from api.resume_parser import parse_resume_file
from api.embedding import generate_embedding
from api.faiss_index import build_faiss_index

RESUME_FOLDER = r"C:\Users\Lohitha\Desktop\jobportal\backend\uploads\resumes"

resume_texts = []
resume_files = []

def index_resumes_from_folder():

    print("Scanning resumes folder...")

    for file in os.listdir(RESUME_FOLDER):

        if not file.lower().endswith((".pdf", ".docx")):
            continue

        path = os.path.join(RESUME_FOLDER, file)

        print("Parsing:", file)

        text = parse_resume_file(path)

        if not text:
            continue

        resume_texts.append(text)
        resume_files.append(file)

    print("Total resumes parsed:", len(resume_texts))

    embeddings = []

    for text in resume_texts:
        emb = generate_embedding(text)
        embeddings.append(emb)

    print("Embeddings generated:", len(embeddings))

    build_faiss_index(embeddings)

    print("FAISS index built")