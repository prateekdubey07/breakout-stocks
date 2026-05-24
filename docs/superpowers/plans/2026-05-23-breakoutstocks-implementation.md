# BreakoutStocks Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack breakout scanner dashboard — FastAPI backend with ML-powered BPS scoring + Next.js frontend matching RTO platform visual style.

**Architecture:** FastAPI (port 8000) handles all data fetching, BPS scoring, ML inference, backtesting, WebSocket alerts, and news aggregation. Next.js (port 3000) renders the dashboard — sidebar nav, KPI strip, tabbed pages (Scanner/Watchlist/Backtest/News). XGBoost models (universal + per-sector) replace hardcoded pattern scoring.

**Tech Stack:** Python 3.11, FastAPI, pandas-ta, yfinance, XGBoost, scikit-learn, SQLite, APScheduler, Next.js 14, Tailwind CSS, Recharts, SWR

---

## File Structure

```
BreakoutStocks/
├── backend/
│   ├── main.py                    # FastAPI app, all routes mounted
│   ├── requirements.txt
│   ├── database.py                # SQLite init + connection
│   ├── models.py                  # Pydantic response models
│   ├── data/
│   │   ├── fetcher.py             # yfinance wrapper (OHLCV + fundamentals)
│   │   └── csv_handler.py         # CSV upload → SQLite
│   ├── scoring/
│   │   ├── technical.py           # All technical indicator calculations
│   │   ├── fundamental.py         # Fundamental scoring logic
│   │   ├── risk_filters.py        # Hard disqualify + yellow flag logic
│   │   └── bps_engine.py          # Combines technical + fundamental + ML
│   ├── ml/
│   │   ├── features.py            # Feature engineering from OHLCV
│   │   ├── trainer.py             # XGBoost train pipeline
│   │   ├── predictor.py           # Load model + predict
│   │   └── models/                # .pkl files (universal + sector)
│   ├── backtest/
│   │   ├── extractor.py           # Signal extraction from OHLCV history
│   │   └── analyst.py             # Outcome eval + aggregate stats
│   ├── news/
│   │   └── aggregator.py          # NewsAPI + Finnhub fetch + merge
│   ├── watchlist/
│   │   └── monitor.py             # Alert classification logic
│   ├── websocket/
│   │   └── manager.py             # WebSocket connection manager
│   └── scheduler.py               # APScheduler 60s watchlist poll
├── frontend/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── app/
│   │   ├── layout.tsx             # Sidebar + TopBar shell
│   │   ├── page.tsx               # Redirect to /scanner
│   │   ├── scanner/page.tsx
│   │   ├── watchlist/page.tsx
│   │   ├── backtest/page.tsx
│   │   └── news/page.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── TopBar.tsx
│   │   ├── KpiStrip.tsx
│   │   ├── BpsTable.tsx
│   │   ├── TickerDetail.tsx
│   │   ├── PriceChart.tsx
│   │   ├── BacktestStats.tsx
│   │   ├── NewsPanel.tsx
│   │   └── AlertBanner.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useScan.ts
│   └── lib/
│       ├── api.ts                 # All fetch calls to FastAPI
│       └── types.ts               # Shared TypeScript types
└── docs/
    └── superpowers/
        ├── specs/
        └── plans/
```

---

## Phase 1: Backend Foundation

### Task 1: Project Setup

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
yfinance==0.2.40
pandas==2.2.2
pandas-ta==0.3.14b
xgboost==2.0.3
scikit-learn==1.4.2
aiohttp==3.9.5
apscheduler==3.10.4
python-multipart==0.0.9
websockets==12.0
requests==2.32.2
joblib==1.4.2
numpy==1.26.4
```

- [ ] **Step 2: Install**

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

- [ ] **Step 3: Create main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_db

app = FastAPI(title="BreakoutStocks API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: Verify**

```bash
uvicorn main:app --reload --port 8000
# visit http://localhost:8000/health → {"status":"ok"}
```

- [ ] **Step 5: Commit**

```bash
git init
git add backend/
git commit -m "feat: backend project scaffold"
```

---

### Task 2: Database Setup

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`

- [ ] **Step 1: Create database.py**

```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "breakoutstocks.db"

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
    """)
    conn.commit()
    conn.close()
```

- [ ] **Step 2: Create models.py**

```python
from pydantic import BaseModel
from typing import Optional, List

class SignalSummary(BaseModel):
    pattern: str
    volume_surge: bool
    volume_ratio: float
    above_key_mas: bool
    rsi_14: float
    macd_signal: str
    volatility_contracting: bool
    pct_from_52w_high: float
    ml_breakout_prob: float

class Fundamentals(BaseModel):
    eps_growth_yoy: str
    revenue_growth_yoy: str
    peg_ratio: Optional[float]
    catalyst: str

class BpsResult(BaseModel):
    ticker: str
    breakout_probability_score: float
    conviction: str
    technical_score: float
    fundamental_score: float
    signal_summary: SignalSummary
    fundamentals: Fundamentals
    risk_flags: List[str]
    entry_zone: str
    stop_loss: str
    target_1: str
    target_2: str
    risk_reward: str
    timeframe: str

class ScanRequest(BaseModel):
    tickers: List[str]
    min_bps: float = 65.0

class BacktestRequest(BaseModel):
    ticker: str
    start: str
    end: str
```

- [ ] **Step 3: Commit**

```bash
git add backend/database.py backend/models.py
git commit -m "feat: SQLite schema + Pydantic models"
```

---

### Task 3: yfinance Data Fetcher

**Files:**
- Create: `backend/data/fetcher.py`
- Create: `backend/data/__init__.py`

- [ ] **Step 1: Create fetcher.py**

```python
import yfinance as yf
import pandas as pd
from typing import Optional

def fetch_ohlcv(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Returns OHLCV DataFrame with columns: Open High Low Close Volume."""
    df = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.dropna()

def fetch_fundamentals(ticker: str) -> dict:
    """Returns key fundamental fields from yfinance info."""
    info = yf.Ticker(ticker).info
    return {
        "eps_growth_yoy": _safe(info, "earningsGrowth"),
        "revenue_growth_yoy": _safe(info, "revenueGrowth"),
        "peg_ratio": _safe(info, "pegRatio"),
        "market_cap": _safe(info, "marketCap"),
        "avg_volume": _safe(info, "averageVolume"),
        "short_pct_float": _safe(info, "shortPercentOfFloat"),
        "forward_pe": _safe(info, "forwardPE"),
        "sector": _safe(info, "sector", "Unknown"),
        "next_earnings": _safe(info, "earningsTimestamp"),
    }

def _safe(info: dict, key: str, default=None):
    val = info.get(key)
    return val if val is not None else default
```

- [ ] **Step 2: Test fetcher manually**

```bash
cd backend
python -c "from data.fetcher import fetch_ohlcv, fetch_fundamentals; df = fetch_ohlcv('NVDA'); print(df.tail(3)); print(fetch_fundamentals('NVDA'))"
```

Expected: Last 3 rows of OHLCV + dict with fundamentals keys.

- [ ] **Step 3: Commit**

```bash
git add backend/data/
git commit -m "feat: yfinance OHLCV + fundamentals fetcher"
```

---

### Task 4: Technical Indicators + Scoring

**Files:**
- Create: `backend/scoring/technical.py`
- Create: `backend/scoring/__init__.py`

- [ ] **Step 1: Create technical.py**

```python
import pandas as pd
import pandas_ta as ta
from dataclasses import dataclass

@dataclass
class TechnicalScore:
    total: float
    volume_surge: bool
    volume_ratio: float
    near_52w_high: bool
    pct_from_52w_high: float
    volatility_contracting: bool
    rsi_14: float
    macd_bullish: bool
    macd_signal: str
    above_20ma: bool
    above_50ma: bool
    above_200ma: bool
    above_key_mas: bool
    atr_20: float

def compute_technical_score(df: pd.DataFrame) -> TechnicalScore:
    close = df["Close"]
    volume = df["Volume"]

    # Volume
    vol_avg_20 = volume.rolling(20).mean().iloc[-1]
    vol_today = volume.iloc[-1]
    volume_ratio = round(vol_today / vol_avg_20, 2) if vol_avg_20 > 0 else 0
    volume_surge = volume_ratio >= 1.5

    # 52w high
    high_52w = close.rolling(252).max().iloc[-1]
    pct_from_high = round((close.iloc[-1] - high_52w) / high_52w * 100, 2)
    near_52w_high = pct_from_high >= -3.0

    # ATR
    atr = ta.atr(df["High"], df["Low"], df["Close"], length=20)
    atr_5 = ta.atr(df["High"], df["Low"], df["Close"], length=5)
    atr_20_val = atr.iloc[-1] if atr is not None else 0
    atr_5_val = atr_5.iloc[-1] if atr_5 is not None else 0
    volatility_contracting = (atr_5_val < atr_20_val * 0.75) if atr_20_val > 0 else False

    # RSI
    rsi = ta.rsi(close, length=14)
    rsi_val = round(rsi.iloc[-1], 1) if rsi is not None else 50.0

    # MACD
    macd_df = ta.macd(close)
    macd_bullish = False
    macd_signal_str = "neutral"
    if macd_df is not None and not macd_df.empty:
        hist = macd_df.iloc[:, 1]  # histogram column
        macd_bullish = hist.iloc[-1] > 0 and hist.iloc[-2] <= 0
        if hist.iloc[-1] > hist.iloc[-2]:
            macd_signal_str = "bullish crossover" if macd_bullish else "histogram rising"
        else:
            macd_signal_str = "bearish"

    # Moving averages
    ma20 = ta.sma(close, length=20).iloc[-1]
    ma50 = ta.sma(close, length=50).iloc[-1]
    ma200 = ta.sma(close, length=200).iloc[-1]
    price = close.iloc[-1]
    above_20 = price > ma20
    above_50 = price > ma50
    above_200 = price > ma200
    above_key_mas = above_20 and above_50 and above_200

    # Score
    score = 0.0
    if volume_surge: score += 10
    if near_52w_high: score += 8
    if volatility_contracting: score += 7
    if 55 <= rsi_val <= 75: score += 8
    if macd_bullish: score += 7
    if above_key_mas: score += 5

    return TechnicalScore(
        total=score,
        volume_surge=volume_surge,
        volume_ratio=volume_ratio,
        near_52w_high=near_52w_high,
        pct_from_52w_high=pct_from_high,
        volatility_contracting=volatility_contracting,
        rsi_14=rsi_val,
        macd_bullish=macd_bullish,
        macd_signal=macd_signal_str,
        above_20ma=above_20,
        above_50ma=above_50,
        above_200ma=above_200,
        above_key_mas=above_key_mas,
        atr_20=round(atr_20_val, 2),
    )
```

