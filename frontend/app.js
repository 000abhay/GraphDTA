const dashboardData = {
  features: [
    {
      tag: "Input + Run",
      title: "Protein-first workflow",
      text: "The app starts with a protein sequence box and a Run button so ranking happens through a clear single action.",
    },
    {
      tag: "Top N Output",
      title: "Best drug shortlist",
      text: "Results are returned as a ranked list of candidate drugs with predicted affinity scores.",
    },
    {
      tag: "Evaluation",
      title: "Model quality evidence",
      text: "Saved DAVIS metrics and plots remain visible so users can understand why the ranking output is trustworthy.",
    },
    {
      tag: "Project Context",
      title: "Scientific workflow clarity",
      text: "The dashboard still explains data preparation, graph encoding, architecture, and saved artifacts around the core prediction flow.",
    },
  ],
  workflow: [
    {
      tag: "01",
      title: "Submit Protein",
      text: "The user enters a protein sequence in the frontend and chooses how many top candidates to return.",
    },
    {
      tag: "02",
      title: "Encode Sequence",
      text: "The backend converts the sequence into the fixed-length token format used by the GraphDTA protein branch.",
    },
    {
      tag: "03",
      title: "Score Drugs",
      text: "The saved GCNNet model evaluates candidate compounds from the cached DAVIS dataset against the query protein.",
    },
    {
      tag: "04",
      title: "Rank Results",
      text: "Predicted affinity scores are grouped by unique drug and sorted from strongest to weakest candidate.",
    },
    {
      tag: "05",
      title: "Display Top N",
      text: "The frontend renders the best N drug list with predicted affinity values immediately after the run completes.",
    },
  ],
  metrics: [
    {
      name: "RMSE",
      display: "0.5954",
      description: "Prediction error magnitude on the DAVIS test split.",
      fill: 59,
    },
    {
      name: "MSE",
      display: "0.3545",
      description: "Average squared regression error for the saved model.",
      fill: 35,
    },
    {
      name: "Pearson",
      display: "0.7480",
      description: "Linear agreement between predicted and observed affinity.",
      fill: 75,
    },
    {
      name: "Spearman",
      display: "0.6385",
      description: "Rank-order consistency across the benchmark pairs.",
      fill: 64,
    },
    {
      name: "CI",
      display: "0.8489",
      description: "Pairwise ordering quality for ranking-oriented screening.",
      fill: 85,
    },
  ],
  dataset: [
    {
      title: "Unique Drugs",
      text: "68 unique compounds represented as molecular graphs.",
    },
    {
      title: "Protein Targets",
      text: "442 protein sequences used in the DAVIS benchmark split.",
    },
    {
      title: "Training Set",
      text: "25,046 interaction pairs available for learning.",
    },
    {
      title: "Testing Set",
      text: "5,010 interaction pairs used for evaluation.",
    },
  ],
  architecture: [
    {
      title: "Drug Graph Branch",
      text: "Three GCNConv layers learn chemistry-aware structure before global pooling and dense projection.",
    },
    {
      title: "Protein Sequence Branch",
      text: "An embedding layer plus one-dimensional convolution extracts local residue patterns from the query sequence.",
    },
    {
      title: "Fusion Prediction Head",
      text: "Graph and protein embeddings are fused to produce a continuous drug-target affinity score.",
    },
  ],
};

function fillCards(containerId, items, render) {
  const container = document.getElementById(containerId);
  if (!container) return;
  container.innerHTML = items.map((item, index) => render(item, index)).join("");
}

fillCards(
  "feature-grid",
  dashboardData.features,
  (item) => `
    <article class="feature-card">
      <span class="feature-card__tag">${item.tag}</span>
      <h3>${item.title}</h3>
      <p>${item.text}</p>
    </article>
  `
);

fillCards(
  "workflow-board",
  dashboardData.workflow,
  (item) => `
    <article class="workflow-step">
      <span class="workflow-step__tag">${item.tag}</span>
      <h3>${item.title}</h3>
      <p>${item.text}</p>
    </article>
  `
);

