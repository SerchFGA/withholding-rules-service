"""Pruebas de app.fetch: sin red real, con httpx.MockTransport y un resolver falso."""
import hashlib
import socket

import httpx
import pytest

from app import fetch as fetch_mod
from app.fetch import Fetched, FetchError, fetch
from app.models import Deadline, DeadlineExceeded

PUBLIC_IP = "93.184.216.34"


def make_resolver(table=None):
    """Resolver falso: cada host va a la IP de la tabla, o a una pública."""
    table = table or {}

    def resolver(host, port, *args, **kwargs):
        ip = table.get(host, PUBLIC_IP)
        family = socket.AF_INET6 if ":" in ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (ip, port))]

    return resolver


def make_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def forbidden(request):
    raise AssertionError(f"no debió salir ninguna petición: {request.url}")


def test_fetch_returns_content_and_hash():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=b"%PDF-1.7 hola", headers={"content-type": "application/pdf"})

    got = fetch("https://example.org/doc.pdf", Deadline.start(), make_client(handler), make_resolver())
    assert isinstance(got, Fetched)
    assert got.content == b"%PDF-1.7 hola"
    assert got.content_type == "application/pdf"
    assert got.sha256 == hashlib.sha256(b"%PDF-1.7 hola").hexdigest()
    assert got.url == "https://example.org/doc.pdf"
    assert "Mozilla" in seen[0].headers["user-agent"]
    assert "*/*" in seen[0].headers["accept"]


@pytest.mark.parametrize("url", [
    "http://example.org/doc.pdf",
    "ftp://example.org/doc.pdf",
    "file:///etc/passwd",
    "https:///sin-host",
])
def test_rejects_non_https(url):
    with pytest.raises(FetchError):
        fetch(url, Deadline.start(), make_client(forbidden), make_resolver())


@pytest.mark.parametrize("ip", [
    "10.0.0.5", "172.16.3.1", "192.168.1.10",   # privadas
    "127.0.0.1", "::1",                          # loopback
    "169.254.169.254", "fe80::1",                # link-local (metadatos de nube)
    "240.0.0.1", "0.0.0.0",                      # reservada y sin especificar
    "::ffff:127.0.0.1", "::ffff:10.0.0.1",       # IPv4 disfrazada de IPv6
    "fc00::1", "100.64.0.1",                     # local única y CGNAT
])
def test_rejects_host_resolving_to_internal_ip(ip):
    resolver = make_resolver({"interno.example.org": ip})
    with pytest.raises(FetchError):
        fetch("https://interno.example.org/x", Deadline.start(), make_client(forbidden), resolver)


def test_rejects_when_any_resolved_address_is_internal():
    def resolver(host, port, *args, **kwargs):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", port))]

    with pytest.raises(FetchError):
        fetch("https://mixto.example.org/x", Deadline.start(), make_client(forbidden), resolver)


@pytest.mark.parametrize("url", ["https://127.0.0.1/x", "https://[::1]/x", "https://169.254.169.254/latest"])
def test_rejects_literal_internal_ip_with_default_resolver(url):
    # IP literal: socket.getaddrinfo no sale a la red.
    with pytest.raises(FetchError):
        fetch(url, Deadline.start(), make_client(forbidden))


def test_rejects_unresolvable_host():
    def resolver(host, port, *args, **kwargs):
        raise socket.gaierror("no existe")

    with pytest.raises(FetchError):
        fetch("https://nada.example.org/x", Deadline.start(), make_client(forbidden), resolver)


def test_follows_redirect_and_validates_each_hop():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b"})
        return httpx.Response(200, content=b"<html>ok</html>", headers={"content-type": "text/html"})

    got = fetch("https://example.org/a", Deadline.start(), make_client(handler), make_resolver())
    assert calls == ["https://example.org/a", "https://example.org/b"]
    assert got.url == "https://example.org/b"
    assert got.content == b"<html>ok</html>"


@pytest.mark.parametrize("location", [
    "https://interno.example.org/secreto",   # host que resuelve a IP privada
    "https://192.168.0.1/admin",             # IP privada literal
    "http://example.org/plano",              # baja a http
])
def test_rejects_redirect_to_forbidden_target(location):
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(301, headers={"location": location})

    resolver = make_resolver({"interno.example.org": "10.1.2.3", "192.168.0.1": "192.168.0.1"})
    with pytest.raises(FetchError):
        fetch("https://example.org/a", Deadline.start(), make_client(handler), resolver)
    assert calls == ["https://example.org/a"]


def test_stops_after_five_redirects():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(302, headers={"location": f"/r{len(calls)}"})

    with pytest.raises(FetchError):
        fetch("https://example.org/r0", Deadline.start(), make_client(handler), make_resolver())
    assert len(calls) == 6   # la original más cinco saltos


