"""Vercel Python serverless function that runs the unbubble pipeline.

Streams JSONL (one line per stage) so the calling Next.js function can
write blobs incrementally as each stage completes.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
from http.server import BaseHTTPRequestHandler

# unbubble_sources is installed from the repo root via requirements.txt
from unbubble_sources.config import load_config
from unbubble_sources.data import NewsEvent
from unbubble_sources.stream_logger import StreamLogger


def _find_config() -> str:
    """Locate the livedemo config file next to this file."""
    return os.path.join(os.path.dirname(__file__), "livedemo.yaml")


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel requires lowercase
    def do_POST(self) -> None:  # noqa: N802
        # Verify internal shared secret
        expected = os.environ.get("INTERNAL_API_SECRET", "")
        auth = self.headers.get("Authorization", "")
        if not expected or auth != f"Bearer {expected}":
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Forbidden"}).encode())
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length))

        query: str = body["query"]
        api_key: str | None = body.get("api_key")

        # Set API key for the pipeline components to pick up
        if api_key:
            os.environ["CLAUDE_API_KEY"] = api_key

        config = load_config(_find_config())

        q: queue.Queue[dict | None] = queue.Queue()
        stream_logger = StreamLogger(output_queue=q)

        from unbubble_sources.config import create_from_config

        pipeline, _, _ = create_from_config(config, stream_logger=stream_logger)
        event = NewsEvent(description=query)

        # Run pipeline in a background thread so we can stream results
        error: BaseException | None = None

        def run_pipeline() -> None:
            nonlocal error
            try:
                asyncio.run(pipeline.run(event))
            except BaseException as exc:
                error = exc
            finally:
                q.put(None)  # sentinel: done

        thread = threading.Thread(target=run_pipeline)
        thread.start()

        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson")
        self.end_headers()

        # Stream JSONL lines as they arrive from the pipeline
        while True:
            item = q.get()
            if item is None:
                break
            self.wfile.write((json.dumps(item, default=str) + "\n").encode())
            self.wfile.flush()

        thread.join()

        # If the pipeline errored, emit an error line
        if error is not None:
            err_line = json.dumps({"type": "error", "error": str(error)})
            self.wfile.write((err_line + "\n").encode())
            self.wfile.flush()
