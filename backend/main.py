import fitz  
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    pages = []

    for page_number, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page_number": page_number + 1,
            "text": text
        })

    doc.close()
    return pages

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    pages = extract_text_from_pdf(tmp_path)

    return {
        "filename": file.filename,
        "pages": pages
    }
