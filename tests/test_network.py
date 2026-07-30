"""Tests for network.py — HTTP parsing (mocked)."""
from unittest.mock import Mock, patch
import pytest
import network as net

class TestExtractVar:
    def test_extracts_simple_var(self):
        html = '<script>var MERCHANTID = "ABC123"; var x = 1;</script>'
        result = net._extract_var(html, "MERCHANTID")
        assert result == "ABC123"

    def test_extracts_merchant_name(self):
        html = '<script>var MERCHANTNAME = "Test Casino";</script>'
        result = net._extract_var(html, "MERCHANTNAME")
        assert result == "Test Casino"

class TestParseMerchantInfo:
    def test_parses_both_values(self):
        html = '<script>var MERCHANTID = "42"; var MERCHANTNAME = "Golden";</script>'
        mid, mname = net.parse_merchant_info(html)
        assert mid == "42"
        assert mname == "Golden"

class TestBuildAPIURL:
    def test_append_api_path(self):
        assert net.build_api_url("https://example.com") == "https://example.com/api/v1/index.php"
    def test_strips_trailing_slash(self):
        assert net.build_api_url("https://example.com/") == "https://example.com/api/v1/index.php"

class TestCheckIPReputation:
    @patch("network.requests.get")
    def test_no_key_returns_unknown(self, mock_get):
        score, ip = net.check_ip_reputation(None)
        assert score == 0
        assert ip == "Unknown"
        mock_get.assert_not_called()

    @patch("network.requests.get")
    def test_your_key_returns_unknown(self, mock_get):
        score, ip = net.check_ip_reputation("YOUR_KEY_HERE")
        assert score == 0
        assert ip == "Unknown"
        mock_get.assert_not_called()


class TestCreateSession:
    def test_no_proxy_creates_session(self):
        s = net.create_session()
        assert s is not None
        assert not hasattr(s, "proxies") or not s.proxies

    def test_with_proxy_sets_proxies(self):
        s = net.create_session(proxy="http://user:pass@1.2.3.4:8080")
        assert s is not None
        assert s.proxies.get("http") == "http://user:pass@1.2.3.4:8080"
        assert s.proxies.get("https") == "http://user:pass@1.2.3.4:8080"
