'use client'
import { useState, useMemo, useEffect } from 'react'
import { useScan } from '@/hooks/useScan'
import { useWebSocket } from '@/hooks/useWebSocket'
import KpiStrip from '@/components/KpiStrip'
import BpsTable from '@/components/BpsTable'
import TickerDetail from '@/components/TickerDetail'
import AlertBanner from '@/components/AlertBanner'

const BASE = 'http://localhost:8000'

function timeAgo(iso: string) {
  const diff = Math.floor((Date.now() - new Date(iso + 'Z').getTime()) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function ScannerPage() {
  const [input, setInput] = useState('')
  const [minBps, setMinBps] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const [lastScan, setLastScan] = useState<{ scanned_at: string; trigger: string } | null>(null)
  const { results, loading, error, scan, setResults } = useScan()
  const { alerts, connected } = useWebSocket()

  const selectedResult = useMemo(
    () => results.find(r => r.ticker === selected) ?? null,
    [results, selected]
  )

  const kpis = useMemo(() => {
    const high = results.filter(r => r.conviction === 'HIGH').length
    const med  = results.filter(r => r.conviction === 'MEDIUM').length
    const avgBps = results.length
      ? Math.round(results.reduce((s, r) => s + r.breakout_probability_score, 0) / results.length)
      : 0
    const topBps = results.length ? Math.max(...results.map(r => r.breakout_probability_score)) : 0
    return [
      { label: 'Scanned',    value: results.length, sub: 'tickers',      color: 'text-white' },
      { label: 'HIGH Conv',  value: high,            sub: 'setups',       color: 'text-[#22c55e]' },
      { label: 'MEDIUM',     value: med,             sub: 'setups',       color: 'text-[#3b82f6]' },
      { label: 'Avg BPS',    value: avgBps,          sub: 'score',        color: 'text-[#f59e0b]' },
      { label: 'Top BPS',    value: topBps,          sub: 'best pick',    color: 'text-[#22c55e]' },
      { label: 'WS Status',  value: connected ? 'LIVE' : 'OFF', sub: 'websocket', color: connected ? 'text-[#22c55e]' : 'text-[#ef4444]' },
    ]
  }, [results, connected])

  // On mount: load default tickers + restore cached scan results (no auto re-scan)
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

  function handleScan() {
    const tickers = input.split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
    scan(tickers, minBps)
    setLastScan(null)
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AlertBanner alerts={alerts} />

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
        <button
          onClick={handleScan}
          disabled={loading}
          className="bg-[#1e3a5f] hover:bg-[#1e4a7f] disabled:opacity-50 border border-[#3b82f6]/40 text-[#3b82f6] text-[11px] font-bold px-4 py-1.5 rounded transition-colors"
        >
          {loading ? 'Scanning...' : 'Scan'}
        </button>
        {error && <span className="text-[10px] text-[#ef4444]">{error}</span>}
        {lastScan && (
          <span className="text-[10px] text-[#64748b]">
            {lastScan.trigger === 'auto' ? '⚡ auto' : '↩ cached'} · {timeAgo(lastScan.scanned_at)}
          </span>
        )}
      </div>

      <KpiStrip kpis={kpis} />

      <div className="flex flex-1 overflow-hidden">
        <div className="w-[420px] flex-shrink-0 border-r border-[#1e293b] overflow-hidden flex flex-col">
          {results.length === 0 && !loading ? (
            <div className="flex-1 flex items-center justify-center text-[#4b5563] text-sm">
              Run a scan to see results
            </div>
          ) : (
            <BpsTable results={results} selected={selected} onSelect={setSelected} />
          )}
        </div>
        <div className="flex-1 overflow-hidden">
          <TickerDetail result={selectedResult} />
        </div>
      </div>
    </div>
  )
}
