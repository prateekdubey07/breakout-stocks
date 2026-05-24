'use client'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface Point { date: string; close: number }

export default function PriceChart({ data }: { data: Point[] }) {
  return (
    <div className="bg-[#0a0e17] rounded h-20">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 4 }}>
          <XAxis dataKey="date" hide />
          <YAxis domain={['auto', 'auto']} tick={{ fill: '#64748b', fontSize: 9 }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: 'none', fontSize: 11 }}
            labelStyle={{ color: '#94a3b8' }}
            itemStyle={{ color: '#3b82f6' }}
          />
          <Line type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
