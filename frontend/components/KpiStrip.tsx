interface Kpi { label: string; value: string | number; sub: string; color: string }

export default function KpiStrip({ kpis }: { kpis: Kpi[] }) {
  return (
    <div className="grid grid-cols-6 gap-2 px-5 py-3 border-b border-[#1e293b]">
      {kpis.map(({ label, value, sub, color }) => (
        <div key={label} className="bg-[#111827] border border-[#1e293b] rounded-md px-3 py-2">
          <div className="text-[#64748b] text-[9px] uppercase tracking-wide mb-1">{label}</div>
          <div className={`text-[22px] font-bold leading-none ${color}`}>{value}</div>
          <div className="text-[#64748b] text-[9px] mt-1">{sub}</div>
        </div>
      ))}
    </div>
  )
}
