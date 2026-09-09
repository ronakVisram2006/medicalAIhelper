import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    TrainingArguments, Trainer, DataCollatorWithPadding
)
import numpy as np
from sklearn.metrics import classification_report

df = pd.read_csv("dataset.csv")

# Drop blank/separator rows
df = df.dropna(subset=['label', 'sentence'])
df = df[df['label'].astype(str).str.strip() != '']

valid_labels = {
    "OTHER", "SYMPTOM", "HISTORY", "MEDICATION_INSTRUCTION",
    "LAB_RESULT", "DIAGNOSIS", "FOLLOW_UP"
}
bad_rows = df[~df['label'].isin(valid_labels)]
if len(bad_rows) > 0:
    print(f"Dropping {len(bad_rows)} rows with unexpected labels:")
    print(bad_rows['label'].unique())
df = df[df['label'].isin(valid_labels)]

label_list = sorted(df['label'].unique().tolist())
label2id = {label: i for i, label in enumerate(label_list)}
id2label = {i: label for label, i in label2id.items()}

df['label_id'] = df['label'].map(label2id)
df = df.drop(columns=['label']).rename(columns={'label_id': 'label'})

dataset = Dataset.from_pandas(df.reset_index(drop=True))

model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenize(batch):
    return tokenizer(batch["sentence"], truncation=True, max_length=64)

dataset = dataset.map(tokenize, batched=True)
dataset = dataset.remove_columns(["sentence"])

dataset = dataset.train_test_split(test_size=0.1)
train_dataset = dataset["train"]
test_dataset = dataset["test"]

data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

model = AutoModelForSequenceClassification.from_pretrained(
    model_name,
    num_labels=len(label_list),
    id2label=id2label,
    label2id=label2id
)

training_args = TrainingArguments(
    output_dir="./model",
    eval_strategy="no",       
    save_strategy="no",
    learning_rate=2e-5,
    per_device_train_batch_size=32,
    per_device_eval_batch_size=32,
    num_train_epochs=2,
    weight_decay=0.01,
)

def compute_metrics(pred):
    preds = np.argmax(pred.predictions, axis=1)
    report = classification_report(
        pred.label_ids, preds,
        labels=list(range(len(label_list))),
        target_names=label_list,
        output_dict=True,
        zero_division=0,
    )
    return {"accuracy": report["accuracy"]}

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

trainer.train()

metrics = trainer.evaluate()
print("Final eval metrics:", metrics)

trainer.save_model("./final_medical_classifier")
tokenizer.save_pretrained("./final_medical_classifier")
print("Model saved to ./final_medical_classifier")