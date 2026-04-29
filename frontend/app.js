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
const rankingArtifactCard = document.getElementById("ranking-artifact-card");
const rankingArtifactImage = document.getElementById("ranking-artifact-image");
const artifactPlaceholder = document.getElementById("artifact-placeholder");
const bestCandidateCard = document.getElementById("best-candidate-card");
const bestCandidateRank = document.getElementById("best-candidate-rank");
const bestCandidateScore = document.getElementById("best-candidate-score");
const bestCandidateSmiles = document.getElementById("best-candidate-smiles");
const resultsTableWrap = document.getElementById("results-table-wrap");
const resultsTableBody = document.getElementById("results-table-body");

function renderResults(items) {
  resultsGrid.innerHTML = items
    .map(
      (item) => `
        <article class="result-card">
          <span class="result-rank">Rank ${item.rank}</span>
          <strong>${item.affinity.toFixed(4)}</strong>
          <p class="result-label">Predicted Affinity</p>
          <code>${item.smiles}</code>
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

function showArtifact() {
  if (!rankingArtifactCard || !rankingArtifactImage || !artifactPlaceholder) return;
  rankingArtifactImage.src = `/top_drugs_affinity.png?t=${Date.now()}`;
  rankingArtifactCard.classList.remove("artifact-card--hidden");
  artifactPlaceholder.classList.add("artifact-placeholder--hidden");
}

function resetResultViews() {
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

if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const proteinSequence = document.getElementById("protein-sequence").value.trim();
    const topN = document.getElementById("top-n").value;

    if (!proteinSequence) {
      resultsStatus.textContent = "Please enter a protein sequence first.";
      resetResultViews();
      return;
    }

    setRunningState(true);
    resultsStatus.innerHTML =
      '<span class="status-inline"><span class="status-spinner"></span>Running prediction for the submitted protein sequence...</span>';
    resetResultViews();

    try {
      const response = await fetch("/api/rank", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          protein_sequence: proteinSequence,
          top_n: topN,
        }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.details || payload.error || "Prediction failed.");
      }

      const results = payload.results || [];
      renderResults(results);
      renderBestCandidate(results[0]);
      renderResultsTable(results);
      resultsStatus.innerHTML = `Showing <strong>${results.length}</strong> ranked drug candidates for the submitted protein sequence.`;
      showArtifact();
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
