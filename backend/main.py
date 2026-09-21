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

import numpy as np
from sentence_transformers import SentenceTransformer

embedder = SentenceTransformer('all-MiniLM-L6-v2')

client = OpenAI(
    api_key=os.environ["GROQ_API_KEY"],
    base_url="https://api.groq.com/openai/v1"
)

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
    "sentences": [],
    "labeled_sentences": [],
    "sentence_embeddings": None,
}


def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    pages = []
    for page_number, page in enumerate(doc):
        text = page.get_text()
        pages.append({"page_number": page_number + 1, "text": text})
    doc.close()
    return pages


def classify_sentence(sentence: str) -> str:
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    predicted_class_id = torch.argmax(outputs.logits, dim=1).item()
    return model.config.id2label[predicted_class_id]


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        pages = extract_text_from_pdf(tmp_path)
        full_text = "\n".join([p["text"] for p in pages])
        DOCUMENT_STORE["full_text"] = full_text
        DOCUMENT_STORE["pages"] = pages
        sentences = nltk.sent_tokenize(full_text)
        DOCUMENT_STORE["sentences"] = sentences

        labeled = []
        for s in sentences:
            label = classify_sentence(s)
            labeled.append({"sentence": s, "label": label})
        DOCUMENT_STORE["labeled_sentences"] = labeled

        if sentences:
            DOCUMENT_STORE["sentence_embeddings"] = embedder.encode(sentences)
        else:
            DOCUMENT_STORE["sentence_embeddings"] = None

        return {"filename": file.filename, "pages": pages}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/classify")
def classify_text(payload: dict):
    sentence = payload["sentence"]
    label = classify_sentence(sentence)
    return {"label": label}


LABEL_KEYWORDS = {
    "MEDICATION_INSTRUCTION": ["medication", "medicine", "drug", "dose", "dosage", "prescription", "taking", "mg", "pills", "cholesterol"],
    "DIAGNOSIS": ["diagnosis", "condition", "diagnosed", "wrong", "assessment", "disease"],
    "SYMPTOM": ["symptom", "feeling", "experiencing", "complain", "pain", "issue"],
    "FOLLOW_UP": ["follow-up", "follow up", "next appointment", "return", "when should", "plan"],
    "LAB_RESULT": ["lab", "result", "level", "test", "value", "blood pressure", "vitals", "reading"],
    "HISTORY": ["history", "previously", "past", "prior", "before"],
}


def guess_label(question: str):
    q = question.lower()
    for label, keywords in LABEL_KEYWORDS.items():
        if any(k in q for k in keywords):
            return label
    return None


def retrieve_relevant_sentences(question: str, top_k: int = 15):
    sentences = DOCUMENT_STORE["sentences"]
    labeled = DOCUMENT_STORE["labeled_sentences"]
    all_embeddings = DOCUMENT_STORE["sentence_embeddings"]

    if not sentences or all_embeddings is None:
        return []

    guessed_label = guess_label(question)

    if guessed_label:
        indices = [i for i, item in enumerate(labeled) if item["label"] == guessed_label]
        if not indices:
            indices = list(range(len(sentences)))
    else:
        indices = list(range(len(sentences)))

    pool_sentences = [sentences[i] for i in indices]
    pool_embeddings = all_embeddings[indices]

    question_embedding = embedder.encode([question])[0]
    similarities = np.dot(pool_embeddings, question_embedding) / (
        np.linalg.norm(pool_embeddings, axis=1) * np.linalg.norm(question_embedding) + 1e-8
    )

    top_indices = np.argsort(similarities)[::-1][:top_k] 
    return [pool_sentences[i] for i in top_indices]


@app.post("/ask")
def ask_question(payload: dict):
    if not DOCUMENT_STORE["sentences"]:
        return {"answer": "No document has been uploaded yet. Please upload a PDF first."}

    question = payload["question"]
    relevant_sentences = retrieve_relevant_sentences(question, top_k=15)
    context = "\n".join(relevant_sentences)

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=500,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise medical document assistant. Answer using ONLY "
                    "information explicitly stated in the provided excerpts. "
                    "Be specific and complete — if multiple relevant facts exist, include all of them. "
                    "If the answer is not in the excerpts, respond exactly: "
                    "'This information is not found in the document.' "
                    "Do not guess or use outside medical knowledge."
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


@app.get("/classify_document")
def classify_document():
    return {"classified": DOCUMENT_STORE["labeled_sentences"]}


@app.get("/export_sentences")
def export_sentences():
    return DOCUMENT_STORE["sentences"]