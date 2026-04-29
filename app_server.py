import json
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


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
        self.serve_static(head_only=False)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/rank":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint.")
            return

        length = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self.respond_json({"error": "Invalid JSON payload."}, status=HTTPStatus.BAD_REQUEST)
            return

        protein = payload.get("protein_sequence", "")
        top_n = payload.get("top_n", 3)

        if not str(protein).strip():
            self.respond_json({"error": "Protein sequence is required."}, status=HTTPStatus.BAD_REQUEST)
            return

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

        try:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            error_text = exc.stderr.strip() or exc.stdout.strip() or "Ranking failed."
            self.respond_json(
                {
                    "error": "Failed to rank drugs. Make sure you are running the server inside the GraphDTA environment.",
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

    def log_message(self, format, *args):
        return


def main():
    port = 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), GraphDTAHandler)
    print(f"GraphDTA app server running on http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
