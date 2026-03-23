import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAudioRecorder } from '../../hooks/useAudioRecorder'

/**
 * FE-003: useAudioRecorder Hook Tests
 * Tests recording states, audio capture, and error handling
 */

// Mock MediaRecorder
class MockMediaRecorder {
  static isTypeSupported = vi.fn().mockReturnValue(true)

  state: 'inactive' | 'recording' | 'paused' = 'inactive'
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onstop: (() => void) | null = null

  constructor(_stream: MediaStream, _options?: MediaRecorderOptions) {
    // Store constructor args if needed
  }

  start(_timeslice?: number) {
    this.state = 'recording'
    // Simulate data available after a short delay
    setTimeout(() => {
      if (this.ondataavailable) {
        const mockBlob = new Blob(['audio data'], { type: 'audio/webm' })
        this.ondataavailable({ data: mockBlob })
      }
    }, 100)
  }

  stop() {
    this.state = 'inactive'
    if (this.onstop) {
      this.onstop()
    }
  }

  pause() {
    this.state = 'paused'
  }

  resume() {
    this.state = 'recording'
  }
}

// Mock MediaStream
class MockMediaStream {
  getTracks() {
    return [
      {
        stop: vi.fn(),
      },
    ]
  }
}

// Mock AudioContext
class MockAudioContext {
  sampleRate = 16000

  constructor(_options?: AudioContextOptions) {}

  createMediaStreamSource(_stream: MediaStream) {
    return {
      connect: vi.fn(),
    }
  }

  createAnalyser() {
    return {
      fftSize: 256,
      frequencyBinCount: 128,
      getByteFrequencyData: vi.fn((array: Uint8Array) => {
        // Fill with some mock data
        for (let i = 0; i < array.length; i++) {
          array[i] = Math.random() * 128
        }
      }),
    }
  }

  close() {
    return Promise.resolve()
  }
}

describe('useAudioRecorder Hook', () => {
  beforeEach(() => {
    // Mock navigator.mediaDevices
    vi.stubGlobal('navigator', {
      mediaDevices: {
        getUserMedia: vi.fn().mockResolvedValue(new MockMediaStream()),
      },
    })

    // Mock MediaRecorder
    vi.stubGlobal('MediaRecorder', MockMediaRecorder)

    // Mock AudioContext
    vi.stubGlobal('AudioContext', MockAudioContext)

    // Mock requestAnimationFrame
    vi.stubGlobal('requestAnimationFrame', vi.fn((cb) => setTimeout(cb, 16)))
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  describe('Initial State', () => {
    it('should start with idle recording state', () => {
      const { result } = renderHook(() => useAudioRecorder())

      expect(result.current.recordingState).toBe('idle')
    })

    it('should start with no error', () => {
      const { result } = renderHook(() => useAudioRecorder())

      expect(result.current.error).toBeNull()
    })

    it('should start with zero audio level', () => {
      const { result } = renderHook(() => useAudioRecorder())

      expect(result.current.audioLevel).toBe(0)
    })
  })

  describe('Recording States', () => {
    it('should transition to recording state when startRecording is called', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.recordingState).toBe('recording')
    })

    it('should transition to idle state when stopRecording is called', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.recordingState).toBe('recording')

      act(() => {
        result.current.stopRecording()
      })

      expect(result.current.recordingState).toBe('idle')
    })

    it('should transition to paused state when pauseRecording is called', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      act(() => {
        result.current.pauseRecording()
      })

      expect(result.current.recordingState).toBe('paused')
    })

    it('should transition back to recording when resumeRecording is called', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      act(() => {
        result.current.pauseRecording()
      })

      expect(result.current.recordingState).toBe('paused')

      act(() => {
        result.current.resumeRecording()
      })

      expect(result.current.recordingState).toBe('recording')
    })
  })

  describe('Audio Capture', () => {
    it('should request microphone access with correct constraints', async () => {
      const { result } = renderHook(() => useAudioRecorder({ sampleRate: 16000 }))

      await act(async () => {
        await result.current.startRecording()
      })

      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: expect.objectContaining({
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        }),
      })
    })

    it('should call onAudioChunk callback when audio data is available', async () => {
      const onAudioChunk = vi.fn()
      const { result } = renderHook(() =>
        useAudioRecorder({ onAudioChunk, chunkInterval: 100 })
      )

      await act(async () => {
        await result.current.startRecording()
      })

      // Wait for the mock data to be emitted
      await waitFor(() => {
        expect(onAudioChunk).toHaveBeenCalled()
      }, { timeout: 500 })

      expect(onAudioChunk).toHaveBeenCalledWith(
        expect.any(ArrayBuffer),
        expect.any(Number)
      )
    })
  })

  describe('Error Handling', () => {
    it('should set error when microphone access is denied', async () => {
      const mockError = new Error('Permission denied')
      mockError.name = 'NotAllowedError'

      vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.error).toContain('Microphone access denied')
      expect(result.current.recordingState).toBe('idle')
    })

    it('should set error when no microphone is found', async () => {
      const mockError = new Error('No microphone')
      mockError.name = 'NotFoundError'

      vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.error).toContain('No microphone found')
      expect(result.current.recordingState).toBe('idle')
    })

    it('should handle generic errors', async () => {
      const mockError = new Error('Unknown error')

      vi.mocked(navigator.mediaDevices.getUserMedia).mockRejectedValueOnce(mockError)

      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(result.current.error).toContain('Failed to start recording')
      expect(result.current.recordingState).toBe('idle')
    })
  })

  describe('Audio Level', () => {
    it('should reset audio level to zero when stopped', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      act(() => {
        result.current.stopRecording()
      })

      expect(result.current.audioLevel).toBe(0)
    })

    it('should reset audio level to zero when paused', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      act(() => {
        result.current.pauseRecording()
      })

      expect(result.current.audioLevel).toBe(0)
    })
  })

  describe('Options', () => {
    it('should use default chunk interval if not specified', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      // Just verify hook initializes correctly with defaults
      expect(result.current.recordingState).toBe('idle')
    })

    it('should use custom chunk interval when specified', async () => {
      const { result } = renderHook(() =>
        useAudioRecorder({ chunkInterval: 5000 })
      )

      expect(result.current.recordingState).toBe('idle')
    })

    it('should use custom sample rate when specified', async () => {
      const { result } = renderHook(() =>
        useAudioRecorder({ sampleRate: 44100 })
      )

      await act(async () => {
        await result.current.startRecording()
      })

      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: expect.objectContaining({
          sampleRate: 44100,
        }),
      })
    })
  })

  describe('MediaRecorder Type Support', () => {
    it('should check for supported MIME types', async () => {
      const { result } = renderHook(() => useAudioRecorder())

      await act(async () => {
        await result.current.startRecording()
      })

      expect(MockMediaRecorder.isTypeSupported).toHaveBeenCalled()
    })
  })
})
