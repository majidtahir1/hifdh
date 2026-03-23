import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

/**
 * FE-009: Main App Integration Tests
 * Tests the overall app flow and component integration
 */

// Mock the API module
vi.mock('../services/api', () => ({
  startSession: vi.fn(),
  getAllJuzInfo: vi.fn(),
}))

// Mock the hooks
vi.mock('../hooks/useWebSocket', () => ({
  useWebSocket: vi.fn(() => ({
    connectionState: 'disconnected',
    connect: vi.fn(),
    disconnect: vi.fn(),
    sendMessage: vi.fn(),
    sendBinary: vi.fn(),
  })),
}))

vi.mock('../hooks/useAudioRecorder', () => ({
  useAudioRecorder: vi.fn(() => ({
    recordingState: 'idle',
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    pauseRecording: vi.fn(),
    resumeRecording: vi.fn(),
    error: null,
    audioLevel: 0,
  })),
}))

import { startSession, getAllJuzInfo } from '../services/api'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAudioRecorder } from '../hooks/useAudioRecorder'

const mockSessionResponse = {
  session_id: 'test-session-123',
  prompt_ayah: {
    surah: 1,
    ayah: 1,
    juz: 1,
    audio_url: 'https://example.com/audio.mp3',
    text_uthmani: 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ',
    text_normalized: 'بسم الله الرحمن الرحيم',
    text_tokens: ['بسم', 'الله', 'الرحمن', 'الرحيم'],
  },
  expected_ayahs: [
    {
      surah: 1,
      ayah: 2,
      juz: 1,
      audio_url: '',
      text_uthmani: 'الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ',
      text_normalized: 'الحمد لله رب العالمين',
      text_tokens: ['الحمد', 'لله', 'رب', 'العالمين'],
    },
  ],
}

