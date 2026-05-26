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
        real_ip = _public_header_ip(request.headers.get("x-real-ip"))
        if real_ip:
            return real_ip
        forwarded_for = request.headers.get("x-forwarded-for", "")
        forwarded_parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if len(forwarded_parts) == 1:
            forwarded_ip = _public_header_ip(forwarded_parts[0])
            if forwarded_ip:
                return forwarded_ip
    return direct[:64]


def _public_header_ip(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError:
        return None
    if parsed.is_private or parsed.is_loopback or parsed.is_link_local or parsed.is_reserved or parsed.is_multicast:
        return None
    return value[:64]