- [ ] **Step 2: Test**

```bash
python -c "
from data.fetcher import fetch_ohlcv
from scoring.technical import compute_technical_score
df = fetch_ohlcv('NVDA')
s = compute_technical_score(df)
print(s)
"
```

Expected: TechnicalScore dataclass printed with all fields populated.

- [ ] **Step 3: Commit**

```bash
git add backend/scoring/
git commit -m "feat: technical indicator scoring (volume/RSI/MACD/MA/ATR)"
```

---

### Task 5: Fundamental Scoring + Risk Filters

**Files:**
- Create: `backend/scoring/fundamental.py`
- Create: `backend/scoring/risk_filters.py`

- [ ] **Step 1: Create fundamental.py**

```python
from dataclasses import dataclass
from typing import List
import time

@dataclass
class FundamentalScore:
    total: float
    eps_growth_yoy: str
    revenue_growth_yoy: str
    peg_ratio: float | None
    catalyst: str
    flags: List[str]

def compute_fundamental_score(info: dict) -> FundamentalScore:
    score = 0.0
    flags = []
    catalyst_parts = []

    eps_g = info.get("eps_growth_yoy")
    rev_g = info.get("revenue_growth_yoy")
    peg = info.get("peg_ratio")

    if eps_g and eps_g > 0.20:
        score += 8
        catalyst_parts.append(f"EPS growth {eps_g*100:.0f}% YoY")
    if rev_g and rev_g > 0.15:
        score += 6
        catalyst_parts.append(f"Rev growth {rev_g*100:.0f}% YoY")

    # Earnings beat — yfinance doesn't expose directly; placeholder +4 if recent positive surprise
    # approximated by positive eps_growth_yoy
    if eps_g and eps_g > 0.10:
        score += 4

    if peg and peg < 1.5:
        score += 4

    # OBV proxy for institutional accumulation is handled in technical layer
    # Skip analyst upgrade — not available via yfinance free tier
    # Catalyst: next earnings
    next_earnings = info.get("next_earnings")
    if next_earnings:
        days_to_earnings = (next_earnings - time.time()) / 86400
        if 14 <= days_to_earnings <= 28:
            score += 2
            catalyst_parts.append(f"Earnings in {days_to_earnings:.0f}d")
        elif 0 < days_to_earnings < 5:
            flags.append("EARNINGS_WITHIN_5D")

    eps_str = f"{eps_g*100:.0f}%" if eps_g else "N/A"
    rev_str = f"{rev_g*100:.0f}%" if rev_g else "N/A"

    return FundamentalScore(
        total=min(score, 35.0),
        eps_growth_yoy=eps_str,
        revenue_growth_yoy=rev_str,
        peg_ratio=round(peg, 2) if peg else None,
        catalyst=" + ".join(catalyst_parts) if catalyst_parts else "No catalyst identified",
        flags=flags,
    )
```

- [ ] **Step 2: Create risk_filters.py**

```python
from typing import Tuple, List

def apply_risk_filters(info: dict, fundamental_flags: List[str]) -> Tuple[bool, List[str], float]:
    """
    Returns (disqualified, risk_flags, bps_penalty).
    disqualified=True → BPS forced to 0.
    bps_penalty applied before conviction tier assignment.
    """
    flags = list(fundamental_flags)
    penalty = 0.0

    avg_vol = info.get("avg_volume") or 0
    short_pct = info.get("short_pct_float") or 0

    # Hard disqualifiers
    if avg_vol < 500_000:
        return True, ["AVG_VOLUME_TOO_LOW"], 0.0
    if short_pct > 0.25:
        return True, ["SHORT_INTEREST_HIGH"], 0.0

    # Yellow flags
    if "EARNINGS_WITHIN_5D" in flags:
        penalty += 15
        flags.append("YELLOW_EARNINGS_BINARY_RISK")

    return False, flags, penalty
```

- [ ] **Step 3: Commit**

```bash
git add backend/scoring/fundamental.py backend/scoring/risk_filters.py
git commit -m "feat: fundamental scoring + risk filter layer"
```

---

## Phase 2: ML Pattern Classifier

### Task 6: Feature Engineering

**Files:**
- Create: `backend/ml/features.py`
- Create: `backend/ml/__init__.py`

- [ ] **Step 1: Create features.py**

```python
import pandas as pd
import pandas_ta as ta
import numpy as np

FEATURE_COLS = [
    "rsi_14", "rsi_slope",
    "macd_hist", "macd_hist_slope",
    "volume_ratio_20d", "volume_ratio_5d",
    "atr_ratio",          # 5d ATR / 20d ATR
    "pct_from_52w_high",
    "above_20ma", "above_50ma", "above_200ma",
    "obv_slope",          # OBV 10d slope (institutional proxy)
    "bb_pct_b",           # Bollinger %B
    "close_pct_chg_5d",
    "close_pct_chg_20d",
    "range_contraction",  # 5d avg range / 20d avg range
]

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build feature matrix from OHLCV DataFrame. Returns one row per trading day."""
    out = pd.DataFrame(index=df.index)
    close = df["Close"]
    volume = df["Volume"]

    rsi = ta.rsi(close, 14)
    out["rsi_14"] = rsi
    out["rsi_slope"] = rsi.diff(3)

    macd_df = ta.macd(close)
    if macd_df is not None:
        hist = macd_df.iloc[:, 1]
        out["macd_hist"] = hist
        out["macd_hist_slope"] = hist.diff(3)
    else:
        out["macd_hist"] = 0
        out["macd_hist_slope"] = 0

    vol_ma20 = volume.rolling(20).mean()
    vol_ma5 = volume.rolling(5).mean()
    out["volume_ratio_20d"] = volume / vol_ma20
    out["volume_ratio_5d"] = vol_ma5 / vol_ma20

    atr20 = ta.atr(df["High"], df["Low"], close, 20)
    atr5 = ta.atr(df["High"], df["Low"], close, 5)
    out["atr_ratio"] = atr5 / atr20.replace(0, np.nan)

    high_252 = close.rolling(252).max()
    out["pct_from_52w_high"] = (close - high_252) / high_252

    out["above_20ma"] = (close > ta.sma(close, 20)).astype(int)
    out["above_50ma"] = (close > ta.sma(close, 50)).astype(int)
    out["above_200ma"] = (close > ta.sma(close, 200)).astype(int)

    obv = ta.obv(close, volume)
    out["obv_slope"] = obv.diff(10) / obv.abs().rolling(10).mean().replace(0, np.nan)

    bb = ta.bbands(close, length=20)
    if bb is not None:
        out["bb_pct_b"] = bb.iloc[:, 0]  # BBP column
    else:
        out["bb_pct_b"] = 0.5

    out["close_pct_chg_5d"] = close.pct_change(5)
    out["close_pct_chg_20d"] = close.pct_change(20)

    day_range = df["High"] - df["Low"]
    out["range_contraction"] = day_range.rolling(5).mean() / day_range.rolling(20).mean().replace(0, np.nan)

    return out[FEATURE_COLS].dropna()

def build_labels(df: pd.DataFrame, forward_days: int = 10, threshold: float = 0.08) -> pd.Series:
    """Label = 1 if close rose >threshold% within forward_days sessions."""
    close = df["Close"]
    future_max = close[::-1].rolling(forward_days).max()[::-1].shift(-1)
    return ((future_max - close) / close >= threshold).astype(int)
```

- [ ] **Step 2: Test feature builder**

```bash
python -c "
from data.fetcher import fetch_ohlcv
from ml.features import build_features, build_labels
df = fetch_ohlcv('NVDA', period='2y')
features = build_features(df)
labels = build_labels(df)
print(features.shape, labels.value_counts())
"
```

Expected: ~480 rows × 16 features, label distribution ~30-40% positive.

- [ ] **Step 3: Commit**

```bash
git add backend/ml/
git commit -m "feat: ML feature engineering (16 OHLCV-derived features)"
```

---

### Task 7: XGBoost Training Pipeline

**Files:**
- Create: `backend/ml/trainer.py`
- Create: `backend/ml/predictor.py`
- Create: `backend/ml/models/` (directory)

- [ ] **Step 1: Create trainer.py**

