"""Disposable services for the ten investigations. Never publish host ports."""
import hashlib
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import threading
from urllib.parse import parse_qs, urlsplit

state = {"remediated": False}
ADDRESS = socket.gethostbyname(socket.gethostname())
LOGIN = """<!doctype html><html lang="en"><title>Atlas lab — sign in</title>
<style>body{font:18px system-ui;max-width:540px;margin:80px auto;background:#e9e9e6;color:#242424}label,input,button{display:block;margin:12px 0}input,button{padding:12px}</style>
<h1>Atlas operations</h1><p>Disposable Hercules capture lab.</p>
<form action="/login" method="post"><label for="email">Email</label><input id="email" name="email" type="email" required><label for="password">Password</label><input id="password" name="password" type="password" required><button>Sign in</button></form>"""
FLAG = "HERCULES{state_and_requests_tell_the_story}"


class Lab(BaseHTTPRequestHandler):
    server_version = "AtlasLab/1.0"
    sys_version = ""

    def log_message(self, *_):
        pass

    def send(self, status, body="", headers=None, content_type="text/html; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Hercules-Lab", "disposable")
        if state["remediated"]:
            self.send_header("Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'")
            self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        route = urlsplit(self.path).path
        if self.server.server_port == 8080:
            self.send(302, "Redirect to the lab TLS endpoint.", {"Location": f"https://{ADDRESS}:8443/login"})
        elif route in ("/", "/login"):
            self.send(200, LOGIN)
        elif route == "/robots.txt":
            self.send(200, "User-agent: *\nDisallow: /debug\nDisallow: /api/draft\n", content_type="text/plain")
        elif route == "/debug":
            self.send(404 if state["remediated"] else 200,
                      "Not found" if state["remediated"] else json.dumps({"build": "lab-2026.10", "debug": True, "environment": "disposable", "credentials": "none"}), content_type="application/json")
        elif route in ("/admin", "/admin/"):
            self.send(403, "Access denied. No credentials or administrative access supplied.")
        elif route == "/health":
            self.send(200, json.dumps({"status": "ok", "remediated": state["remediated"]}), content_type="application/json")
        elif route == "/dashboard":
            self.send(200 if "atlas-session=lab-reviewer" in self.headers.get("Cookie", "") else 401,
                      "<h1>Dashboard</h1><p>Signed in as the disposable lab reviewer.</p>" if "atlas-session=lab-reviewer" in self.headers.get("Cookie", "") else "Sign in first")
        elif route == "/ctf":
            self.send(200, "<h1>Draft room</h1><p>Look at robots.txt and the browser state before guessing routes.</p><a href='/ctf/bootstrap'>Prepare a draft session</a>")
        elif route == "/ctf/bootstrap":
            self.send(200, "<h1>Draft session ready</h1><p>The draft API expects its route token as a request header, not a query parameter.</p><code>X-Draft-Route: atlas-7</code>", {"Set-Cookie": "ctf-session=atlas-reader; HttpOnly; SameSite=Lax; Path=/"})
        elif route == "/api/draft":
            cookie = self.headers.get("Cookie", "")
            header = self.headers.get("X-Draft-Route", "")
            if "ctf-session=atlas-reader" not in cookie:
                self.send(401, json.dumps({"error": "draft session missing"}), content_type="application/json")
            elif header != "atlas-7":
                self.send(400, json.dumps({"error": "route header missing"}), content_type="application/json")
            else:
                self.send(200, json.dumps({"flag": FLAG, "sha256": hashlib.sha256(FLAG.encode()).hexdigest()}), content_type="application/json")
        elif route == "/slow":
            import time
            time.sleep(2)
            self.send(200, "<h1>Slow service</h1><p>The request eventually completed.</p>")
        else:
            # Ordinary 404s let investigators reject scanner guesses.
            self.send(404, "<h1>Not found</h1><p>This route is absent from the lab.</p>")

    def do_POST(self):
        route = urlsplit(self.path).path
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
        if route == "/login":
            form = parse_qs(body)
            valid = form.get("email") == ["reviewer@lab.test"] and form.get("password") == ["lab-only-password"]
            self.send(303 if valid else 401, "Disposable lab authentication." if valid else "Credentials rejected",
                      {"Location": "/dashboard", "Set-Cookie": "atlas-session=lab-reviewer; HttpOnly; SameSite=Lax; Path=/"} if valid else {})
        elif route == "/lab-control/remediate":
            # This service is confined to the internal fixture network. Only a
            # deterministic lab configuration is changed, never a real website.
            state["remediated"] = True
            self.send(200, json.dumps(state), content_type="application/json")
        else:
            self.send(404, "Not found")


def dns_server():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind(("0.0.0.0", 53))
    while True:
        data, address = udp.recvfrom(4096)
        try:
            cursor = 12
            while data[cursor]:
                cursor += data[cursor] + 1
            end = cursor + 5
            qtype = struct.unpack("!H", data[cursor + 1:cursor + 3])[0]
            answer = b""
            if qtype == 1:
                answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton(ADDRESS)
            reply = data[:2] + struct.pack("!HHHHH", 0x8180, 1, bool(answer), 0, 0) + data[12:end] + answer
            udp.sendto(reply, address)
        except (IndexError, ValueError, struct.error):
            pass


# Each transaction gets a different internal subnet. Generate only its local
# fixture certificate; this never modifies host or browser trust stores.
subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", "/lab/tls/key.pem", "-out", "/lab/tls/cert.pem",
                "-days", "30", "-subj", "/CN=lab", "-addext",
                f"subjectAltName=DNS:lab,IP:{ADDRESS}"], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
threading.Thread(target=dns_server, daemon=True).start()
for port in (8000, 8080, 8443):
    server = ThreadingHTTPServer(("0.0.0.0", port), Lab)
    if port == 8443:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("/lab/tls/cert.pem", "/lab/tls/key.pem")
        server.socket = context.wrap_socket(server.socket, server_side=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
print("Disposable lab services ready", flush=True)
threading.Event().wait()