def test_size_cap_is_enforced_while_reading(monkeypatch):
    monkeypatch.setattr(fetch_mod, "MAX_BYTES", 5_000)
    produced = []

    def body():
        for _ in range(100):
            produced.append(1)
            yield b"x" * 1_000

    def handler(request):
        return httpx.Response(200, content=body())   # sin Content-Length

    with pytest.raises(FetchError):
        fetch("https://example.org/grande", Deadline.start(), make_client(handler), make_resolver())
    assert len(produced) < 100   # se cortó al leer, no después


def test_size_cap_rejects_declared_length(monkeypatch):
    monkeypatch.setattr(fetch_mod, "MAX_BYTES", 5_000)

    def handler(request):
        return httpx.Response(200, content=b"x" * 6_000)

    with pytest.raises(FetchError):
        fetch("https://example.org/grande", Deadline.start(), make_client(handler), make_resolver())


def test_default_size_cap_is_30_mb():
    assert fetch_mod.MAX_BYTES == 30 * 1024 * 1024


def test_content_at_cap_is_accepted(monkeypatch):
    monkeypatch.setattr(fetch_mod, "MAX_BYTES", 5_000)

    def handler(request):
        return httpx.Response(200, content=b"x" * 5_000)

    got = fetch("https://example.org/justo", Deadline.start(), make_client(handler), make_resolver())
    assert len(got.content) == 5_000


def test_expired_deadline_raises_before_any_request():
    deadline = Deadline(expires_at=0.0, clock=lambda: 10.0)
    with pytest.raises(DeadlineExceeded):
        fetch("https://example.org/a", deadline, make_client(forbidden), make_resolver())


def test_attempt_timeout_is_min_of_remaining_and_30():
    seen = []

    def handler(request):
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, content=b"ok")

    client = make_client(handler)
    fetch("https://example.org/a", Deadline(expires_at=100.0, clock=lambda: 0.0), client, make_resolver())
    fetch("https://example.org/a", Deadline(expires_at=7.0, clock=lambda: 0.0), client, make_resolver())
    assert seen[0]["read"] == 30 and seen[0]["connect"] == 30
    assert seen[1]["read"] == 7 and seen[1]["connect"] == 7


def test_deadline_expiring_mid_download_raises_deadline_exceeded():
    now = [0.0]

    def body():
        for _ in range(10):
            now[0] += 50.0   # cada trozo "tarda" 50 s
            yield b"x" * 10

    def handler(request):
        return httpx.Response(200, content=body())

    deadline = Deadline(expires_at=120.0, clock=lambda: now[0])
    with pytest.raises(DeadlineExceeded):
        fetch("https://example.org/lento", deadline, make_client(handler), make_resolver())


def test_timeout_from_transport_with_expired_deadline_is_deadline_exceeded():
    now = [0.0]

    def handler(request):
        now[0] = 500.0
        raise httpx.ReadTimeout("lento", request=request)

    deadline = Deadline(expires_at=120.0, clock=lambda: now[0])
    with pytest.raises(DeadlineExceeded):
        fetch("https://example.org/lento", deadline, make_client(handler), make_resolver())


def test_http_error_status_is_fetch_error():
    def handler(request):
        return httpx.Response(404, content=b"no")

    with pytest.raises(FetchError) as info:
        fetch("https://example.org/a", Deadline.start(), make_client(handler), make_resolver())
    assert "404" in str(info.value)


SECRET_URL = "https://user:hunter2@example.org/doc.pdf?token=SECRETO123&amount=12000#frag"


def assert_safe(error):
    text = f"{error} {error!r} {error.__cause__!r} {error.__context__!r}"
    for leaked in ("SECRETO123", "token", "12000", "hunter2", "user:", "?"):
        assert leaked not in text


def test_error_message_has_no_query_string_or_credentials():
    def status(request):
        return httpx.Response(500, content=b"boom")

    def network(request):
        raise httpx.ConnectError(f"fallo al conectar con {request.url}", request=request)

    def redirect(request):
        return httpx.Response(302, headers={"location": "http://example.org/x?token=SECRETO123"})

    for handler in (status, network, redirect):
        with pytest.raises(FetchError) as info:
            fetch(SECRET_URL, Deadline.start(), make_client(handler), make_resolver())
        assert_safe(info.value)
        assert "example.org" in str(info.value)

    with pytest.raises(FetchError) as info:
        fetch(SECRET_URL.replace("https", "http"), Deadline.start(), make_client(forbidden), make_resolver())
    assert_safe(info.value)

    with pytest.raises(FetchError) as info:
        fetch(SECRET_URL, Deadline.start(), make_client(forbidden), make_resolver({"example.org": "10.0.0.1"}))
    assert_safe(info.value)
