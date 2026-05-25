'use client'
import { useEffect, useRef, useState } from 'react'
import type { WatchlistAlert } from '@/lib/types'

export function useWebSocket() {
  const [alerts, setAlerts] = useState<WatchlistAlert[]>([])
  const [connected, setConnected] = useState(false)
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    function connect() {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const wsUrl = apiUrl.replace(/^https/, 'wss').replace(/^http/, 'ws') + '/ws/alerts'
      const socket = new WebSocket(wsUrl)
      ws.current = socket

      socket.onopen = () => setConnected(true)
      socket.onclose = () => {
        setConnected(false)
        setTimeout(connect, 3000)
      }
      socket.onerror = () => socket.close()
      socket.onmessage = (e) => {
        try {
          const alert: WatchlistAlert = JSON.parse(e.data)
          setAlerts(prev => [alert, ...prev].slice(0, 50))
        } catch {}
      }
    }
    connect()
    return () => ws.current?.close()
  }, [])

  return { alerts, connected }
}
