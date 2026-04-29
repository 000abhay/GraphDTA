import json
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"

STATIC_ROUTES = {
    "/": FRONTEND_DIR / "index.html",
    "/index.html": FRONTEND_DIR / "index.html",
    "/styles.css": FRONTEND_DIR / "styles.css",
    "/app.js": FRONTEND_DIR / "app.js",
    "/true_vs_pred.png": ROOT / "true_vs_pred.png",
    "/top_drugs_affinity.png": ROOT / "top_drugs_affinity.png",
    "/docs/report_assets/workflow_diagram.png": ROOT / "docs" / "report_assets" / "workflow_diagram.png",
    "/docs/report_assets/gcn_architecture.png": ROOT / "docs" / "report_assets" / "gcn_architecture.png",
}

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".png": "image/png",
}


class GraphDTAHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.serve_static(head_only=True)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/protein-3d":
            self.handle_protein_3d()
            return
        self.serve_static(head_only=False)

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in {"/api/rank", "/api/score", "/api/drug-3d"}:
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint.")
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.respond_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/drug-3d":
            smiles = payload.get("smiles", "")
            if not str(smiles).strip():
                self.respond_json({"error": "Drug SMILES is required."}, status=HTTPStatus.BAD_REQUEST)
                return

            command = [
                sys.executable,
                "-c",
                (
                    "import json; "
                    "from rank_drugs import generate_drug_3d_molblock; "
                    f"print(json.dumps({{'smiles': {str(smiles)!r}, 'molblock': generate_drug_3d_molblock({str(smiles)!r})}}))"
                ),
            ]
        else:
            protein = payload.get("protein_sequence", "")
            if not str(protein).strip():
                self.respond_json({"error": "Protein sequence is required."}, status=HTTPStatus.BAD_REQUEST)
                return

            if path == "/api/rank":
                top_n = payload.get("top_n", 3)
                try:
                    top_n = max(1, min(10, int(top_n)))
                except (TypeError, ValueError):
                    self.respond_json({"error": "top_n must be a valid integer."}, status=HTTPStatus.BAD_REQUEST)
                    return

                command = [
                    sys.executable,
                    str(ROOT / "rank_drugs.py"),
                    "--protein",
                    str(protein),
                    "--top-n",
                    str(top_n),
                    "--json",
                ]
            else:
                smiles = payload.get("smiles", "")
                if not str(smiles).strip():
                    self.respond_json({"error": "Drug SMILES is required."}, status=HTTPStatus.BAD_REQUEST)
                    return

                command = [
                    sys.executable,
                    "-c",
                    (
                        "import json; "
                        "from rank_drugs import score_drug_target_pair; "
                        f"print(json.dumps(score_drug_target_pair({protein!r}, {str(smiles)!r})))"
                    ),
                ]

        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raw_error = exc.stderr.strip() or exc.stdout.strip() or "Request failed."
            error_lines = [line.strip() for line in raw_error.splitlines() if line.strip()]
            error_text = error_lines[-1] if error_lines else raw_error
            self.respond_json(
                {
                    "error": "Request failed. Make sure you are running the server inside the GraphDTA environment.",
                    "details": error_text,
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if not stdout_lines:
            self.respond_json({"error": "Ranking completed but returned no data."}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        try:
            result = json.loads(stdout_lines[-1])
        except json.JSONDecodeError:
            self.respond_json(
                {
                    "error": "Ranking output was not valid JSON.",
                    "details": completed.stdout,
                },
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        if "error" in result:
            self.respond_json(
                {"error": result["error"]},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        self.respond_json(result)

    def respond_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def serve_static(self, head_only=False):
        path = urlparse(self.path).path
        file_path = STATIC_ROUTES.get(path)
        if not file_path or not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found.")
            return

        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", CONTENT_TYPES.get(file_path.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def handle_protein_3d(self):
        query = parse_qs(urlparse(self.path).query)
        pdb_id = (query.get("pdb_id") or [""])[0].strip()
        if not pdb_id:
            self.respond_json({"error": "PDB ID is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        pdb_id = pdb_id.lower()
        if len(pdb_id) != 4 or not pdb_id.isalnum():
            self.respond_json({"error": "PDB ID must be a 4-character identifier."}, status=HTTPStatus.BAD_REQUEST)
            return

        url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
        request = Request(url, headers={"User-Agent": "GraphDTA-App/1.0"})
        try:
            with urlopen(request, timeout=20) as response:
                pdb_text = response.read().decode("utf-8")
        except Exception as exc:
            self.respond_json(
                {"error": "Could not fetch protein structure from RCSB PDB.", "details": str(exc)},
                status=HTTPStatus.BAD_GATEWAY,
            )
            return

        self.respond_json({"pdb_id": pdb_id.upper(), "pdb_text": pdb_text})

    def log_message(self, format, *args):
        return


def main():
    port = 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), GraphDTAHandler)
    print(f"GraphDTA app server running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
