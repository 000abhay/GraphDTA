import torch
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from torch_geometric.loader import DataLoader
from models.gcn import GCNNet
from utils import TestbedDataset

# ================= CONFIG =================
PROTEIN_SEQUENCE = "MKWVTFISLLFLFSSAYS"
TOP_N = 3
MODEL_PATH = "model_GCNNet_davis.model"
DATASET_NAME = "davis_test"
CSV_PATH = "data/davis_test.csv"

# ================= DEVICE =================
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ================= PROTEIN ENCODING =================
SEQ_VOC = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
SEQ_DICT = {v: i + 1 for i, v in enumerate(SEQ_VOC)}
MAX_SEQ_LEN = 1000

def seq_cat(prot):
    x = np.zeros(MAX_SEQ_LEN, dtype=np.int64)
    for i, ch in enumerate(prot[:MAX_SEQ_LEN]):
        x[i] = SEQ_DICT.get(ch, 0)
    return x

protein_tensor = torch.tensor(seq_cat(PROTEIN_SEQUENCE)).to(device)

# ================= LOAD MODEL =================
model = GCNNet()
model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
model.to(device)
model.eval()

# ================= LOAD DATA =================
print("Loading cached dataset...")
dataset = TestbedDataset(root="data", dataset=DATASET_NAME)
loader = DataLoader(dataset, batch_size=256, shuffle=False)

# ================= LOAD SMILES =================
df = pd.read_csv(CSV_PATH)
drug_smiles = df["compound_iso_smiles"].values

# ================= PREDICT =================
predictions = []

with torch.no_grad():
    for batch in loader:
        batch = batch.to(device)

        batch.target = protein_tensor.unsqueeze(0).repeat(batch.num_graphs, 1)

        out = model(batch)
        predictions.extend(out.cpu().numpy().flatten())

predictions = np.array(predictions)

assert len(predictions) == len(drug_smiles), "Mismatch predictions vs SMILES"

# ================= UNIQUE DRUG RANKING =================
drug_scores = {}

for smile, score in zip(drug_smiles, predictions):
    if smile not in drug_scores:
        drug_scores[smile] = score
    else:
        drug_scores[smile] = max(drug_scores[smile], score)

top_drugs = sorted(
    drug_scores.items(),
    key=lambda x: x[1],
    reverse=True
)[:TOP_N]

# ================= OUTPUT =================
print("\n=== Top UNIQUE Predicted Drugs ===")
print("Protein:", PROTEIN_SEQUENCE)

for rank, (smile, score) in enumerate(top_drugs, 1):
    print(f"\nRank {rank}")
    print(f"Drug SMILES : {smile}")
    print(f"Affinity    : {score:.4f}")

# ================= PLOT =================
labels = [f"Rank {i+1}" for i in range(len(top_drugs))]
scores = [s for _, s in top_drugs]

plt.figure(figsize=(6, 4))
plt.bar(labels, scores)
plt.ylabel("Predicted Affinity (-log10 Kd)")
plt.title("Top Unique Drug Candidates")
plt.tight_layout()
plt.savefig("top_drugs_affinity.png")
plt.show()

print("\nSaved plot: top_drugs_affinity.png")
