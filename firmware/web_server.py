import asyncio
import json

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

    async def start(self):
        self.server = await asyncio.start_server(self._handle_client, "0.0.0.0", self.port)
        print("Web server running on port", self.port)

    async def _handle_client(self, reader, writer):
        try:
            line = await reader.readline()
            if not line:
                writer.close()
                await writer.wait_closed()
                return

            req_line = line.decode().strip()
            parts = req_line.split()
            if len(parts) < 2:
                writer.close()
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

            # Read body
            body = b""
            if content_length > 0:
                body = await reader.read(content_length)

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

        except Exception as e:
            print("HTTP handler error:", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _serve_index(self, writer):
        html_data = None
        for p in ("web/index.html", "/web/index.html", "index.html"):
            try:
                with open(p, "rb") as f:
                    html_data = f.read()
                break
            except Exception:
                pass

        if not html_data:
            html_data = b"<h1>Smart Lava Lamp</h1><p>Deploy UI files or check status at /api/status</p>"

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
                ok = self.state.set_power(bool(data["on"]))
                if ok:
                    await self._send_response(writer, 200, {"success": True, "power": self.state.power_on})
                else:
                    await self._send_response(writer, 409, {"error": "Cannot power on: fault latched (%s)" % (self.state.safety.fault or "")})
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
                p = self.state.set_power_pct(val)
                await self._send_response(writer, 200, {"success": True, "power_pct": p})
            else:
                await self._send_response(writer, 400, {"error": "Missing 'power_pct' or 'value'"})
            return

        if path == "/api/reset-fault" and method == "POST":
            self.state.reset_fault()
            await self._send_response(writer, 200, {"success": True})
            return

        await self._send_response(writer, 404, {"error": "Not found"})

    async def _send_response(self, writer, code, payload):
        body_bytes = json.dumps(payload).encode()
        header = (
            "HTTP/1.1 %d OK\r\n"
            "Content-Type: application/json\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Access-Control-Allow-Headers: Authorization, Content-Type\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % (code, len(body_bytes))
        )
        writer.write(header.encode())
        writer.write(body_bytes)
        await writer.drain()
