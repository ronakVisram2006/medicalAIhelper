from transformers import pipeline
clf = pipeline("text-classification", model="OXRON2/medical-note-classifier")
print(clf("Patient reports persistent headache for 3 days."))
print(clf("Continue taking 500mg amoxicillin twice daily."))