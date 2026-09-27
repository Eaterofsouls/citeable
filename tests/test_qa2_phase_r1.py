"""Phase R1 Regression Suite: Security and Boundary Hardening (TR-101 to TR-105)."""
import ipaddress
import pytest
import requests
from unittest.mock import patch, MagicMock
from pathlib import Path

from areos.util.ssrf import TargetIPAdapter, safe_get, resolve_and_validate, SSRF_DENYLIST
from areos.auditors.sitemap_auditor import _parse_sitemap_xml


class TestR1SSRFAndSecurity:
    """Tests for SSRF TargetIPAdapter, DNS rebinding defense, and IP validation."""

    def test_ssrf_target_ip_adapter_pins_connection(self):
        """Verify TargetIPAdapter sets assert_hostname and server_hostname for SNI."""
        adapter = TargetIPAdapter(target_ip="93.184.216.34", original_host="example.com")
        assert adapter.target_ip == "93.184.216.34"
        assert adapter.original_host == "example.com"
        with patch("areos.util.ssrf.PoolManager") as mock_pm:
            adapter.init_poolmanager(connections=10, maxsize=10, block=False)
            mock_pm.assert_called_once()
            _, kwargs = mock_pm.call_args
            assert kwargs["assert_hostname"] == "example.com"
            assert kwargs["server_hostname"] == "example.com"

    def test_ssrf_rejects_cloud_imds_and_private_ips(self):
        """Verify resolve_and_validate rejects private and cloud metadata IPs."""
        for bad_ip in ["169.254.169.254", "127.0.0.1", "10.0.0.1", "172.16.0.1", "192.168.1.1"]:
            with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", (bad_ip, 0))]):
                with pytest.raises(ValueError, match="restricted address"):
                    resolve_and_validate("evil.com")

    def test_ssrf_safe_get_stream_boundary_check(self):
        """Verify safe_get enforces max_bytes limit."""
        with patch("areos.util.ssrf.resolve_and_validate", return_value="93.184.216.34"):
            with patch("requests.Session.get") as mock_get:
                mock_resp = MagicMock()
                mock_resp.is_redirect = False
                mock_resp.iter_content.return_value = [b"A" * 1024, b"B" * 1024]
                mock_get.return_value = mock_resp
                with pytest.raises(ValueError, match="exceeds"):
                    safe_get("http://example.com", max_bytes=1500)

    def test_ssrf_rejects_octal_loopback(self):
        """Verify resolve_and_validate raises ValueError for octal-encoded loopback (0177.0.0.1)."""
        with pytest.raises(ValueError):
            resolve_and_validate("0177.0.0.1")

    def test_ssrf_rejects_hex_loopbacks(self):
        """Verify resolve_and_validate raises ValueError for hex-encoded loopbacks (0x7f.0.0.1 and 0x7f000001)."""
        for hex_ip in ["0x7f.0.0.1", "0x7f000001"]:
            with pytest.raises(ValueError):
                resolve_and_validate(hex_ip)

    def test_ssrf_rejects_ipv6_loopback(self):
        """Verify resolve_and_validate raises ValueError for IPv6 loopback (::1)."""
        with pytest.raises(ValueError):
            resolve_and_validate("::1")

    def test_ssrf_rejects_ipv6_mapped_ipv4_private(self):
        """Verify resolve_and_validate raises ValueError for IPv6-mapped IPv4 private address (::ffff:127.0.0.1)."""
        with pytest.raises(ValueError):
            resolve_and_validate("::ffff:127.0.0.1")

    def test_ssrf_redirect_chain_blocks_before_second_hop(self):
        """Verify redirect chain with private target raises before following the second hop."""
        import areos.util.ssrf as ssrf_mod
        r1 = requests.Response()
        r1.status_code = 302
        r1.headers["Location"] = "http://127.0.0.1/admin"

        orig_resolve = ssrf_mod.resolve_and_validate

        def mock_resolve(domain):
            if domain == "public.example.com":
                return "93.184.216.34"
            return orig_resolve(domain)

        with patch("requests.Session.get", return_value=r1) as mock_get:
            with patch("areos.util.ssrf.resolve_and_validate", side_effect=mock_resolve):
                with pytest.raises(ValueError, match="restricted address"):
                    safe_get("http://public.example.com/start")
                assert mock_get.call_count == 1


class TestR1SitemapBounds:
    """Tests for sitemap URL count capping."""

    def test_sitemap_xml_caps_at_50k_urls(self):
        """Verify standard urlset caps at exactly 50,000 URLs."""
        urls_xml = "".join([f"<url><loc>https://example.com/page{i}</loc></url>" for i in range(50050)])
        xml = f"<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{urls_xml}</urlset>"
        urls, _ = _parse_sitemap_xml(xml)
        assert len(urls) == 50000

    def test_sitemap_index_caps_at_50k_urls(self):
        """Verify sitemapindex caps at exactly 50,000 URLs."""
        sitemaps_xml = "".join([f"<sitemap><loc>https://example.com/sitemap{i}.xml</loc></sitemap>" for i in range(50050)])
        xml = f"<sitemapindex xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{sitemaps_xml}</sitemapindex>"
        urls, _ = _parse_sitemap_xml(xml)
        assert len(urls) == 50000


class TestR1FrontendXSSProtection:
    """Tests for DOM sanitization in UI scripts."""

    def test_app_js_escapes_statement_xss(self):
        app_js = Path("areos/ui/app.js").read_text(encoding="utf-8")
        assert "const formatStatement = (" in app_js
        assert "escapeHtml(text)" in app_js

    def test_studio_js_escapes_error_stack_and_domain(self):
        studio_js = Path("areos/ui/studio.js").read_text(encoding="utf-8")
        assert "escapeHtml(err.stack" in studio_js
        assert "escapeHtml(domain)" in studio_js

    def test_nav_js_escapes_cmdk_claim_fields(self):
        nav_js = Path("areos/ui/nav.js").read_text(encoding="utf-8")
        assert "safeKid" in nav_js
        assert "safeStmt" in nav_js
