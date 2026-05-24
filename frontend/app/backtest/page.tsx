'use client'
import { useState } from 'react'
import { runBacktest } from '@/lib/api'
import BacktestStats from '@/components/BacktestStats'
import type { BacktestSummary } from '@/lib/types'

export default function BacktestPage() {
  const [ticker, setTicker] = useState('')
  const [start, setStart] = useState('2023-01-01')
  const [end, setEnd] = useState(new Date().toISOString().slice(0, 10))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<BacktestSummary | null>(null)

  async function handleRun() {
    if (!ticker) return
    setLoading(true)
    setError(null)
    try {
      const data = await runBacktest(ticker.trim().toUpperCase(), start, end)
      setResult(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Backtest failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <div className="text-white font-bold mb-3">Backtest</div>
        <div className="flex items-center gap-3 flex-wrap">
          <input
            value={ticker}
            onChange={e => setTicker(e.target.value)}
            placeholder="Ticker (e.g. NVDA)"
            className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#3b82f6] w-40"
          />
          <input type="date" value={start} onChange={e => setStart(e.target.value)}
            className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-[12px] text-[#e2e8f0] focus:outline-none focus:border-[#3b82f6]" />
          <span className="text-[#64748b] text-[11px]">to</span>
          <input type="date" value={end} onChange={e => setEnd(e.target.value)}
            className="bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-[12px] text-[#e2e8f0] focus:outline-none focus:border-[#3b82f6]" />
          <button
            onClick={handleRun}
            disabled={loading || !ticker}
            className="bg-[#1e3a5f] hover:bg-[#1e4a7f] disabled:opacity-50 border border-[#3b82f6]/40 text-[#3b82f6] text-[11px] font-bold px-4 py-1.5 rounded transition-colors"
          >
            {loading ? 'Running...' : 'Run Backtest'}
          </button>
          {error && <span className="text-[10px] text-[#ef4444]">{error}</span>}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {!result && !loading && (
          <div className="flex items-center justify-center h-full text-[#4b5563] text-sm">
            Enter a ticker and date range to run backtest
          </div>
        )}
        {result && <BacktestStats summary={result} />}
      </div>
    </div>
  )
}