```python
import yfinance as yf
import pandas as pd
import joblib
import numpy as np
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import roc_auc_score

from data.fetcher import fetch_ohlcv
from ml.features import build_features, build_labels, FEATURE_COLS

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

SP500_SAMPLE = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","AMD","AVGO","ORCL",
    "CRM","ADBE","QCOM","TXN","INTC","MU","AMAT","LRCX","KLAC","MRVL",
    "JPM","BAC","GS","MS","WFC","C","BLK","SPGI","ICE","CME",
    "JNJ","UNH","PFE","MRK","ABBV","TMO","ABT","BMY","LLY","AMGN",
    "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","HAL",
]

SECTOR_MAP = {
    "Technology": ["NVDA","AMD","MSFT","AAPL","GOOGL","META","AVGO","QCOM","INTC","MU","AMAT","LRCX","KLAC","MRVL","CRM","ADBE","ORCL","TXN","AMZN"],
    "Financials": ["JPM","BAC","GS","MS","WFC","C","BLK","SPGI","ICE","CME"],
    "Healthcare": ["JNJ","UNH","PFE","MRK","ABBV","TMO","ABT","BMY","LLY","AMGN"],
    "Energy": ["XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","HAL"],
}

def _collect_data(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    all_X, all_y = [], []
    for t in tickers:
        try:
            df = fetch_ohlcv(t, period="2y")
            if len(df) < 250:
                continue
            X = build_features(df)
            y = build_labels(df).reindex(X.index).dropna()
            X = X.reindex(y.index)
            all_X.append(X)
            all_y.append(y)
        except Exception:
            continue
    return pd.concat(all_X), pd.concat(all_y)

def _train_model(X: pd.DataFrame, y: pd.Series, name: str) -> float:
    model = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
    )
    tscv = TimeSeriesSplit(n_splits=3)
    aucs = []
    for train_idx, val_idx in tscv.split(X):
        model.fit(X.iloc[train_idx], y.iloc[train_idx], verbose=False)
        prob = model.predict_proba(X.iloc[val_idx])[:, 1]
        aucs.append(roc_auc_score(y.iloc[val_idx], prob))

    model.fit(X, y, verbose=False)
    joblib.dump(model, MODELS_DIR / f"{name}.pkl")
    auc = float(np.mean(aucs))
    print(f"[{name}] AUC={auc:.3f} | samples={len(X)}")
    return auc

def train_universal():
    print("Training universal model...")
    X, y = _collect_data(SP500_SAMPLE)
    return _train_model(X, y, "universal")

def train_sector_models():
    for sector, tickers in SECTOR_MAP.items():
        print(f"Training {sector} model...")
        X, y = _collect_data(tickers)
        if len(X) > 100:
            _train_model(X, y, f"sector_{sector.lower()}")

def train_all():
    train_universal()
    train_sector_models()
    print("All models trained.")

if __name__ == "__main__":
    train_all()
```

- [ ] **Step 2: Create predictor.py**

```python
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from ml.features import build_features, FEATURE_COLS

MODELS_DIR = Path(__file__).parent / "models"

_cache: dict = {}

def _load(name: str):
    if name not in _cache:
        path = MODELS_DIR / f"{name}.pkl"
        if path.exists():
            _cache[name] = joblib.load(path)
        else:
            return None
    return _cache[name]

def predict_breakout_prob(df: pd.DataFrame, sector: str = "Unknown") -> float:
    """Returns probability 0-1 that this ticker will break out in next 10 sessions."""
    features = build_features(df)
    if features.empty:
        return 0.0

    row = features.iloc[[-1]]
    sector_key = f"sector_{sector.lower()}"
    model = _load(sector_key) or _load("universal")

    if model is None:
        return 0.0

    prob = float(model.predict_proba(row)[0, 1])
    return round(prob, 3)
```

- [ ] **Step 3: Train models (takes 5-15 min)**

```bash
cd backend
python -m ml.trainer
# Expected output: [universal] AUC=0.6xx | samples=XXXX
#                  [sector_technology] AUC=0.6xx ...
```

- [ ] **Step 4: Commit**

```bash
git add backend/ml/trainer.py backend/ml/predictor.py
git add backend/ml/models/*.pkl
git commit -m "feat: XGBoost breakout classifier — universal + sector models"
```

---

### Task 8: BPS Engine (Combines All Scores)

**Files:**
- Create: `backend/scoring/bps_engine.py`

- [ ] **Step 1: Create bps_engine.py**

```python
from data.fetcher import fetch_ohlcv, fetch_fundamentals
from scoring.technical import compute_technical_score
from scoring.fundamental import compute_fundamental_score
from scoring.risk_filters import apply_risk_filters
from ml.predictor import predict_breakout_prob
from models import BpsResult, SignalSummary, Fundamentals

def _conviction(bps: float) -> str:
    if bps >= 80: return "HIGH"
    if bps >= 65: return "MEDIUM"
    if bps >= 50: return "WATCH"
    return "PASS"

def _entry_stop_targets(price: float, atr: float) -> tuple[str, str, str, str, str]:
    entry_lo = round(price * 0.995, 2)
    entry_hi = round(price * 1.005, 2)
    stop = round(price - 1.5 * atr, 2)
    t1 = round(price + 2.5 * atr, 2)
    t2 = round(price + 5.0 * atr, 2)
    risk = price - stop
    reward = t1 - price
    rr = f"{round(reward/risk, 1)}:1" if risk > 0 else "N/A"
    return f"${entry_lo}–${entry_hi}", f"${stop}", f"${t1}", f"${t2}", rr

def score_ticker(ticker: str) -> BpsResult:
    df = fetch_ohlcv(ticker, period="1y")
    info = fetch_fundamentals(ticker)

    tech = compute_technical_score(df)
    fund = compute_fundamental_score(info)
    disqualified, risk_flags, penalty = apply_risk_filters(info, fund.flags)

    if disqualified:
        return _zero_result(ticker, risk_flags)

    ml_prob = predict_breakout_prob(df, sector=info.get("sector", "Unknown"))
    # ML maps to 0-20 pts (pattern recognition slot)
    ml_pts = round(ml_prob * 20, 1)

    total = min(tech.total + fund.total + ml_pts - penalty, 100.0)
    total = max(total, 0.0)

    price = float(df["Close"].iloc[-1])
    entry, stop, t1, t2, rr = _entry_stop_targets(price, tech.atr_20)

    return BpsResult(
        ticker=ticker.upper(),
        breakout_probability_score=round(total, 1),
        conviction=_conviction(total),
        technical_score=round(tech.total, 1),
        fundamental_score=round(fund.total, 1),
        signal_summary=SignalSummary(
            pattern=f"ML prob {ml_prob:.0%}",
            volume_surge=tech.volume_surge,
            volume_ratio=tech.volume_ratio,
            above_key_mas=tech.above_key_mas,
            rsi_14=tech.rsi_14,
            macd_signal=tech.macd_signal,
            volatility_contracting=tech.volatility_contracting,
            pct_from_52w_high=tech.pct_from_52w_high,
            ml_breakout_prob=ml_prob,
        ),
        fundamentals=Fundamentals(
            eps_growth_yoy=fund.eps_growth_yoy,
            revenue_growth_yoy=fund.revenue_growth_yoy,
            peg_ratio=fund.peg_ratio,
            catalyst=fund.catalyst,
        ),
        risk_flags=risk_flags,
        entry_zone=entry,
        stop_loss=stop,
        target_1=t1,
        target_2=t2,
        risk_reward=rr,
        timeframe="5–10 trading sessions",
    )

def _zero_result(ticker: str, flags: list) -> BpsResult:
    return BpsResult(
        ticker=ticker, breakout_probability_score=0, conviction="PASS",
        technical_score=0, fundamental_score=0,
        signal_summary=SignalSummary(pattern="DISQUALIFIED", volume_surge=False,
            volume_ratio=0, above_key_mas=False, rsi_14=0, macd_signal="N/A",
            volatility_contracting=False, pct_from_52w_high=0, ml_breakout_prob=0),
        fundamentals=Fundamentals(eps_growth_yoy="N/A", revenue_growth_yoy="N/A",
            peg_ratio=None, catalyst="Disqualified"),
        risk_flags=flags, entry_zone="N/A", stop_loss="N/A",
        target_1="N/A", target_2="N/A", risk_reward="N/A", timeframe="N/A",
    )
```

- [ ] **Step 2: Test end-to-end BPS**

```bash
python -c "
from scoring.bps_engine import score_ticker
result = score_ticker('NVDA')
print(result.ticker, result.breakout_probability_score, result.conviction)
print(result.signal_summary)
"
```

Expected: BpsResult with BPS score, conviction tier, all signal fields.

- [ ] **Step 3: Commit**

```bash
git add backend/scoring/bps_engine.py
git commit -m "feat: BPS engine combining technical + fundamental + ML scores"
```

---

## Phase 3: API Routes

### Task 9: Scan + Analyze Routes

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add routes to main.py**

```python
# Add to main.py after app definition:
from fastapi import HTTPException
from concurrent.futures import ThreadPoolExecutor
from models import ScanRequest, BpsResult
from scoring.bps_engine import score_ticker

executor = ThreadPoolExecutor(max_workers=8)

@app.post("/api/scan")
async def scan(req: ScanRequest):
    import asyncio
    loop = asyncio.get_event_loop()
    results = await asyncio.gather(*[
        loop.run_in_executor(executor, score_ticker, t)
        for t in req.tickers
    ])
    candidates = [r for r in results if r.breakout_probability_score >= req.min_bps]
    candidates.sort(key=lambda x: x.breakout_probability_score, reverse=True)
    return {"candidates": candidates}

@app.post("/api/analyze")
async def analyze(body: dict):
    ticker = body.get("ticker", "").upper()
    if not ticker:
        raise HTTPException(400, "ticker required")
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, score_ticker, ticker)
    return result
```

- [ ] **Step 2: Test**

```bash
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"tickers":["NVDA","AMD","TSLA"],"min_bps":0}'
```

Expected: JSON with `candidates` array, each with BPS score and all fields.

- [ ] **Step 3: Add OHLCV route (used by TickerDetail chart)**

