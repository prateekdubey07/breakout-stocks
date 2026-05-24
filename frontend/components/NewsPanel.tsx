import type { NewsItem } from '@/lib/types'

const SENTIMENT_STYLE: Record<string, string> = {
  bullish: 'text-[#22c55e] bg-[#14532d]',
  bearish: 'text-[#ef4444] bg-[#3a1a1a]',
  neutral: 'text-[#94a3b8] bg-[#1e293b]',
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const h = Math.floor(diff / 3_600_000)
  if (h < 1) return `${Math.floor(diff / 60_000)}m ago`
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function NewsPanel({ items }: { items: NewsItem[] }) {
  if (!items.length) return (
    <div className="flex items-center justify-center h-40 text-[#4b5563] text-sm">No news loaded</div>
  )
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="bg-[#111827] border border-[#1e293b] rounded p-3 hover:border-[#334155] transition-colors">
          <div className="flex items-start justify-between gap-3">
            <div className="flex-1 min-w-0">
              <div className="text-[12px] text-[#e2e8f0] font-medium leading-tight mb-1 line-clamp-2">
                {item.headline}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                {item.tickers?.map(t => (
                  <span key={t} className="text-[9px] bg-[#1e293b] text-[#3b82f6] px-1.5 py-0.5 rounded font-bold">{t}</span>
                ))}
                <span className="text-[9px] text-[#4b5563]">{item.source}</span>
                <span className="text-[9px] text-[#4b5563]">{timeAgo(item.published_at)}</span>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1 flex-shrink-0">
              <span className={`text-[8px] font-bold uppercase px-2 py-0.5 rounded ${SENTIMENT_STYLE[item.sentiment] ?? SENTIMENT_STYLE.neutral}`}>
                {item.sentiment}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