const mockJuzInfo = [
  { juz_number: 1, start_surah: 1, start_ayah: 1, end_surah: 2, end_ayah: 141, total_ayahs: 148 },
  { juz_number: 2, start_surah: 2, start_ayah: 142, end_surah: 2, end_ayah: 252, total_ayahs: 111 },
]

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getAllJuzInfo).mockResolvedValue(mockJuzInfo)
    vi.mocked(startSession).mockResolvedValue(mockSessionResponse)

    // Reset hook mocks
    vi.mocked(useWebSocket).mockReturnValue({
      connectionState: 'disconnected',
      connect: vi.fn(),
      disconnect: vi.fn(),
      sendMessage: vi.fn(),
      sendBinary: vi.fn(),
    })

    vi.mocked(useAudioRecorder).mockReturnValue({
      recordingState: 'idle',
      startRecording: vi.fn().mockResolvedValue(undefined),
      stopRecording: vi.fn(),
      pauseRecording: vi.fn(),
      resumeRecording: vi.fn(),
      error: null,
      audioLevel: 0,
    })
  })

  describe('Header', () => {
    it('should render app title', () => {
      render(<App />)

      expect(screen.getByText('Hifdh Review')).toBeInTheDocument()
    })

    it('should not show New Session button on select view', () => {
      render(<App />)

      expect(screen.queryByText('New Session')).not.toBeInTheDocument()
    })
  })

  describe('Footer', () => {
    it('should render footer text', () => {
      render(<App />)

      expect(
        screen.getByText(/Hifdh Review App - Practice your Quran memorization/)
      ).toBeInTheDocument()
    })
  })

  describe('Select View (Initial)', () => {
    it('should show JuzSelector on initial render', () => {
      render(<App />)

      expect(screen.getByText('Select Your Review Range')).toBeInTheDocument()
    })

    it('should show juz selection dropdowns', () => {
      render(<App />)

      expect(screen.getByLabelText('From Juz')).toBeInTheDocument()
      expect(screen.getByLabelText('To Juz')).toBeInTheDocument()
    })

    it('should show start button', () => {
      render(<App />)

      expect(screen.getByText('Start Review Session')).toBeInTheDocument()
    })
  })

  describe('Starting a Session', () => {
    it('should call startSession API when start is clicked', async () => {
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const startButton = screen.getByText('Start Review Session')
      await user.click(startButton)

      await waitFor(() => {
        expect(startSession).toHaveBeenCalledWith({
          juz_start: 1,
          juz_end: 1,
          num_ayahs: 3,
        })
      })
    })

    it('should show error message when session start fails', async () => {
      vi.mocked(startSession).mockRejectedValueOnce(new Error('API Error'))
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const startButton = screen.getByText('Start Review Session')
      await user.click(startButton)

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to start session/)
        ).toBeInTheDocument()
      })
    })

    it('should be able to dismiss error message', async () => {
      vi.mocked(startSession).mockRejectedValueOnce(new Error('API Error'))
      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText(/Failed to start session/)).toBeInTheDocument()
      })

      await user.click(screen.getByText('Dismiss'))

      expect(screen.queryByText(/Failed to start session/)).not.toBeInTheDocument()
    })
  })

  describe('Session View', () => {
    it('should transition to session view after starting', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Listen to this ayah:')).toBeInTheDocument()
      })
    })

    it('should show New Session button in session view', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('New Session')).toBeInTheDocument()
      })
    })

    it('should display prompt ayah in session view', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('PROMPT')).toBeInTheDocument()
      })
    })

    it('should display expected ayah to recite', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText(/Now recite/)).toBeInTheDocument()
      })
    })

    it('should show connection status', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Connected')).toBeInTheDocument()
      })
    })

    it('should show recording controls', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Start Recording')).toBeInTheDocument()
      })
    })

    it('should show transcript display', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Your Recitation')).toBeInTheDocument()
      })
    })
  })

  describe('Connection Status Display', () => {
    it('should show connecting status', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connecting',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Connecting...')).toBeInTheDocument()
      })
    })

    it('should show error status', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'error',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Error')).toBeInTheDocument()
      })
    })
  })

  describe('New Session Navigation', () => {
    it('should return to select view when New Session is clicked', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Start session
      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('New Session')).toBeInTheDocument()
      })

      // Click New Session
      await user.click(screen.getByText('New Session'))

      // Should be back at select view
      expect(screen.getByText('Select Your Review Range')).toBeInTheDocument()
    })
  })

  describe('WebSocket Integration', () => {
    it('should connect WebSocket when session starts', async () => {
      const connectMock = vi.fn()
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'disconnected',
        connect: connectMock,
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(connectMock).toHaveBeenCalledWith('test-session-123')
      })
    })

    it('should disconnect WebSocket when starting new session', async () => {
      const disconnectMock = vi.fn()
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: disconnectMock,
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('New Session')).toBeInTheDocument()
      })

      await user.click(screen.getByText('New Session'))

      expect(disconnectMock).toHaveBeenCalled()
    })
  })

  describe('Recording Controls Integration', () => {
    it('should disable recording when not connected', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'disconnected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        const recordButton = screen.getByText('Start Recording')
        expect(recordButton).toBeDisabled()
      })
    })

    it('should enable recording when connected', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        const recordButton = screen.getByText('Start Recording')
        expect(recordButton).not.toBeDisabled()
      })
    })
  })

  describe('Replay Audio', () => {
    it('should show replay audio button', async () => {
      vi.mocked(useWebSocket).mockReturnValue({
        connectionState: 'connected',
        connect: vi.fn(),
        disconnect: vi.fn(),
        sendMessage: vi.fn(),
        sendBinary: vi.fn(),
      })

      const user = userEvent.setup()
      render(<App />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      await user.click(screen.getByText('Start Review Session'))

      await waitFor(() => {
        expect(screen.getByText('Replay Audio')).toBeInTheDocument()
      })
    })
  })
})
