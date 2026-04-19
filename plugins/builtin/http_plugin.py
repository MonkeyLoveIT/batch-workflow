"""
HTTP request plugin.
Makes HTTP requests as tasks.
"""

from typing import Any, Dict, Optional
import logging
import urllib.request
import urllib.parse
import urllib.error
import json

from core.plugin import Plugin, register_plugin

logger = logging.getLogger(__name__)


@register_plugin("http")
class HTTPPlugin(Plugin):
    """
    Plugin for making HTTP requests.

    Configuration:
        - url: Target URL (required)
        - method: HTTP method (default: GET)
        - headers: Dict of HTTP headers
        - body: Request body (dict will be JSON-encoded)
        - timeout: Request timeout in seconds
    """

    name = "http"
    version = "0.1.0"

    def validate(self, config: Dict[str, Any]) -> bool:
        if "url" not in config:
            logger.error("URL is required")
            return False
        return True

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        url = context.get("url")
        method = context.get("method", "GET").upper()
        headers = context.get("headers", {})
        body = context.get("body")
        timeout = context.get("timeout", 30)

        logger.info(f"Making {method} request to {url}")

        try:
            # Prepare body
            data = None
            if body:
                if isinstance(body, dict):
                    data = json.dumps(body).encode("utf-8")
                    headers.setdefault("Content-Type", "application/json")
                elif isinstance(body, str):
                    data = body.encode("utf-8")

            # Build request
            req = urllib.request.Request(url, data=data, method=method)
            for key, value in headers.items():
                req.add_header(key, value)

            # Execute request
            with urllib.request.urlopen(req, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
                response_headers = dict(response.headers)

                return {
                    "success": True,
                    "status_code": response.status,
                    "headers": response_headers,
                    "body": response_body,
                }

        except urllib.error.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP {e.code}: {e.reason}",
                "status_code": e.code,
                "body": e.read().decode("utf-8") if e.fp else None,
            }
        except urllib.error.URLError as e:
            return {
                "success": False,
                "error": f"URL error: {e.reason}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
