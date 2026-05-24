'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/scanner', label: 'Scanner', icon: '📡' },
  { href: '/watchlist', label: 'Watchlist', icon: '👁' },
  { href: '/backtest', label: 'Backtest', icon: '📊' },
  { href: '/news', label: 'News Feed', icon: '📰' },
]

export default function Sidebar() {
  const path = usePathname()
  return (
    <aside className="w-40 min-h-screen bg-[#0a0e17] border-r border-[#1e293b] flex flex-col">
      <div className="px-4 py-4 border-b border-[#1e293b]">
        <div className="text-white font-bold text-sm">BreakoutStocks</div>
        <div className="text-[#64748b] text-[9px] uppercase tracking-widest mt-0.5">Breakout Platform</div>
      </div>
      <nav className="flex-1 py-2">
        {NAV.map(({ href, label, icon }) => (
          <Link
            key={href}
            href={href}
            className={`flex items-center gap-2 px-4 py-2 text-[11px] border-l-2 transition-colors ${
              path.startsWith(href)
                ? 'text-white border-[#22c55e] bg-white/5'
                : 'text-[#64748b] border-transparent hover:text-[#94a3b8]'
            }`}
          >
            <span>{icon}</span>
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
