import argparse
import json

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import torch
from rdkit import Chem
from rdkit.Chem import AllChem, Crippen, Descriptors, Lipinski, rdMolDescriptors
from torch_geometric.data import Batch, Data
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


def one_of_k_encoding(x, allowable_set):
    if x not in allowable_set:
        raise ValueError(f"input {x} not in allowable set {allowable_set}")
    return list(map(lambda s: x == s, allowable_set))


def one_of_k_encoding_unk(x, allowable_set):
    if x not in allowable_set:
        x = allowable_set[-1]
    return list(map(lambda s: x == s, allowable_set))


def atom_features(atom):
    return np.array(
        one_of_k_encoding_unk(
            atom.GetSymbol(),
            [
                "C", "N", "O", "S", "F", "Si", "P", "Cl", "Br", "Mg", "Na", "Ca",
                "Fe", "As", "Al", "I", "B", "V", "K", "Tl", "Yb", "Sb", "Sn",
                "Ag", "Pd", "Co", "Se", "Ti", "Zn", "H", "Li", "Ge", "Cu", "Au",
                "Ni", "Cd", "In", "Mn", "Zr", "Cr", "Pt", "Hg", "Pb", "Unknown",
            ],
        )
        + one_of_k_encoding(atom.GetDegree(), list(range(11)))
        + one_of_k_encoding_unk(atom.GetTotalNumHs(), list(range(11)))
        + one_of_k_encoding_unk(atom.GetImplicitValence(), list(range(11)))
        + [atom.GetIsAromatic()]
    )


def smile_to_graph(smile):
    mol = Chem.MolFromSmiles(smile)
    if mol is None:
        raise ValueError("Invalid SMILES string.")

    c_size = mol.GetNumAtoms()
    features = []
    for atom in mol.GetAtoms():
        feature = atom_features(atom)
        features.append(feature / sum(feature))

    edges = []
    for bond in mol.GetBonds():
        edges.append([bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()])
    graph = nx.Graph(edges).to_directed()
    edge_index = [[e1, e2] for e1, e2 in graph.edges]

    if not edge_index:
        edge_index = [[0, 0]]

    return c_size, features, edge_index


def validate_protein_sequence(sequence):
    cleaned = "".join(sequence.upper().split())
    if not cleaned:
        raise ValueError("Protein sequence cannot be empty.")
    invalid_chars = sorted({ch for ch in cleaned if ch not in SEQ_DICT})
    if invalid_chars:
        raise ValueError(
            "Protein sequence contains invalid characters: "
            + ", ".join(invalid_chars)
            + ". Use amino-acid letters only."
        )
    if len(cleaned) > MAX_SEQ_LEN:
        raise ValueError(f"Protein sequence is too long. Maximum length is {MAX_SEQ_LEN}.")
    return cleaned


def validate_smiles(smiles):
    cleaned = "".join(str(smiles).split())
    if not cleaned:
        raise ValueError("Drug SMILES cannot be empty.")
    if Chem.MolFromSmiles(cleaned) is None:
        raise ValueError("Invalid SMILES string.")
    return cleaned


def generate_drug_3d_molblock(smiles):
    smiles = validate_smiles(smiles)
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)

    status = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if status != 0:
        raise ValueError("Could not generate a 3D conformer for this SMILES string.")

    AllChem.UFFOptimizeMolecule(mol, maxIters=400)
    mol = Chem.RemoveHs(mol)
    return Chem.MolToMolBlock(mol)


def load_model(device):
    model = GCNNet()
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device)
    model.eval()
    return model


def clamp(value, lower=0.0, upper=100.0):
    return max(lower, min(upper, float(value)))


def band_from_score(score):
    if score >= 70:
        return "High"
    if score >= 40:
        return "Moderate"
    return "Low"


def estimate_solubility_label(log_p, tpsa, hbd, mw):
    solubility_index = 60 - (log_p * 12) + (tpsa * 0.18) + (hbd * 4) - max(mw - 350, 0) * 0.05
    if solubility_index >= 55:
        return "Good"
    if solubility_index >= 35:
        return "Moderate"
    return "Low"


