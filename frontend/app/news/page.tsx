'use client'
import { useState } from 'react'
import { getNews } from '@/lib/api'
import NewsPanel from '@/components/NewsPanel'
import type { NewsItem } from '@/lib/types'

const SENTIMENT_FILTER = ['all', 'bullish', 'bearish', 'neutral'] as const

export default function NewsPage() {
  const [tickers, setTickers] = useState('AAPL,MSFT,NVDA,TSLA,META')
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<typeof SENTIMENT_FILTER[number]>('all')

  async function handleLoad() {
    setLoading(true)
    try {
      const list = tickers.split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
      const data = await getNews(list)
      setItems(data)
    } catch {} finally {
      setLoading(false)
    }
  }

  const filtered = filter === 'all' ? items : items.filter(i => i.sentiment === filter)
  const counts = {
    bullish: items.filter(i => i.sentiment === 'bullish').length,
    bearish: items.filter(i => i.sentiment === 'bearish').length,
    neutral: items.filter(i => i.sentiment === 'neutral').length,
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <div className="text-white font-bold mb-3">News Feed</div>
        <div className="flex items-center gap-3 flex-wrap">
          <input
            value={tickers}
            onChange={e => setTickers(e.target.value)}
            placeholder="AAPL,MSFT,NVDA..."
            className="flex-1 min-w-[200px] bg-[#111827] border border-[#1e293b] rounded px-3 py-1.5 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#3b82f6]"
          />
          <button
            onClick={handleLoad}
            disabled={loading}
            className="bg-[#1e3a5f] hover:bg-[#1e4a7f] disabled:opacity-50 border border-[#3b82f6]/40 text-[#3b82f6] text-[11px] font-bold px-4 py-1.5 rounded transition-colors"
          >
            {loading ? 'Loading...' : 'Load News'}
          </button>
        </div>

        {items.length > 0 && (
          <div className="flex gap-2 mt-2">
            {SENTIMENT_FILTER.map(s => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className={`text-[10px] px-2 py-0.5 rounded font-semibold transition-colors ${
                  filter === s
                    ? s === 'bullish' ? 'bg-[#22c55e] text-black'
                    : s === 'bearish' ? 'bg-[#ef4444] text-black'
                    : s === 'neutral' ? 'bg-[#64748b] text-white'
                    : 'bg-[#3b82f6] text-black'
                    : 'bg-[#1e293b] text-[#94a3b8] hover:bg-[#334155]'
                }`}
              >
                {s === 'all' ? `All (${items.length})` : `${s} (${counts[s as keyof typeof counts]})`}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {items.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full text-[#4b5563] text-sm">
            Enter tickers and click Load News
          </div>
        ) : (
          <NewsPanel items={filtered} />
        )}
      </div>
    </div>
  )
}
