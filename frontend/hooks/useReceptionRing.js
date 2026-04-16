import { useState, useEffect, useCallback } from "react"

/**
 * Combined hook for handling reception ring notifications.
 * Integrates WebSocket connection with ring display and sound.
 */
export function useReceptionRing(token, apiBaseUrl = "") {
  const [ring, setRing] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [ws, setWs] = useState(null)
  const [error, setError] = useState(null)

  // Connect to WebSocket
  useEffect(() => {
    if (!token) return

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = "127.0.0.1:8000"
    const wsUrl = `${protocol}//${host}/ws/notifications/`

    let wsInstance = null
    let reconnectTimeout = null

    const connect = () => {
      try {
        wsInstance = new WebSocket(wsUrl)

        wsInstance.onopen = () => {
          setIsConnected(true)
          setError(null)
        }

        wsInstance.onmessage = event => {
          try {
            const data = JSON.parse(event.data)

            if (data.type === "ring") {
              setRing(data)
            }
          } catch (e) {
            console.error("Failed to parse notification:", e)
          }
        }

        wsInstance.onerror = e => {
          setError(e)
        }

        wsInstance.onclose = () => {
          setIsConnected(false)
          setWs(null)

          // Reconnect after 3 seconds
          reconnectTimeout = setTimeout(() => {
            if (token) {
              connect()
            }
          }, 3000)
        }

        setWs(wsInstance)
      } catch (e) {
        setError(e)
      }
    }

    connect()

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout)
      }
      if (wsInstance) {
        wsInstance.close()
      }
    }
  }, [token])

  // Dismiss the ring
  const dismissRing = useCallback(() => {
    setRing(null)
  }, [])

  // Respond to the ring
  const respondToRing = useCallback(
    async response => {
      if (!ring?.ringId) return

      try {
        const responseData = await fetch(
          `${apiBaseUrl}/api/v1/targets/respond/${ring.ringId}/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ response }),
          },
        )

        if (responseData.ok) {
          const result = await responseData.json()
          console.log("Ring response sent:", result)
        }
      } catch (e) {
        console.error("Failed to send ring response:", e)
      }

      setRing(null)
    },
    [ring, token, apiBaseUrl],
  )

  return {
    ring,
    isConnected,
    error,
    dismissRing,
    respondToRing,
  }
}

export default useReceptionRing