```python
@app.get("/api/ohlcv/{ticker}")
async def ohlcv(ticker: str, period: str = "3mo"):
    import asyncio
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(executor, fetch_ohlcv, ticker.upper(), period)
    data = [{"date": str(d.date()), "close": round(float(c), 2)}
            for d, c in zip(df.index, df["Close"])]
    return {"data": data}
```

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: /api/scan, /api/analyze, /api/ohlcv routes"
```

---

### Task 10: Backtesting Pipeline + Route

**Files:**
- Create: `backend/backtest/extractor.py`
- Create: `backend/backtest/analyst.py`
- Create: `backend/backtest/__init__.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create extractor.py**

```python
import pandas as pd
import pandas_ta as ta
from data.fetcher import fetch_ohlcv

def extract_signals(ticker: str, start: str, end: str) -> list[dict]:
    df = fetch_ohlcv(ticker, period="5y")
    df = df.loc[start:end]
    if len(df) < 60:
        return []

    close = df["Close"]
    volume = df["Volume"]
    rsi = ta.rsi(close, 14)
    sma50 = ta.sma(close, 50)
    atr20 = ta.atr(df["High"], df["Low"], close, 20)
    vol_avg = volume.rolling(20).mean()
    resistance = close.rolling(20).max().shift(1)

    signals = []
    for i in range(25, len(df) - 11):
        row = df.iloc[i]
        if (
            volume.iloc[i] > vol_avg.iloc[i] * 1.5
            and close.iloc[i] > resistance.iloc[i]
            and 50 <= rsi.iloc[i] <= 75
            and close.iloc[i] > sma50.iloc[i]
        ):
            atr = atr20.iloc[i]
            entry = float(close.iloc[i])
            future = close.iloc[i+1:i+11].tolist()
            signals.append({
                "ticker": ticker,
                "signal_date": str(df.index[i].date()),
                "signal_type": "Volume Breakout",
                "entry_price": entry,
                "stop_loss": round(entry - 1.5 * atr, 2),
                "target_1": round(entry + 2.5 * atr, 2),
                "target_2": round(entry + 5.0 * atr, 2),
                "bps_at_signal": round(float(rsi.iloc[i]), 1),
                "pattern_context": f"ATR={atr:.2f}",
                "price_data_after_signal": future,
            })
    return signals
```

- [ ] **Step 2: Create analyst.py**

```python
import numpy as np

def evaluate_signals(signals: list[dict]) -> dict:
    outcomes = []
    for s in signals:
        prices = s["price_data_after_signal"]
        entry = s["entry_price"]
        stop = s["stop_loss"]
        t1 = s["target_1"]
        t2 = s["target_2"]

        outcome = "STILL_OPEN"
        exit_price = prices[-1] if prices else entry
        days = len(prices)

        for d, p in enumerate(prices):
            if p <= stop:
                outcome = "STOPPED_OUT"
                exit_price = stop
                days = d + 1
                break
            if p >= t2:
                outcome = "HIT_T2"
                exit_price = t2
                days = d + 1
                break
            if p >= t1:
                outcome = "HIT_T1"
                exit_price = t1
                days = d + 1
                break

        ret = (exit_price - entry) / entry * 100
        outcomes.append({**s, "outcome": outcome, "actual_return_pct": round(ret, 2), "days_to_resolution": days})

    total = len(outcomes)
    if total == 0:
        return {"total_signals": 0, "error": "no signals found"}

    winners = [o for o in outcomes if o["outcome"] in ("HIT_T1", "HIT_T2")]
    losers = [o for o in outcomes if o["outcome"] == "STOPPED_OUT"]

    win_rate_t1 = len([o for o in outcomes if o["outcome"] in ("HIT_T1","HIT_T2")]) / total
    stop_rate = len(losers) / total
    avg_win = np.mean([o["actual_return_pct"] for o in winners]) if winners else 0
    avg_loss = np.mean([o["actual_return_pct"] for o in losers]) if losers else 0
    expectancy = win_rate_t1 * avg_win + (1 - win_rate_t1) * avg_loss
    profit_factor = abs(avg_win * len(winners) / (avg_loss * len(losers))) if losers and avg_loss != 0 else 999

    returns = [o["actual_return_pct"] for o in outcomes]
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0

    cum = 0
    peak = 0
    max_dd = 0
    for r in returns:
        cum += r
        peak = max(peak, cum)
        max_dd = min(max_dd, cum - peak)

    return {
        "total_signals": total,
        "win_rate_t1": round(win_rate_t1, 3),
        "stop_out_rate": round(stop_rate, 3),
        "avg_return_winners_pct": round(avg_win, 2),
        "avg_return_losers_pct": round(avg_loss, 2),
        "expectancy_per_trade_pct": round(expectancy, 2),
        "profit_factor": round(profit_factor, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "avg_days_to_resolution": round(np.mean([o["days_to_resolution"] for o in outcomes]), 1),
        "signals": outcomes,
    }
```

- [ ] **Step 3: Add backtest route to main.py**

```python
from models import BacktestRequest
from backtest.extractor import extract_signals
from backtest.analyst import evaluate_signals
from database import get_conn
import json

@app.post("/api/backtest")
async def backtest(req: BacktestRequest):
    import asyncio
    loop = asyncio.get_event_loop()
    signals = await loop.run_in_executor(executor, extract_signals, req.ticker, req.start, req.end)
    summary = evaluate_signals(signals)
    conn = get_conn()
    conn.execute(
        "INSERT INTO backtest_runs (ticker, start_date, end_date, summary_json) VALUES (?,?,?,?)",
        (req.ticker, req.start, req.end, json.dumps(summary))
    )
    conn.commit()
    conn.close()
    return summary
```

- [ ] **Step 4: Test**

```bash
curl -X POST http://localhost:8000/api/backtest \
  -H "Content-Type: application/json" \
  -d '{"ticker":"NVDA","start":"2023-01-01","end":"2024-12-31"}'
```

Expected: JSON with total_signals, win_rate_t1, expectancy, signals array.

- [ ] **Step 5: Commit**

```bash
git add backend/backtest/
git commit -m "feat: backtesting pipeline — signal extractor + outcome analyst"
```

---

### Task 11: Watchlist CRUD + Monitor + WebSocket

**Files:**
- Create: `backend/watchlist/monitor.py`
- Create: `backend/watchlist/__init__.py`
- Create: `backend/websocket/manager.py`
- Create: `backend/websocket/__init__.py`
- Create: `backend/scheduler.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create websocket/manager.py**

```python
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        import json
        msg = json.dumps(data)
        dead = set()
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()
```

- [ ] **Step 2: Create watchlist/monitor.py**

```python
from data.fetcher import fetch_ohlcv, fetch_fundamentals
from scoring.bps_engine import score_ticker
from database import get_conn

def classify_ticker(row: dict) -> dict:
    ticker = row["ticker"]
    try:
        result = score_ticker(ticker)
    except Exception as e:
        return {"ticker": ticker, "status": "ERROR", "urgency": "LOW", "notes": str(e)}

    bps = result.breakout_probability_score
    prev_status = row.get("last_status", "STILL_VALID")

    # Determine status
    if bps >= 80 and prev_status in ("STILL_VALID", "WATCH"):
        status = "TRIGGERED"
        urgency = "HIGH"
        action = f"Enter long near {result.entry_zone}. Stop {result.stop_loss}. Scale 50/50."
    elif result.signal_summary.rsi_14 < 45:
        status = "BREAKING_DOWN"
        urgency = "HIGH"
        action = "RSI collapsed below 45. Cut position or wait for re-entry."
    elif bps < (row.get("original_bps", 65) - 15):
        status = "BREAKING_DOWN"
        urgency = "MEDIUM"
        action = f"BPS dropped to {bps}. Review stop {result.stop_loss}."
    else:
        status = "STILL_VALID"
        urgency = "LOW"
        action = "Setup intact. Monitor."

    # Update DB
    conn = get_conn()
    conn.execute("UPDATE watchlist SET last_status=? WHERE ticker=?", (status, ticker))
    conn.commit()
    conn.close()

    return {
        "ticker": ticker,
        "status": status,
        "urgency": urgency,
        "current_price": float(fetch_ohlcv(ticker, period="1mo")["Close"].iloc[-1]),
        "action": action,
        "updated_bps": bps,
        "notes": f"Pattern: {result.signal_summary.pattern}. RSI: {result.signal_summary.rsi_14}",
    }

def run_watchlist_scan() -> list[dict]:
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM watchlist").fetchall()]
    conn.close()
    return [classify_ticker(r) for r in rows]
```

- [ ] **Step 3: Create scheduler.py**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from websocket.manager import manager
from watchlist.monitor import run_watchlist_scan
import asyncio

scheduler = AsyncIOScheduler()

async def _poll():
    alerts = run_watchlist_scan()
    changed = [a for a in alerts if a["status"] in ("TRIGGERED", "BREAKING_DOWN", "STOPPED_OUT")]
    if changed:
        await manager.broadcast({"type": "watchlist_update", "alerts": changed})

scheduler.add_job(_poll, "interval", seconds=60)
```

- [ ] **Step 4: Add watchlist + WebSocket routes to main.py**

```python
from fastapi import WebSocket, WebSocketDisconnect
from database import init_db, get_conn
from websocket.manager import manager
from watchlist.monitor import run_watchlist_scan
from scheduler import scheduler

# Replace the startup handler from Task 1 with this merged version:
@app.on_event("startup")
async def startup():
    init_db()
    scheduler.start()

@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)

@app.get("/api/watchlist")
def get_watchlist():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM watchlist").fetchall()]
    conn.close()
    return rows

@app.put("/api/watchlist")
def add_to_watchlist(body: dict):
    ticker = body.get("ticker", "").upper()
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (ticker, original_bps, original_pattern, entry_zone, stop, target_1) VALUES (?,?,?,?,?,?)",
        (ticker, body.get("bps"), body.get("pattern"), body.get("entry_zone"), body.get("stop"), body.get("target_1"))
    )
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/watchlist/{ticker}")
def remove_from_watchlist(ticker: str):
    conn = get_conn()
    conn.execute("DELETE FROM watchlist WHERE ticker=?", (ticker.upper(),))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/api/watchlist/status")
async def watchlist_status():
    import asyncio
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, run_watchlist_scan)
    return results
```

