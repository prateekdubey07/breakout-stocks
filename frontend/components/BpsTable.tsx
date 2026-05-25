import type { BpsResult } from '@/lib/types'

const CONVICTION_STYLE: Record<string, string> = {
  HIGH:   'bg-[#14532d] text-[#22c55e]',
  MEDIUM: 'bg-[#1c3a5f] text-[#3b82f6]',
  WATCH:  'bg-[#451a03] text-[#f59e0b]',
  PASS:   'bg-[#1e293b] text-[#4b5563]',
}
const BPS_COLOR: Record<string, string> = {
  HIGH: 'text-[#22c55e]', MEDIUM: 'text-[#3b82f6]', WATCH: 'text-[#f59e0b]', PASS: 'text-[#4b5563]',
}
const BAR_COLOR: Record<string, string> = {
  HIGH: 'bg-[#22c55e]', MEDIUM: 'bg-[#3b82f6]', WATCH: 'bg-[#f59e0b]', PASS: 'bg-[#374151]',
}

interface Props {
  results: BpsResult[]
  selected: string | null
  onSelect: (ticker: string) => void
}

export default function BpsTable({ results, selected, onSelect }: Props) {
  return (
    <div className="flex flex-col overflow-hidden h-full">
      <div className="grid grid-cols-[68px_1fr_76px_72px_44px_40px] px-4 py-1.5 bg-[#0a0e17] border-b border-[#1e293b]">
        {['TICKER', 'BPS', 'PATTERN', 'STATUS', 'R:R', 'RS'].map(h => (
          <span key={h} className="text-[#64748b] text-[9px] uppercase tracking-wide">{h}</span>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto">
        {results.map(r => {
          const hasEarnings = r.risk_flags?.includes('EARNINGS_WITHIN_5D')
          const rs = r.rs_vs_spy
          return (
            <div
              key={r.ticker}
              onClick={() => onSelect(r.ticker)}
              className={`grid grid-cols-[68px_1fr_76px_72px_44px_40px] items-center px-4 py-2 border-b border-[#0f1623] cursor-pointer transition-colors
                ${selected === r.ticker ? 'bg-[#1a2035] border-l-2 border-l-[#3b82f6]' : 'hover:bg-white/5'}`}
            >
              <div className="flex items-center gap-1 min-w-0">
                <span className="font-bold text-[12px] text-white truncate">{r.ticker}</span>
                {hasEarnings && (
                  <span title="Earnings within 5 days — trade with caution" className="text-[#f59e0b] text-[10px] shrink-0">⚠</span>
                )}
              </div>
              <div className="flex items-center gap-2 pr-2">
                <span className={`font-bold text-[12px] min-w-[24px] ${BPS_COLOR[r.conviction]}`}>
                  {r.breakout_probability_score}
                </span>
                <div className="flex-1 h-[3px] bg-[#1e293b] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${BAR_COLOR[r.conviction]}`}
                    style={{ width: `${r.breakout_probability_score}%` }}
                  />
                </div>
              </div>
              <span className="text-[#94a3b8] text-[9px] truncate">
                {r.signal_summary.pattern.split(' ')[0]}
              </span>
              <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${CONVICTION_STYLE[r.conviction]}`}>
                {r.conviction}
              </span>
              <span className={`text-[10px] font-semibold ${BPS_COLOR[r.conviction]}`}>{r.risk_reward}</span>
              <span className={`text-[10px] font-semibold ${
                rs == null ? 'text-[#4b5563]' : rs >= 1 ? 'text-[#22c55e]' : 'text-[#ef4444]'
              }`}>
                {rs != null ? (rs >= 0 ? `+${rs.toFixed(1)}` : rs.toFixed(1)) : '—'}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
