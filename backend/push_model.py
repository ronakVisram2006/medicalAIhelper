from transformers import AutoModelForSequenceClassification, AutoTokenizer

model = AutoModelForSequenceClassification.from_pretrained("./final_medical_classifier")
tokenizer = AutoTokenizer.from_pretrained("./final_medical_classifier")

model.push_to_hub("OXRON2/medical-note-classifier", private=True)
tokenizer.push_to_hub("OXRON2/medical-note-classifier", private=True)