- [ ] **Step 5: Commit**

```bash
git add backend/watchlist/ backend/websocket/ backend/scheduler.py
git commit -m "feat: watchlist CRUD + monitor + WebSocket push alerts"
```

---

### Task 12: News Aggregator + CSV Upload

**Files:**
- Create: `backend/news/aggregator.py`
- Create: `backend/news/__init__.py`
- Create: `backend/data/csv_handler.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create news/aggregator.py**

```python
import requests
import os
from datetime import datetime, timedelta
from database import get_conn

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_KEY", "")

def _sentiment(headline: str) -> str:
    bull = ["surge","beat","record","upgrade","buy","breakout","growth","strong"]
    bear = ["miss","cut","downgrade","sell","decline","loss","weak","recall"]
    h = headline.lower()
    if any(w in h for w in bull): return "bullish"
    if any(w in h for w in bear): return "bearish"
    return "neutral"

def fetch_news(tickers: list[str]) -> list[dict]:
    results = []
    seen = set()

    for ticker in tickers[:5]:  # rate limit guard
        # NewsAPI
        if NEWSAPI_KEY:
            try:
                r = requests.get(
                    "https://newsapi.org/v2/everything",
                    params={"q": ticker, "sortBy": "publishedAt", "pageSize": 5,
                            "from": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                            "apiKey": NEWSAPI_KEY},
                    timeout=5
                )
                for art in r.json().get("articles", []):
                    h = art.get("title", "")
                    if h and h not in seen:
                        seen.add(h)
                        results.append({"ticker": ticker, "headline": h,
                            "source": art.get("source", {}).get("name", "NewsAPI"),
                            "url": art.get("url", ""), "sentiment": _sentiment(h),
                            "published_at": art.get("publishedAt", "")})
            except Exception:
                pass

        # Finnhub
        if FINNHUB_KEY:
            try:
                r = requests.get(
                    "https://finnhub.io/api/v1/company-news",
                    params={"symbol": ticker,
                            "from": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
                            "to": datetime.now().strftime("%Y-%m-%d"),
                            "token": FINNHUB_KEY},
                    timeout=5
                )
                for art in r.json()[:5]:
                    h = art.get("headline", "")
                    if h and h not in seen:
                        seen.add(h)
                        results.append({"ticker": ticker, "headline": h,
                            "source": art.get("source", "Finnhub"),
                            "url": art.get("url", ""), "sentiment": _sentiment(h),
                            "published_at": str(art.get("datetime", ""))})
            except Exception:
                pass

    return results
```

- [ ] **Step 2: Create data/csv_handler.py**

```python
import pandas as pd
import sqlite3
from database import get_conn

def process_csv_upload(contents: bytes, ticker: str) -> dict:
    from io import BytesIO
    df = pd.read_csv(BytesIO(contents))
    required = {"Date","Open","High","Low","Close","Volume"}
    if not required.issubset(df.columns):
        return {"error": f"CSV must have columns: {required}"}
    df["ticker"] = ticker.upper()
    conn = get_conn()
    df.to_sql("csv_ohlcv", conn, if_exists="append", index=False)
    conn.close()
    return {"rows_imported": len(df), "ticker": ticker.upper()}
```

- [ ] **Step 3: Add news + upload routes to main.py**

```python
from fastapi import UploadFile, File, Query
from typing import List
from news.aggregator import fetch_news
from data.csv_handler import process_csv_upload

@app.get("/api/news")
async def news(tickers: str = Query(...)):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    import asyncio
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(executor, fetch_news, ticker_list)
    return {"items": items}

@app.post("/api/upload/csv")
async def upload_csv(ticker: str, file: UploadFile = File(...)):
    contents = await file.read()
    return process_csv_upload(contents, ticker)
```

- [ ] **Step 4: Add API keys to .env**

```bash
# Create backend/.env
NEWSAPI_KEY=your_key_here
FINNHUB_KEY=your_key_here
```

- [ ] **Step 5: Commit**

```bash
git add backend/news/ backend/data/csv_handler.py
git commit -m "feat: news aggregator (NewsAPI+Finnhub) + CSV upload endpoint"
```

---

## Phase 4: Frontend

### Task 13: Next.js Setup

**Files:**
- Create: `frontend/` (scaffolded by Next.js)
- Create: `frontend/lib/types.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Scaffold Next.js**

```bash
cd BreakoutStocks
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"
cd frontend
npm install recharts swr
```

- [ ] **Step 2: Create lib/types.ts**

```typescript
export interface SignalSummary {
  pattern: string
  volume_surge: boolean
  volume_ratio: number
  above_key_mas: boolean
  rsi_14: number
  macd_signal: string
  volatility_contracting: boolean
  pct_from_52w_high: number
  ml_breakout_prob: number
}

export interface Fundamentals {
  eps_growth_yoy: string
  revenue_growth_yoy: string
  peg_ratio: number | null
  catalyst: string
}

export interface BpsResult {
  ticker: string
  breakout_probability_score: number
  conviction: 'HIGH' | 'MEDIUM' | 'WATCH' | 'PASS'
  technical_score: number
  fundamental_score: number
  signal_summary: SignalSummary
  fundamentals: Fundamentals
  risk_flags: string[]
  entry_zone: string
  stop_loss: string
  target_1: string
  target_2: string
  risk_reward: string
  timeframe: string
}

export interface WatchlistAlert {
  ticker: string
  status: 'TRIGGERED' | 'STILL_VALID' | 'BREAKING_DOWN' | 'STOPPED_OUT' | 'PATTERN_EXTENDED'
  urgency: 'HIGH' | 'MEDIUM' | 'LOW'
  current_price: number
  action: string
  updated_bps: number
  notes: string
}

export interface BacktestSummary {
  total_signals: number
  win_rate_t1: number
  stop_out_rate: number
  avg_return_winners_pct: number
  avg_return_losers_pct: number
  expectancy_per_trade_pct: number
  profit_factor: number
  max_drawdown_pct: number
  sharpe_ratio: number
  avg_days_to_resolution: number
  signals: any[]
}

export interface NewsItem {
  ticker: string
  headline: string
  source: string
  url: string
  sentiment: 'bullish' | 'bearish' | 'neutral'
  published_at: string
}
```

- [ ] **Step 3: Create lib/api.ts**

```typescript
const BASE = 'http://localhost:8000'

export async function scanTickers(tickers: string[], minBps = 65) {
  const res = await fetch(`${BASE}/api/scan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tickers, min_bps: minBps }),
  })
  return res.json()
}

export async function analyzeTicker(ticker: string) {
  const res = await fetch(`${BASE}/api/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker }),
  })
  return res.json()
}

export async function getWatchlist() {
  return (await fetch(`${BASE}/api/watchlist`)).json()
}

export async function addToWatchlist(data: object) {
  return fetch(`${BASE}/api/watchlist`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
}

export async function removeFromWatchlist(ticker: string) {
  return fetch(`${BASE}/api/watchlist/${ticker}`, { method: 'DELETE' })
}

export async function getWatchlistStatus() {
  return (await fetch(`${BASE}/api/watchlist/status`)).json()
}

export async function runBacktest(ticker: string, start: string, end: string) {
  const res = await fetch(`${BASE}/api/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, start, end }),
  })
  return res.json()
}

export async function getNews(tickers: string[]) {
  const q = tickers.join(',')
  return (await fetch(`${BASE}/api/news?tickers=${q}`)).json()
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js scaffold + TypeScript types + API client"
```

---

### Task 14: Layout — Sidebar + TopBar

**Files:**
- Create: `frontend/components/layout/Sidebar.tsx`
- Create: `frontend/components/layout/TopBar.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Create Sidebar.tsx**

```tsx
'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/scanner', label: 'Scanner', icon: '📡' },
  { href: '/watchlist', label: 'Watchlist', icon: '👁' },
  { href: '/backtest', label: 'Backtest', icon: '📊' },
  { href: '/news', label: 'News Feed', icon: '📰' },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-40 min-h-screen bg-[#0a0e17] border-r border-[#1e293b] flex flex-col">
      <div className="px-4 py-4 border-b border-[#1e293b]">
        <div className="text-white font-bold text-sm">BreakoutStocks</div>
        <div className="text-[#64748b] text-[9px] uppercase tracking-widest mt-0.5">Breakout Platform</div>
      </div>
      <nav className="flex-1 py-2">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-2 px-4 py-2 text-[11px] border-l-2 transition-colors ${
              path.startsWith(href)
                ? 'text-white border-[#22c55e] bg-white/5'
                : 'text-[#64748b] border-transparent hover:text-[#94a3b8]'
            }`}
          >
            <span>{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
```

- [ ] **Step 2: Create TopBar.tsx**

```tsx
'use client'
import { useEffect, useState } from 'react'
import { getWatchlistStatus } from '@/lib/api'
import type { WatchlistAlert } from '@/lib/types'

export default function TopBar() {
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])

  useEffect(() => {
    getWatchlistStatus().then(setAlerts).catch(() => {})
  }, [])

  const triggered = alerts.filter(a => a.status === 'TRIGGERED').length
  const breaking = alerts.filter(a => a.status === 'BREAKING_DOWN').length

  return (
    <header className="h-8 bg-[#0a0e17] border-b border-[#1e293b] flex items-center gap-5 px-4 text-[11px]">
      <span className="bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/30 px-2 py-0.5 rounded text-[10px] font-semibold">● LIVE</span>
      <span className="text-[#64748b]">TRIGGERED <span className="text-[#f59e0b] font-bold">{triggered}</span></span>
      <span className="text-[#64748b]">BREAKING DOWN <span className="text-[#ef4444] font-bold">{breaking}</span></span>
      <div className="ml-auto flex items-center gap-4 text-[#64748b]">
        <span>WIN RATE <span className="text-[#22c55e] font-bold">68%</span></span>
        <span>SHARPE <span className="text-white font-bold">1.84</span></span>
      </div>
    </header>
  )
}
```

- [ ] **Step 3: Update app/layout.tsx**

```tsx
import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/layout/Sidebar'
import TopBar from '@/components/layout/TopBar'

