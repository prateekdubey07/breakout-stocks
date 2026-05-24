# BreakoutStocks Dashboard — Design Spec
**Date:** 2026-05-23  
**Status:** Approved  
**Scope:** Full-stack breakout scanner platform — FastAPI backend + Next.js frontend

---

## Overview

Personal-use trading dashboard that combines technical price-action signals with fundamental data and news to score breakout candidates using a Breakout Probability Score (BPS). Matches the visual language of the RTO Options Platform (dark theme, sidebar nav, dense KPI cards, data tables, conviction badges).

---

## System Architecture

```
Next.js (port 3000)
├── Pages: Scanner / Watchlist / Backtest / News / Alerts / Journal
├── WebSocket client → ws://localhost:8000/ws/alerts
└── REST client → http://localhost:8000/api/*

FastAPI (port 8000)
├── BPS scoring engine (pandas-ta indicators)
├── Backtesting pipeline (signal extraction + stat aggregation)
├── Watchlist monitor (APScheduler 60s polling → WebSocket push)
├── News aggregator (NewsAPI.org + Finnhub free tier)
├── CSV upload handler (manual OHLCV import)
└── SQLite persistence layer
```

**Tech Stack:**
| Layer | Technology |
|---|---|
| Backend | FastAPI, Python 3.11, pandas-ta, yfinance, SQLite, APScheduler |
| Frontend | Next.js 14 App Router, Tailwind CSS, Recharts, SWR |
| News | NewsAPI.org + Finnhub free tier |
| Real-time | WebSocket (FastAPI native) + SWR polling fallback (60s) |
| Deployment | Local, no auth required |

---

## BPS Scoring Engine

### Technical Scoring (65 pts)
| Signal | Points |
|---|---|
| Volume > 150% of 20d avg | +10 |
| Price within 3% of 52w high | +8 |
| 5-day ATR < 75% of 20-day ATR (coiling) | +7 |
| RSI(14) between 55–75 | +8 |
| MACD bullish crossover or histogram positive | +7 |
| Price above 20, 50, and 200 SMA simultaneously | +5 |
| Confirmed pattern (Cup&Handle/FlatBase/BullFlag/AscTriangle/VolSqueeze/VCP) | +20 |
| Pattern forming, not yet triggered | +10 |

> **Pattern detection:** XGBoost classifier replaces hardcoded +20/+10 scoring.
> - Features: ATR ratio, RSI, MACD histogram slope, volume trend, price-to-resistance distance, pivot structure, OBV trend
> - Label: "price rose >8% within 10 sessions" (auto-generated from OHLCV history)
> - Output: breakout_probability (0–1) → maps to 0–20 pts in BPS
> - Model registry: `models/universal.pkl` (S&P 500 trained, fallback for all tickers) + `models/sector_{name}.pkl` (per-sector, overrides universal when available)
> - Inference: use sector model if exists for ticker's sector, else universal
> - Retrain: APScheduler every Sunday, last 2 years of OHLCV data
> - Sectors covered: Technology, Biotech, Energy, Financials, Consumer

### Fundamental Scoring (35 pts)
| Signal | Points |
|---|---|
| EPS growth YoY > 20% | +8 |
| Revenue growth YoY > 15% | +6 |
| Earnings beat last quarter | +4 |
| Guidance raised | +2 |
| PEG ratio < 1.5 | +4 |
| Net institutional accumulation (OBV uptrend proxy — no 13F data from yfinance) | +3 |
| Analyst upgrade or PT raise in last 30 days | +3 |
| Earnings 2–4 weeks away | +2 |
| Binary catalyst pending | +3 |

### Risk Filters
**Hard disqualify (BPS = 0):** share dilution, short interest > 25% float, SEC investigation/fraud, ADV < 500K shares  
**Yellow flag (−15 BPS):** negative OCF without profitability timeline, earnings within 5 trading days

### Conviction Tiers
| BPS | Tier | Action |
|---|---|---|
| 80–100 | HIGH | Act within hours |
| 65–79 | MEDIUM | Monitor, wait for trigger |
| 50–64 | WATCH | Setup forming |
| < 50 | PASS | Skip |

---

## API Routes

