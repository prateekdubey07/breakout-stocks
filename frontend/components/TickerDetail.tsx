'use client'
import { useEffect, useState } from 'react'
import type { BpsResult } from '@/lib/types'
import PriceChart from './PriceChart'
import { addToWatchlist, getNews } from '@/lib/api'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const IND_COLOR = (v: boolean | number | string) => {
  if (typeof v === 'boolean') return v ? 'text-[#22c55e]' : 'text-[#ef4444]'
  if (typeof v === 'number') return v >= 55 && v <= 75 ? 'text-[#22c55e]' : 'text-[#f59e0b]'
  return 'text-[#22c55e]'
}

interface NewsItem { title: string; sentiment: string; source: string; published_at: string; url: string }

async function openPaperTrade(ticker: string, amount: number, stop: string | null, target: string | null, note: string) {
  const d = await fetch(`${BASE}/api/ohlcv/${ticker}?period=5d`).then(r => r.json())
  const price = d.data?.at(-1)?.close
  if (!price) throw new Error('no price')
  const shares = parseFloat((amount / price).toFixed(4))
  const parsePrice = (v: string | null) => v ? parseFloat(String(v).replace(/[^0-9.]/g, '')) || null : null
  await fetch(`${BASE}/api/paper-trades`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticker, entry_price: price, shares,
      stop_loss: parsePrice(stop),
      target_1: parsePrice(target),
      notes: note,
    }),
  })
  return price
}

