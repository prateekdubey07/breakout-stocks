import type { BacktestSummary } from '@/lib/types'

function Stat({ label, value, color = 'text-white' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-[#0a0e17] rounded p-3">
      <div className="text-[9px] text-[#64748b] uppercase tracking-wide mb-1">{label}</div>
      <div className={`text-[18px] font-bold ${color}`}>{value}</div>
    </div>
  )
}

export default function BacktestStats({ summary }: { summary: BacktestSummary }) {
  const s = summary
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Total Signals" value={s.total_signals} />
        <Stat label="Win Rate" value={`${(s.win_rate_t1 * 100).toFixed(1)}%`} color={s.win_rate_t1 >= 0.5 ? 'text-[#22c55e]' : 'text-[#ef4444]'} />
        <Stat label="Stop Rate" value={`${(s.stop_out_rate * 100).toFixed(1)}%`} color="text-[#ef4444]" />
        <Stat label="Avg Days Held" value={s.avg_days_to_resolution.toFixed(1)} />
      </div>
      <div className="grid grid-cols-4 gap-2">
        <Stat label="Avg Win" value={`${s.avg_return_winners_pct.toFixed(1)}%`} color="text-[#22c55e]" />
        <Stat label="Avg Loss" value={`${s.avg_return_losers_pct.toFixed(1)}%`} color="text-[#ef4444]" />
        <Stat label="Expectancy" value={`${s.expectancy_per_trade_pct.toFixed(2)}%`} color={s.expectancy_per_trade_pct >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'} />
        <Stat label="Profit Factor" value={s.profit_factor.toFixed(2)} color={s.profit_factor >= 1.5 ? 'text-[#22c55e]' : 'text-[#f59e0b]'} />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <Stat label="Sharpe Ratio" value={s.sharpe_ratio.toFixed(2)} color={s.sharpe_ratio >= 1 ? 'text-[#22c55e]' : 'text-[#f59e0b]'} />
        <Stat label="Max Drawdown" value={`${s.max_drawdown_pct.toFixed(1)}%`} color="text-[#ef4444]" />
      </div>

      {s.signals && s.signals.length > 0 && (
        <div className="bg-[#111827] border border-[#1e293b] rounded">
          <div className="px-4 py-2 border-b border-[#1e293b] text-[10px] text-[#64748b] uppercase tracking-wide">Signal Log</div>
          <div className="max-h-60 overflow-y-auto">
            {s.signals.map((sig, i) => (
              <div key={i} className="grid grid-cols-[80px_80px_80px_80px_1fr] px-4 py-2 border-b border-[#0f1623] text-[10px]">
                <span className="text-[#64748b]">{sig.date}</span>
                <span className="text-[#94a3b8]">${sig.entry_price?.toFixed(2)}</span>
                <span className={sig.outcome === 'WIN' ? 'text-[#22c55e]' : sig.outcome === 'STOP' ? 'text-[#ef4444]' : 'text-[#f59e0b]'}>
                  {sig.outcome}
                </span>
                <span className={sig.pnl_pct >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}>
                  {(sig.pnl_pct * 100).toFixed(1)}%
                </span>
                <span className="text-[#4b5563]">{sig.pattern}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
