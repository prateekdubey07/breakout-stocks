const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function scanTickers(tickers: string[], minBps = 0) {
  const BATCH = 20
  const all: any[] = []
  for (let i = 0; i < tickers.length; i += BATCH) {
    const batch = tickers.slice(i, i + BATCH)
    const res = await fetch(`${BASE}/api/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tickers: batch, min_bps: minBps }),
    })
    const data = await res.json()
    const candidates = Array.isArray(data) ? data : (data.candidates ?? [])
    all.push(...candidates)
  }
  return {
    candidates: all.sort((a, b) => b.breakout_probability_score - a.breakout_probability_score),
  }
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

export async function runBacktest(ticker: string, start: string, end: string, starting_capital = 10000) {
  const res = await fetch(`${BASE}/api/backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ticker, start, end, starting_capital }),
  })
  return res.json()
}

export async function getDefaultTickers(): Promise<string[]> {
  return (await fetch(`${BASE}/api/default-tickers`)).json()
}

export async function getNews(tickers: string[]) {
  const q = tickers.join(',')
  return (await fetch(`${BASE}/api/news?tickers=${q}`)).json()
}
