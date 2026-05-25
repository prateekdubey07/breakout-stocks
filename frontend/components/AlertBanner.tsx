'use client'
import type { WatchlistAlert } from '@/lib/types'

const STATUS_STYLE: Record<string, string> = {
  TRIGGERED:      'bg-[#14532d] border-[#22c55e]/40 text-[#22c55e]',
  BREAKING_DOWN:  'bg-[#3a1a1a] border-[#ef4444]/40 text-[#ef4444]',
  STILL_VALID:    'bg-[#1c3a5f] border-[#3b82f6]/40 text-[#3b82f6]',
}

export default function AlertBanner({ alerts }: { alerts: WatchlistAlert[] }) {
  if (!alerts.length) return null
  return (
    <div className="px-5 py-2 flex gap-2 overflow-x-auto border-b border-[#1e293b] bg-[#0a0e17]">
      {alerts.slice(0, 8).map((a, i) => (
        <div key={i} className={`flex-shrink-0 flex items-center gap-2 rounded border px-2 py-1 text-[10px] font-semibold ${STATUS_STYLE[a.status] ?? 'bg-[#1e293b] text-[#94a3b8]'}`}>
          <span className="text-white font-bold">{a.ticker}</span>
          <span>{(a.status ?? '').replace('_', ' ')}</span>
          {a.updated_bps !== undefined && <span className="opacity-70">BPS {a.updated_bps}</span>}
        </div>
      ))}
    </div>
  )
}
