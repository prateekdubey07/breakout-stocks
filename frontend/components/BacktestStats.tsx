'use client'
import type { BacktestSummary } from '@/lib/types'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

function Stat({ label, value, color = 'text-white', big }: { label: string; value: string | number; color?: string; big?: boolean }) {
  return (
    <div className="bg-[#0a0e17] rounded p-3">
      <div className="text-[9px] text-[#64748b] uppercase tracking-wide mb-1">{label}</div>
      <div className={`font-bold ${big ? 'text-[24px]' : 'text-[18px]'} ${color}`}>{value}</div>
    </div>
  )
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
}

export default function BacktestStats({ summary }: { summary: BacktestSummary }) {
  const s = summary
  const isProfit = (s.total_pnl_usd ?? 0) >= 0

  if ((s as any).error || s.total_signals === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-[#64748b] text-sm">
        {(s as any).error ?? 'No signals found for this ticker and date range.'}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Capital summary — hero row */}
      {s.final_capital != null && (
        <div className="grid grid-cols-4 gap-2">
          <Stat label="Starting Capital" value={fmt(s.starting_capital)} big />
          <Stat label="Final Capital" value={fmt(s.final_capital)} color={isProfit ? 'text-[#22c55e]' : 'text-[#ef4444]'} big />
          <Stat label="Total P&L" value={(isProfit ? '+' : '') + fmt(s.total_pnl_usd)} color={isProfit ? 'text-[#22c55e]' : 'text-[#ef4444]'} big />
          <Stat label="Total Return" value={`${isProfit ? '+' : ''}${s.total_return_pct?.toFixed(1)}%`} color={isProfit ? 'text-[#22c55e]' : 'text-[#ef4444]'} big />
        </div>
      )}

      {/* Equity curve */}
      {s.equity_curve && s.equity_curve.length > 1 && (
        <div className="bg-[#111827] border border-[#1e293b] rounded p-3">
          <div className="text-[9px] text-[#64748b] uppercase tracking-wide mb-2">Equity Curve</div>
          <div className="h-36">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={s.equity_curve} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
                <XAxis dataKey="trade" hide />
                <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 9 }} tickFormatter={v => `$${(v/1000).toFixed(0)}k`} width={40} />
                <Tooltip
                  contentStyle={{ background: '#1e293b', border: 'none', fontSize: 11 }}
                  labelFormatter={l => `Trade ${l}`}
                  formatter={(v: number) => [fmt(v), 'Capital']}
                />
                <ReferenceLine y={s.starting_capital} stroke="#374151" strokeDasharray="4 2" />
                <Line type="monotone" dataKey="capital" stroke={isProfit ? '#22c55e' : '#ef4444'} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Trade stats */}
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Total Signals" value={s.total_signals} />
        {s.win_rate_t1 != null && (
          <Stat label="Win Rate" value={`${(s.win_rate_t1 * 100).toFixed(1)}%`} color={s.win_rate_t1 >= 0.5 ? 'text-[#22c55e]' : 'text-[#ef4444]'} />
        )}
        {s.stop_out_rate != null && (
          <Stat label="Stop Rate" value={`${(s.stop_out_rate * 100).toFixed(1)}%`} color="text-[#ef4444]" />
        )}
        {s.avg_days_to_resolution != null && (
          <Stat label="Avg Days Held" value={s.avg_days_to_resolution.toFixed(1)} />
        )}
      </div>
      <div className="grid grid-cols-4 gap-2">
        {s.avg_return_winners_pct != null && (
          <Stat label="Avg Win" value={`${s.avg_return_winners_pct.toFixed(1)}%`} color="text-[#22c55e]" />
        )}
        {s.avg_return_losers_pct != null && (
          <Stat label="Avg Loss" value={`${s.avg_return_losers_pct.toFixed(1)}%`} color="text-[#ef4444]" />
        )}
        {s.expectancy_per_trade_pct != null && (
          <Stat label="Expectancy" value={`${s.expectancy_per_trade_pct.toFixed(2)}%`} color={s.expectancy_per_trade_pct >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'} />
        )}
        {s.profit_factor != null && (
          <Stat label="Profit Factor" value={s.profit_factor.toFixed(2)} color={s.profit_factor >= 1.5 ? 'text-[#22c55e]' : 'text-[#f59e0b]'} />
        )}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {s.sharpe_ratio != null && (
          <Stat label="Sharpe Ratio" value={s.sharpe_ratio.toFixed(2)} color={s.sharpe_ratio >= 1 ? 'text-[#22c55e]' : 'text-[#f59e0b]'} />
        )}
        {s.max_drawdown_pct != null && (
          <Stat label="Max Drawdown" value={`${s.max_drawdown_pct.toFixed(1)}%`} color="text-[#ef4444]" />
        )}
      </div>

      {/* Signal log */}
      {s.signals && s.signals.length > 0 && (
        <div className="bg-[#111827] border border-[#1e293b] rounded">
          <div className="px-4 py-2 border-b border-[#1e293b] text-[10px] text-[#64748b] uppercase tracking-wide">Signal Log</div>
          <div className="max-h-72 overflow-y-auto">
            <div className="grid grid-cols-[90px_80px_110px_65px_80px_1fr] px-4 py-1.5 bg-[#0a0e17] text-[8px] text-[#4b5563] uppercase border-b border-[#1e293b]">
              <span>Date</span><span>Entry</span><span>Outcome</span><span>Return</span><span>P&L $</span><span>Balance</span>
            </div>
            {s.signals.map((sig, i) => {
              const isWin = sig.outcome === 'HIT_T1' || sig.outcome === 'HIT_T2'
              const isStop = sig.outcome === 'STOPPED_OUT'
              const ret = sig.actual_return_pct ?? 0
              return (
                <div key={i} className="grid grid-cols-[90px_80px_110px_65px_80px_1fr] px-4 py-2 border-b border-[#0f1623] text-[10px]">
                  <span className="text-[#64748b]">{sig.signal_date}</span>
                  <span className="text-[#94a3b8]">${sig.entry_price?.toFixed(2)}</span>
                  <span className={isWin ? 'text-[#22c55e]' : isStop ? 'text-[#ef4444]' : 'text-[#f59e0b]'}>{sig.outcome}</span>
                  <span className={ret >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}>{ret.toFixed(1)}%</span>
                  <span className={sig.trade_pnl_usd >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}>
                    {sig.trade_pnl_usd >= 0 ? '+' : ''}{sig.trade_pnl_usd != null ? fmt(sig.trade_pnl_usd) : '—'}
                  </span>
                  <span className="text-[#94a3b8]">{sig.capital_after != null ? fmt(sig.capital_after) : '—'}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