fillCards(
  "metrics-grid",
  dashboardData.metrics,
  (item) => `
    <article class="metric-card">
      <div>
        <p class="eyebrow">${item.name}</p>
        <strong>${item.display}</strong>
        <p>${item.description}</p>
      </div>
      <div class="metric-bar" aria-hidden="true">
        <span style="width: ${item.fill}%"></span>
      </div>
    </article>
  `
);

fillCards(
  "dataset-grid",
  dashboardData.dataset,
  (item) => `
    <article class="dataset-card">
      <strong>${item.title}</strong>
      <p>${item.text}</p>
    </article>
  `
);

fillCards(
  "architecture-list",
  dashboardData.architecture,
  (item) => `
    <article class="architecture-row">
      <strong>${item.title}</strong>
      <p>${item.text}</p>
    </article>
  `
);

const metricSummary = document.getElementById("metrics-summary");
if (metricSummary) {
  metricSummary.textContent =
    "The saved GCNNet DAVIS model is strongest as a ranking-support system, which is why this first interactive flow is centered on protein input followed by a ranked drug shortlist.";
}

const form = document.getElementById("ranking-form");
const resultsStatus = document.getElementById("results-status");
const resultsGrid = document.getElementById("results-grid");
const runButton = form ? form.querySelector('button[type="submit"]') : null;
const pairForm = document.getElementById("pair-form");
const pairRunButton = document.getElementById("pair-submit-button");
const rankingArtifactCard = document.getElementById("ranking-artifact-card");
const rankingArtifactImage = document.getElementById("ranking-artifact-image");
const drug3DArtifactCard = document.getElementById("drug-3d-artifact-card");
const artifactDrugViewerStatus = document.getElementById("artifact-drug-viewer-status");
const artifactDrugViewerFallback = document.getElementById("artifact-drug-viewer-fallback");
const artifactPlaceholder = document.getElementById("artifact-placeholder");
const proteinHint = document.getElementById("protein-hint");
const topNHint = document.getElementById("top-n-hint");
const pairProteinHint = document.getElementById("pair-protein-hint");
const pairSmilesHint = document.getElementById("pair-smiles-hint");
const bestCandidateCard = document.getElementById("best-candidate-card");
const bestCandidateRank = document.getElementById("best-candidate-rank");
const bestCandidateScore = document.getElementById("best-candidate-score");
const bestCandidateSmiles = document.getElementById("best-candidate-smiles");
const bestCandidateSafetyNote = document.getElementById("best-candidate-safety-note");
const bestCandidateSafetyGrid = document.getElementById("best-candidate-safety-grid");
const resultsTableWrap = document.getElementById("results-table-wrap");
const resultsTableBody = document.getElementById("results-table-body");
const downloadCsvButton = document.getElementById("download-csv-button");
const pairResultsStatus = document.getElementById("pair-results-status");
const pairScoreCard = document.getElementById("pair-score-card");
const pairScoreValue = document.getElementById("pair-score-value");
const pairScoreSmiles = document.getElementById("pair-score-smiles");
const pairSafetyNote = document.getElementById("pair-safety-note");
const pairSafetyGrid = document.getElementById("pair-safety-grid");
let latestResults = [];
let latestProteinSequence = "";
let artifactDrugViewer = null;

function renderResults(items) {
  resultsGrid.innerHTML = items
    .map(
      (item) => `
        <article class="result-card">
          <span class="result-rank">Rank ${item.rank}</span>
          <strong>${item.affinity.toFixed(4)}</strong>
          <p class="result-label">Predicted Affinity</p>
          <code>${item.smiles}</code>
          <div class="result-safety">
            <span>Toxicity: <strong>${item.safety.toxicity_risk.label}</strong></span>
            <span>Liver: <strong>${item.safety.liver_injury_risk.label}</strong></span>
            <span>hERG: <strong>${item.safety.cardiac_herg_risk.label}</strong></span>
            <span>Solubility: <strong>${item.safety.solubility.label}</strong></span>
            <span>Half-life: <strong>${item.safety.half_life.label}</strong></span>
          </div>
        </article>
      `
    )
    .join("");
}

