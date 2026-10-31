import { useEffect, useRef, useState } from 'react'

// http -> ws and https -> wss, so production gets an encrypted socket for free.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const WS_URL = API_URL.replace(/^http/, 'ws') + '/ws'
const RETRY_MS = 3000

// Owns the single WebSocket to the backend. The grid never depends on it:
// if the backend is down, `connected` is false and everything else still works.
export default function useBackend(channels, focused, onDirectorFocus) {
  const [connected, setConnected] = useState(false)
  const [stats, setStats] = useState(null)
  const wsRef = useRef(null)
  // The socket callbacks are created once, so they read the latest props from
  // a ref instead of capturing stale values from the first render.
  const latest = useRef({})
  latest.current = { channels, focused, onDirectorFocus }

  function send(msg) {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg))
  }

  useEffect(() => {
    let stopped = false
    let retryTimer

    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen = () => {
        setConnected(true)
        // A new connection knows nothing, so always tell it the full list.
        send({ type: 'set_channels', channels: latest.current.channels, focus: latest.current.focused })
      }
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'stats') setStats(msg)
        else if (msg.type === 'focus') latest.current.onDirectorFocus(msg.channel, msg.reason)
      }
      ws.onclose = () => {
        // Ignore old sockets (React StrictMode mounts effects twice in dev).
        if (wsRef.current !== ws) return
        setConnected(false)
        setStats(null)
        if (!stopped) retryTimer = setTimeout(connect, RETRY_MS)
      }
    }

    connect()
    return () => {
      stopped = true
      clearTimeout(retryTimer)
      const ws = wsRef.current
      wsRef.current = null
      ws?.close()
    }
  }, [])

  // Whenever the grid changes, tell the backend so it can JOIN/PART chats.
  useEffect(() => {
    send({ type: 'set_channels', channels, focus: focused })
  }, [channels])

  return {
    connected,
    stats,
    sendManualFocus: (channel) => send({ type: 'manual_focus', channel }),
  }
}
