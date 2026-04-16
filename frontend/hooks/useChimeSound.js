import { useRef, useCallback, useEffect } from "react"

/**
 * Custom hook for playing a chime sound using Web Audio API.
 * Designed to work even when the tab is in the background.
 */
export function useChimeSound() {
  const audioContextRef = useRef(null)
  const gainNodeRef = useRef(null)
  const intervalRef = useRef(null)
  const isPlayingRef = useRef(false)

  // Initialize audio context lazily (must be done after user interaction)
  const initAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      const AudioContext = window.AudioContext || window.webkitAudioContext
      audioContextRef.current = new AudioContext()

      // Create gain node for volume control
      gainNodeRef.current = audioContextRef.current.createGain()
      gainNodeRef.current.gain.value = 0.5
      gainNodeRef.current.connect(audioContextRef.current.destination)
    }

    // Resume if suspended (needed for background playback)
    if (audioContextRef.current.state === "suspended") {
      audioContextRef.current.resume()
    }

    return audioContextRef.current
  }, [])

  // Generate a chime sound using oscillators
  const playChime = useCallback(() => {
    const ctx = initAudioContext()
    const now = ctx.currentTime

    // Create multiple oscillators for a rich chime sound
    const frequencies = [880, 1108.73, 1318.51] // A5, C#6, E6 (A major chord)

    frequencies.forEach((freq, index) => {
      const oscillator = ctx.createOscillator()
      const noteGain = ctx.createGain()

      // Bell-like waveform (combination of sine and overtones)
      oscillator.type = "sine"
      oscillator.frequency.value = freq

      // Envelope for bell-like attack and decay
      noteGain.gain.setValueAtTime(0, now)
      noteGain.gain.linearRampToValueAtTime(0.3, now + 0.01) // Quick attack
      noteGain.gain.exponentialRampToValueAtTime(0.001, now + 1.5) // Long decay

      oscillator.connect(noteGain)
      noteGain.connect(gainNodeRef.current)

      oscillator.start(now)
      oscillator.stop(now + 2)
    })

    // Add a high-pitched accent tone
    const accentOsc = ctx.createOscillator()
    const accentGain = ctx.createGain()

    accentOsc.type = "sine"
    accentOsc.frequency.value = 1760 // A6

    accentGain.gain.setValueAtTime(0, now)
    accentGain.gain.linearRampToValueAtTime(0.15, now + 0.005)
    accentGain.gain.exponentialRampToValueAtTime(0.001, now + 0.8)

    accentOsc.connect(accentGain)
    accentGain.connect(gainNodeRef.current)

    accentOsc.start(now)
    accentOsc.stop(now + 1)
  }, [initAudioContext])

  // Start looped playback
  const startLoop = useCallback(
    (intervalMs = 2000) => {
      if (isPlayingRef.current) return

      isPlayingRef.current = true

      // Play immediately
      playChime()

      // Then loop at specified interval
      intervalRef.current = setInterval(() => {
        playChime()
      }, intervalMs)
    },
    [playChime],
  )

  // Stop looped playback
  const stopLoop = useCallback(() => {
    isPlayingRef.current = false

    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopLoop()
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [stopLoop])

  return {
    playChime,
    startLoop,
    stopLoop,
    isPlaying: isPlayingRef.current,
  }
}

export default useChimeSound
