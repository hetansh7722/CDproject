#!/usr/bin/env python3
"""Web frontend server for the Symbol Table Generator (standard library only).

    python server.py            ->  http://localhost:8000
    python server.py 5000       ->  http://localhost:5000
"""
import json
import os
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from symtab import analyze, LANGUAGES

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, "web")
SAMPLES = os.path.join(ROOT, "samples")
EXT_LANG = {".c": "c", ".py": "python"}
MIME = {".html": "text/html", ".css": "text/css", ".js": "text/javascript"}


def result_to_json(result):
    """Same shape as report.to_json, plus tokens and a summary for the UI."""
    scopes = [{
        "id": s.id, "name": s.name, "level": s.level, "parent": s.parent_id,
        "symbols": [{**{k: v for k, v in asdict(sym).items() if k != "warned_uninit"},
                     "type_str": sym.type_str} for sym in s.symbols.values()],
    } for s in result.table.all_scopes]
    return {
        "language": result.language,
        "scopes": scopes,
        "tokens": [{"line": t.line, "col": t.col, "type": t.type, "value": t.value}
                   for t in result.tokens if t.type != "EOF"],
        "diagnostics": [asdict(d) for d in result.diagnostics],
        "summary": {
            "scopes": len(scopes),
            "symbols": sum(len(s["symbols"]) for s in scopes),
            "errors": len(result.errors),
            "warnings": len(result.warnings),
        },
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/samples":
            out = {lang: {} for lang in LANGUAGES}      # {"c": {file: text}, "python": {...}}
            for f in sorted(os.listdir(SAMPLES)):
                lang = EXT_LANG.get(os.path.splitext(f)[1])
                if lang:
                    with open(os.path.join(SAMPLES, f), encoding="utf-8") as fh:
                        out[lang][f] = fh.read()
            return self._send(200, json.dumps(out))
        name = "index.html" if path == "/" else os.path.basename(path)
        full = os.path.join(WEB, name)
        if not os.path.isfile(full):
            return self._send(404, "not found", "text/plain")
        with open(full, "rb") as fh:
            self._send(200, fh.read(), MIME.get(os.path.splitext(name)[1], "application/octet-stream"))

    def do_POST(self):
        if self.path != "/api/analyze":
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
            language = body.get("language", "c")
            if language not in LANGUAGES:
                raise ValueError(f"unsupported language {language!r}")
            self._send(200, json.dumps(result_to_json(analyze(body["source"], language))))
        except Exception as e:  # keep the server alive on bad input
            self._send(400, json.dumps({"error": str(e)}))

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"Symbol Table Generator running at http://localhost:{port}  (Ctrl+C to stop)")
    try:
        ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