def estimate_half_life_label(log_p, aromatic_rings, rot_bonds, mw):
    persistence_index = (log_p * 14) + (aromatic_rings * 8) + (rot_bonds * 2.5) + max(mw - 250, 0) * 0.04
    if persistence_index >= 70:
        return "Long"
    if persistence_index >= 40:
        return "Medium"
    return "Short"


def build_safety_snapshot(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {
            "mode": "heuristic",
            "note": "Could not parse molecule for safety snapshot.",
            "toxicity_risk": {"score": 0, "label": "Unknown"},
            "liver_injury_risk": {"score": 0, "label": "Unknown"},
            "cardiac_herg_risk": {"score": 0, "label": "Unknown"},
            "solubility": {"label": "Unknown"},
            "half_life": {"label": "Unknown"},
        }

    mw = Descriptors.MolWt(mol)
    log_p = Crippen.MolLogP(mol)
    tpsa = rdMolDescriptors.CalcTPSA(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    rot_bonds = Lipinski.NumRotatableBonds(mol)
    aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
    heavy_atoms = mol.GetNumHeavyAtoms()
    has_basic_nitrogen = any(atom.GetSymbol() == "N" and atom.GetFormalCharge() >= 0 for atom in mol.GetAtoms())

    toxicity_score = clamp(
        20
        + (log_p * 10)
        + (aromatic_rings * 6)
        + max(mw - 350, 0) * 0.04
        + max(heavy_atoms - 25, 0) * 0.8
        - (tpsa * 0.08)
    )
    liver_score = clamp(
        18
        + (log_p * 12)
        + (aromatic_rings * 5)
        + max(hba - 6, 0) * 3
        + max(mw - 300, 0) * 0.05
        - (tpsa * 0.05)
    )
    cardiac_score = clamp(
        15
        + (log_p * 14)
        + (aromatic_rings * 7)
        + (8 if has_basic_nitrogen else 0)
        + max(mw - 280, 0) * 0.04
        - (tpsa * 0.06)
    )

    return {
        "mode": "heuristic",
        "note": "Prototype screening estimate derived from simple molecular descriptors. Not a validated clinical safety prediction.",
        "toxicity_risk": {"score": round(toxicity_score, 1), "label": band_from_score(toxicity_score)},
        "liver_injury_risk": {"score": round(liver_score, 1), "label": band_from_score(liver_score)},
        "cardiac_herg_risk": {"score": round(cardiac_score, 1), "label": band_from_score(cardiac_score)},
        "solubility": {"label": estimate_solubility_label(log_p, tpsa, hbd, mw)},
        "half_life": {"label": estimate_half_life_label(log_p, aromatic_rings, rot_bonds, mw)},
    }


def score_drug_target_pair(protein_sequence, smiles):
    protein_sequence = validate_protein_sequence(protein_sequence)
    smiles = validate_smiles(smiles)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    protein_tensor = torch.tensor(seq_cat(protein_sequence), dtype=torch.long)
    _, features, edge_index = smile_to_graph(smiles)

    graph_data = Data(
        x=torch.tensor(np.asarray(features), dtype=torch.float32),
        edge_index=torch.tensor(edge_index, dtype=torch.long).t().contiguous(),
    )
    graph_data.target = protein_tensor.unsqueeze(0)
    batch = Batch.from_data_list([graph_data]).to(device)

    model = load_model(device)
    with torch.no_grad():
        output = model(batch).view(-1).item()

    return {
        "protein_sequence": protein_sequence,
        "smiles": smiles,
        "affinity": round(float(output), 4),
        "safety": build_safety_snapshot(smiles),
    }


def rank_drugs_for_protein(protein_sequence, top_n=DEFAULT_TOP_N):
    protein_sequence = validate_protein_sequence(protein_sequence)
    top_n = int(top_n)
    if top_n < 1 or top_n > 10:
        raise ValueError("Top N must be between 1 and 10.")

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
        {
            "rank": idx,
            "smiles": smile,
            "affinity": round(score, 4),
            "safety": build_safety_snapshot(smile),
        }
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

    try:
        results = rank_drugs_for_protein(args.protein, args.top_n)
    except ValueError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
            return
        raise

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
