'use client'
import { useEffect, useState } from 'react'
import { getWatchlistStatus } from '@/lib/api'
import type { WatchlistAlert } from '@/lib/types'

export default function TopBar() {
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])

  useEffect(() => {
    getWatchlistStatus().then(setAlerts).catch(() => {})
  }, [])

  const triggered = alerts.filter(a => a.status === 'TRIGGERED').length
  const breaking = alerts.filter(a => a.status === 'BREAKING_DOWN').length

  return (
    <header className="h-8 bg-[#0a0e17] border-b border-[#1e293b] flex items-center gap-5 px-4 text-[11px]">
      <span className="bg-[#22c55e]/10 text-[#22c55e] border border-[#22c55e]/30 px-2 py-0.5 rounded text-[10px] font-semibold">● LIVE</span>
      <span className="text-[#64748b]">TRIGGERED <span className="text-[#f59e0b] font-bold">{triggered}</span></span>
      <span className="text-[#64748b]">BREAKING DOWN <span className="text-[#ef4444] font-bold">{breaking}</span></span>
    </header>
  )
}
