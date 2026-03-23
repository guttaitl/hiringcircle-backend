try:
    import win32com.client
except ImportError:
    win32com = None

import os

def convert_doc_to_docx(doc_path: str) -> str:
    """
    Convert .doc → .docx using MS Word (Windows only)
    """

    if not doc_path.lower().endswith(".doc"):
        return doc_path

    docx_path = doc_path + "x"

    if os.path.exists(docx_path):
        return docx_path

    # Skip conversion on Linux servers
    if win32com is None:
        print("DOC conversion skipped: win32com not available")
        return doc_path

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False

    try:
        doc = word.Documents.Open(os.path.abspath(doc_path))
        doc.SaveAs(os.path.abspath(docx_path), FileFormat=16)
        doc.Close()
    finally:
        word.Quit()

    return docx_path