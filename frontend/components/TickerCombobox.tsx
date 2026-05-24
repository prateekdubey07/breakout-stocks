'use client'
import { useEffect, useState, useRef } from 'react'

export default function TickerCombobox({
  value, onChange, tickers, placeholder = 'Search ticker...',
  width = 'w-36',
}: {
  value: string
  onChange: (v: string) => void
  tickers: string[]
  placeholder?: string
  width?: string
}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(value)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { setQuery(value) }, [value])
  useEffect(() => {
    const handler = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = query
    ? tickers.filter(t => t.includes(query.toUpperCase())).slice(0, 50)
    : tickers.slice(0, 50)

  return (
    <div ref={ref} className={`relative ${width}`}>
      <input
        value={query}
        onChange={e => { setQuery(e.target.value.toUpperCase()); setOpen(true) }}
        onFocus={() => setOpen(true)}
        placeholder={placeholder}
        className="w-full bg-[#111827] border border-[#1e293b] rounded px-2 py-1.5 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#3b82f6]"
      />
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 z-50 w-full bg-[#111827] border border-[#1e293b] rounded mt-0.5 max-h-64 overflow-y-auto shadow-xl">
          {filtered.map(t => (
            <div key={t} onMouseDown={() => { onChange(t); setQuery(t); setOpen(false) }}
              className={`px-3 py-1.5 text-[11px] cursor-pointer hover:bg-[#1e293b] ${t === value ? 'text-[#3b82f6]' : 'text-[#e2e8f0]'}`}>
              {t}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
