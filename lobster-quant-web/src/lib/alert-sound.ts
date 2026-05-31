/**
 * Alert Sound Utility
 * Generates alert notification sounds using the Web Audio API.
 * No external audio files or libraries required.
 */

let audioCtx: AudioContext | null = null

function getAudioContext(): AudioContext {
  if (!audioCtx) {
    audioCtx = new AudioContext()
  }
  // Resume if suspended (browsers block audio until user interaction)
  if (audioCtx.state === 'suspended') {
    audioCtx.resume()
  }
  return audioCtx
}

/**
 * Play a short alert tone (two-tone chime).
 * Safe to call multiple times — browsers throttle rapid audio.
 */
export function playAlertSound(): void {
  try {
    const ctx = getAudioContext()
    const now = ctx.currentTime

    // First tone: 880 Hz (A5) for 120ms
    const osc1 = ctx.createOscillator()
    const gain1 = ctx.createGain()
    osc1.type = 'sine'
    osc1.frequency.setValueAtTime(880, now)
    gain1.gain.setValueAtTime(0.3, now)
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.12)
    osc1.connect(gain1)
    gain1.connect(ctx.destination)
    osc1.start(now)
    osc1.stop(now + 0.12)

    // Second tone: 1100 Hz (C#6) for 180ms — slightly delayed for chime effect
    const osc2 = ctx.createOscillator()
    const gain2 = ctx.createGain()
    osc2.type = 'sine'
    osc2.frequency.setValueAtTime(1100, now + 0.12)
    gain2.gain.setValueAtTime(0.3, now + 0.12)
    gain2.gain.exponentialRampToValueAtTime(0.01, now + 0.3)
    osc2.connect(gain2)
    gain2.connect(ctx.destination)
    osc2.start(now + 0.12)
    osc2.stop(now + 0.3)
  } catch {
    // Silently fail — audio may be blocked by browser policy
  }
}
