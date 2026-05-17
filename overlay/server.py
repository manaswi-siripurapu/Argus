from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS


def create_app(get_output_fn, get_state_fn):
    app = Flask(__name__, static_folder=".")
    CORS(app)

    @app.route("/")
    def index():
        return send_from_directory("overlay", "index.html")

    @app.route("/status")
    def status():
        output = get_output_fn()
        state = get_state_fn()
        return jsonify({**output, **state})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
