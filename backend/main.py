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
from bisect import bisect_right
import numpy as np
from sentence_transformers import SentenceTransformer

import re

GLOBAL_PATTERNS = [
    r"\bsummar(i[sz]e|y)\b",
    r"\boverview\b",
    r"\bkey (points|information|info|takeaways|details)\b",
    r"\bmain (points|ideas|findings)\b",
    r"\bwhat('s| is) (this|the) (document|pdf|report) (about)?\b",
    r"\btl;?dr\b",
    r"\bgist\b",
    r"\bhighlights\b",
]

CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
PAGE_CITE_RE = re.compile(r"\[p(\d+)\]")

def is_global_query(q: str) -> bool:
    q = q.lower()
    return any(re.search(p, q) for p in GLOBAL_PATTERNS)

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

model_path = "OXRON2/medical-note-classifier"

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

DOCUMENT_STORE = {
    "full_text": "",
    "pages": [],
    "sentences": [],
    "sentence_pages": [],   
    "labeled_sentences": [],
    "sentence_embeddings": None,
     "summary": None,
     "sentence_lines": [],
}

SUMMARY_SYSTEM = (
    "Summarise my document in clear, easy language."
    "Start with 2–3 short sentences explaining what the document is mainly about.  "
    "Then give me bullet points of the important details that appear in the document.  "
    "Only include things that are actually written in the document.  "
    "Use bullet points for diagnoses, medications and doses, lab results, and follow‑up instructions — but only if they are present.  "
    "After every sentence or bullet point, show the page number where you found the information, written like [p1], [p2], etc.  "
    "Only cite pages that appear in the document.  "
    "Do not add any medical knowledge or opinions.  "
    "Do not guess or interpret anything.  "
    "If the document is empty, write exactly: “The document is empty.”"
)


def labeled_page_text(pages):
    return "\n\n".join(f"[Page {p['page_number']}]\n{p['text']}" for p in pages)


def chunk_pages(pages, max_chars=12000):
    chunks, current, size = [], [], 0
    for p in pages:
        block = f"[Page {p['page_number']}]\n{p['text']}"
        if size + len(block) > max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(block)
        size += len(block)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def extract_sources(answer: str, hits: list):
    order = {}  

    def fix(match):
        out = ""
        for raw in match.group(1).split(","):
            i = int(raw)
            if 1 <= i <= len(hits):   
                n = order.setdefault(i, len(order) + 1)
                out += f"[{n}]"
        return out

    cleaned = CITE_RE.sub(fix, answer)
    sources = [
        {
            "id": n,
            "page": hits[i - 1]["page"],
            "line_start": hits[i - 1]["line_start"],
            "line_end": hits[i - 1]["line_end"],
            "quote": hits[i - 1]["sentence"],
        }
        for i, n in order.items()
    ]
    return cleaned, sources


def strip_invalid_page_cites(text: str, num_pages: int) -> str:
    return PAGE_CITE_RE.sub(
        lambda m: m.group(0) if 1 <= int(m.group(1)) <= num_pages else "",
        text,
    )


def extract_text_from_pdf(file_path):
    doc = fitz.open(file_path)
    pages = []
    for page_number, page in enumerate(doc):
        lines = [l.strip() for l in page.get_text().split("\n") if l.strip()]
        pages.append({"page_number": page_number + 1, "text": "\n".join(lines)})
    doc.close()
    return pages

def classify_sentence(sentence: str) -> str:
    inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding="max_length", max_length=128)
    with torch.no_grad():
        outputs = model(**inputs)
    predicted_class_id = torch.argmax(outputs.logits, dim=1).item()
    return model.config.id2label[predicted_class_id]

def call_llm(system: str, user: str, max_tokens: int = 1500) -> str:
    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=max_tokens,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content


def summarise_document() -> str:
    if DOCUMENT_STORE.get("summary"):
        return DOCUMENT_STORE["summary"]

    pages = DOCUMENT_STORE["pages"]
    full_text = DOCUMENT_STORE["full_text"]

    #Short document 
    if len(full_text) < 40000:
        summary = call_llm(SUMMARY_SYSTEM, f"Document:\n{labeled_page_text(pages)}\n\nSummarise this document.")
    #Longer document, chunk and summarise
    else:
        chunks = chunk_pages(pages)
        partials = [
            call_llm(SUMMARY_SYSTEM, f"Document section:\n{c}\n\nList the key facts in this section, keeping the page citations.")
            for c in chunks
        ]
        summary = call_llm(
            SUMMARY_SYSTEM,
            "Notes from each section:\n\n" + "\n\n".join(partials)
            + "\n\nCombine these into one overview plus key points, keeping the page citations.",
        )

    summary = strip_invalid_page_cites(summary, len(pages))

    DOCUMENT_STORE["summary"] = summary
    return summary


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
        DOCUMENT_STORE["summary"] = None
        DOCUMENT_STORE["pages"] = pages

        sentences, sentence_pages, sentence_lines = [], [], []
        for p in pages:
            text = p["text"]

            starts, pos = [], 0
            for line in text.split("\n"):
                starts.append(pos)
                pos += len(line) + 1

            cursor = 0
            for s in nltk.sent_tokenize(text):
                found = text.find(s, cursor)
                if found == -1:
                    found = cursor
                cursor = found + len(s)

                start_line = bisect_right(starts, found)                      
                end_line = bisect_right(starts, max(found, cursor - 1))

                clean = " ".join(s.split())
                if clean:
                    sentences.append(clean)
                    sentence_pages.append(p["page_number"])
                    sentence_lines.append((start_line, end_line))

            DOCUMENT_STORE["sentences"] = sentences
            DOCUMENT_STORE["sentence_pages"] = sentence_pages
            DOCUMENT_STORE["sentence_lines"] = sentence_lines

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

