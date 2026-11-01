#!/usr/bin/env python3
"""HTTP metrics agent. Runs on every monitored server and exposes /metrics."""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import psutil

from monitoring.core import token_matches

PORT = int(os.getenv("AGENT_PORT", "9101"))
AGENT_SECRET = os.getenv("AGENT_TOKEN", "")


def get_metrics() -> dict:
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        partitions.append(
            {
                "mount": part.mountpoint,
                "total_gb": round(usage.total / 1024**3, 2),
                "used_gb": round(usage.used / 1024**3, 2),
                "free_gb": round(usage.free / 1024**3, 2),
                "percent": usage.percent,
            }
        )
    return {
        "cpu_percent": round(psutil.cpu_percent(interval=1), 1),
        "ram": {
            "total_gb": round(ram.total / 1024**3, 2),
            "used_gb": round(ram.used / 1024**3, 2),
            "free_gb": round(ram.available / 1024**3, 2),
            "percent": ram.percent,
            "free_percent": round(100 - ram.percent, 1),
        },
        "disk": {
            "total_gb": round(disk.total / 1024**3, 2),
            "used_gb": round(disk.used / 1024**3, 2),
            "free_gb": round(disk.free / 1024**3, 2),
            "percent": disk.percent,
            "free_percent": round(100 - disk.percent, 1),
        },
        "partitions": partitions,
        "boot_time": psutil.boot_time(),
    }


class AgentHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return

        provided = parse_qs(parsed.query).get("token", [""])[0]
        if not token_matches(AGENT_SECRET, provided):
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b'{"error":"forbidden"}')
            return

        try:
            body = json.dumps(get_metrics()).encode()
        except Exception as error:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(error)}).encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not AGENT_SECRET:
        raise SystemExit("AGENT_TOKEN is empty; set it before starting the agent")
    HTTPServer(("0.0.0.0", PORT), AgentHandler).serve_forever()
