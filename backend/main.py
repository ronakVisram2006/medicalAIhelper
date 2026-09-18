import fitz  
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import tempfile
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os
from openai import OpenAI   

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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




def retrieve_relevant_sentences(question: str, top_k: int = 15):
    sentences = DOCUMENT_STORE["sentences"]
    if not sentences:
        return []

    q_words = set(question.lower().split())
    scored = []
    for s in sentences:
        s_words = set(s.lower().split())
        overlap = len(q_words & s_words)
        if overlap > 0:
            scored.append((overlap, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [s for _, s in scored[:top_k]]

    return top if top else sentences[:top_k]

@app.post("/ask")
def ask_question(payload: dict):
    question = payload["question"]
    text = DOCUMENT_STORE["full_text"]
    relevant_sentences = retrieve_relevant_sentences(question, top_k=15)
    context = "\n".join(relevant_sentences)

    response = client.chat.completions.create(
        model="gpt-4o", 
        max_tokens=500,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a medical document assistant. Answer the user's "
                    "question using ONLY the provided document excerpts. If the "
                    "answer isn't in the excerpts, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": f"Document excerpts:\n{context}\n\nQuestion: {question}",
            },
        ],
    )

    answer = response.choices[0].message.content
    return {"answer": answer}


@app.get("/export_sentences")
def export_sentences():
    return DOCUMENT_STORE["sentences"]
