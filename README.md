# LLM Proxy

A reverse proxy for LLM services that modifies request parameters and handles streaming responses.

## Overview

This proxy acts as middleware between clients and an LLM service (e.g., a language model API). It injects `max_tokens` into requests, forwards traffic to a target server, and processes streaming responses to ensure compatibility.

## Installation

```bash
pip install flask click requests
```

## Usage

Start the proxy with:

```bash
python llm-proxy.py --target http://target-url --port 11432 --max-tokens 8192
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--target` | Target LLM service URL | `http://localhost:11433` |
| `--port` | Proxy server port | `11432` |
| `--max-tokens` | Max tokens to inject in requests | `8192` |
| `--debug` | Enable debug logging | `False` |

## Endpoints

### `/`

- **GET**: Returns proxy status and configuration.

  ```json
  {"message": "Welcome to the LLM Proxy!", "target": "...", "max_tokens": ...}
  ```

### `/health`

- **GET**: Returns health status.

  ```json
  {"status": "healthy"}
  ```

### `/status`

- **GET**: Returns detailed runtime info.

  ```json
  {"status": "running", "target": "...", "max_tokens": ...}
  ```

### `/config`

- **GET**: Returns proxy configuration.

  ```json
  {"target": "...", "max_tokens": ...}
  ```

### `/<path:path>`

- **All methods**: Proxies requests to the target service and modifies the `max_tokens` parameter in the request body.

## How It Works

1. **Request Injection**: Adds/updates `max_tokens` in the request body (if JSON).
2. **Streaming Handling**: Modifies streaming responses by replacing `finish_reason: "length"` with `"stop"`.
3. **Logging**: Detailed logs for debugging and monitoring.

## Contributing

Contributions are welcome! Open an issue or submit a PR.
