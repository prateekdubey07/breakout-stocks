'use client'
import type { BpsResult } from '@/lib/types'

interface Props {
  results: BpsResult[]
  onSectorClick?: (sector: string) => void
}

const SECTOR_SHORT: Record<string, string> = {
  'Technology':              'Tech',
  'Communication Services':  'Comms',
  'Consumer Cyclical':       'Cons Cyc',
  'Consumer Defensive':      'Cons Def',
  'Financial Services':      'Financials',
  'Healthcare':              'Health',
  'Industrials':             'Indust',
  'Energy':                  'Energy',
  'Materials':               'Materials',
  'Real Estate':             'RE',
  'Utilities':               'Utilities',
  'Unknown':                 'Other',
}

function bpsToColor(avg: number): string {
  if (avg >= 70) return 'bg-[#14532d] text-[#22c55e] border-[#22c55e]/30'
  if (avg >= 55) return 'bg-[#1c3a5f] text-[#3b82f6] border-[#3b82f6]/30'
  if (avg >= 40) return 'bg-[#451a03] text-[#f59e0b] border-[#f59e0b]/30'
  return 'bg-[#1e293b] text-[#4b5563] border-[#4b5563]/20'
}

export default function SectorHeatmap({ results, onSectorClick }: Props) {
  // Group by sector — use canonical name from fundamentals.sector
  const sectorMap = new Map<string, { scores: number[]; tickers: string[] }>()

  for (const r of results) {
    const raw = r.fundamentals?.sector || 'Unknown'
    const sector = SECTOR_SHORT[raw] ?? raw
    if (!sectorMap.has(sector)) sectorMap.set(sector, { scores: [], tickers: [] })
    const entry = sectorMap.get(sector)!
    if (r.breakout_probability_score > 0) entry.scores.push(r.breakout_probability_score)
    entry.tickers.push(r.ticker)
  }

  const sectors = Array.from(sectorMap.entries())
    .map(([name, { scores, tickers }]) => ({
      name,
      avg: scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0,
      count: tickers.length,
      topTicker: tickers[0] ?? '',
    }))
    .filter(s => s.count > 0)
    .sort((a, b) => b.avg - a.avg)

  if (sectors.length === 0) return null

  return (
    <div className="p-4">
      <div className="text-[10px] text-[#64748b] uppercase tracking-wide mb-3">Sector Heatmap</div>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6">
        {sectors.map(s => (
          <button
            key={s.name}
            onClick={() => onSectorClick?.(s.name)}
            className={`rounded border p-2 text-center transition-opacity hover:opacity-80 ${bpsToColor(s.avg)}`}
          >
            <div className="text-[9px] font-bold truncate">{s.name}</div>
            <div className="text-[18px] font-black leading-tight">{s.avg || '—'}</div>
            <div className="text-[8px] opacity-70">{s.count} ticker{s.count !== 1 ? 's' : ''}</div>
          </button>
        ))}
      </div>
      <div className="flex gap-3 mt-2">
        {[['≥70 HIGH', 'text-[#22c55e]'], ['≥55 MEDIUM', 'text-[#3b82f6]'], ['≥40 WATCH', 'text-[#f59e0b]'], ['<40 PASS', 'text-[#4b5563]']].map(([label, color]) => (
          <span key={label} className={`text-[8px] ${color}`}>{label}</span>
        ))}
      </div>
    </div>
  )
}
