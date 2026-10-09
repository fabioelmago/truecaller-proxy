import os
from flask import Flask, request, jsonify, render_template

import requests

app = Flask(__name__)

TRUECALLER_API_BASE = "https://tools.irbots.com/truecaller/api/v1"
TRUECALLER_API_KEY = os.environ.get("TRUECALLER_API_KEY", "")
PROXY_SECRET = os.environ.get("PROXY_SECRET", "")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Proxy-Secret"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def _unauthorized():
    return jsonify({"error": "No autorizado"}), 401


@app.route("/lookup", methods=["POST", "OPTIONS"])
def lookup():
    if request.method == "OPTIONS":
        return "", 204

    if not PROXY_SECRET or request.headers.get("X-Proxy-Secret") != PROXY_SECRET:
        return _unauthorized()

    body = request.get_json(silent=True) or {}
    number = str(body.get("number", "")).strip()
    if not number:
        return jsonify({"error": "Falta el numero"}), 400
    if not number.startswith("+"):
        number = "+" + number

    try:
        resp = requests.post(
            f"{TRUECALLER_API_BASE}/lookup",
            headers={
                "Authorization": f"Bearer {TRUECALLER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"number": number},
            timeout=15,
        )
    except requests.RequestException:
        return jsonify({"error": "No se pudo conectar con Truecaller"}), 502

    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail", f"Error {resp.status_code}")
        except ValueError:
            detail = f"Error {resp.status_code}"
        return jsonify({"error": detail}), resp.status_code

    data = resp.json()
    entries = data.get("data", {})
    entry_key = next((k for k in entries if k != "time"), None)
    entry = entries.get(entry_key) if entry_key else None

    name = None
    if isinstance(entry, dict):
        for value in entry.values():
            if isinstance(value, str) and value.strip() and value != "Not Found":
                name = value
                break

    if not name:
        return jsonify({"name": "Sin informacion"})
    return jsonify({"name": name})


@app.route("/status", methods=["GET", "OPTIONS"])
def status():
    if request.method == "OPTIONS":
        return "", 204

    if not PROXY_SECRET or request.headers.get("X-Proxy-Secret") != PROXY_SECRET:
        return _unauthorized()

    try:
        resp = requests.get(
            f"{TRUECALLER_API_BASE}/status",
            headers={"Authorization": f"Bearer {TRUECALLER_API_KEY}"},
            timeout=15,
        )
    except requests.RequestException:
        return jsonify({"error": "No se pudo conectar con Truecaller"}), 502

    return jsonify(resp.json()), resp.status_code


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
