from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, get_conn
from models import ScanRequest, BpsResult, BacktestRequest
from scoring.bps_engine import score_ticker
from data.fetcher import fetch_ohlcv
from backtest.extractor import extract_signals
from backtest.analyst import evaluate_signals
import json


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="BreakoutStocks API", lifespan=lifespan)

executor = ThreadPoolExecutor(max_workers=8)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


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
    summary = evaluate_signals(signals)
    conn = get_conn()
    conn.execute(
        "INSERT INTO backtest_runs (ticker, start_date, end_date, summary_json) VALUES (?,?,?,?)",
        (req.ticker, req.start, req.end, json.dumps(summary))
    )
    conn.commit()
    conn.close()
    return summary
