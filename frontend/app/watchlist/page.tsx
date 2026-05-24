'use client'
import { useEffect, useState } from 'react'
import { getWatchlist, removeFromWatchlist } from '@/lib/api'
import { useWebSocket } from '@/hooks/useWebSocket'
import AlertBanner from '@/components/AlertBanner'

interface WatchlistItem {
  ticker: string
  bps: number
  pattern: string
  entry_zone: string
  stop: string
  target_1: string
  added_at?: string
}

const STATUS_COLOR: Record<string, string> = {
  TRIGGERED:     'text-[#22c55e] bg-[#14532d]',
  BREAKING_DOWN: 'text-[#ef4444] bg-[#3a1a1a]',
  STILL_VALID:   'text-[#3b82f6] bg-[#1c3a5f]',
}

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([])
  const { alerts, connected } = useWebSocket()

  useEffect(() => {
    getWatchlist().then(setItems).catch(() => {})
  }, [])

  function handleRemove(ticker: string) {
    removeFromWatchlist(ticker).then(() => setItems(prev => prev.filter(i => i.ticker !== ticker)))
  }

  const latestStatus: Record<string, string> = {}
  alerts.forEach(a => { if (!latestStatus[a.ticker]) latestStatus[a.ticker] = a.status })

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <AlertBanner alerts={alerts} />
      <div className="px-5 py-3 border-b border-[#1e293b] flex items-center justify-between">
        <div>
          <div className="text-white font-bold">Watchlist</div>
          <div className="text-[#64748b] text-[10px]">{items.length} tickers monitored · WS {connected ? 'LIVE' : 'OFF'}</div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex items-center justify-center h-full text-[#4b5563] text-sm">
            No tickers in watchlist. Add them from the Scanner.
          </div>
        ) : (
          <table className="w-full">
            <thead className="sticky top-0 bg-[#0a0e17]">
              <tr>
                {['Ticker', 'BPS', 'Pattern', 'Entry', 'Stop', 'Target', 'Status', ''].map(h => (
                  <th key={h} className="px-4 py-2 text-left text-[9px] text-[#64748b] uppercase tracking-wide border-b border-[#1e293b]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map(item => {
                const status = latestStatus[item.ticker]
                return (
                  <tr key={item.ticker} className="border-b border-[#0f1623] hover:bg-white/5 transition-colors">
                    <td className="px-4 py-3 font-bold text-white text-[12px]">{item.ticker}</td>
                    <td className="px-4 py-3 text-[#22c55e] font-bold text-[12px]">{item.bps}</td>
                    <td className="px-4 py-3 text-[#94a3b8] text-[10px]">{item.pattern}</td>
                    <td className="px-4 py-3 text-[#3b82f6] text-[11px]">{item.entry_zone}</td>
                    <td className="px-4 py-3 text-[#ef4444] text-[11px]">{item.stop}</td>
                    <td className="px-4 py-3 text-[#22c55e] text-[11px]">{item.target_1}</td>
                    <td className="px-4 py-3">
                      {status && (
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded ${STATUS_COLOR[status] ?? 'text-[#94a3b8] bg-[#1e293b]'}`}>
                          {status.replace('_', ' ')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleRemove(item.ticker)}
                        className="text-[#ef4444] hover:text-white text-[10px] transition-colors"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
