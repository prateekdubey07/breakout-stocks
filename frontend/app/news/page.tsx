'use client'
import { useState, useEffect } from 'react'
import { getNews, getDefaultTickers } from '@/lib/api'
import NewsPanel from '@/components/NewsPanel'
import type { NewsItem } from '@/lib/types'

const SENTIMENT_FILTER = ['all', 'bullish', 'bearish', 'neutral'] as const

export default function NewsPage() {
  const [tickers, setTickers] = useState('AAPL,MSFT,NVDA,TSLA,META')
  const [items, setItems] = useState<NewsItem[]>([])
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<typeof SENTIMENT_FILTER[number]>('all')

  useEffect(() => {
    getDefaultTickers().then(t => setTickers(t.join(','))).catch(() => {})
  }, [])

  async function handleLoad() {
    setLoading(true)
    try {
      const list = tickers.split(',').map(t => t.trim().toUpperCase()).filter(Boolean)
      const data = await getNews(list)
      setItems(Array.isArray(data) ? data : (data.items ?? []))
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
          <div className="mt-3 flex gap-3 flex-wrap">
            {[
              { label: 'Total Articles', value: items.length, color: 'text-white', bg: 'bg-[#111827]', border: 'border-[#1e293b]', key: 'all' },
              { label: 'Bullish', value: counts.bullish, color: 'text-[#22c55e]', bg: 'bg-[#0d1f12]', border: 'border-[#22c55e]/30', key: 'bullish' },
              { label: 'Bearish', value: counts.bearish, color: 'text-[#ef4444]', bg: 'bg-[#1f0d0d]', border: 'border-[#ef4444]/30', key: 'bearish' },
              { label: 'Neutral', value: counts.neutral, color: 'text-[#94a3b8]', bg: 'bg-[#111827]', border: 'border-[#334155]', key: 'neutral' },
            ].map(card => (
              <button
                key={card.key}
                onClick={() => setFilter(card.key as typeof SENTIMENT_FILTER[number])}
                className={`${card.bg} border ${card.border} rounded px-4 py-2.5 text-left transition-all ${filter === card.key ? 'ring-1 ring-white/20' : 'opacity-80 hover:opacity-100'}`}
              >
                <div className="text-[9px] text-[#64748b] uppercase tracking-wide mb-0.5">{card.label}</div>
                <div className={`text-2xl font-black ${card.color}`}>{card.value}</div>
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
