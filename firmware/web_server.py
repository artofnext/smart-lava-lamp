import asyncio
import json

STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    404: "Not Found",
    409: "Conflict",
}

def constant_time_compare(val1, val2):
    if not val1 or not val2 or len(val1) != len(val2):
        return False
    result = 0
    for x, y in zip(val1, val2):
        result |= ord(x) ^ ord(y)
    return result == 0

class WebServer:
    def __init__(self, app_state, port=80):
        self.state = app_state
        self.port = port
        self.server = None
        self._html_cache = None

    async def start(self):
        self.server = await asyncio.start_server(self._handle_client, "0.0.0.0", self.port)
        print("Web server running on port", self.port)

    async def _handle_client(self, reader, writer):
        try:
            await asyncio.wait_for(self._process_request(reader, writer), 5)
            await asyncio.sleep_ms(25)
        except Exception as e:
            print("HTTP handler error:", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _process_request(self, reader, writer):
        line = await reader.readline()
        if not line:
            return

        req_line = line.decode().strip()
        parts = req_line.split()
        if len(parts) < 2:
            return
        method, url = parts[0], parts[1]

        # Parse query params if any
        query_token = None
        if "?" in url:
            path, qs = url.split("?", 1)
            for q in qs.split("&"):
                if q.startswith("token="):
                    query_token = q.split("=", 1)[1]
        else:
            path = url

        # Read headers
        headers = {}
        content_length = 0
        while True:
            hline = await reader.readline()
            if not hline or hline == b"\r\n" or hline == b"\n":
                break
            hstr = hline.decode()
            if ":" in hstr:
                k, v = hstr.split(":", 1)
                k_lower = k.strip().lower()
                headers[k_lower] = v.strip()
                if k_lower == "content-length":
                    try:
                        content_length = int(v.strip())
                    except Exception:
                        pass

        # Read full body across TCP segments (critical behind Nginx reverse proxy)
        body = b""
        while len(body) < content_length:
            chunk = await reader.read(content_length - len(body))
            if not chunk:
                break
            body += chunk

        if method == "OPTIONS":
            await self._send_response(writer, 200, {})
            return

        # Serve static UI
        if path in ("/", "/index.html"):
            await self._serve_index(writer)
            return

        # API Token check
        expected_token = self.state.config.get("token", "")
        auth_header = headers.get("authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        elif query_token:
            token = query_token

        if not constant_time_compare(expected_token, token):
            await self._send_response(writer, 401, {"error": "Unauthorized"})
            return

        # API Routes
        await self._route_api(method, path, body, writer)

    async def _serve_index(self, writer):
        if self._html_cache is None:
            for p in ("web/index.html", "/web/index.html", "index.html"):
                try:
                    with open(p, "rb") as f:
                        self._html_cache = f.read()
                    break
                except Exception:
                    pass
        html_data = self._html_cache or b"<h1>Smart Lava Lamp</h1>"

        header = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html; charset=utf-8\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % len(html_data)
        )
        writer.write(header.encode())
        writer.write(html_data)
        await writer.drain()

    async def _route_api(self, method, path, body, writer):
        data = None
        if body:
            try:
                data = json.loads(body.decode())
            except Exception:
                pass

        if path == "/api/status" and method == "GET":
            await self._send_response(writer, 200, self.state.get_status())
            return

        if path == "/api/history" and method == "GET":
            await self._send_response(writer, 200, {"interval_s": 10, "temps": self.state.history})
            return

        if path == "/api/power" and method == "POST":
            if data and "on" in data:
                target_on = bool(data["on"])
                await self._send_response(writer, 200, {"success": True, "power": target_on})
                await asyncio.sleep_ms(30)
                self.state.set_power(target_on)
            else:
                await self._send_response(writer, 400, {"error": "Missing 'on' boolean"})
            return

        if path == "/api/power-level" and method == "POST":
            val = None
            if data:
                if "power_pct" in data:
                    val = float(data["power_pct"])
                elif "value" in data:
                    val = float(data["value"])
            if val is not None:
                clamped = max(0.0, min(100.0, val))
                await self._send_response(writer, 200, {"success": True, "power_pct": clamped})
                await asyncio.sleep_ms(30)
                self.state.set_power_pct(clamped)
            else:
                await self._send_response(writer, 400, {"error": "Missing 'power_pct' or 'value'"})
            return

        if path == "/api/reset-fault" and method == "POST":
            self.state.reset_fault()
            await self._send_response(writer, 200, {"success": True})
            return

        if path == "/api/led":
            if method == "POST" and data:
                led_state = self.state.update_led(data)
                await self._send_response(writer, 200, {"success": True, "led": led_state})
            else:
                await self._send_response(writer, 200, self.state.leds.to_dict(self.state.power_on))
            return

        await self._send_response(writer, 404, {"error": "Not found"})

    async def _send_response(self, writer, code, payload):
        body_bytes = json.dumps(payload).encode()
        reason = STATUS_TEXT.get(code, "OK")
        header = (
            "HTTP/1.1 %d %s\r\n"
            "Content-Type: application/json\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            "Access-Control-Allow-Headers: Authorization, Content-Type\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % (code, reason, len(body_bytes))
        )
        writer.write(header.encode())
        writer.write(body_bytes)
        await writer.drain()
