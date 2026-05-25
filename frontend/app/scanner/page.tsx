'use client'
import { useState, useMemo, useEffect } from 'react'
import { useScan } from '@/hooks/useScan'
import { useWebSocket } from '@/hooks/useWebSocket'
import KpiStrip from '@/components/KpiStrip'
import BpsTable from '@/components/BpsTable'
import TickerDetail from '@/components/TickerDetail'
import AlertBanner from '@/components/AlertBanner'
import SectorHeatmap from '@/components/SectorHeatmap'
import type { BpsResult } from '@/lib/types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function timeAgo(iso: string) {
  const s = iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z'
  const diff = Math.floor((Date.now() - new Date(s).getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

function scanAgeSeconds(iso: string) {
  const s = iso.includes('Z') || iso.includes('+') ? iso : iso + 'Z'
  return Math.floor((Date.now() - new Date(s).getTime()) / 1000)
}

function ScanSkeleton() {
  return (
    <div className="flex flex-col overflow-hidden h-full">
      <div className="grid grid-cols-[68px_1fr_76px_72px_44px_40px] px-4 py-1.5 bg-[#0a0e17] border-b border-[#1e293b]">
        {['TICKER', 'BPS', 'PATTERN', 'STATUS', 'R:R', 'RS'].map(h => (
          <span key={h} className="text-[#64748b] text-[9px] uppercase tracking-wide">{h}</span>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="grid grid-cols-[68px_1fr_76px_72px_44px_40px] items-center px-4 py-2 border-b border-[#0f1623] animate-pulse">
            <div className="h-3 w-10 bg-[#1e293b] rounded" />
            <div className="flex items-center gap-2 pr-2">
              <div className="h-3 w-6 bg-[#1e293b] rounded" />
              <div className="flex-1 h-[3px] bg-[#1e293b] rounded-full" />
            </div>
            <div className="h-3 w-14 bg-[#1e293b] rounded" />
            <div className="h-4 w-12 bg-[#1e293b] rounded" />
            <div className="h-3 w-8 bg-[#1e293b] rounded" />
            <div className="h-3 w-6 bg-[#1e293b] rounded" />
          </div>
        ))}
      </div>
    </div>
  )
}

interface GapResult {
  ticker: string
  gap_pct: number
  last_close: number
  prior_close: number
  direction: 'up' | 'down'
}

export default function ScannerPage() {
  const [input, setInput] = useState('')
  const [minBps, setMinBps] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [lastScan, setLastScan] = useState<{ scanned_at: string; trigger: string } | null>(null)
  const [, setTick] = useState(0)
  const [view, setView] = useState<'list' | 'heatmap' | 'gap'>('list')
  const [dedupesSectors, setDedupesSectors] = useState(false)
  const [sectorFilter, setSectorFilter] = useState<string | null>(null)
  const [gaps, setGaps] = useState<GapResult[]>([])
  const [gapLoading, setGapLoading] = useState(false)
  const [minGapPct, setMinGapPct] = useState(2)

  const { results, loading, error, scan, setResults } = useScan()
  const { alerts, connected } = useWebSocket()

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 30_000)
    return () => clearInterval(id)
  }, [])

  const isStale = lastScan != null && scanAgeSeconds(lastScan.scanned_at) > 600

  const selectedResult = useMemo(
    () => results.find(r => r.ticker === selected) ?? null,
    [results, selected]
  )

  // Correlation filter: keep highest BPS per sector, dedupe same-sector duplicates
  const displayResults = useMemo(() => {
    let res = results
    if (sectorFilter) {
      const short: Record<string, string> = {
        'Technology': 'Tech', 'Communication Services': 'Comms',
        'Consumer Cyclical': 'Cons Cyc', 'Consumer Defensive': 'Cons Def',
        'Financial Services': 'Financials', 'Healthcare': 'Health',
        'Industrials': 'Indust', 'Energy': 'Energy',
        'Materials': 'Materials', 'Real Estate': 'RE', 'Utilities': 'Utilities',
      }
      res = res.filter(r => {
        const raw = r.fundamentals?.sector || 'Unknown'
        const mapped = short[raw] ?? raw
        return mapped === sectorFilter || raw === sectorFilter
      })
    }
    if (!dedupesSectors) return res
    // Keep only highest-BPS ticker per sector
    const seen = new Map<string, BpsResult>()
    for (const r of res) {
      const sector = r.fundamentals?.sector || 'Unknown'
      const existing = seen.get(sector)
      if (!existing || r.breakout_probability_score > existing.breakout_probability_score) {
        seen.set(sector, r)
      }
    }
    return Array.from(seen.values()).sort((a, b) => b.breakout_probability_score - a.breakout_probability_score)
  }, [results, dedupesSectors, sectorFilter])

  const kpis = useMemo(() => {
    const high = results.filter(r => r.conviction === 'HIGH').length
    const med  = results.filter(r => r.conviction === 'MEDIUM').length
    const scoredResults = results.filter(r => r.breakout_probability_score > 0)
    const avgBps = scoredResults.length
      ? Math.round(scoredResults.reduce((s, r) => s + r.breakout_probability_score, 0) / scoredResults.length)
      : 0
    const topBps = results.length ? Math.max(...results.map(r => r.breakout_probability_score)) : 0
    return [
      { label: 'Scanned',    value: results.length, sub: 'tickers',      color: 'text-white' },
      { label: 'HIGH Conv',  value: high,            sub: 'setups',       color: 'text-[#22c55e]' },
      { label: 'MEDIUM',     value: med,             sub: 'setups',       color: 'text-[#3b82f6]' },
      { label: 'Avg BPS',    value: avgBps,          sub: 'scored only',  color: 'text-[#f59e0b]' },
      { label: 'Top BPS',    value: topBps,          sub: 'best pick',    color: 'text-[#22c55e]' },
      { label: 'WS Status',  value: connected ? 'LIVE' : 'OFF', sub: 'websocket', color: connected ? 'text-[#22c55e]' : 'text-[#ef4444]' },
    ]
  }, [results, connected])

  useEffect(() => {
    fetch(`${BASE}/api/default-tickers`)
      .then(r => r.json())
      .then((tickers: string[]) => setInput(tickers.join(',')))
      .catch(() => {})

    fetch(`${BASE}/api/scan-results/latest`)
      .then(r => r.json())
      .then(d => {
        if (d.candidates?.length) {
          setResults(d.candidates)
          setLastScan({ scanned_at: d.scanned_at, trigger: d.trigger })
        }
      })
      .catch(() => {})
  }, [])

  async function handleScan() {
    const tickers = input.split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
    setLastScan(null)
    setSectorFilter(null)
    await scan(tickers, minBps)
    setLastScan({ scanned_at: new Date().toISOString(), trigger: 'manual' })
  }

  async function handleGapScan() {
    setGapLoading(true)
    setView('gap')
    try {
      const data = await fetch(`${BASE}/api/scan/gap?min_gap_pct=${minGapPct}`).then(r => r.json())
      setGaps(data.gaps ?? [])
    } catch {
      setGaps([])
    } finally {
      setGapLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AlertBanner alerts={alerts} />

      {/* Controls */}
      <div className="px-5 py-3 border-b border-[#1e293b] flex items-center gap-3 flex-wrap">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="AAPL,MSFT,NVDA..."
          className="flex-1 min-w-[200px] bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#3b82f6]"
        />
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#64748b] uppercase">Min BPS</span>
          <input
            type="number" min={0} max={100} value={minBps}
            onChange={e => setMinBps(Number(e.target.value))}
            className="w-16 bg-[#111827] border border-[#1e293b] rounded px-2 py-1.5 text-[12px] text-center text-[#e2e8f0] focus:outline-none focus:border-[#3b82f6]"
          />
        </div>
        <button onClick={handleScan} disabled={loading}
          className="bg-[#1e3a5f] hover:bg-[#1e4a7f] disabled:opacity-50 border border-[#3b82f6]/40 text-[#3b82f6] text-[11px] font-bold px-4 py-1.5 rounded transition-colors">
          {loading ? 'Scanning...' : 'Scan'}
        </button>
        {/* Gap scan */}
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-[#64748b]">Gap≥</span>
          <input type="number" min={0.5} max={20} step={0.5} value={minGapPct}
            onChange={e => setMinGapPct(Number(e.target.value))}
            className="w-12 bg-[#111827] border border-[#1e293b] rounded px-2 py-1.5 text-[12px] text-center text-[#e2e8f0] focus:outline-none focus:border-[#a855f7]" />
          <span className="text-[10px] text-[#64748b]">%</span>
        </div>
        <button onClick={handleGapScan} disabled={gapLoading}
          className="bg-[#2d1b4e] hover:bg-[#3d2560] disabled:opacity-50 border border-[#a855f7]/40 text-[#a855f7] text-[11px] font-bold px-3 py-1.5 rounded transition-colors">
          {gapLoading ? 'Scanning...' : 'Gap Scan'}
        </button>

        {error && <span className="text-[10px] text-[#ef4444]">{error}</span>}
        {lastScan && (
          <span className={`text-[10px] ${isStale ? 'text-[#ef4444]' : 'text-[#64748b]'}`}>
            {lastScan.trigger === 'auto' ? '⚡ auto' : '↩ manual'} · {timeAgo(lastScan.scanned_at)}
            {isStale && ' · STALE'}
          </span>
        )}
        {lastScan && (
          <button onClick={handleScan} disabled={loading} title="Force refresh"
            className={`text-[16px] leading-none disabled:opacity-50 transition-colors ${isStale ? 'text-[#ef4444] hover:text-[#f87171]' : 'text-[#64748b] hover:text-[#3b82f6]'}`}>
            ↻
          </button>
        )}
      </div>

      <KpiStrip kpis={kpis} />

      {/* View + filter toolbar */}
      {results.length > 0 && (
        <div className="px-4 py-2 border-b border-[#1e293b] flex items-center gap-3">
          {(['list', 'heatmap'] as const).map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`text-[10px] uppercase font-bold px-3 py-1 rounded transition-colors ${view === v ? 'bg-[#1e293b] text-white' : 'text-[#64748b] hover:text-white'}`}>
              {v === 'list' ? 'List' : 'Sector Map'}
            </button>
          ))}
          {sectorFilter && (
            <button onClick={() => setSectorFilter(null)}
              className="text-[10px] text-[#f59e0b] border border-[#f59e0b]/30 px-2 py-1 rounded hover:bg-[#f59e0b]/10">
              ✕ {sectorFilter}
            </button>
          )}
          <label className="flex items-center gap-1.5 ml-auto cursor-pointer">
            <input type="checkbox" checked={dedupesSectors} onChange={e => setDedupesSectors(e.target.checked)}
              className="w-3 h-3 accent-[#3b82f6]" />
            <span className="text-[10px] text-[#64748b]">Dedupe sectors</span>
          </label>
        </div>
      )}

      {/* Main content */}
      {view === 'heatmap' ? (
        <div className="flex-1 overflow-y-auto">
          <SectorHeatmap results={results} onSectorClick={s => { setSectorFilter(s); setView('list') }} />
          {sectorFilter && (
            <div className="px-4 pb-2">
              <BpsTable results={displayResults} selected={selected} onSelect={setSelected} />
            </div>
          )}
        </div>
      ) : view === 'gap' ? (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="text-[10px] text-[#64748b] uppercase tracking-wide mb-3">
            Pre-Market Gap Scanner — tickers gapping ≥{minGapPct}% vs prior close
          </div>
          {gapLoading ? (
            <div className="text-[#64748b] text-sm animate-pulse">Scanning gaps...</div>
          ) : gaps.length === 0 ? (
            <div className="text-[#4b5563] text-sm">No gaps found above {minGapPct}% threshold.</div>
          ) : (
            <table className="w-full max-w-lg">
              <thead><tr className="text-[8px] text-[#4b5563] uppercase border-b border-[#1e293b]">
                {['Ticker', 'Gap %', 'Prior Close', 'Last Close', 'Dir'].map(h =>
                  <th key={h} className="text-left px-3 py-1.5">{h}</th>)}
              </tr></thead>
              <tbody>
                {gaps.map(g => (
                  <tr key={g.ticker} className="border-b border-[#0f1623] hover:bg-white/5">
                    <td className="px-3 py-2 font-bold text-white text-[12px]">{g.ticker}</td>
                    <td className={`px-3 py-2 font-bold text-[12px] ${g.gap_pct > 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                      {g.gap_pct > 0 ? '+' : ''}{g.gap_pct.toFixed(2)}%
                    </td>
                    <td className="px-3 py-2 text-[#94a3b8] text-[11px]">${g.prior_close}</td>
                    <td className="px-3 py-2 text-[#94a3b8] text-[11px]">${g.last_close}</td>
                    <td className="px-3 py-2 text-[11px]">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${g.direction === 'up' ? 'bg-[#14532d] text-[#22c55e]' : 'bg-[#450a0a] text-[#ef4444]'}`}>
                        {g.direction.toUpperCase()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          <div className="w-[440px] flex-shrink-0 border-r border-[#1e293b] overflow-hidden flex flex-col">
            {loading ? (
              <ScanSkeleton />
            ) : displayResults.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-[#4b5563] text-sm">
                Run a scan to see results
              </div>
            ) : (
              <BpsTable results={displayResults} selected={selected} onSelect={setSelected} />
            )}
          </div>
          <div className="flex-1 overflow-hidden">
            <TickerDetail result={selectedResult} />
          </div>
        </div>
      )}
    </div>
  )
}
