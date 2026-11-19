"""Descarga una publicación por URL con defensas contra SSRF. Lo descargado es dato, nunca instrucción."""
import hashlib
import ipaddress
import socket
import ssl
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx
from app.models import Deadline

MAX_BYTES = 30 * 1024 * 1024
MAX_REDIRECTS = 5
ATTEMPT_TIMEOUT = 30.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "application/pdf,text/html,application/xhtml+xml,image/*,*/*;q=0.8",
}


class FetchError(Exception):
    """Fallo de descarga. El mensaje nunca lleva query string ni credenciales."""


@dataclass(frozen=True)
class Fetched:
    url: str            # la URL final, después de redirecciones
    content: bytes
    content_type: str
    sha256: str


def _safe(url: str) -> str:   # sin usuario, clave, query ni fragmento: lo único que va a un mensaje
    try:
        parts = urlsplit(url)
        return f"{parts.scheme}://{parts.hostname or ''}{parts.path}"
    except ValueError:
        return "(URL ilegible)"


def _check_url(url: str, resolver) -> str:
    """Exige https y que ninguna dirección del host sea interna. Devuelve la URL segura para mensajes."""
    safe = _safe(url)
    try:
        parts = urlsplit(url)
        target = (parts.hostname, parts.port or 443) if parts.scheme == "https" and parts.hostname else None
    except ValueError:
        target = None
    if not target:
        raise FetchError(f"solo se admite https: {safe}")
    try:
        addresses = [ipaddress.ip_address(info[4][0]) for info in resolver(*target, type=socket.SOCK_STREAM)]
    except (OSError, ValueError):
        addresses = []
    if not addresses:
        raise FetchError(f"no se pudo resolver el host: {safe}")
    for ip in addresses:
        ip = getattr(ip, "ipv4_mapped", None) or ip
        if not ip.is_global or ip.is_multicast:   # privadas, loopback, link-local, reservadas, CGNAT
            raise FetchError(f"el host resuelve a una dirección interna: {safe}")
    return safe


def fetch(url: str, deadline: Deadline, client: httpx.Client | None = None, resolver=None) -> Fetched:
    if client is None:
        with httpx.Client(verify=ssl.create_default_context()) as own:   # almacén del sistema
            return fetch(url, deadline, own, resolver)
    for _ in range(MAX_REDIRECTS + 1):
        deadline.check()
        safe = _check_url(url, resolver or socket.getaddrinfo)
        timeout = min(deadline.remaining(), ATTEMPT_TIMEOUT)
        try:
            with client.stream("GET", url, headers=HEADERS, timeout=timeout, follow_redirects=False) as response:
                if response.has_redirect_location:
                    url = urljoin(url, response.headers["location"])
                    continue
                if response.status_code != 200:
                    raise FetchError(f"HTTP {response.status_code}: {safe}")
                content = bytearray()
                for chunk in response.iter_bytes():
                    deadline.check()
                    content += chunk
                    if len(content) > MAX_BYTES:   # se corta al leer, sin esperar al final
                        raise FetchError(f"el documento pasa de {MAX_BYTES} bytes: {safe}")
                content_type = response.headers.get("content-type", "")
                return Fetched(url, bytes(content), content_type, hashlib.sha256(content).hexdigest())
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            failure = type(exc).__name__   # el texto de httpx puede traer la URL entera
        deadline.check()   # fuera del except: la excepción original no queda encadenada
        raise FetchError(f"fallo de red ({failure}): {safe}")
    raise FetchError(f"más de {MAX_REDIRECTS} redirecciones: {_safe(url)}")
