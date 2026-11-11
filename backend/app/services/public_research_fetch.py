"""Bounded public-web fetches pinned to validated DNS addresses."""
from __future__ import annotations

import ipaddress
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit

import certifi
import requests
import urllib3

MAX_BYTES = 2_000_000
MAX_REDIRECTS = 4


def _destination(url: str) -> tuple[str, str, int, str, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("Invalid public research URL")
    host = parsed.hostname
    port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    if port != (443 if parsed.scheme == "https" else 80):
        raise ValueError("Non-web research port")
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("Research hostname has no addresses")
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        # Transition mechanisms can embed an internal IPv4 destination in global IPv6.
        if not address.is_global or address.is_multicast or address.is_reserved or (address.version == 6 and (
            address.ipv4_mapped is not None or address.sixtofour is not None
            or address.teredo is not None or address in ipaddress.ip_network("64:ff9b::/96")
            or address in ipaddress.ip_network("64:ff9b:1::/48")
        )):
            raise ValueError("Non-public research destination")
    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query
    return parsed.scheme, host, port, addresses[0][4][0], target


def fetch_public_text(url: str, *, timeout: float = 12) -> tuple[str, int]:
    deadline = time.monotonic() + timeout
    try:
        for hop in range(MAX_REDIRECTS + 1):
            scheme, host, port, address, target = _destination(url)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError("Research fetch deadline exceeded")
            options = {"host": address, "port": port, "maxsize": 1}
            if scheme == "https":
                pool = urllib3.HTTPSConnectionPool(
                    **options, assert_hostname=host, server_hostname=host,
                    ssl_context=ssl.create_default_context(cafile=certifi.where()),
                )
            else:
                pool = urllib3.HTTPConnectionPool(**options)
            response = None
            try:
                response = pool.urlopen(
                    "GET", target, headers={
                        "Host": f"[{host}]" if ":" in host else host,
                        "User-Agent": "Mozilla/5.0 OPTIME Decision Evidence/1.0",
                    }, redirect=False, retries=False, preload_content=False,
                    timeout=urllib3.Timeout(connect=min(5, remaining), read=remaining, total=remaining),
                )
                if response.status in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location")
                    if not location or hop == MAX_REDIRECTS:
                        raise ValueError("Invalid or excessive research redirects")
                    url = urljoin(url, location)
                    continue
                body = bytearray()
                while True:
                    if time.monotonic() >= deadline:
                        raise ValueError("Research fetch deadline exceeded")
                    chunk = response.read(min(65536, MAX_BYTES + 1 - len(body)), decode_content=True)
                    if not chunk:
                        break
                    body.extend(chunk)
                    if len(body) > MAX_BYTES:
                        raise ValueError("Research response exceeds size limit")
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError:
                    encoding = requests.utils.get_encoding_from_headers(response.headers) or "utf-8"
                    text = body.decode(encoding, errors="replace")
                return text, int(response.status)
            finally:
                if response is not None:
                    response.close()
                pool.close()
    except (ValueError, OSError, LookupError, urllib3.exceptions.HTTPError) as error:
        raise requests.RequestException(f"Public research fetch rejected: {error}") from error
    raise requests.RequestException("Public research fetch failed")
