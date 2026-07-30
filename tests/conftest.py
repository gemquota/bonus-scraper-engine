import os, sys, tempfile, pytest

# Point to project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def temp_db():
    """Swap DB to a temp file for every test."""
    import db
    orig = db.DB_PATH
    tmp = tempfile.mktemp(suffix=".db")
    db.DB_PATH = tmp
    db._cache.clear()
    db.initialize_database()
    yield
    db._cache.clear()
    if os.path.exists(tmp): os.unlink(tmp)
    db.DB_PATH = orig

@pytest.fixture
def sample_bonus():
    return {
        "id": "123", "name": "Welcome Bonus 100%", "amount": "100",
        "rollover": "30", "minwithdraw": "50", "maxwithdraw": "500",
        "balance": "0", "claimconfig": "", "claimcondition": "2025-12-31",
        "bonus": "", "bonusrandom": "", "reset": "",
        "mintopup": "", "maxtopup": "", "referlink": "",
        "transactiontype": "deposit", "bonusfixed": "100",
    }

@pytest.fixture
def db_conn():
    import db
    return db.get_connection()
