import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


def create_app(get_output_fn, get_state_fn, submit_command_fn=None):
    overlay_dir = os.path.dirname(os.path.abspath(__file__))
    app = Flask(__name__, static_folder=overlay_dir)
    CORS(app)

    @app.route("/")
    def index():
        return send_from_directory(overlay_dir, "index.html")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/status")
    def status():
        output = get_output_fn()
        state = get_state_fn()
        return jsonify({**output, **state})

    @app.route("/command", methods=["POST"])
    def command():
        if submit_command_fn is None:
            return jsonify({"ok": False, "error": "Command input is not enabled."}), 503
        data = request.get_json(silent=True) or {}
        text = str(data.get("command", "")).strip()
        if not text:
            return jsonify({"ok": False, "error": "Command cannot be empty."}), 400
        submit_command_fn(text)
        return jsonify({"ok": True, "queued": text})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