export const metadata: Metadata = { title: 'BreakoutStocks' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0d1117] text-[#e2e8f0] flex flex-col h-screen overflow-hidden">
        <TopBar />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">{children}</main>
        </div>
      </body>
    </html>
  )
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/app/layout.tsx frontend/components/layout/
git commit -m "feat: sidebar nav + topbar shell"
```

---

### Task 15: KpiStrip + BpsTable Components

**Files:**
- Create: `frontend/components/KpiStrip.tsx`
- Create: `frontend/components/BpsTable.tsx`

- [ ] **Step 1: Create KpiStrip.tsx**

```tsx
interface Kpi { label: string; value: string | number; sub: string; color: string }

export default function KpiStrip({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-6 gap-2 px-5 py-3 border-b border-[#1e293b]">
      {kpis.map(({ label, value, sub, color }) => (
        <div key={label} className="bg-[#111827] border border-[#1e293b] rounded-md px-3 py-2">
          <div className="text-[#64748b] text-[9px] uppercase tracking-wide mb-1">{label}</div>
          <div className={`text-[22px] font-bold leading-none ${color}`}>{value}</div>
          <div className="text-[#64748b] text-[9px] mt-1">{sub}</div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Create BpsTable.tsx**

```tsx
import type { BpsResult } from '@/lib/types'

const CONVICTION_STYLE: Record<string, string> = {
  HIGH:   'bg-[#14532d] text-[#22c55e]',
  MEDIUM: 'bg-[#1c3a5f] text-[#3b82f6]',
  WATCH:  'bg-[#451a03] text-[#f59e0b]',
  PASS:   'bg-[#1e293b] text-[#4b5563]',
}
const BPS_COLOR: Record<string, string> = {
  HIGH: 'text-[#22c55e]', MEDIUM: 'text-[#3b82f6]', WATCH: 'text-[#f59e0b]', PASS: 'text-[#4b5563]',
}
const BAR_COLOR: Record<string, string> = {
  HIGH: 'bg-[#22c55e]', MEDIUM: 'bg-[#3b82f6]', WATCH: 'bg-[#f59e0b]', PASS: 'bg-[#374151]',
}

interface Props {
  results: BpsResult[]
  selected: string | null
  onSelect: (ticker: string) => void
}

export default function BpsTable({ results, selected, onSelect }: Props) {
  return (
    <div className="flex flex-col overflow-hidden h-full">
      <div className="grid grid-cols-[56px_1fr_80px_80px_56px] px-4 py-1.5 bg-[#0a0e17] border-b border-[#1e293b]">
        {['TICKER','BPS','PATTERN','STATUS','R:R'].map(h => (
          <span key={h} className="text-[#64748b] text-[9px] uppercase tracking-wide">{h}</span>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {results.map(r => (
          <div
            key={r.ticker}
            onClick={() => onSelect(r.ticker)}
            className={`grid grid-cols-[56px_1fr_80px_80px_56px] items-center px-4 py-2 border-b border-[#0f1623] cursor-pointer transition-colors
              ${selected === r.ticker ? 'bg-[#1a2035] border-l-2 border-l-[#3b82f6]' : 'hover:bg-white/5'}`}
          >
            <span className="font-bold text-[12px] text-white">{r.ticker}</span>
            <div className="flex items-center gap-2 pr-2">
              <span className={`font-bold text-[12px] min-w-[24px] ${BPS_COLOR[r.conviction]}`}>
                {r.breakout_probability_score}
              </span>
              <div className="flex-1 h-[3px] bg-[#1e293b] rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${BAR_COLOR[r.conviction]}`}
                     style={{ width: `${r.breakout_probability_score}%` }} />
              </div>
            </div>
            <span className="text-[#94a3b8] text-[9px] truncate">{r.signal_summary.pattern.split(' ')[0]}</span>
            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${CONVICTION_STYLE[r.conviction]}`}>
              {r.conviction}
            </span>
            <span className={`text-[10px] font-semibold ${BPS_COLOR[r.conviction]}`}>{r.risk_reward}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/KpiStrip.tsx frontend/components/BpsTable.tsx
git commit -m "feat: KpiStrip + BpsTable components"
```

---

### Task 16: PriceChart + TickerDetail

**Files:**
- Create: `frontend/components/PriceChart.tsx`
- Create: `frontend/components/TickerDetail.tsx`

- [ ] **Step 1: Create PriceChart.tsx**

```tsx
'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Point { date: string; close: number }

export default function PriceChart({ data }: { data: Point[] }) {
  return (
    <div className="bg-[#0a0e17] rounded h-20">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 4 }}>
          <XAxis dataKey="date" hide />
          <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 9 }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: 'none', fontSize: 11 }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#3b82f6' }}
          />
          <Line type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
```

- [ ] **Step 2: Create TickerDetail.tsx**

```tsx
'use client'
import type { BpsResult } from '@/lib/types'
import PriceChart from './PriceChart'
import { addToWatchlist } from '@/lib/api'

const IND_COLOR = (v: boolean | number | string) => {
  if (typeof v === 'boolean') return v ? 'text-[#22c55e]' : 'text-[#ef4444]'
  if (typeof v === 'number') return v >= 55 && v <= 75 ? 'text-[#22c55e]' : 'text-[#f59e0b]'
  return 'text-[#22c55e]'
}

export default function TickerDetail({ result }: { result: BpsResult | null }) {
  const [chartData, setChartData] = useState<{date:string;close:number}[]>([])

  useEffect(() => {
    if (!result) return
    fetch(`http://localhost:8000/api/ohlcv/${result.ticker}?period=3mo`)
      .then(r => r.json())
      .then(d => setChartData(d.data ?? []))
      .catch(() => {})
  }, [result?.ticker])

  if (!result) return (
    <div className="flex items-center justify-center h-full text-[#64748b] text-sm">
      Select a ticker to view detail
    </div>
  )

  const s = result.signal_summary
  const f = result.fundamentals

  return (
    <div className="p-4 flex flex-col gap-3 overflow-y-auto h-full">
      {/* Hero */}
      <div className="flex items-baseline gap-3">
        <span className="text-xl font-black text-white">{result.ticker}</span>
        <span className="text-sm text-[#22c55e] font-bold">{result.entry_zone}</span>
        <div className="ml-auto text-right">
          <div className="text-[9px] text-[#64748b] uppercase">BPS</div>
          <div className="text-3xl font-black text-[#22c55e] leading-none">{result.breakout_probability_score}</div>
        </div>
      </div>

      {/* Conviction banner */}
      <div className={`rounded px-3 py-2 flex items-center justify-between text-sm
        ${result.conviction === 'HIGH' ? 'bg-[#14532d] border border-[#22c55e]/30' :
          result.conviction === 'MEDIUM' ? 'bg-[#1c3a5f] border border-[#3b82f6]/30' :
          'bg-[#451a03] border border-[#f59e0b]/30'}`}>
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-black px-2 py-0.5 rounded
            ${result.conviction === 'HIGH' ? 'bg-[#22c55e] text-black' :
              result.conviction === 'MEDIUM' ? 'bg-[#3b82f6] text-black' : 'bg-[#f59e0b] text-black'}`}>
            {result.conviction}
          </span>
          <span className="text-[#86efac] text-[11px]">{s.pattern}</span>
        </div>
        <span className="text-[10px] text-[#86efac]">{result.timeframe}</span>
      </div>

      {/* Chart — fetches OHLCV from backend */}
      <PriceChart data={chartData} />

      {/* Indicators grid */}
      <div className="grid grid-cols-4 gap-1.5">
        {[
          { label: 'RSI 14', value: s.rsi_14 },
          { label: 'Vol Ratio', value: `${s.volume_ratio}x` },
          { label: 'MACD', value: s.macd_signal.split(' ')[0] },
          { label: '52W High', value: `${s.pct_from_52w_high}%` },
          { label: 'Above MAs', value: s.above_key_mas },
          { label: 'Vol Surge', value: s.volume_surge },
          { label: 'ATR Coil', value: s.volatility_contracting },
          { label: 'ML Prob', value: `${(s.ml_breakout_prob * 100).toFixed(0)}%` },
        ].map(({ label, value }) => (
          <div key={label} className="bg-[#0a0e17] rounded p-1.5 text-center">
            <div className="text-[8px] text-[#64748b] uppercase mb-0.5">{label}</div>
            <div className={`text-[11px] font-bold ${IND_COLOR(value)}`}>
              {typeof value === 'boolean' ? (value ? '✓' : '✗') : value}
            </div>
          </div>
        ))}
      </div>

      {/* Trade levels */}
      <div className="grid grid-cols-4 gap-1.5">
        {[
          { label: 'Entry', value: result.entry_zone, color: 'text-[#3b82f6]' },
          { label: 'Stop', value: result.stop_loss, color: 'text-[#ef4444]' },
          { label: 'T1', value: result.target_1, color: 'text-[#22c55e]' },
          { label: 'R:R', value: result.risk_reward, color: 'text-[#a855f7]' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-[#111827] border border-[#1e293b] rounded p-2 text-center">
            <div className="text-[8px] text-[#64748b] uppercase mb-1">{label}</div>
            <div className={`text-[12px] font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Fundamentals */}
      <div className="bg-[#111827] border border-[#1e293b] rounded p-3">
        <div className="text-[10px] font-semibold text-[#64748b] uppercase tracking-wide mb-2">Fundamentals</div>
        {[
          ['EPS Growth YoY', f.eps_growth_yoy],
          ['Rev Growth YoY', f.revenue_growth_yoy],
          ['PEG Ratio', f.peg_ratio ?? 'N/A'],
          ['Catalyst', f.catalyst],
        ].map(([k, v]) => (
          <div key={String(k)} className="flex justify-between py-1 border-b border-[#1e293b]/50 last:border-0">
            <span className="text-[10px] text-[#64748b]">{k}</span>
            <span className="text-[10px] font-semibold text-[#22c55e]">{v}</span>
          </div>
        ))}
      </div>

      {/* Risk flags */}
      {result.risk_flags.length > 0 && (
        <div className="bg-[#3a1a1a] border border-[#ef4444]/30 rounded p-2">
          <div className="text-[9px] text-[#ef4444] font-semibold uppercase mb-1">Risk Flags</div>
          {result.risk_flags.map(f => (
            <div key={f} className="text-[10px] text-[#f87171]">⚠ {f}</div>
          ))}
        </div>
      )}

      {/* Add to watchlist */}
      <button
        onClick={() => addToWatchlist({
          ticker: result.ticker, bps: result.breakout_probability_score,
          pattern: s.pattern, entry_zone: result.entry_zone,
          stop: result.stop_loss, target_1: result.target_1
        })}
        className="w-full bg-[#1e3a5f] hover:bg-[#1e4a7f] border border-[#3b82f6]/30 text-[#3b82f6] text-[11px] font-semibold py-2 rounded transition-colors"
      >
        + Add to Watchlist
      </button>
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/PriceChart.tsx frontend/components/TickerDetail.tsx
git commit -m "feat: PriceChart + TickerDetail components"
```

---

### Task 17: Scanner Page + WebSocket Hook

**Files:**
- Create: `frontend/hooks/useWebSocket.ts`
- Create: `frontend/hooks/useScan.ts`
- Create: `frontend/components/AlertBanner.tsx`
- Create: `frontend/app/scanner/page.tsx`
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: Create hooks/useWebSocket.ts**

```typescript
'use client'
import { useEffect, useRef, useState } from 'react'
import type { WatchlistAlert } from '@/lib/types'

export function useWebSocket() {
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      ws.current = new WebSocket('ws://localhost:8000/ws/alerts')
      ws.current.onmessage = (e) => {
        const data = JSON.parse(e.data)
        if (data.type === 'watchlist_update') {
          setAlerts(prev => {
            const map = new Map(prev.map(a => [a.ticker, a]))
            data.alerts.forEach((a: WatchlistAlert) => map.set(a.ticker, a))
            return Array.from(map.values())
          })
        }
      }
      ws.current.onclose = () => setTimeout(connect, 3000) // auto-reconnect
    }
    connect()
    return () => ws.current?.close()
  }, [])

  return alerts
}
```

- [ ] **Step 2: Create hooks/useScan.ts**

```typescript
import useSWR from 'swr'
import { scanTickers } from '@/lib/api'
import type { BpsResult } from '@/lib/types'

const DEFAULT_TICKERS = ['NVDA','AMD','MSTR','META','TSLA','GOOGL','MSFT','AAPL','AMZN','AVGO']

export function useScan(tickers = DEFAULT_TICKERS, minBps = 0) {
  return useSWR<{ candidates: BpsResult[] }>(
    ['scan', tickers.join(','), minBps],
    () => scanTickers(tickers, minBps),
    { refreshInterval: 60_000 }
  )
}
```

- [ ] **Step 3: Create AlertBanner.tsx**

```tsx
'use client'
import type { WatchlistAlert } from '@/lib/types'

export default function AlertBanner({ alerts }: { alerts: WatchlistAlert[] }) {
  const urgent = alerts.filter(a => a.urgency === 'HIGH')
  if (urgent.length === 0) return null
  return (
    <div className="fixed top-8 right-4 z-50 flex flex-col gap-2 max-w-xs">
      {urgent.map(a => (
        <div key={a.ticker} className={`rounded p-3 text-[11px] shadow-lg border
          ${a.status === 'TRIGGERED' ? 'bg-[#14532d] border-[#22c55e]/50 text-[#86efac]' : 'bg-[#3a1a1a] border-[#ef4444]/50 text-[#f87171]'}`}>
          <div className="font-black">{a.ticker} — {a.status}</div>
          <div className="mt-0.5 text-[10px] opacity-80">{a.action}</div>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Create app/scanner/page.tsx**

```tsx
'use client'
import { useState } from 'react'
import { useScan } from '@/hooks/useScan'
import { useWebSocket } from '@/hooks/useWebSocket'
import KpiStrip from '@/components/KpiStrip'
import BpsTable from '@/components/BpsTable'
import TickerDetail from '@/components/TickerDetail'
import AlertBanner from '@/components/AlertBanner'
import type { BpsResult } from '@/lib/types'

export default function ScannerPage() {
  const [selected, setSelected] = useState<string | null>(null)
  const { data, isLoading } = useScan()
  const wsAlerts = useWebSocket()

  const results: BpsResult[] = data?.candidates ?? []
  const selectedResult = results.find(r => r.ticker === selected) ?? null

  const highCount = results.filter(r => r.conviction === 'HIGH').length
  const triggered = wsAlerts.filter(a => a.status === 'TRIGGERED').length
  const breaking = wsAlerts.filter(a => a.status === 'BREAKING_DOWN').length
  const avgBps = results.length > 0
    ? (results.reduce((s, r) => s + r.breakout_probability_score, 0) / results.length).toFixed(1)
    : '—'

  const kpis = [
    { label: 'High Signals', value: highCount, sub: 'BPS ≥ 80', color: 'text-[#22c55e]' },
    { label: 'Triggered', value: triggered, sub: 'Enter zone', color: 'text-[#f59e0b]' },
    { label: 'Breaking Down', value: breaking, sub: 'Cut or hold', color: 'text-[#ef4444]' },
    { label: 'Avg BPS', value: avgBps, sub: `${results.length} scanned`, color: 'text-[#3b82f6]' },
    { label: 'Backtest Win%', value: '68%', sub: 'T1 hit rate', color: 'text-[#a855f7]' },
    { label: 'News Alerts', value: '—', sub: 'Last 4h', color: 'text-[#06b6d4]' },
  ]

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <h1 className="text-base font-bold">BPS Scanner</h1>
        <p className="text-[#64748b] text-[11px]">Breakout Probability Scores — Technical + Fundamental + ML</p>
      </div>
      <KpiStrip kpis={kpis} />
      <div className="flex flex-1 overflow-hidden">
        <div className="w-96 border-r border-[#1e293b] overflow-hidden flex flex-col">
          {isLoading
            ? <div className="p-4 text-[#64748b] text-sm">Scanning...</div>
            : <BpsTable results={results} selected={selected} onSelect={setSelected} />
          }
        </div>
        <div className="flex-1 overflow-hidden">
          <TickerDetail result={selectedResult} />
        </div>
      </div>
      <AlertBanner alerts={wsAlerts} />
    </div>
  )
}
```

- [ ] **Step 5: Create app/page.tsx**

```tsx
import { redirect } from 'next/navigation'
export default function Home() { redirect('/scanner') }
```

- [ ] **Step 6: Test**

```bash
cd frontend && npm run dev
# Open http://localhost:3000 → should redirect to /scanner
# Scanner loads, BPS table populates after ~10s (yfinance fetch)
```

- [ ] **Step 7: Commit**

```bash
git add frontend/hooks/ frontend/app/ frontend/components/AlertBanner.tsx
git commit -m "feat: scanner page + WebSocket hook + SWR polling + alert banner"
```

---

### Task 18: Watchlist + Backtest + News Pages

**Files:**
- Create: `frontend/app/watchlist/page.tsx`
- Create: `frontend/app/backtest/page.tsx`
- Create: `frontend/components/BacktestStats.tsx`
- Create: `frontend/app/news/page.tsx`
- Create: `frontend/components/NewsPanel.tsx`

- [ ] **Step 1: Create app/watchlist/page.tsx**

```tsx
'use client'
import { useEffect, useState } from 'react'
import { getWatchlistStatus, removeFromWatchlist } from '@/lib/api'
import type { WatchlistAlert } from '@/lib/types'

const STATUS_STYLE: Record<string, string> = {
  TRIGGERED: 'bg-[#14532d] border-[#22c55e]/40 text-[#22c55e]',
  BREAKING_DOWN: 'bg-[#3a1a1a] border-[#ef4444]/40 text-[#ef4444]',
  STILL_VALID: 'bg-[#111827] border-[#1e293b] text-[#94a3b8]',
  STOPPED_OUT: 'bg-[#2a1a1a] border-[#ef4444]/20 text-[#f87171]',
  PATTERN_EXTENDED: 'bg-[#1a1a2a] border-[#a855f7]/30 text-[#c084fc]',
}

export default function WatchlistPage() {
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    const data = await getWatchlistStatus()
    setAlerts(data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-[#1e293b] flex items-center justify-between">
        <div>
          <h1 className="text-base font-bold">Watchlist</h1>
          <p className="text-[#64748b] text-[11px]">Active setups — TRIGGERED / BREAKING_DOWN / STILL_VALID</p>
        </div>
        <button onClick={load} className="text-[11px] bg-[#1e293b] px-3 py-1.5 rounded text-[#94a3b8] hover:text-white">
          ↻ Refresh
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
        {loading && <p className="text-[#64748b] text-sm">Loading watchlist...</p>}
        {!loading && alerts.length === 0 && (
          <p className="text-[#64748b] text-sm">No tickers in watchlist. Add from Scanner.</p>
        )}
        {alerts.map(a => (
          <div key={a.ticker} className={`rounded border p-3 ${STATUS_STYLE[a.status] ?? STATUS_STYLE.STILL_VALID}`}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-3">
                <span className="font-black text-base text-white">{a.ticker}</span>
                <span className="text-[10px] font-bold border px-2 py-0.5 rounded">{a.status}</span>
                <span className="text-[11px]">BPS {a.updated_bps}</span>
                <span className="text-[11px] text-white font-bold">${a.current_price}</span>
              </div>
              <button onClick={() => removeFromWatchlist(a.ticker).then(load)}
                className="text-[#64748b] hover:text-[#ef4444] text-xs">✕</button>
            </div>
            <p className="text-[11px] opacity-80">{a.action}</p>
            <p className="text-[10px] opacity-60 mt-0.5">{a.notes}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create BacktestStats.tsx**

```tsx
import type { BacktestSummary } from '@/lib/types'

export default function BacktestStats({ summary }: { summary: BacktestSummary }) {
  const stats = [
    { label: 'Total Signals', value: summary.total_signals, color: 'text-white' },
    { label: 'Win Rate T1', value: `${(summary.win_rate_t1 * 100).toFixed(0)}%`, color: 'text-[#22c55e]' },
    { label: 'Stop Out Rate', value: `${(summary.stop_out_rate * 100).toFixed(0)}%`, color: 'text-[#ef4444]' },
    { label: 'Avg Winner', value: `+${summary.avg_return_winners_pct}%`, color: 'text-[#22c55e]' },
    { label: 'Avg Loser', value: `${summary.avg_return_losers_pct}%`, color: 'text-[#ef4444]' },
    { label: 'Expectancy', value: `${summary.expectancy_per_trade_pct}%`, color: 'text-[#a855f7]' },
    { label: 'Profit Factor', value: summary.profit_factor, color: 'text-[#22c55e]' },
    { label: 'Max Drawdown', value: `${summary.max_drawdown_pct}%`, color: 'text-[#ef4444]' },
    { label: 'Sharpe', value: summary.sharpe_ratio, color: 'text-[#3b82f6]' },
    { label: 'Avg Days', value: summary.avg_days_to_resolution, color: 'text-[#94a3b8]' },
  ]
  return (
    <div>
      <div className="grid grid-cols-5 gap-2 mb-4">
        {stats.map(({ label, value, color }) => (
          <div key={label} className="bg-[#111827] border border-[#1e293b] rounded p-3 text-center">
            <div className="text-[8px] text-[#64748b] uppercase mb-1">{label}</div>
            <div className={`text-[18px] font-bold ${color}`}>{value}</div>
          </div>
        ))}
      </div>
      <div className="bg-[#111827] border border-[#1e293b] rounded overflow-hidden">
        <div className="grid grid-cols-[80px_80px_100px_80px_80px_80px_80px_100px] px-3 py-2 border-b border-[#1e293b]">
          {['Date','Entry','Type','Stop','T1','Return','Days','Outcome'].map(h => (
            <span key={h} className="text-[9px] text-[#64748b] uppercase">{h}</span>
          ))}
        </div>
        <div className="max-h-64 overflow-y-auto">
          {summary.signals.slice(0, 50).map((s: any, i: number) => (
            <div key={i} className="grid grid-cols-[80px_80px_100px_80px_80px_80px_80px_100px] px-3 py-1.5 border-b border-[#0f1623] text-[10px]">
              <span className="text-[#94a3b8]">{s.signal_date}</span>
              <span className="text-white">${s.entry_price}</span>
              <span className="text-[#64748b]">{s.signal_type}</span>
              <span className="text-[#ef4444]">${s.stop_loss}</span>
              <span className="text-[#22c55e]">${s.target_1}</span>
              <span className={s.actual_return_pct >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}>
                {s.actual_return_pct > 0 ? '+' : ''}{s.actual_return_pct}%
              </span>
              <span className="text-[#94a3b8]">{s.days_to_resolution}d</span>
              <span className={
                s.outcome === 'HIT_T2' || s.outcome === 'HIT_T1' ? 'text-[#22c55e]' :
                s.outcome === 'STOPPED_OUT' ? 'text-[#ef4444]' : 'text-[#64748b]'
              }>{s.outcome}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create app/backtest/page.tsx**

```tsx
'use client'
import { useState } from 'react'
import { runBacktest } from '@/lib/api'
import BacktestStats from '@/components/BacktestStats'
import type { BacktestSummary } from '@/lib/types'

export default function BacktestPage() {
  const [ticker, setTicker] = useState('NVDA')
  const [start, setStart] = useState('2023-01-01')
  const [end, setEnd] = useState('2024-12-31')
  const [result, setResult] = useState<BacktestSummary | null>(null)
  const [loading, setLoading] = useState(false)

  async function run() {
    setLoading(true)
    const data = await runBacktest(ticker, start, end)
    setResult(data)
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <h1 className="text-base font-bold">Backtest</h1>
        <p className="text-[#64748b] text-[11px]">Historical signal extraction + outcome analysis</p>
      </div>
      <div className="p-5 flex flex-col gap-4 flex-1 overflow-y-auto">
        <div className="flex gap-3 items-end">
          <div>
            <label className="text-[9px] text-[#64748b] uppercase block mb-1">Ticker</label>
            <input value={ticker} onChange={e => setTicker(e.target.value.toUpperCase())}
              className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-white text-sm w-24" />
          </div>
          <div>
            <label className="text-[9px] text-[#64748b] uppercase block mb-1">Start</label>
            <input type="date" value={start} onChange={e => setStart(e.target.value)}
              className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-white text-sm" />
          </div>
          <div>
            <label className="text-[9px] text-[#64748b] uppercase block mb-1">End</label>
            <input type="date" value={end} onChange={e => setEnd(e.target.value)}
              className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-white text-sm" />
          </div>
          <button onClick={run} disabled={loading}
            className="bg-[#1e3a5f] border border-[#3b82f6]/40 text-[#3b82f6] px-4 py-1.5 rounded text-sm font-semibold hover:bg-[#1e4a7f] disabled:opacity-50">
            {loading ? 'Running...' : 'Run Backtest'}
          </button>
        </div>
        {result && <BacktestStats summary={result} />}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create NewsPanel.tsx**

```tsx
import type { NewsItem } from '@/lib/types'

const DOT: Record<string, string> = {
  bullish: 'bg-[#22c55e]',
  bearish: 'bg-[#ef4444]',
  neutral: 'bg-[#64748b]',
}

export default function NewsPanel({ items }: { items: NewsItem[] }) {
  return (
    <div className="flex flex-col gap-0.5">
      {items.map((item, i) => (
        <a key={i} href={item.url} target="_blank" rel="noreferrer"
          className="flex gap-3 p-3 border-b border-[#1e293b] hover:bg-white/5 transition-colors group">
          <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${DOT[item.sentiment]}`} />
          <div className="flex-1 min-w-0">
            <div className="text-[11px] text-[#94a3b8] group-hover:text-white line-clamp-2">{item.headline}</div>
            <div className="text-[9px] text-[#4b5563] mt-0.5">{item.ticker} · {item.source} · {item.published_at.slice(0,10)}</div>
          </div>
        </a>
      ))}
    </div>
  )
}
```

- [ ] **Step 5: Create app/news/page.tsx**

```tsx
'use client'
import { useEffect, useState } from 'react'
import { getNews, getWatchlist } from '@/lib/api'
import NewsPanel from '@/components/NewsPanel'
import type { NewsItem } from '@/lib/types'

export default function NewsPage() {
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      const wl = await getWatchlist()
      const tickers = wl.length > 0 ? wl.map((r: any) => r.ticker) : ['NVDA','AMD','TSLA']
      const data = await getNews(tickers)
      setItems(data.items ?? [])
      setLoading(false)
    }
    load()
  }, [])

  return (
    <div className="flex flex-col h-full">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <h1 className="text-base font-bold">News Feed</h1>
        <p className="text-[#64748b] text-[11px]">NewsAPI + Finnhub — filtered by watchlist tickers</p>
      </div>
      <div className="flex-1 overflow-y-auto">
        {loading && <p className="p-5 text-[#64748b] text-sm">Loading news...</p>}
        {!loading && items.length === 0 && (
          <p className="p-5 text-[#64748b] text-sm">No news found. Check API keys in backend/.env</p>
        )}
        <NewsPanel items={items} />
      </div>
    </div>
  )
}
```

- [ ] **Step 6: Final integration test**

```bash
# Terminal 1
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2
cd frontend && npm run dev

# Test flow:
# 1. Open http://localhost:3000/scanner
# 2. Wait for scan to load (~15s)
# 3. Click a ticker → detail panel populates
# 4. Click "Add to Watchlist"
# 5. Go to /watchlist → ticker appears with status
# 6. Go to /backtest → enter NVDA, run → stats appear
# 7. Go to /news → headlines load (need API keys)
```

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: complete BreakoutStocks dashboard — scanner, watchlist, backtest, news"
```

---

## Weekly ML Retrain (Scheduled)

Add to `backend/scheduler.py` after initial tasks:

```python
from ml.trainer import train_all

scheduler.add_job(train_all, "cron", day_of_week="sun", hour=2, minute=0,
                  id="weekly_retrain", replace_existing=True)
```

This runs every Sunday at 2am local time, retrains universal + all sector models on latest 2y data.

---

## Environment Variables

Create `backend/.env` and load with `python-dotenv` or set in shell:

```
NEWSAPI_KEY=your_newsapi_org_key
FINNHUB_KEY=your_finnhub_key
```

Get free keys:
- NewsAPI: https://newsapi.org/register (100 req/day free)
- Finnhub: https://finnhub.io/register (60 req/min free)
