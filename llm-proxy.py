import click
from flask import Flask, request, Response
import jsonify
import requests
import threading
import logging
import json

app = Flask(__name__)


@click.command()
@click.option(
    "--target",
    default="http://localhost:11433",
    help="Target service URL to which the proxy forwards requests.",
)
@click.option("--port", default=11432, help="Port on which the proxy server will run.")
@click.option(
    "--max-tokens",
    default=8192,
    help="Maximum tokens value to inject in the request body.",
)
@click.option("--debug", is_flag=True, help="Enable debug mode.")
def start_proxy(target, port, max_tokens, debug):

    app.config["DEBUG"] = debug
    app.config["TARGET_SERVER"] = target
    app.config["MAX_TOKENS"] = max_tokens

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if app.config.get("DEBUG") else logging.INFO,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    @app.route("/", methods=["GET"])
    def index():
        return jsonify(
            {
                "message": "Welcome to the LLM Proxy!",
                "target": app.config["TARGET_SERVER"],
                "max_tokens": app.config["MAX_TOKENS"],
            }
        )

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "healthy"})

    @app.route("/status", methods=["GET"])
    def status():
        return jsonify(
            {
                "status": "running",
                "target": app.config["TARGET_SERVER"],
                "max_tokens": app.config["MAX_TOKENS"],
            }
        )

    @app.route("/config", methods=["GET"])
    def config():
        return jsonify(
            {
                "target": app.config["TARGET_SERVER"],
                "max_tokens": app.config["MAX_TOKENS"],
            }
        )

    @app.route(
        "/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    )
    def proxy(path):
        url = f"{app.config['TARGET_SERVER']}/{path}"

        logging.info(f"→ Proxying {request.method} request to: {url}")

        headers = {
            key: value for key, value in request.headers if key.lower() != "host"
        }
        if request.data:
            modified_data = modify_request_body(request.data, app.config["MAX_TOKENS"])
        else:
            modified_data = None

        logging.debug(f"→ Forwarding headers: {headers}")
        if modified_data:
            logging.debug(
                f"→ Forwarding body: {modified_data[:100]}...[Truncated]"
            )  # Truncate large bodies

        response = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=modified_data,
            params=request.args,
            stream=True,
        )

        excluded_headers = [
            "content-encoding",
            "content-length",
            "transfer-encoding",
            "connection",
        ]
        response_headers = [
            (name, value)
            for (name, value) in response.raw.headers.items()
            if name.lower() not in excluded_headers
        ]

        def generate():
            for line in response.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        yield f"data: {data}\n\n"
                    else:
                        try:
                            json_data = json.loads(data)
                            choices = json_data.get("choices", [])
                            for choice in choices:
                                if choice.get("finish_reason") == "length":
                                    choice["finish_reason"] = "stop"
                            modified_data = json.dumps(json_data)
                            logging.debug(
                                f"→ Streaming modified chunk: {modified_data[:100]}...[Truncated]"
                            )
                            yield f"data: {modified_data}\n\n"
                        except json.JSONDecodeError:
                            logging.warning(
                                "⚠️ Failed to decode streamed JSON. Yielding raw line."
                            )
                            yield line + "\n\n"
                else:
                    yield line + "\n\n"

        return Response(
            generate(), status=response.status_code, headers=response_headers
        )

    def modify_request_body(original_body, max_tokens):
        try:
            data = json.loads(original_body)
            data["max_tokens"] = max_tokens
            return json.dumps(data)
        except json.JSONDecodeError:
            logging.error(
                "❌ Failed to decode JSON from the request body. Returning original."
            )
            return original_body

    logging.info(
        f"🚀 Starting proxy server on http://0.0.0.0:{port} → {target} with max_tokens={max_tokens}"
    )
    app.run(host="0.0.0.0", port=port, threaded=True, debug=app.config["DEBUG"])


if __name__ == "__main__":
    start_proxy()
