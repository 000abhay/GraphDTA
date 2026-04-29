import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from torch_geometric.loader import DataLoader

from models.gcn import GCNNet
from utils import TestbedDataset


MODEL_PATH = "model_GCNNet_davis.model"
DATASET_NAME = "davis_test"
CSV_PATH = "data/davis_test.csv"
DEFAULT_TOP_N = 3
DEFAULT_PROTEIN_SEQUENCE = "MKWVTFISLLFLFSSAYS"

SEQ_VOC = "ABCDEFGHIKLMNOPQRSTUVWXYZ"
SEQ_DICT = {v: i + 1 for i, v in enumerate(SEQ_VOC)}
MAX_SEQ_LEN = 1000


def seq_cat(prot):
    x = np.zeros(MAX_SEQ_LEN, dtype=np.int64)
    for i, ch in enumerate(prot[:MAX_SEQ_LEN]):
        x[i] = SEQ_DICT.get(ch, 0)
    return x


def validate_protein_sequence(sequence):
    cleaned = "".join(sequence.upper().split())
    if not cleaned:
        raise ValueError("Protein sequence cannot be empty.")
    return cleaned


def load_model(device):
    model = GCNNet()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()
    return model


def rank_drugs_for_protein(protein_sequence, top_n=DEFAULT_TOP_N):
    protein_sequence = validate_protein_sequence(protein_sequence)
    top_n = max(1, int(top_n))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    protein_tensor = torch.tensor(seq_cat(protein_sequence)).to(device)

    model = load_model(device)

    print("Loading cached dataset...")
    dataset = TestbedDataset(root="data", dataset=DATASET_NAME)
    loader = DataLoader(dataset, batch_size=256, shuffle=False)

    df = pd.read_csv(CSV_PATH)
    drug_smiles = df["compound_iso_smiles"].values

    predictions = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            batch.target = protein_tensor.unsqueeze(0).repeat(batch.num_graphs, 1)
            out = model(batch)
            predictions.extend(out.cpu().numpy().flatten())

    predictions = np.array(predictions)
    if len(predictions) != len(drug_smiles):
        raise RuntimeError("Mismatch between predictions and SMILES count.")

    drug_scores = {}
    for smile, score in zip(drug_smiles, predictions):
        score = float(score)
        if smile not in drug_scores:
            drug_scores[smile] = score
        else:
            drug_scores[smile] = max(drug_scores[smile], score)

    top_drugs = sorted(drug_scores.items(), key=lambda item: item[1], reverse=True)[:top_n]
    return [
        {"rank": idx, "smiles": smile, "affinity": round(score, 4)}
        for idx, (smile, score) in enumerate(top_drugs, 1)
    ]


def save_ranking_plot(results, output_path):
    labels = [f"Rank {item['rank']}" for item in results]
    scores = [item["affinity"] for item in results]
    smiles_labels = [item["smiles"] for item in results]

    fig_height = max(4.2, 1.1 * len(results) + 1.8)
    plt.figure(figsize=(10, fig_height))
    colors = ["#0f6b5b", "#2a9d8f", "#74c69d", "#95d5b2", "#b7e4c7"][: len(results)]
    bars = plt.barh(labels, scores, color=colors)
    plt.xlabel("Predicted Affinity (-log10 Kd)")
    plt.title("Top Ranked Drug Candidates")
    plt.xlim(0, max(scores) * 1.18)
    plt.gca().invert_yaxis()

    for bar, score, smile in zip(bars, scores, smiles_labels):
        short_smile = smile if len(smile) <= 42 else smile[:39] + "..."
        plt.text(
            bar.get_width() + 0.03,
            bar.get_y() + bar.get_height() / 2,
            f"{score:.4f}\n{short_smile}",
            va="center",
            fontsize=9,
        )

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Rank candidate drugs for a protein sequence.")
    parser.add_argument("--protein", default=DEFAULT_PROTEIN_SEQUENCE, help="Protein sequence to score.")
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Number of top drug candidates.")
    parser.add_argument("--json", action="store_true", help="Emit results as JSON.")
    parser.add_argument(
        "--plot-path",
        default="top_drugs_affinity.png",
        help="Path to save the ranking plot. Use empty string to skip plot generation.",
    )
    args = parser.parse_args()

    results = rank_drugs_for_protein(args.protein, args.top_n)

    if args.plot_path:
        save_ranking_plot(results, args.plot_path)

    if args.json:
        payload = {
            "protein_sequence": validate_protein_sequence(args.protein),
            "top_n": max(1, int(args.top_n)),
            "results": results,
            "plot_path": args.plot_path,
        }
        print(json.dumps(payload))
        return

    print("\n=== Top UNIQUE Predicted Drugs ===")
    print("Protein:", validate_protein_sequence(args.protein))
    for item in results:
        print(f"\nRank {item['rank']}")
        print(f"Drug SMILES : {item['smiles']}")
        print(f"Affinity    : {item['affinity']:.4f}")

    if args.plot_path:
        print(f"\nSaved plot: {args.plot_path}")


if __name__ == "__main__":
    main()
