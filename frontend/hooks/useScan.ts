'use client'
import { useState, useCallback } from 'react'
import type { BpsResult } from '@/lib/types'
import { scanTickers } from '@/lib/api'

export function useScan() {
  const [results, setResults] = useState<BpsResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const scan = useCallback(async (tickers: string[], minBps = 50) => {
    setLoading(true)
    setError(null)
    try {
      const data = await scanTickers(tickers, minBps)
      setResults(Array.isArray(data) ? data : (data.candidates ?? []))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scan failed')
    } finally {
      setLoading(false)
    }
  }, [])

  return { results, loading, error, scan, setResults }
}
