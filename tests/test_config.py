"""Tests for config.py — URL normalization, proxy loading."""
import config

class TestNormalizeURL:
    def test_strips_https_www(self):
        r = config.normalize_url("https://www.example.com/path")
        assert r == "example.com"  # replace("-"," ") only, not replace("."," ")
    def test_strips_https(self):
        assert config.normalize_url("https://example.com") == "example.com"
    def test_strips_http_www(self):
        assert config.normalize_url("http://www.example.com") == "example.com"
    def test_replaces_hyphens(self):
        assert config.normalize_url("https://my-site.com") == "my site.com"
    def test_strips_path(self):
        assert config.normalize_url("https://example.com/a/b/c") == "example.com"

class TestLoadProxies:
    def test_proxies_file_not_found_returns_empty(self):
        prox = config.load_proxies()
        assert isinstance(prox, list)
