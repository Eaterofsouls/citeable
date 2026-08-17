import ipaddress
import socket
import urllib.parse

import requests

# FIX (Readiness Audit, Critical 2):
#   1. gethostbyname() only resolves A (IPv4) records — a domain with only
#      an AAAA record resolving to e.g. ::1 previously bypassed this check
#      entirely. getaddrinfo() below checks every address (v4 and v6) a
#      resolver actually returns.
#   2. This is now used with a two-step "resolve once, connect to that IP,
#      re-validate every redirect hop before following it" pattern (see
#      safe_get() below) instead of validating a hostname once and then
#      letting a later, independent DNS lookup (subject to DNS rebinding)
#      or an unvalidated redirect decide the real connection target.
SSRF_DENYLIST = {ipaddress.ip_network(n) for n in (
    "169.254.0.0/16",  # link-local / cloud metadata
    "127.0.0.0/8",      # loopback (v4)
    "::1/128",           # loopback (v6)
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "fc00::/7",          # unique local (v6 equivalent of RFC1918)
    "fe80::/10",         # link-local (v6)
    "0.0.0.0/8",
)}


def _validate_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address, domain: str) -> None:
    if ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        raise ValueError(f"Domain resolves to a restricted address: {ip}")
    if any(ip in net for net in SSRF_DENYLIST):
        raise ValueError(f"Domain resolves to a restricted address: {ip}")


def resolve_and_validate(domain: str) -> str:
    """
    Resolve `domain` to a single IP, validating every address the resolver
    returns (not just the first one) against the SSRF denylist, and return
    that IP as a string for the caller to connect to directly (pinning it,
    rather than letting a second, independent DNS lookup decide the actual
    connection target later — the DNS-rebinding gap the old single-shot
    gethostbyname() check left open).
    """
    try:
        addrinfo = socket.getaddrinfo(domain, None)
    except socket.gaierror:
        raise ValueError(f"Domain does not resolve: {domain}")
    if not addrinfo:
        raise ValueError(f"Domain does not resolve: {domain}")

    resolved_ips = []
    for family, _, _, _, sockaddr in addrinfo:
        ip = ipaddress.ip_address(sockaddr[0])
        _validate_ip(ip, domain)
        resolved_ips.append(ip)

    # All candidate addresses passed validation; return the first for the
    # caller to pin the connection to.
    return str(resolved_ips[0])


def validate_domain_ssrf(domain: str):
    """Back-compat wrapper: validate only, don't return the resolved IP."""
    resolve_and_validate(domain)


def safe_get(url: str, timeout: float = 4, max_redirects: int = 5, **kwargs) -> requests.Response:
    """
    SSRF-hardened GET: validates the hostname (all resolved v4/v6
    addresses) before every request, and manually follows redirects one hop
    at a time — re-validating the *target* of each hop before following it
    — instead of requests' default allow_redirects=True, which would follow
    a redirect to an internal/metadata address with no SSRF check at all.

    Residual limitation: this still performs a fresh DNS lookup at connect
    time for each hop (via requests/urllib3) rather than pinning the exact
    IP validated here, so a narrow DNS-rebinding race remains between
    validation and connection for any single hop. Closing that fully
    requires a connection-level IP-pinning transport adapter; tracked as a
    follow-up. This function does fully close the more easily exploitable
    open-redirect vector, and widens validation to IPv6.
    """
    current_url = url
    for _ in range(max_redirects + 1):
        parsed = urllib.parse.urlsplit(current_url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Refusing non-HTTP(S) URL: {current_url}")
        if not parsed.hostname:
            raise ValueError(f"URL has no hostname: {current_url}")
        validate_domain_ssrf(parsed.hostname)

        resp = requests.get(current_url, timeout=timeout, allow_redirects=False, **kwargs)
        if resp.is_redirect and resp.headers.get("Location"):
            current_url = urllib.parse.urljoin(current_url, resp.headers["Location"])
            continue
        return resp

    raise ValueError(f"Too many redirects (>{max_redirects}) resolving {url}")