function renderBestCandidate(item) {
  if (!bestCandidateCard || !item) return;
  bestCandidateRank.textContent = `Rank ${item.rank}`;
  bestCandidateScore.textContent = item.affinity.toFixed(4);
  bestCandidateSmiles.textContent = item.smiles;
  bestCandidateSafetyNote.textContent = item.safety.note || "";
  bestCandidateSafetyGrid.innerHTML = `
    <div class="safety-pill"><span>Toxicity risk</span><strong>${item.safety.toxicity_risk.label} (${item.safety.toxicity_risk.score})</strong></div>
    <div class="safety-pill"><span>Liver injury risk</span><strong>${item.safety.liver_injury_risk.label} (${item.safety.liver_injury_risk.score})</strong></div>
    <div class="safety-pill"><span>Cardiac risk (hERG)</span><strong>${item.safety.cardiac_herg_risk.label} (${item.safety.cardiac_herg_risk.score})</strong></div>
    <div class="safety-pill"><span>Solubility</span><strong>${item.safety.solubility.label}</strong></div>
    <div class="safety-pill"><span>Half-life</span><strong>${item.safety.half_life.label}</strong></div>
  `;
  bestCandidateCard.classList.remove("best-candidate-card--hidden");
}

function renderResultsTable(items) {
  if (!resultsTableWrap || !resultsTableBody) return;
  resultsTableBody.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td>Rank ${item.rank}</td>
          <td>${item.affinity.toFixed(4)}</td>
          <td><code>${item.smiles}</code></td>
          <td>
            Toxicity: ${item.safety.toxicity_risk.label}<br />
            Liver: ${item.safety.liver_injury_risk.label}<br />
            hERG: ${item.safety.cardiac_herg_risk.label}<br />
            Solubility: ${item.safety.solubility.label}<br />
            Half-life: ${item.safety.half_life.label}
          </td>
        </tr>
      `
    )
    .join("");
  resultsTableWrap.classList.remove("results-table-wrap--hidden");
}

function setRunningState(isRunning) {
  if (!runButton) return;
  runButton.disabled = isRunning;
  runButton.textContent = isRunning ? "Running..." : "Run Prediction";
}

function setPairRunningState(isRunning) {
  if (!pairRunButton) return;
  pairRunButton.disabled = isRunning;
  pairRunButton.textContent = isRunning ? "Scoring..." : "Score Pair";
}

function showArtifact() {
  if (!rankingArtifactCard || !rankingArtifactImage || !artifactPlaceholder) return;
  rankingArtifactImage.src = `/top_drugs_affinity.png?t=${Date.now()}`;
  rankingArtifactCard.classList.remove("artifact-card--hidden");
  if (drug3DArtifactCard) {
    drug3DArtifactCard.classList.remove("artifact-card--hidden");
  }
  artifactPlaceholder.classList.add("artifact-placeholder--hidden");
}

function resetResultViews() {
  latestResults = [];
  resultsGrid.innerHTML = "";
  if (bestCandidateCard) {
    bestCandidateCard.classList.add("best-candidate-card--hidden");
  }
  if (resultsTableWrap) {
    resultsTableWrap.classList.add("results-table-wrap--hidden");
  }
  if (resultsTableBody) {
    resultsTableBody.innerHTML = "";
  }
}

function setFieldHint(element, message, isError = false) {
  if (!element) return;
  element.textContent = message;
  element.classList.toggle("field-hint--error", isError);
}

function validateProteinSequence(sequence) {
  const cleaned = sequence.toUpperCase().replace(/\s+/g, "");
  if (!cleaned) {
    return { valid: false, message: "Protein sequence is required." };
  }
  if (cleaned.length > 1000) {
    return { valid: false, message: "Protein sequence is too long. Maximum length is 1000." };
  }
  if (!/^[ABCDEFGHIKLMNOPQRSTUVWXYZ]+$/.test(cleaned)) {
    return {
      valid: false,
      message: "Protein sequence can contain uppercase amino-acid letters only.",
    };
  }
  return {
    valid: true,
    cleaned,
    message: `Sequence length: ${cleaned.length} amino acids.`,
  };
}

function validateTopN(value) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isInteger(parsed)) {
    return { valid: false, message: "Top N must be a whole number." };
  }
  if (parsed < 1 || parsed > 10) {
    return { valid: false, message: "Top N must be between 1 and 10." };
  }
  return { valid: true, value: parsed, message: `Top N is set to ${parsed}.` };
}

function validateSmiles(smiles) {
  const cleaned = String(smiles).trim();
  if (!cleaned) {
    return { valid: false, message: "Drug SMILES is required." };
  }
  if (cleaned.length < 3) {
    return { valid: false, message: "Drug SMILES looks too short." };
  }
  return { valid: true, cleaned, message: "SMILES will be validated by the backend model." };
}

function downloadResultsCsv() {
  if (!latestResults.length) return;

  const rows = [
    [
      "protein_sequence",
      "rank",
      "predicted_affinity",
      "smiles",
      "toxicity_risk",
      "liver_injury_risk",
      "cardiac_herg_risk",
      "solubility",
      "half_life",
    ],
    ...latestResults.map((item) => [
      latestProteinSequence,
      item.rank,
      item.affinity.toFixed(4),
      item.smiles,
      item.safety.toxicity_risk.label,
      item.safety.liver_injury_risk.label,
      item.safety.cardiac_herg_risk.label,
      item.safety.solubility.label,
      item.safety.half_life.label,
    ]),
  ];

  const csv = rows
    .map((row) =>
      row
        .map((value) => `"${String(value).replace(/"/g, '""')}"`)
        .join(",")
    )
    .join("\n");

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "graphdta_ranked_results.csv";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

