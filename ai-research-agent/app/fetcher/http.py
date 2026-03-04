from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BLOCKED_NETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]
ALLOWED_CT = {"text/html", "text/plain", "application/json"}


def is_url_safe(url: str) -> bool:
    p = urlparse(url)
    if p.scheme not in {"http", "https"}:
        return False
    if not p.hostname:
        return False
    if p.hostname in {"localhost", "metadata.google.internal"}:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if any(ip in net for net in BLOCKED_NETS):
            return False
    return True


async def fetch_url(
    url: str,
    max_bytes: int,
    timeout_connect: float,
    timeout_read: float,
    user_agent: str = "AIResearchAgentDemo/1.0",
) -> dict:
    if not is_url_safe(url):
        return {"ok": False, "status": "blocked", "error": "unsafe url"}
    try:
        req = Request(url, headers={"User-Agent": user_agent})
        with urlopen(req, timeout=timeout_connect + timeout_read) as r:  # noqa: S310
            ct = (r.headers.get("content-type", "").split(";")[0] or "").lower()
            final_url = r.geturl()
            if ct == "application/pdf" or str(final_url).lower().endswith(".pdf"):
                return {"ok": False, "status": "skipped", "error": "skipped PDF in demo mode"}
            if ct not in ALLOWED_CT:
                return {"ok": False, "status": "skipped", "error": f"unsupported content-type {ct}"}
            body = r.read(max_bytes + 1)
            if len(body) > max_bytes:
                body = body[:max_bytes]
        return {
            "ok": True,
            "status": "fetched",
            "url": str(final_url),
            "content": body.decode("utf-8", errors="ignore"),
            "content_type": ct,
            "bytes": len(body),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "status": "failed", "error": str(exc)}