```
POST /api/scan
  body: { tickers: string[], min_bps: number }
  returns: { candidates: BpsResult[] }  — ranked by BPS desc

POST /api/analyze
  body: { ticker: string }
  returns: BpsResult — full breakdown + entry/stop/targets + narrative

POST /api/backtest
  body: { ticker: string, start: string, end: string }
  returns: { signals: Signal[], summary: BacktestSummary }

GET  /api/watchlist
PUT  /api/watchlist              body: { ticker: string }
DELETE /api/watchlist/:id
GET  /api/watchlist/status       → runs Agent 3 alert classification

GET  /api/news?tickers=NVDA,AMD  → merged NewsAPI + Finnhub, deduped, 20 items

POST /api/upload/csv             → OHLCV file → stored in SQLite

WS   /ws/alerts                  → pushes { ticker, status, urgency, action, updated_bps }
                                   only on status change, every 60s poll cycle
```

---

## SQLite Schema

```sql
watchlist    (id, ticker, added_at, original_bps, original_pattern, entry_zone, stop, target_1)
signals      (id, ticker, signal_date, signal_type, entry_price, stop_loss, target_1, target_2, bps_at_signal, pattern_context)
backtest_runs(id, ticker, start_date, end_date, ran_at, summary_json)
news_cache   (id, ticker, headline, source, url, sentiment, published_at, fetched_at)
```

---

## Frontend Structure

```
app/
├── layout.tsx              — sidebar + top status bar
├── scanner/page.tsx        — BPS table + ticker detail panel
├── watchlist/page.tsx      — alert feed with status classification
├── backtest/page.tsx       — date picker + equity curve + stats grid
├── news/page.tsx           — news feed filtered by watchlist
├── alerts/page.tsx         — WebSocket alert history log
└── journal/page.tsx        — trade log table

components/
├── KpiStrip.tsx            — 6 KPI cards (always visible)
├── BpsTable.tsx            — sortable rows with BPS bars + conviction badges
├── TickerDetail.tsx        — chart + indicators + trade levels + fundamentals + news
├── PriceChart.tsx          — Recharts LineChart + volume bars
├── BacktestStats.tsx       — win rate, Sharpe, drawdown, equity curve
├── NewsPanel.tsx           — bull/bear/neutral tagged news items
├── AlertBanner.tsx         — WebSocket TRIGGERED toasts
└── WatchlistRow.tsx        — status rows with urgency color coding

hooks/
├── useWebSocket.ts         — connects to ws://localhost:8000/ws/alerts
├── useScan.ts              — SWR polling fallback every 60s
└── useBacktest.ts          — trigger backtest + stream progress
```

---

## UI Behavior

- Click ticker in BpsTable → TickerDetail panel updates inline (no page navigation)
- TRIGGERED alert → toast banner + row highlights with green pulse animation
- BREAKING_DOWN → red pulse + auto-scroll to row in watchlist
- Backtest tab → date range picker → runs async → equity curve + stats appear on complete
- WebSocket disconnect → silent fallback to SWR 60s polling, reconnects automatically
- Top status bar always shows: signal count, triggered count, win rate, expectancy, Sharpe

---

## Visual Design

Matches RTO Options Platform:
- Background: `#0d1117` / `#0a0e17`
- Sidebar: collapsible, `#0a0e17`, active item has left green border
- KPI cards: `#111827` with colored top border per metric type
- Conviction colors: green `#22c55e` (HIGH), blue `#3b82f6` (MEDIUM), amber `#f59e0b` (WATCH), red `#ef4444` (BREAKING/DISQUAL)
- Font: system sans-serif, monospace for price/number data
- Chart: dark `#0a0e17` background, blue line, green volume

---

## Data Flow: Backtest Pipeline

```
POST /api/backtest
  → Agent 4 (Signal Extractor): scans OHLCV for signal dates
       criteria: vol > 150% 20d avg, close above 20d resistance,
                 RSI 50–75, price above 50 SMA
  → Agent 2 (Backtest Analyst): evaluates each signal outcome
       HIT_T1 / HIT_T2 / STOPPED_OUT / STILL_OPEN
       computes: MFE, MAE, days-to-resolution, return%
  → aggregates: win_rate, profit_factor, Sharpe, max_drawdown, expectancy
  → returns full summary + per-signal detail to frontend
```

---

## Data Flow: Real-Time Alerts

```
APScheduler (every 60s)
  → fetches current prices for all watchlist tickers via yfinance
  → re-scores each: BPS + RSI + volume ratio + MACD + price vs entry zone
  → compares to previous state
  → if status changed: pushes via WebSocket to all connected clients
  → statuses: TRIGGERED / STILL_VALID / PATTERN_EXTENDED / BREAKING_DOWN / STOPPED_OUT
```

---

## Out of Scope

- Authentication (personal tool, local only)
- Paid data feeds
- Options Greeks or options flow
- Mobile layout
- Multi-user / multi-tenant