if (downloadCsvButton) {
  downloadCsvButton.addEventListener("click", downloadResultsCsv);
}

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const proteinSequence = document.getElementById("protein-sequence").value.trim();
    const topN = document.getElementById("top-n").value;
    const proteinValidation = validateProteinSequence(proteinSequence);
    const topNValidation = validateTopN(topN);

    setFieldHint(
      proteinHint,
      proteinValidation.valid
        ? proteinValidation.message
        : proteinValidation.message,
      !proteinValidation.valid
    );
    setFieldHint(
      topNHint,
      topNValidation.valid ? topNValidation.message : topNValidation.message,
      !topNValidation.valid
    );

    if (!proteinValidation.valid || !topNValidation.valid) {
      resultsStatus.textContent = "Please correct the input fields before running prediction.";
      resetResultViews();
      return;
    }

    setRunningState(true);
    resultsStatus.innerHTML =
      '<span class="status-inline"><span class="status-spinner"></span>Running prediction for the submitted protein sequence...</span>';
    resetResultViews();
    latestProteinSequence = proteinValidation.cleaned;

    try {
      const response = await fetch("/api/rank", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protein_sequence: proteinValidation.cleaned,
          top_n: topNValidation.value,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.details || payload.error || "Prediction failed.");
      }

      const results = payload.results || [];
      latestResults = results;
      renderResults(results);
      renderBestCandidate(results[0]);
      renderResultsTable(results);
      resultsStatus.innerHTML = `Showing <strong>${results.length}</strong> ranked drug candidates for the submitted protein sequence.`;
      showArtifact();
      if (results[0]) {
        loadBestDrug3D(results[0].smiles);
      }
    } catch (error) {
      resultsStatus.textContent = error.message.includes("running the server inside the GraphDTA environment")
        ? error.message
        : `Prediction failed: ${error.message}`;
      resetResultViews();
    } finally {
      setRunningState(false);
    }
  });
}

function renderPairScore(payload) {
  if (!pairScoreCard) return;
  pairScoreValue.textContent = payload.affinity.toFixed(4);
  pairScoreSmiles.textContent = payload.smiles;
  pairSafetyNote.textContent = payload.safety.note || "";
  pairSafetyGrid.innerHTML = `
    <div class="safety-pill"><span>Toxicity risk</span><strong>${payload.safety.toxicity_risk.label} (${payload.safety.toxicity_risk.score})</strong></div>
    <div class="safety-pill"><span>Liver injury risk</span><strong>${payload.safety.liver_injury_risk.label} (${payload.safety.liver_injury_risk.score})</strong></div>
    <div class="safety-pill"><span>Cardiac risk (hERG)</span><strong>${payload.safety.cardiac_herg_risk.label} (${payload.safety.cardiac_herg_risk.score})</strong></div>
    <div class="safety-pill"><span>Solubility</span><strong>${payload.safety.solubility.label}</strong></div>
    <div class="safety-pill"><span>Half-life</span><strong>${payload.safety.half_life.label}</strong></div>
  `;
  pairScoreCard.classList.remove("pair-score-card--hidden");
}

