import asyncio
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_conn
from models import ScanRequest, BpsResult, BacktestRequest
from scoring.bps_engine import score_ticker
from data.fetcher import fetch_ohlcv, prefetch_ohlcv_batch
from backtest.extractor import extract_signals
from backtest.analyst import evaluate_signals
from websocket.manager import manager
from watchlist.monitor import run_watchlist_scan
from news.aggregator import fetch_news
from data.csv_handler import process_csv_upload
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    from scheduler import setup_scheduler, scheduler
    setup_scheduler()
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="BreakoutStocks API", lifespan=lifespan)

executor = ThreadPoolExecutor(max_workers=8)

import os as _os
_CORS_ORIGINS = [o.strip() for o in _os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _save_scan_results(tickers: list, candidates: list, trigger: str = "manual"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO scan_results (tickers_json, results_json, trigger) VALUES (?,?,?)",
        (json.dumps(tickers), json.dumps([c.dict() if hasattr(c, 'dict') else c for c in candidates]), trigger)
    )
    # keep only last 50 scans
    conn.execute("DELETE FROM scan_results WHERE id NOT IN (SELECT id FROM scan_results ORDER BY id DESC LIMIT 50)")
    conn.commit()
    conn.close()


async def _score_timeout(loop, executor, ticker: str, timeout: float = 12.0):
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(executor, score_ticker, ticker),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] {ticker} skipped after {timeout:.0f}s")
        return None
    except Exception as exc:
        print(f"[ERROR] {ticker}: {exc}")
        return None


@app.post("/api/scan")
async def scan(req: ScanRequest):
    loop = asyncio.get_event_loop()
    # ONE Alpaca call fetches all tickers' OHLCV — drops 100 per-ticker calls to 1
    await loop.run_in_executor(executor, prefetch_ohlcv_batch, req.tickers, "2y")
    results = await asyncio.gather(*[
        _score_timeout(loop, executor, t)
        for t in req.tickers
    ])
    candidates = [
        r for r in results
        if r is not None and r.breakout_probability_score >= req.min_bps
    ]
    candidates.sort(key=lambda x: x.breakout_probability_score, reverse=True)
    _save_scan_results(req.tickers, candidates, trigger="manual")
    return {"candidates": candidates}


@app.get("/api/scan-results/latest")
def get_latest_scan():
    conn = get_conn()
    row = conn.execute("SELECT * FROM scan_results ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return {"candidates": [], "scanned_at": None, "trigger": None}
    return {
        "candidates": json.loads(row["results_json"]),
        "scanned_at": row["scanned_at"],
        "trigger": row["trigger"],
    }


@app.post("/api/analyze")
async def analyze(body: dict):
    ticker = body.get("ticker", "").upper()
    if not ticker:
        raise HTTPException(400, "ticker required")
    import asyncio
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, score_ticker, ticker)
    return result


@app.get("/api/ohlcv/{ticker}")
async def ohlcv(ticker: str, period: str = "3mo"):
    import asyncio
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(executor, fetch_ohlcv, ticker.upper(), period)
    data = [{"date": str(d.date()), "close": round(float(c), 2)}
            for d, c in zip(df.index, df["Close"])]
    return {"data": data}


@app.post("/api/backtest")
async def backtest(req: BacktestRequest):
    import asyncio
    loop = asyncio.get_event_loop()
    signals = await loop.run_in_executor(executor, extract_signals, req.ticker, req.start, req.end)
    summary = evaluate_signals(signals, req.starting_capital)
    conn = get_conn()
    conn.execute(
        "INSERT INTO backtest_runs (ticker, start_date, end_date, summary_json) VALUES (?,?,?,?)",
        (req.ticker, req.start, req.end, json.dumps(summary))
    )
    conn.commit()
    conn.close()
    return summary


@app.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/api/default-tickers")
def get_default_tickers():
    conn = get_conn()
    rows = [r[0] for r in conn.execute("SELECT ticker FROM default_tickers ORDER BY ticker").fetchall()]
    conn.close()
    return rows


@app.get("/api/watchlist")
def get_watchlist():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM watchlist").fetchall()]
    conn.close()
    return rows


@app.get("/api/watchlist/status")
async def watchlist_status():
    import asyncio
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(executor, run_watchlist_scan)
    return results


@app.put("/api/watchlist")
def add_to_watchlist(body: dict):
    ticker = body.get("ticker", "").upper()
    if not ticker:
        raise HTTPException(400, "ticker required")
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO watchlist (ticker, original_bps, original_pattern, entry_zone, stop, target_1) VALUES (?,?,?,?,?,?)",
        (ticker, body.get("bps"), body.get("pattern"), body.get("entry_zone"),
         body.get("stop"), body.get("target_1"))
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


@app.get("/api/news")
async def news(tickers: str = Query(...)):
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    import asyncio
    loop = asyncio.get_event_loop()
    items = await loop.run_in_executor(executor, fetch_news, ticker_list)
    return {"items": items}


