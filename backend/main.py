import fitz  
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

model_path = "./final_medical_classifier"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

DOCUMENT_STORE = {
    "full_text": "",
    "pages": [],
    "sentences": []
}

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
    
@app.post("/classify")
def classify_text(payload: dict):
    sentence = payload["sentence"]
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
    outputs = model(**inputs)
    predicted_class_id = torch.argmax(outputs.logits, dim=1).item()
    return {"label": model.config.id2label[predicted_class_id]}


@app.post("/ask")
def ask_question(payload: dict):
    question = payload["question"]
    text = DOCUMENT_STORE["full_text"]

    answer = f"You asked: {question}. I will analyse the document soon."

    return {"answer": answer}


@app.get("/export_sentences")
def export_sentences():
    return DOCUMENT_STORE["sentences"]
