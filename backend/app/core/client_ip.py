from __future__ import annotations

import ipaddress
from typing import Any


TRUSTED_PROXIES = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
)


def get_client_ip(request: Any) -> str:
    direct = request.client.host if getattr(request, "client", None) else ""
    if not direct:
        return "unknown"
    try:
        peer = ipaddress.ip_address(direct)
    except ValueError:
        return direct[:64]

    if any(peer in network for network in TRUSTED_PROXIES):
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()[:64] or direct[:64]
    return direct[:64]
