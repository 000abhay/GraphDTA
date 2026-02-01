import torch
import numpy as np
import matplotlib.pyplot as plt

from torch_geometric.data import DataLoader
from models.gcn import GCNNet
from utils import TestbedDataset, mse, rmse, pearson, spearman

# ---------------- Device ----------------
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---------------- Load model ----------------
model = GCNNet()
model.load_state_dict(torch.load("model_GCNNet_davis.model", map_location=device))
model.to(device)
model.eval()

# ---------------- Load test dataset ----------------
test_data = TestbedDataset(root="data", dataset="davis_test")
test_loader = DataLoader(test_data, batch_size=512, shuffle=False)

# ---------------- Prediction ----------------
y_true = []
y_pred = []

with torch.no_grad():
    for data in test_loader:
        data = data.to(device)
        out = model(data)

        y_pred.append(out.cpu().numpy())
        y_true.append(data.y.cpu().numpy())

y_true = np.concatenate(y_true).reshape(-1)
y_pred = np.concatenate(y_pred).reshape(-1)

# ---------------- Metrics ----------------
print("\n=== Test Metrics ===")
print("MSE      :", mse(y_true, y_pred))
print("RMSE     :", rmse(y_true, y_pred))
print("Pearson  :", pearson(y_true, y_pred))
print("Spearman :", spearman(y_true, y_pred))

# ---------------- Save predictions ----------------
np.save("davis_predictions.npy", y_pred)
print("\nPredictions saved to davis_predictions.npy")

# ---------------- Plot ----------------
plt.figure(figsize=(6,6))
plt.scatter(y_true, y_pred, alpha=0.5)
plt.plot([y_true.min(), y_true.max()],
         [y_true.min(), y_true.max()],
         'r--')

plt.xlabel("True Affinity")
plt.ylabel("Predicted Affinity")
plt.title("True vs Predicted Affinity (DAVIS)")
plt.tight_layout()
plt.savefig("true_vs_pred.png", dpi=300)

print("Plot saved as true_vs_pred.png")
