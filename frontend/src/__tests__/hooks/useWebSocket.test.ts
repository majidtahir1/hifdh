import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useWebSocket } from '../../hooks/useWebSocket'

/**
 * FE-002: useWebSocket Hook Tests
 * Tests WebSocket connection states, message handling, and reconnection logic
 */

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  onopen: ((event: Event) => void) | null = null
  onclose: ((event: CloseEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null

  url: string
  sentMessages: (string | ArrayBuffer)[] = []

  constructor(url: string) {
    this.url = url
    // Simulate async connection
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      if (this.onopen) {
        this.onopen(new Event('open'))
      }
    }, 10)
  }

  send(data: string | ArrayBuffer) {
    if (this.readyState === MockWebSocket.OPEN) {
      this.sentMessages.push(data)
    }
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { wasClean: true }))
    }
  }

  // Helper to simulate receiving a message
  simulateMessage(data: object) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }))
    }
  }

  // Helper to simulate an error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'))
    }
  }

  // Helper to simulate unclean close for reconnection testing
  simulateUncleanClose() {
    this.readyState = MockWebSocket.CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { wasClean: false }))
    }
  }
}

// Store reference to last created WebSocket for testing
let lastWebSocket: MockWebSocket | null = null

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    // Mock global WebSocket
    vi.stubGlobal('WebSocket', class extends MockWebSocket {
      constructor(url: string) {
        super(url)
        lastWebSocket = this
      }
    })
    lastWebSocket = null
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  describe('Connection States', () => {
    it('should start with disconnected state', () => {
      const { result } = renderHook(() => useWebSocket())

      expect(result.current.connectionState).toBe('disconnected')
    })

    it('should transition to connecting when connect is called', () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      expect(result.current.connectionState).toBe('connecting')
    })

    it('should transition to connected on successful connection', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })
    })

    it('should transition to error state on WebSocket error', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(lastWebSocket).not.toBeNull()
      })

      act(() => {
        lastWebSocket?.simulateError()
      })

      expect(result.current.connectionState).toBe('error')
    })

    it('should transition to disconnected on close', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      act(() => {
        lastWebSocket?.close()
      })

      expect(result.current.connectionState).toBe('disconnected')
    })
  })

  describe('Message Handling', () => {
    it('should call onMessage callback when message is received', async () => {
      const onMessage = vi.fn()
      const { result } = renderHook(() => useWebSocket({ onMessage }))

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      const testMessage = { type: 'transcription', confirmed_words: [], tentative_words: [] }

      act(() => {
        lastWebSocket?.simulateMessage(testMessage)
      })

      expect(onMessage).toHaveBeenCalledWith(testMessage)
    })

    it('should send JSON messages correctly', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      const testMessage = { type: 'start_recording' }

      act(() => {
        result.current.sendMessage(testMessage as any)
      })

      expect(lastWebSocket?.sentMessages).toContain(JSON.stringify(testMessage))
    })

    it('should send binary data correctly', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      const testData = new ArrayBuffer(8)

      act(() => {
        result.current.sendBinary(testData)
      })

      expect(lastWebSocket?.sentMessages).toContain(testData)
    })

    it('should not send messages when disconnected', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.sendMessage({ type: 'start_recording' })
      })

      expect(consoleWarnSpy).toHaveBeenCalledWith('WebSocket is not connected. Cannot send message.')
      consoleWarnSpy.mockRestore()
    })
  })

  describe('Disconnect Functionality', () => {
    it('should disconnect and reset state', async () => {
      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      act(() => {
        result.current.disconnect()
      })

      expect(result.current.connectionState).toBe('disconnected')
    })

    it('should call onClose callback on disconnect', async () => {
      const onClose = vi.fn()
      const { result } = renderHook(() => useWebSocket({ onClose }))

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(result.current.connectionState).toBe('connected')
      })

      act(() => {
        result.current.disconnect()
      })

      expect(onClose).toHaveBeenCalled()
    })
  })

  describe('Callbacks', () => {
    it('should call onOpen callback when connected', async () => {
      const onOpen = vi.fn()
      const { result } = renderHook(() => useWebSocket({ onOpen }))

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(onOpen).toHaveBeenCalled()
      })
    })

    it('should call onError callback on error', async () => {
      const onError = vi.fn()
      const { result } = renderHook(() => useWebSocket({ onError }))

      act(() => {
        result.current.connect('test-session-123')
      })

      await waitFor(() => {
        expect(lastWebSocket).not.toBeNull()
      })

      act(() => {
        lastWebSocket?.simulateError()
      })

      expect(onError).toHaveBeenCalled()
    })
  })

  describe('WebSocket URL Construction', () => {
    it('should construct correct WebSocket URL', async () => {
      // Mock window.location
      vi.stubGlobal('location', {
        protocol: 'http:',
        host: 'localhost:3000',
      })

      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('session-abc')
      })

      expect(lastWebSocket?.url).toBe('ws://localhost:3000/ws/session/session-abc')
    })

    it('should use wss for https protocol', async () => {
      vi.stubGlobal('location', {
        protocol: 'https:',
        host: 'example.com',
      })

      const { result } = renderHook(() => useWebSocket())

      act(() => {
        result.current.connect('session-xyz')
      })

      expect(lastWebSocket?.url).toBe('wss://example.com/ws/session/session-xyz')
    })
  })
})