@app.post("/summarise")
def summarise_endpoint():
    if not DOCUMENT_STORE["sentences"]:
        return {"answer": "No document has been uploaded yet. Please upload a PDF first."}
    return {"answer": summarise_document()}


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
    sentence_pages = DOCUMENT_STORE["sentence_pages"]
    sentence_lines = DOCUMENT_STORE["sentence_lines"]
    all_embeddings = DOCUMENT_STORE["sentence_embeddings"]

    if not sentences or all_embeddings is None:
        return []

    question_embedding = embedder.encode([question])[0]
    similarities = np.dot(all_embeddings, question_embedding) / (
        np.linalg.norm(all_embeddings, axis=1) * np.linalg.norm(question_embedding) + 1e-8
    )

    top_indices = np.argsort(similarities)[::-1][:top_k]

    return [
        {
            "sentence": sentences[i],
            "page": sentence_pages[i],
            "line_start": sentence_lines[i][0],
            "line_end": sentence_lines[i][1],
            "score": float(similarities[i]),
        }
        for i in top_indices
    ]


NOT_FOUND = "This information is not found in the document." 

LIST_RE = re.compile(r"\b(all|list|which|what)\b.*\b(medications?|medicines?|drugs?|labs?|tests?|results?)\b")

@app.post("/ask")
def ask_question(payload: dict):
    if not DOCUMENT_STORE["sentences"]:
        return {"answer": "No document has been uploaded yet. Please upload a PDF first.", "sources": []}

    question = payload["question"]

    if is_global_query(question):
        return summarise_document()        

    top_k = 30 if LIST_RE.search(question.lower()) else 15
    hits = retrieve_relevant_sentences(question, top_k=top_k)

    if not hits or hits[0]["score"] < 0.2:   
        return {"answer": NOT_FOUND, "sources": []}

    context = "\n".join(f"[{n}] {h['sentence']}" for n, h in enumerate(hits, start=1))

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        max_tokens=4000,
        temperature=0,
        extra_body={"reasoning_effort": "low"}, 
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise medical document assistant. Answer using ONLY "
                    "information explicitly stated in the provided excerpts. "
                    "Be specific and complete: if multiple relevant facts exist, include all of them, "
                    "and when asked for a list, include every matching item in the excerpts. "
                    "If the answer is not in the excerpts, respond exactly: "
                    f"'{NOT_FOUND}' "
                    "Do not guess or use outside medical knowledge. "
                    "The excerpts are numbered like [1], [2]. Every sentence or bullet in your "
                    "answer MUST end with the number(s) of the excerpt(s) it came from, each in its own "
                    "brackets, like [1] or [2][5]. An answer without citations is invalid. "
                    "Only cite numbers that appear in the excerpts. "
                    "Do not cite anything for the 'not found' response. "
                    "Example: 'He takes carvedilol 12.5 mg twice daily [3]. He also takes apixaban 5 mg twice daily [7].'"
                    "When the answer lists several items that share the same fields (medications, lab results, "
                    "vital signs), format it as a markdown table with one row per item. Use the field names as "
                    "column headers and put the excerpt number(s) in a final column named Source, like [3]. "
                    "Otherwise answer in short sentences. "
                    "Use plain, simple wording, but never leave out required details such as status or dose changes. "
                    "Never leave out items because of category or relevance unless the question asks for a category. "
                    "For medications, include a Status column (Taking, Held, Stopped, Started, Dose changed) "
                    "based only on the excerpts, and give both the old and new dose when a dose changed. "
                    "Only include a Notes or Reason column if the excerpts explicitly state the reason; "
                    "never add an indication from your own knowledge. "
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Document excerpts:\n{context}\n\nQuestion: {question}\n\n"
                    "Remember: cite excerpt numbers after every statement."
                ),
            },
        ],
    )

    print("finish_reason:", response.choices[0].finish_reason)   # 'length' means max_tokens is still too low
    finish = response.choices[0].finish_reason
    print("finish_reason:", finish)
    answer = response.choices[0].message.content or ""

    if finish == "length":
        return {
            "answer": "The answer was too long to generate completely. Try asking about one item at a time, for example a single medication or lab test.",
            "sources": [],
        }
    answer = response.choices[0].message.content or ""

    answer, sources = extract_sources(answer, hits)


    if not sources and NOT_FOUND not in answer:
        sources = [
            {
                "id": n,
                "page": h["page"],
                "line_start": h["line_start"],
                "line_end": h["line_end"],
                "quote": h["sentence"],
                "score": round(h["score"], 2),
            }
            for n, h in enumerate(hits[:3], start=1)
        ]

    return {"answer": answer, "sources": sources}

@app.get("/classify_document")
def classify_document():
    return {"classified": DOCUMENT_STORE["labeled_sentences"]}


@app.get("/export_sentences")
def export_sentences():
    return DOCUMENT_STORE["sentences"]