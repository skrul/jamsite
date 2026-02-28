import http.server
import socketserver
import threading
import json
import uuid
import time

BROADCAST_PORT = 8001


def get_subnet(ip):
    """Extract /24 subnet from an IPv4 address (e.g., '10.0.0.31' -> '10.0.0')."""
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3])
    # IPv6 or unexpected format — use the full address as its own "subnet"
    return ip


def get_client_ip(handler):
    """Get the client's real IP, checking X-Real-IP for proxied requests."""
    return handler.headers.get("X-Real-IP") or handler.client_address[0]


class BroadcastHub:
    """Manages connected SSE clients and broadcasts messages between them."""

    def __init__(self):
        self.clients = {}  # client_id -> (wfile, subnet, ip)
        self.lock = threading.Lock()

    def add_client(self, client_id, wfile, subnet, ip):
        with self.lock:
            self.clients[client_id] = (wfile, subnet, ip)

    def remove_client(self, client_id):
        with self.lock:
            self.clients.pop(client_id, None)

    def get_clients_by_subnet(self):
        """Return a dict of subnet -> list of (client_id, ip)."""
        groups = {}
        with self.lock:
            for cid, (wfile, subnet, ip) in self.clients.items():
                groups.setdefault(subnet, []).append((cid, ip))
        return groups

    def broadcast(self, sender_id, message):
        data = json.dumps(message)
        sender_entry = self.clients.get(sender_id)
        sender_subnet = sender_entry[1] if sender_entry else None
        with self.lock:
            dead = []
            for cid, (wfile, subnet, ip) in self.clients.items():
                if cid == sender_id:
                    continue
                if subnet != sender_subnet:
                    continue
                try:
                    wfile.write(f"data: {data}\n\n".encode())
                    wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    dead.append(cid)
            for cid in dead:
                self.clients.pop(cid, None)


# Module-level hub instance shared by all handlers
hub = BroadcastHub()


def handle_sse(handler, broadcast_hub):
    """Handle an SSE connection. Blocks until the client disconnects."""
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "keep-alive")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()

    client_id = str(uuid.uuid4())[:8]
    client_ip = get_client_ip(handler)
    subnet = get_subnet(client_ip)

    event = json.dumps({"type": "connected", "clientId": client_id})
    handler.wfile.write(f"data: {event}\n\n".encode())
    handler.wfile.flush()

    broadcast_hub.add_client(client_id, handler.wfile, subnet, client_ip)
    try:
        while True:
            time.sleep(15)
            handler.wfile.write(b": keepalive\n\n")
            handler.wfile.flush()
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        broadcast_hub.remove_client(client_id)


def handle_send(handler, broadcast_hub):
    """Handle a POST to broadcast a song to all other clients."""
    content_length = int(handler.headers.get("Content-Length", 0))
    body = handler.rfile.read(content_length)
    data = json.loads(body)

    sender_id = data.get("senderId", "")
    message = {
        "type": "song",
        "uuid": data["uuid"],
        "slug": data.get("slug", ""),
        "title": data["title"],
        "artist": data["artist"],
    }
    broadcast_hub.broadcast(sender_id, message)

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps({"ok": True}).encode())


def handle_health(handler, broadcast_hub):
    """Return the number of connected clients."""
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    with broadcast_hub.lock:
        count = len(broadcast_hub.clients)
    handler.wfile.write(json.dumps({"clients": count}).encode())


def handle_admin(handler, broadcast_hub):
    """Render an HTML page showing connected clients grouped by subnet."""
    groups = broadcast_hub.get_clients_by_subnet()
    total = sum(len(clients) for clients in groups.values())

    rows = ""
    for subnet in sorted(groups.keys()):
        clients = groups[subnet]
        rows += f'<tr class="subnet-header"><td colspan="2">{subnet}.* ({len(clients)} client{"s" if len(clients) != 1 else ""})</td></tr>\n'
        for cid, ip in sorted(clients, key=lambda c: c[1]):
            rows += f"<tr><td>{cid}</td><td>{ip}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>Broadcast Admin</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: -apple-system, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; }}
  h1 {{ font-size: 1.4rem; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th, td {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid #eee; }}
  th {{ border-bottom: 2px solid #ccc; }}
  .subnet-header td {{ background: #f5f5f5; font-weight: 600; padding-top: 12px; }}
  .empty {{ color: #999; font-style: italic; }}
</style>
</head>
<body>
<h1>Broadcast Clients ({total})</h1>
{f'<table><tr><th>ID</th><th>IP</th></tr>{rows}</table>' if total > 0 else '<p class="empty">No clients connected.</p>'}
</body>
</html>"""

    handler.send_response(200)
    handler.send_header("Content-Type", "text/html")
    handler.end_headers()
    handler.wfile.write(html.encode())


def handle_cors_preflight(handler):
    """Handle OPTIONS preflight for CORS."""
    handler.send_response(204)
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.end_headers()


class BroadcastHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for the standalone broadcast server (production)."""

    def do_GET(self):
        if self.path == "/api/events":
            handle_sse(self, hub)
        elif self.path == "/api/health":
            handle_health(self, hub)
        elif self.path == "/api/admin":
            handle_admin(self, hub)
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path == "/api/send":
            handle_send(self, hub)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        handle_cors_preflight(self)

    def log_message(self, format, *args):
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def start_broadcast_server(port=BROADCAST_PORT):
    server = ThreadedHTTPServer(("", port), BroadcastHandler)
    print(f"Broadcast server listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    start_broadcast_server()
