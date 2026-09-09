from transformers import pipeline

clf = pipeline(
    "text-classification",
    model="./final_medical_classifier",
    tokenizer="./final_medical_classifier"
)

test_sentences = [
    "Patient reports worsening shortness of breath and leg swelling over the past week.",
    "History of type 2 diabetes diagnosed 5 years ago, previously well controlled on metformin.",
    "CBC reveals hemoglobin of 9.1 g/dL and platelet count of 110,000/uL.",
    "Assessment: acute exacerbation of COPD likely triggered by viral upper respiratory infection.",
    "Start prednisone 40 mg daily tapering over the next two weeks.",
    "Follow-up appointment scheduled in three weeks to reassess symptoms and labs.",
    "Signed: Dr. Example, MD, Internal Medicine.",
]

for sentence in test_sentences:
    result = clf(sentence)[0]
    print(f"{result['label']:<25} ({result['score']:.2f})  {sentence}")