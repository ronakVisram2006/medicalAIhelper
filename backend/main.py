import fitz  
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
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


DOCUMENT_STORE = {
    "full_text": "",
    "pages": [],
    "sentences": []
    
}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
        
    print("starting PDF extraction...")
    pages = extract_text_from_pdf(tmp_path)
    print("Finished PDF extraction.")
    
    full_text = "\n".join([p["text"] for p in pages])
    DOCUMENT_STORE["full_text"] = full_text
    DOCUMENT_STORE["pages"] = pages
    sentences = nltk.sent_tokenize(full_text)
    DOCUMENT_STORE["sentences"] = sentences
    

    return {
        "filename": file.filename,
        "pages": pages
    }


@app.post("/ask")
def ask_question(payload: dict):
    question = payload["question"]
    text = DOCUMENT_STORE["full_text"]

    answer = f"You asked: {question}. I will analyse the document soon."

    return {"answer": answer}


@app.get("/export_sentences")
def export_sentences():
    return DOCUMENT_STORE["sentences"]
