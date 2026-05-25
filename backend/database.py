import os
import sqlite3
from pathlib import Path

# DB_PATH env var lets Railway (or any deployment) point to a persistent volume.
# Locally falls back to the backend directory.
_default = str(Path(__file__).parent / "breakoutstocks.db")
DB_PATH = Path(os.getenv("DB_PATH", _default))

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL UNIQUE,
            added_at TEXT DEFAULT (datetime('now')),
            original_bps REAL,
            original_pattern TEXT,
            entry_zone TEXT,
            stop REAL,
            target_1 REAL,
            last_status TEXT DEFAULT 'STILL_VALID'
        );
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            signal_type TEXT,
            entry_price REAL,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            bps_at_signal REAL,
            pattern_context TEXT
        );
        CREATE TABLE IF NOT EXISTS backtest_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            start_date TEXT,
            end_date TEXT,
            ran_at TEXT DEFAULT (datetime('now')),
            summary_json TEXT
        );
        CREATE TABLE IF NOT EXISTS news_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            headline TEXT,
            source TEXT,
            url TEXT,
            sentiment TEXT DEFAULT 'neutral',
            published_at TEXT,
            fetched_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS default_tickers (
            ticker TEXT PRIMARY KEY,
            added_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS fundamentals_cache (
            ticker TEXT PRIMARY KEY,
            data_json TEXT NOT NULL,
            cached_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS paper_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            entry_price REAL NOT NULL,
            shares REAL NOT NULL,
            stop_loss REAL,
            target_1 REAL,
            target_2 REAL,
            entry_date TEXT DEFAULT (date('now')),
            exit_price REAL,
            exit_date TEXT,
            status TEXT DEFAULT 'OPEN',
            pnl_usd REAL,
            pnl_pct REAL,
            notes TEXT
        );
        CREATE TABLE IF NOT EXISTS scan_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scanned_at TEXT DEFAULT (datetime('now')),
            tickers_json TEXT,
            results_json TEXT NOT NULL,
            trigger TEXT DEFAULT 'manual'
        );
    """)
    conn.commit()

    # Seed default tickers if table is empty
    DEFAULT_TICKERS = [
        "NVDA","AAPL","MSFT","AMZN","GOOGL","GOOG","AVGO","META","TSLA","BRK.B",
        "WMT","LLY","JPM","XOM","JNJ","V","COST","MA","ORCL","MU","NFLX","CVX",
        "ABBV","BAC","PLTR","AMD","CAT","PG","HD","KO","CSCO","GE","MRK","AMAT",
        "LRCX","MS","RTX","GS","UNH","WFC","PM","INTC","GEV","LIN","IBM","TMUS",
        "MCD","PEP","VZ","AXP","C","KLAC","T","NEE","AMGN","TMO","ABT","TJX",
        "TXN","GILD","CRM","DIS","ISRG","BA","PFE","SCHW","APH","COP","ANET",
        "ADI","DE","BLK","UBER","HON","UNP","LMT","ETN","WELL","QCOM","DHR",
        "BKNG","LOW","APP","PANW","CB","SPGI","BMY","SYK","PLD","NEM","GLW",
        "ACN","INTU","PH","COF","VRTX","PGR","MDT","MO","DELL",
    ]
    existing = conn.execute("SELECT COUNT(*) FROM default_tickers").fetchone()[0]
    if existing == 0:
        conn.executemany("INSERT OR IGNORE INTO default_tickers (ticker) VALUES (?)",
                         [(t,) for t in DEFAULT_TICKERS])
        conn.commit()
    conn.close()
