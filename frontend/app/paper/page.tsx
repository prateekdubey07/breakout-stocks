'use client'
import { useEffect, useState } from 'react'
import { getDefaultTickers } from '@/lib/api'
import TickerCombobox from '@/components/TickerCombobox'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Trade {
  id: number; ticker: string; entry_price: number; shares: number
  stop_loss: number | null; target_1: number | null
  entry_date: string; exit_price: number | null; exit_date: string | null
  status: 'OPEN' | 'CLOSED'; pnl_usd: number | null; pnl_pct: number | null
  live_price: number | null; unrealized_pnl_usd: number | null; unrealized_pnl_pct: number | null
  notes: string
}

function fmt(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 })
}

export default function PaperPage() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [tickers, setTickers] = useState<string[]>([])
  const [form, setForm] = useState({ ticker: '', amount: '', stop_loss: '', target_1: '', notes: '' })
  const [closeId, setCloseId] = useState<number | null>(null)
  const [closePrice, setClosePrice] = useState('')
  const [loading, setLoading] = useState(false)

  const load = () => fetch(`${BASE}/api/paper-trades`).then(r => r.json()).then(setTrades).catch(() => {})

  useEffect(() => {
    load()
    getDefaultTickers().then(setTickers).catch(() => {})
  }, [])

  async function handleOpen() {
    if (!form.ticker || !form.amount) return
    const amount = parseFloat(form.amount)
    if (isNaN(amount) || amount <= 0) return

    // Fetch live price to calculate shares
    setLoading(true)
    try {
      const df = await fetch(`${BASE}/api/ohlcv/${form.ticker}?period=5d`).then(r => r.json())
      const price = df.data?.at(-1)?.close
      if (!price) throw new Error('no price')
      const shares = parseFloat((amount / price).toFixed(4))
      await fetch(`${BASE}/api/paper-trades`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: form.ticker,
          entry_price: price,
          shares,
          stop_loss: form.stop_loss ? parseFloat(form.stop_loss) : null,
          target_1: form.target_1 ? parseFloat(form.target_1) : null,
          notes: form.notes || `$${amount} @ $${price.toFixed(2)}`,
        }),
      })
      setForm({ ticker: '', amount: '', stop_loss: '', target_1: '', notes: '' })
      await load()
    } catch (e) {
      alert('Failed to get price for ' + form.ticker)
    } finally {
      setLoading(false)
    }
  }

  async function handleClose() {
    if (!closeId || !closePrice) return
    await fetch(`${BASE}/api/paper-trades/${closeId}/close`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ exit_price: parseFloat(closePrice) }),
    })
    setCloseId(null); setClosePrice(''); load()
  }

  const handleDelete = async (id: number) => { await fetch(`${BASE}/api/paper-trades/${id}`, { method: 'DELETE' }); load() }

  const open = trades.filter(t => t.status === 'OPEN')
  const closed = trades.filter(t => t.status === 'CLOSED')
  const totalUnrealized = open.reduce((s, t) => s + (t.unrealized_pnl_usd ?? 0), 0)
  const totalRealized = closed.reduce((s, t) => s + (t.pnl_usd ?? 0), 0)
  const totalInvested = open.reduce((s, t) => s + t.entry_price * t.shares, 0)

  const inp = (placeholder: string, key: keyof typeof form, width = 'w-24') => (
    <input value={form[key]} onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
      placeholder={placeholder}
      className={`${width} bg-[#111827] border border-[#1e293b] rounded px-2 py-1.5 text-[12px] text-[#e2e8f0] placeholder-[#4b5563] focus:outline-none focus:border-[#3b82f6]`} />
  )

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <div className="px-5 py-3 border-b border-[#1e293b]">
        <div className="text-white font-bold mb-3">Paper Trading</div>

        {/* Stats row */}
        <div className="flex gap-3 mb-3 flex-wrap">
          {[
            { label: 'Open Positions', value: open.length, color: 'text-white' },
            { label: 'Total Invested', value: fmt(totalInvested), color: 'text-[#3b82f6]' },
            { label: 'Unrealized P&L', value: (totalUnrealized >= 0 ? '+' : '') + fmt(totalUnrealized), color: totalUnrealized >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]' },
            { label: 'Realized P&L', value: (totalRealized >= 0 ? '+' : '') + fmt(totalRealized), color: totalRealized >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]' },
          ].map(s => (
            <div key={s.label} className="bg-[#111827] border border-[#1e293b] rounded px-3 py-2">
              <div className="text-[9px] text-[#64748b] uppercase mb-0.5">{s.label}</div>
              <div className={`font-bold text-[15px] ${s.color}`}>{s.value}</div>
            </div>
          ))}
        </div>

        {/* Entry form */}
        <div className="flex items-center gap-2 flex-wrap">
          <TickerCombobox value={form.ticker} onChange={t => setForm(f => ({ ...f, ticker: t }))} tickers={tickers} width="w-32" />
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-[#64748b]">Invest $</span>
            {inp('Amount', 'amount', 'w-28')}
          </div>
          {inp('Stop $', 'stop_loss')}
          {inp('Target $', 'target_1')}
          {inp('Notes', 'notes', 'w-36')}
          <button onClick={handleOpen} disabled={loading || !form.ticker || !form.amount}
            className="bg-[#14532d] hover:bg-[#166534] border border-[#22c55e]/40 text-[#22c55e] text-[11px] font-bold px-4 py-1.5 rounded transition-colors disabled:opacity-50">
            {loading ? 'Opening...' : '+ Open Trade'}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {open.length > 0 && (
          <div className="p-4">
            <div className="text-[10px] text-[#64748b] uppercase tracking-wide mb-2">Open Positions</div>
            <table className="w-full">
              <thead><tr className="text-[8px] text-[#4b5563] uppercase border-b border-[#1e293b]">
                {['Ticker','Invested','Entry','Shares','Stop','Target','Live','Unr. P&L','%','Date',''].map(h =>
                  <th key={h} className="text-left px-3 py-1.5">{h}</th>)}
              </tr></thead>
              <tbody>
                {open.map(t => {
                  const invested = t.entry_price * t.shares
                  return (
                    <tr key={t.id} className="border-b border-[#0f1623] hover:bg-white/5">
                      <td className="px-3 py-2 font-bold text-white">{t.ticker}</td>
                      <td className="px-3 py-2 text-[#3b82f6] text-[11px]">{fmt(invested)}</td>
                      <td className="px-3 py-2 text-[#94a3b8] text-[11px]">{fmt(t.entry_price)}</td>
                      <td className="px-3 py-2 text-[#64748b] text-[10px]">{t.shares}</td>
                      <td className="px-3 py-2 text-[#ef4444] text-[11px]">{t.stop_loss ? fmt(t.stop_loss) : '—'}</td>
                      <td className="px-3 py-2 text-[#22c55e] text-[11px]">{t.target_1 ? fmt(t.target_1) : '—'}</td>
                      <td className="px-3 py-2 text-[#3b82f6] text-[11px]">{t.live_price ? fmt(t.live_price) : '—'}</td>
                      <td className={`px-3 py-2 text-[11px] font-semibold ${(t.unrealized_pnl_usd ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                        {t.unrealized_pnl_usd != null ? ((t.unrealized_pnl_usd >= 0 ? '+' : '') + fmt(t.unrealized_pnl_usd)) : '—'}
                      </td>
                      <td className={`px-3 py-2 text-[11px] ${(t.unrealized_pnl_pct ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                        {t.unrealized_pnl_pct != null ? `${t.unrealized_pnl_pct >= 0 ? '+' : ''}${t.unrealized_pnl_pct.toFixed(1)}%` : '—'}
                      </td>
                      <td className="px-3 py-2 text-[#64748b] text-[10px]">{t.entry_date}</td>
                      <td className="px-3 py-2">
                        {closeId === t.id ? (
                          <div className="flex gap-1 items-center">
                            <input value={closePrice} onChange={e => setClosePrice(e.target.value)} placeholder="Exit $"
                              className="w-20 bg-[#111827] border border-[#ef4444]/50 rounded px-2 py-0.5 text-[11px] text-[#e2e8f0] focus:outline-none" />
                            <button onClick={handleClose} className="text-[#22c55e] text-[11px] font-bold hover:text-white">✓</button>
                            <button onClick={() => setCloseId(null)} className="text-[#64748b] text-[10px] hover:text-white">✕</button>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <button onClick={() => { setCloseId(t.id); setClosePrice(String(t.live_price ?? '')) }}
                              className="text-[#f59e0b] text-[10px] hover:text-white">Close</button>
                            <button onClick={() => handleDelete(t.id)} className="text-[#ef4444] text-[10px] hover:text-white">Del</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {closed.length > 0 && (
          <div className="p-4">
            <div className="text-[10px] text-[#64748b] uppercase tracking-wide mb-2">Closed Trades</div>
            <table className="w-full">
              <thead><tr className="text-[8px] text-[#4b5563] uppercase border-b border-[#1e293b]">
                {['Ticker','Invested','Entry','Exit','Shares','P&L $','P&L %','Entry Date','Exit Date',''].map(h =>
                  <th key={h} className="text-left px-3 py-1.5">{h}</th>)}
              </tr></thead>
              <tbody>
                {closed.map(t => (
                  <tr key={t.id} className="border-b border-[#0f1623] hover:bg-white/5 opacity-70">
                    <td className="px-3 py-2 font-bold text-white">{t.ticker}</td>
                    <td className="px-3 py-2 text-[#3b82f6] text-[11px]">{fmt(t.entry_price * t.shares)}</td>
                    <td className="px-3 py-2 text-[#94a3b8] text-[11px]">{fmt(t.entry_price)}</td>
                    <td className="px-3 py-2 text-[#94a3b8] text-[11px]">{t.exit_price ? fmt(t.exit_price) : '—'}</td>
                    <td className="px-3 py-2 text-[#64748b] text-[10px]">{t.shares}</td>
                    <td className={`px-3 py-2 text-[11px] font-semibold ${(t.pnl_usd ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                      {t.pnl_usd != null ? ((t.pnl_usd >= 0 ? '+' : '') + fmt(t.pnl_usd)) : '—'}
                    </td>
                    <td className={`px-3 py-2 text-[11px] ${(t.pnl_pct ?? 0) >= 0 ? 'text-[#22c55e]' : 'text-[#ef4444]'}`}>
                      {t.pnl_pct != null ? `${t.pnl_pct >= 0 ? '+' : ''}${t.pnl_pct.toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-3 py-2 text-[#64748b] text-[10px]">{t.entry_date}</td>
                    <td className="px-3 py-2 text-[#64748b] text-[10px]">{t.exit_date}</td>
                    <td className="px-3 py-2">
                      <button onClick={() => handleDelete(t.id)} className="text-[#4b5563] text-[10px] hover:text-[#ef4444]">Del</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {trades.length === 0 && (
          <div className="flex items-center justify-center h-40 text-[#4b5563] text-sm">
            No paper trades yet. Search a ticker above and enter an investment amount.
          </div>
        )}
      </div>
    </div>
  )
}