@app.get("/api/paper-trades")
def get_paper_trades():
    conn = get_conn()
    rows = [dict(r) for r in conn.execute("SELECT * FROM paper_trades ORDER BY entry_date DESC").fetchall()]
    conn.close()
    # attach live price / unrealized PnL for open positions
    for row in rows:
        if row["status"] == "OPEN":
            try:
                from data.fetcher import fetch_ohlcv
                df = fetch_ohlcv(row["ticker"], period="5d")
                live = float(df["Close"].iloc[-1])
                row["live_price"] = round(live, 2)
                row["unrealized_pnl_usd"] = round((live - row["entry_price"]) * row["shares"], 2)
                row["unrealized_pnl_pct"] = round((live - row["entry_price"]) / row["entry_price"] * 100, 2)
            except Exception:
                row["live_price"] = None
                row["unrealized_pnl_usd"] = None
                row["unrealized_pnl_pct"] = None
    return rows


@app.post("/api/paper-trades")
def open_paper_trade(body: dict):
    ticker = body.get("ticker", "").upper()
    entry_price = float(body.get("entry_price", 0))
    shares = float(body.get("shares", 0))
    if not ticker or entry_price <= 0 or shares <= 0:
        raise HTTPException(400, "ticker, entry_price and shares required")
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO paper_trades (ticker, entry_price, shares, stop_loss, target_1, target_2, notes) VALUES (?,?,?,?,?,?,?)",
        (ticker, entry_price, shares, body.get("stop_loss"), body.get("target_1"), body.get("target_2"), body.get("notes", ""))
    )
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": trade_id, "ok": True}


@app.patch("/api/paper-trades/{trade_id}/close")
def close_paper_trade(trade_id: int, body: dict):
    exit_price = float(body.get("exit_price", 0))
    if exit_price <= 0:
        raise HTTPException(400, "exit_price required")
    conn = get_conn()
    row = conn.execute("SELECT * FROM paper_trades WHERE id=?", (trade_id,)).fetchone()
    if not row:
        raise HTTPException(404, "trade not found")
    row = dict(row)
    pnl_usd = round((exit_price - row["entry_price"]) * row["shares"], 2)
    pnl_pct = round((exit_price - row["entry_price"]) / row["entry_price"] * 100, 2)
    conn.execute(
        "UPDATE paper_trades SET exit_price=?, exit_date=date('now'), status='CLOSED', pnl_usd=?, pnl_pct=? WHERE id=?",
        (exit_price, pnl_usd, pnl_pct, trade_id)
    )
    conn.commit()
    conn.close()
    return {"pnl_usd": pnl_usd, "pnl_pct": pnl_pct, "ok": True}


@app.delete("/api/paper-trades/{trade_id}")
def delete_paper_trade(trade_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM paper_trades WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/scan/gap")
async def gap_scanner(min_gap_pct: float = 2.0):
    """Return tickers whose last daily close gapped vs prior close by >= min_gap_pct%.
    Uses OHLCV already cached from Alpaca batch; no extra API calls needed."""
    conn = get_conn()
    tickers = [r[0] for r in conn.execute("SELECT ticker FROM default_tickers ORDER BY ticker").fetchall()]
    conn.close()

    # Prefetch if cache empty
    from data.fetcher import _OHLCV_BATCH_CACHE, prefetch_ohlcv_batch
    if not _OHLCV_BATCH_CACHE:
        await asyncio.get_event_loop().run_in_executor(executor, prefetch_ohlcv_batch, tickers, "5d")

    results = []
    for ticker in tickers:
        df = _OHLCV_BATCH_CACHE.get(ticker.upper())
        if df is None or len(df) < 2:
            continue
        prior_close = float(df["Close"].iloc[-2])
        last_close  = float(df["Close"].iloc[-1])
        if prior_close <= 0:
            continue
        gap_pct = round((last_close - prior_close) / prior_close * 100, 2)
        if abs(gap_pct) >= min_gap_pct:
            results.append({
                "ticker": ticker,
                "gap_pct": gap_pct,
                "last_close": round(last_close, 2),
                "prior_close": round(prior_close, 2),
                "direction": "up" if gap_pct > 0 else "down",
            })
    results.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
    return {"gaps": results, "threshold_pct": min_gap_pct}


@app.post("/api/upload/csv")
async def upload_csv(ticker: str, file: UploadFile = File(...)):
    contents = await file.read()
    return process_csv_upload(contents, ticker)


@app.get("/debug/{ticker}")
async def debug_ticker(ticker: str):
    import asyncio
    from data.fetcher import fetch_fundamentals
    from scoring.technical import compute_technical_score
    loop = asyncio.get_event_loop()
    df = await loop.run_in_executor(executor, fetch_ohlcv, ticker.upper(), "2y")
    info = await loop.run_in_executor(executor, fetch_fundamentals, ticker.upper())
    if df.empty or len(df) < 50:
        return {"error": "insufficient OHLCV data", "rows": len(df)}
    tech = compute_technical_score(df)
    return {
        "ticker": ticker.upper(),
        "ohlcv_rows": len(df),
        "last_close": round(float(df["Close"].iloc[-1]), 2),
        "fundamentals": info,
        "technical": {
            "volume_ratio": tech.volume_ratio,
            "rsi_14": tech.rsi_14,
            "macd_bullish": tech.macd_bullish,
            "macd_signal": tech.macd_signal,
            "pct_from_52w_high": tech.pct_from_52w_high,
            "volatility_contracting": tech.volatility_contracting,
            "above_20ma": tech.above_20ma,
            "above_50ma": tech.above_50ma,
            "above_200ma": tech.above_200ma,
            "ma20_price": tech.ma20_price,
            "pattern": tech.pattern,
            "pattern_score": tech.pattern_score,
            "technical_score": tech.total,
        },
    }