if (pairForm) {
  pairForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const proteinSequence = document.getElementById("pair-protein-sequence").value.trim();
    const smiles = document.getElementById("pair-smiles").value.trim();
    const proteinValidation = validateProteinSequence(proteinSequence);
    const smilesValidation = validateSmiles(smiles);

    setFieldHint(pairProteinHint, proteinValidation.message, !proteinValidation.valid);
    setFieldHint(pairSmilesHint, smilesValidation.message, !smilesValidation.valid);

    if (!proteinValidation.valid || !smilesValidation.valid) {
      pairResultsStatus.textContent = "Please correct the protein sequence and SMILES input first.";
      if (pairScoreCard) pairScoreCard.classList.add("pair-score-card--hidden");
      return;
    }

    setPairRunningState(true);
    pairResultsStatus.innerHTML =
      '<span class="status-inline"><span class="status-spinner"></span>Scoring this protein-drug pair...</span>';
    if (pairScoreCard) pairScoreCard.classList.add("pair-score-card--hidden");

    try {
      const response = await fetch("/api/score", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protein_sequence: proteinValidation.cleaned,
          smiles: smilesValidation.cleaned,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.details || payload.error || "Pair scoring failed.");
      }

      renderPairScore(payload);
      pairResultsStatus.innerHTML =
        "Showing a direct affinity estimate and safety snapshot for the submitted protein-drug pair.";
    } catch (error) {
      pairResultsStatus.textContent = `Pair scoring failed: ${error.message}`;
      if (pairScoreCard) pairScoreCard.classList.add("pair-score-card--hidden");
    } finally {
      setPairRunningState(false);
    }
  });
}

function getOrCreateViewer(elementId, backgroundColor = "#f7fbff") {
  const element = document.getElementById(elementId);
  if (!element || typeof $3Dmol === "undefined") return null;
  const viewer = $3Dmol.createViewer(element, { backgroundColor });
  viewer.clear();
  return viewer;
}

async function loadDrugStructure(smiles) {
  const response = await fetch("/api/drug-3d", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ smiles }),
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.details || payload.error || "Could not generate drug 3D structure.");
  }
  return payload;
}

async function loadBestDrug3D(smiles) {
  if (!artifactDrugViewerStatus) return;
  if (artifactDrugViewerFallback) {
    artifactDrugViewerFallback.textContent = "Loading 3D diagram...";
    artifactDrugViewerFallback.classList.remove("viewer-fallback--hidden");
  }
  artifactDrugViewerStatus.innerHTML =
    '<span class="status-inline"><span class="status-spinner"></span>Loading 3D structure for the best-ranked drug...</span>';

  try {
    const payload = await loadDrugStructure(smiles);
    artifactDrugViewer = getOrCreateViewer("artifact-drug-viewer", "#fbfffb");

    if (!artifactDrugViewer) {
      throw new Error("3D viewer library could not be initialized.");
    }

    artifactDrugViewer.addModel(payload.molblock, "mol");
    artifactDrugViewer.setStyle({}, { stick: { radius: 0.18, colorscheme: "greenCarbon" }, sphere: { scale: 0.28 } });
    artifactDrugViewer.zoomTo();
    artifactDrugViewer.resize();
    artifactDrugViewer.render();
    window.setTimeout(() => {
      if (artifactDrugViewer) {
        artifactDrugViewer.resize();
        artifactDrugViewer.render();
      }
    }, 60);
    if (artifactDrugViewerFallback) {
      artifactDrugViewerFallback.classList.add("viewer-fallback--hidden");
    }
    artifactDrugViewerStatus.textContent = "Showing the 3D conformer for the best-ranked drug candidate.";
  } catch (error) {
    if (artifactDrugViewerFallback) {
      artifactDrugViewerFallback.textContent = "3D diagram is not present for this drug.";
      artifactDrugViewerFallback.classList.remove("viewer-fallback--hidden");
    }
    artifactDrugViewerStatus.textContent = `Drug 3D structure error: ${error.message}`;
  }
}
