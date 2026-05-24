'use client'
import { useEffect, useState } from 'react'
import type { BpsResult } from '@/lib/types'
import PriceChart from './PriceChart'
import { addToWatchlist } from '@/lib/api'

const IND_COLOR = (v: boolean | number | string) => {
  if (typeof v === 'boolean') return v ? 'text-[#22c55e]' : 'text-[#ef4444]'
  if (typeof v === 'number') return v >= 55 && v <= 75 ? 'text-[#22c55e]' : 'text-[#f59e0b]'
  return 'text-[#22c55e]'
}

export default function TickerDetail({ result }: { result: BpsResult | null }) {
  const [chartData, setChartData] = useState<{ date: string; close: number }[]>([])

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

      {result.risk_flags.length > 0 && (
        <div className="bg-[#3a1a1a] border border-[#ef4444]/30 rounded p-2">
          <div className="text-[9px] text-[#ef4444] font-semibold uppercase mb-1">Risk Flags</div>
          {result.risk_flags.map(flag => (
            <div key={flag} className="text-[10px] text-[#f87171]">⚠ {flag}</div>
          ))}
        </div>
      )}

      <button
        onClick={() => addToWatchlist({
          ticker: result.ticker, bps: result.breakout_probability_score,
          pattern: s.pattern, entry_zone: result.entry_zone,
          stop: result.stop_loss, target_1: result.target_1,
        })}
        className="w-full bg-[#1e3a5f] hover:bg-[#1e4a7f] border border-[#3b82f6]/30 text-[#3b82f6] text-[11px] font-semibold py-2 rounded transition-colors"
      >
        + Add to Watchlist
      </button>
    </div>
  )
}
