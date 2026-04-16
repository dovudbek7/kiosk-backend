import { useState, useEffect, useCallback, useRef } from "react"

/**
 * WebSocket connection hook for real-time notifications.
 * Connects to ws://127.0.0.1:8000/ws/notifications/
 */
export function useNotifications(token) {
  const [isConnected, setIsConnected] = useState(false)
  const [lastNotification, setLastNotification] = useState(null)
  const [error, setError] = useState(null)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

  const connect = useCallback(() => {
    if (!token) return

    // Close existing connection if any
    if (wsRef.current) {
      wsRef.current.close()
    }

    // Determine WebSocket URL (use same host as current page)
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = "127.0.0.1:8000"
    const wsUrl = `${protocol}//${host}/ws/notifications/`

    try {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        setIsConnected(true)
        setError(null)

        // Send authentication token after connection
        ws.send(JSON.stringify({ token }))
      }

      ws.onmessage = event => {
        try {
          const data = JSON.parse(event.data)
          setLastNotification(data)

          // Trigger callback for specific notification types
          if (data.type === "ring") {
            // Handle ring notification - will be used by ReceptionRing component
            window.dispatchEvent(
              new CustomEvent("ring-notification", { detail: data }),
            )
          }
        } catch (e) {
          console.error("Failed to parse notification:", e)
        }
      }

      ws.onerror = e => {
        setError(e)
        console.error("WebSocket error:", e)
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null

        // Attempt to reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          if (token) {
            connect()
          }
        }, 3000)
      }

      wsRef.current = ws
    } catch (e) {
      setError(e)
      console.error("Failed to create WebSocket:", e)
    }
  }, [token])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
  }, [])

  // Connect when token is available
  useEffect(() => {
    if (token) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [token, connect, disconnect])

  return {
    isConnected,
    lastNotification,
    error,
    connect,
    disconnect,
  }
}

export default useNotifications
