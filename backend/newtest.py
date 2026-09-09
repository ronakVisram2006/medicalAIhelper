from transformers import pipeline
clf = pipeline("text-classification", model="OXRON2/medical-note-classifier")
print(clf("Patient reports worsening shortness of breath."))