export default function TickerDetail({ result }: { result: BpsResult | null }) {
  const [chartData, setChartData] = useState<{ date: string; close: number }[]>([])
  const [paperAmt, setPaperAmt] = useState('')
  const [paperOpen, setPaperOpen] = useState(false)
  const [paperLoading, setPaperLoading] = useState(false)
  const [news, setNews] = useState<NewsItem[]>([])
  const [newsLoading, setNewsLoading] = useState(false)
  const [autoTradeLoading, setAutoTradeLoading] = useState(false)
  const [autoTradeStatus, setAutoTradeStatus] = useState<string | null>(null)

  useEffect(() => {
    if (!result) return
    fetch(`${BASE}/api/ohlcv/${result.ticker}?period=3mo`)
      .then(r => r.json())
      .then(d => setChartData(d.data ?? []))
      .catch(() => {})
    setPaperOpen(false)
    setPaperAmt('')
    setAutoTradeStatus(null)
    // fetch news for this ticker
    setNewsLoading(true)
    setNews([])
    getNews([result.ticker])
      .then(d => setNews(Array.isArray(d) ? d : (d.items ?? [])))
      .catch(() => {})
      .finally(() => setNewsLoading(false))
  }, [result?.ticker])

  const newsCounts = {
    bullish: news.filter(n => n.sentiment === 'bullish').length,
    bearish: news.filter(n => n.sentiment === 'bearish').length,
    neutral: news.filter(n => n.sentiment === 'neutral').length,
  }
  const newsConfirmed = newsCounts.bullish > newsCounts.bearish

  const convictionOk = result?.conviction === 'HIGH' || result?.conviction === 'MEDIUM'
  const canAutoTrade = convictionOk && newsConfirmed && news.length > 0

  async function handlePaperTrade(amount: number) {
    if (!result) return
    setPaperLoading(true)
    try {
      const price = await openPaperTrade(
        result.ticker, amount,
        result.stop_loss, result.target_1,
        `$${amount} via scanner @ live price`,
      )
      setPaperOpen(false)
      setPaperAmt('')
      alert(`Opened paper trade: ${result.ticker} $${amount} @ $${price.toFixed(2)}`)
    } catch {
      alert('Failed to open paper trade for ' + result.ticker)
    } finally {
      setPaperLoading(false)
    }
  }

  async function handleAutoTrade() {
    if (!result || !canAutoTrade) return
    setAutoTradeLoading(true)
    setAutoTradeStatus(null)
    try {
      const price = await openPaperTrade(
        result.ticker, 1000,
        result.stop_loss, result.target_1,
        `AUTO $1000 | BPS:${result.breakout_probability_score} ${result.conviction} | news:${newsCounts.bullish}B/${newsCounts.bearish}bear`,
      )
      setAutoTradeStatus(`AUTO TRADE PLACED: ${result.ticker} $1000 @ $${price.toFixed(2)}`)
    } catch {
      setAutoTradeStatus('Auto trade failed — check backend')
    } finally {
      setAutoTradeLoading(false)
    }
  }

  if (!result) return (
    <div className="flex items-center justify-center h-full text-[#64748b] text-sm">
      Select a ticker to view detail
    </div>
  )

  const s = result.signal_summary
  const f = result.fundamentals

  return (
    <div className="p-4 flex flex-col gap-3 overflow-y-auto h-full">
      <div className="flex items-baseline gap-3">
        <span className="text-xl font-black text-white">{result.ticker}</span>
        <span className="text-sm text-[#22c55e] font-bold">{result.entry_zone}</span>
        <div className="ml-auto text-right">
          <div className="text-[9px] text-[#64748b] uppercase">BPS</div>
          <div className="text-3xl font-black text-[#22c55e] leading-none">{result.breakout_probability_score}</div>
        </div>
      </div>

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

      <PriceChart data={chartData} />

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

      {/* News sentiment for this ticker */}
      <div className="bg-[#111827] border border-[#1e293b] rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[10px] font-semibold text-[#64748b] uppercase tracking-wide">News Sentiment</div>
          {newsLoading && <div className="text-[9px] text-[#64748b]">loading...</div>}
          {!newsLoading && news.length > 0 && (
            <div className="flex gap-2">
              <span className="text-[10px] text-[#22c55e] font-bold">{newsCounts.bullish}B</span>
              <span className="text-[10px] text-[#ef4444] font-bold">{newsCounts.bearish}Bear</span>
              <span className="text-[10px] text-[#64748b]">{newsCounts.neutral}N</span>
            </div>
          )}
          {!newsLoading && news.length === 0 && <div className="text-[9px] text-[#64748b]">no articles</div>}
        </div>
        {news.length > 0 && (
          <div className={`text-[10px] font-bold mb-2 px-2 py-1 rounded ${
            newsConfirmed ? 'bg-[#0d1f12] text-[#22c55e]' : 'bg-[#1f0d0d] text-[#ef4444]'
          }`}>
            {newsConfirmed ? '✓ News CONFIRMS setup (bullish majority)' : '✗ News does NOT confirm (bearish/neutral majority)'}
          </div>
        )}
        {news.slice(0, 3).map((n, i) => (
          <div key={i} className="flex items-start gap-2 py-1 border-b border-[#1e293b]/40 last:border-0">
            <span className={`text-[8px] font-bold shrink-0 mt-0.5 ${
              n.sentiment === 'bullish' ? 'text-[#22c55e]' :
              n.sentiment === 'bearish' ? 'text-[#ef4444]' : 'text-[#64748b]'
            }`}>{n.sentiment.toUpperCase()[0]}</span>
            <span className="text-[10px] text-[#94a3b8] leading-tight line-clamp-2">{n.title}</span>
          </div>
        ))}
      </div>

      {result.risk_flags.length > 0 && (
        <div className="bg-[#3a1a1a] border border-[#ef4444]/30 rounded p-2">
          <div className="text-[9px] text-[#ef4444] font-semibold uppercase mb-1">Risk Flags</div>
          {result.risk_flags.map(flag => (
            <div key={flag} className="text-[10px] text-[#f87171]">⚠ {flag}</div>
          ))}
        </div>
      )}

      {/* Auto-trade status */}
      {autoTradeStatus && (
        <div className={`text-[11px] font-bold px-3 py-2 rounded ${
          autoTradeStatus.startsWith('AUTO TRADE PLACED') ? 'bg-[#0d1f12] text-[#22c55e] border border-[#22c55e]/30' : 'bg-[#1f0d0d] text-[#ef4444]'
        }`}>
          {autoTradeStatus}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => addToWatchlist({
            ticker: result.ticker, bps: result.breakout_probability_score,
            pattern: s.pattern, entry_zone: result.entry_zone,
            stop: result.stop_loss, target_1: result.target_1,
          })}
          className="flex-1 bg-[#1e3a5f] hover:bg-[#1e4a7f] border border-[#3b82f6]/30 text-[#3b82f6] text-[11px] font-semibold py-2 rounded transition-colors"
        >
          + Watchlist
        </button>
        <button
          onClick={() => setPaperOpen(o => !o)}
          className="flex-1 bg-[#14532d] hover:bg-[#166534] border border-[#22c55e]/30 text-[#22c55e] text-[11px] font-semibold py-2 rounded transition-colors"
        >
          + Paper Trade
        </button>
        <button
          onClick={handleAutoTrade}
          disabled={!canAutoTrade || autoTradeLoading}
          title={!canAutoTrade ? (!convictionOk ? 'Need HIGH/MEDIUM conviction' : 'News not bullish') : 'Place $1000 auto trade'}
          className={`flex-1 text-[11px] font-bold py-2 rounded transition-colors border ${
            canAutoTrade
              ? 'bg-[#451a03] hover:bg-[#78350f] border-[#f59e0b]/50 text-[#f59e0b]'
              : 'bg-[#1a1a1a] border-[#374151] text-[#374151] cursor-not-allowed'
          }`}
        >
          {autoTradeLoading ? '...' : canAutoTrade ? 'AUTO $1000' : 'AUTO $1000'}
        </button>
      </div>

      {paperOpen && (
        <div className="flex items-center gap-2 bg-[#0d1f12] border border-[#22c55e]/30 rounded p-2">
          <span className="text-[10px] text-[#64748b]">Invest $</span>
          <input
            value={paperAmt}
            onChange={e => setPaperAmt(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handlePaperTrade(parseFloat(paperAmt))}
            placeholder="Amount"
            className="flex-1 bg-[#111827] border border-[#1e293b] rounded px-2 py-1 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#22c55e]"
          />
          <button
            onClick={() => handlePaperTrade(parseFloat(paperAmt))}
            disabled={paperLoading || !paperAmt}
            className="bg-[#22c55e] hover:bg-[#16a34a] disabled:opacity-50 text-black text-[11px] font-bold px-3 py-1 rounded transition-colors"
          >
            {paperLoading ? '...' : 'Open'}
          </button>
          <button onClick={() => setPaperOpen(false)} className="text-[#64748b] text-[11px] hover:text-white">✕</button>
        </div>
      )}
    </div>
  )
}
