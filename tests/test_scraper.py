"""Tests for scraper.py — error classification, bonus processing."""
from requests.exceptions import HTTPError
from unittest.mock import Mock
import scraper

class TestClassifyError:
    def test_http_error_returns_status_code(self):
        resp = Mock()
        resp.status_code = 403
        exc = HTTPError(response=resp)
        assert scraper.classify_error(exc) == 403

    def test_merchant_in_string_returns_201(self):
        exc = ValueError("MERCHANT error: not found")
        assert scraper.classify_error(exc) == 201

    def test_captcha_returns_202(self):
        exc = ValueError("Captcha detected")
        assert scraper.classify_error(exc) == 202

    def test_timeout_returns_104(self):
        exc = ConnectionError("Timeout reading")
        assert scraper.classify_error(exc) == 104

    def test_connection_refused_returns_101(self):
        exc = ConnectionError("Connection Refused")
        assert scraper.classify_error(exc) == 101

    def test_connection_error_returns_103(self):
        exc = ConnectionError("Connection problem")
        assert scraper.classify_error(exc) == 103

    def test_403_in_string_returns_403(self):
        exc = ValueError("403 Forbidden")
        assert scraper.classify_error(exc) == 403

    def test_login_returns_304(self):
        exc = ValueError("login failed")
        assert scraper.classify_error(exc) == 304

    def test_none_returns_302(self):
        exc = ValueError("None is not valid")
        assert scraper.classify_error(exc) == 302

    def test_default_returns_301(self):
        exc = ValueError("some random error")
        assert scraper.classify_error(exc) == 301

class TestProcessBonus:
    def test_new_bonus_creates_record(self, sample_bonus):
        fp = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        uid, is_new = scraper.process_bonus(sample_bonus, "TestCasino", "https://test.com", fp, 50.0, None)
        assert is_new == 1
        assert uid is not None

    def test_duplicate_fp_returns_existing(self, sample_bonus):
        fp = "dup_fingerprint_001"
        uid1, _ = scraper.process_bonus(sample_bonus, "TestCasino", "https://test.com", fp, 50.0, None)
        uid2, is_new = scraper.process_bonus(sample_bonus, "TestCasino", "https://test.com", fp, 50.0, None)
        assert is_new == 0
        assert uid1 == uid2
