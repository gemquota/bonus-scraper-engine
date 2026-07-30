"""Unit tests for db.py — data layer, filter math, search."""
import datetime, pytest
import db

class TestFloatValue:
    def test_float_parses_string(self):
        assert db.float_value("123.45") == 123.45
    def test_float_parses_int_string(self):
        assert db.float_value("100") == 100.0
    def test_float_returns_zero_for_none(self):
        assert db.float_value(None) == 0.0
    def test_float_returns_zero_for_garbage(self):
        assert db.float_value("abc") == 0.0
    def test_float_returns_value_direct(self):
        assert db.float_value(50.5) == 50.5

class TestFingerprintBonus:
    def test_fingerprint_is_sha256(self):
        fp = db.fingerprint_bonus({"name": "A", "amount": "100", "rollover": "30",
                                    "minwithdraw": "50", "maxwithdraw": "500"})
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)
    def test_fingerprint_differs_for_diff_bonuses(self):
        fp1 = db.fingerprint_bonus({"name": "A", "amount": "100", "rollover": "30",
                                     "minwithdraw": "50", "maxwithdraw": "500"})
        fp2 = db.fingerprint_bonus({"name": "B", "amount": "200", "rollover": "20",
                                     "minwithdraw": "30", "maxwithdraw": "300"})
        assert fp1 != fp2

class TestParseExpiry:
    def test_iso_date(self):
        r = db.parse_expiry("2025-12-31")
        assert r is not None
        assert r.year == 2025 and r.month == 12 and r.day == 31
    def test_slash_date(self):
        r = db.parse_expiry("31/12/2025")
        assert r is not None and r.year == 2025
    def test_short_slash_date(self):
        r = db.parse_expiry("25/12")
        assert r is not None and r.day == 25 and r.month == 12
    def test_none_returns_none(self):
        assert db.parse_expiry(None) is None
    def test_empty_returns_none(self):
        assert db.parse_expiry("") is None

class TestPerceivedValue:
    def test_zero_amount_returns_zero(self):
        assert db.perceived_value({"amount": "0"}) == 0.0
    def test_negative_amount_returns_zero(self):
        assert db.perceived_value({"amount": "-50"}) == 0.0
    def test_positive_amount_returns_positive(self, sample_bonus):
        pv = db.perceived_value(sample_bonus)
        assert pv > 0

class TestFuzzyMatch:
    def test_exact_match(self):
        assert db.is_fuzzy_match("Welcome Bonus", "Welcome Bonus")
    def test_close_match(self):
        assert db.is_fuzzy_match("Welcome Bonus 100%", "Welcome Bonus 100%")
    def test_different_names_no_match(self):
        assert not db.is_fuzzy_match("Apple", "Banana")
    def test_find_matching_name_finds(self):
        names = ["Welcome Bonus 100%", "First Deposit", "Loyalty Reward"]
        assert db.find_matching_name("Welcome Bonus 100%", names) == "Welcome Bonus 100%"
    def test_find_matching_name_not_found(self):
        names = ["First Deposit", "Loyalty Reward"]
        assert db.find_matching_name("Unknown Bonus", names) is None

class TestClean:
    def test_removes_html(self):
        assert db._clean("<b>Hello</b>") == "hello"
    def test_strips_and_lowercases(self):
        assert db._clean("  Hello World  ") == "hello world"
    def test_empty_returns_empty(self):
        assert db._clean("") == ""
    def test_none_returns_empty(self):
        assert db._clean(None) == ""

class TestSearch:
    def test_search_empty_db(self):
        assert db.search("bonus") == []

class TestDatabase:
    def test_execute_insert_and_select(self):
        db.execute("INSERT INTO t(u) VALUES (?)", ("https://test.com",))
        rows = db.execute("SELECT u FROM t")
        assert len(rows) == 1
        assert rows[0][0] == "https://test.com"
    def test_log_event(self):
        db.log_event("INFO", "test", "hello")
        rows = db.execute("SELECT lvl, src, msg FROM l")
        assert len(rows) == 1
        assert rows[0] == ("INFO", "test", "hello")
    def test_get_url_scores_empty(self):
        assert db.get_url_scores() == {}
