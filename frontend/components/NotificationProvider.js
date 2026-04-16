import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react"
import { useReceptionRing } from "../hooks/useReceptionRing"
import { useChimeSound } from "../hooks/useChimeSound"
import ReceptionRing from "./ReceptionRing"

// Create context
const NotificationContext = createContext(null)

/**
 * Notification Provider Component
 * Wraps your app to enable real-time ring notifications.
 *
 * Usage:
 * <NotificationProvider token={accessToken}>
 *   <App />
 * </NotificationProvider>
 */
export function NotificationProvider({ token, apiBaseUrl = "", children }) {
  const { ring, isConnected, error, dismissRing, respondToRing } =
    useReceptionRing(token, apiBaseUrl)
  const [activeRing, setActiveRing] = useState(null)

  // Sync ring state and play sound
  useEffect(() => {
    if (ring) {
      setActiveRing(ring)
    }
  }, [ring])

  const handleDismiss = useCallback(() => {
    setActiveRing(null)
    dismissRing()
  }, [dismissRing])

  const handleResponse = useCallback(
    async response => {
      await respondToRing(response)
      setActiveRing(null)
    },
    [respondToRing],
  )

  const value = {
    isConnected,
    error,
    activeRing,
    dismiss: handleDismiss,
  }

  return (
    <NotificationContext.Provider value={value}>
      {children}

      {/* Reception Ring Modal */}
      {activeRing && (
        <ReceptionRing
          ring={activeRing}
          onDismiss={handleDismiss}
          onResponse={handleResponse}
        />
      )}
    </NotificationContext.Provider>
  )
}

/**
 * Hook to access notification context
 */
export function useNotificationContext() {
  const context = useContext(NotificationContext)
  if (!context) {
    throw new Error(
      "useNotificationContext must be used within a NotificationProvider",
    )
  }
  return context
}

/**
 * Simple standalone hook for ring notifications
 * Use this if you don't want to use the provider
 */
export function useRingNotifications(token, apiBaseUrl = "") {
  const [ring, setRing] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const { startLoop, stopLoop, playChime } = useChimeSound()

  // Connection logic is handled by useReceptionRing
  const {
    ring: wsRing,
    isConnected: wsConnected,
    respondToRing,
  } = useReceptionRing(token, apiBaseUrl)

  useEffect(() => {
    if (wsRing) {
      setRing(wsRing)
      // Initialize audio and play chime
      playChime()
      startLoop(2500)
    }
  }, [wsRing, playChime, startLoop])

  useEffect(() => {
    setIsConnected(wsConnected)
  }, [wsConnected])

  const dismiss = useCallback(() => {
    stopLoop()
    setRing(null)
  }, [stopLoop])

  const respond = useCallback(
    async response => {
      stopLoop()
      await respondToRing(response)
      setRing(null)
    },
    [respondToRing, stopLoop],
  )

  return {
    ring,
    isConnected,
    dismiss,
    respond,
  }
}

export default NotificationProvider
