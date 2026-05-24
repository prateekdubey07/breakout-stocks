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
