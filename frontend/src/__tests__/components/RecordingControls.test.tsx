import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RecordingControls } from '../../components/RecordingControls'

/**
 * FE-007: RecordingControls Component Tests
 * Tests button states, audio level display, and user interactions
 */

describe('RecordingControls Component', () => {
  const defaultProps = {
    recordingState: 'idle' as const,
    audioLevel: 0,
    onStart: vi.fn(),
    onStop: vi.fn(),
    onPause: vi.fn(),
    onResume: vi.fn(),
  }

  describe('Idle State', () => {
    it('should show start recording button when idle', () => {
      render(<RecordingControls {...defaultProps} recordingState="idle" />)

      expect(screen.getByText('Start Recording')).toBeInTheDocument()
    })

    it('should have correct aria-label for start button', () => {
      render(<RecordingControls {...defaultProps} recordingState="idle" />)

      expect(screen.getByLabelText('Start recording')).toBeInTheDocument()
    })

    it('should not show pause or stop buttons when idle', () => {
      render(<RecordingControls {...defaultProps} recordingState="idle" />)

      expect(screen.queryByText('Pause')).not.toBeInTheDocument()
      expect(screen.queryByText('Stop')).not.toBeInTheDocument()
    })

    it('should show idle instruction text', () => {
      render(<RecordingControls {...defaultProps} recordingState="idle" />)

      expect(
        screen.getByText(/Click "Start Recording" when you are ready to recite/)
      ).toBeInTheDocument()
    })
  })

  describe('Recording State', () => {
    it('should show pause and stop buttons when recording', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(screen.getByText('Pause')).toBeInTheDocument()
      expect(screen.getByText('Stop')).toBeInTheDocument()
    })

    it('should not show start button when recording', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(screen.queryByText('Start Recording')).not.toBeInTheDocument()
    })

    it('should show recording indicator', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(screen.getByText('Recording')).toBeInTheDocument()
    })

    it('should show recording instruction text', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(
        screen.getByText(/Recite the ayahs clearly/)
      ).toBeInTheDocument()
    })

    it('should have correct aria-label for pause button', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(screen.getByLabelText('Pause recording')).toBeInTheDocument()
    })

    it('should have correct aria-label for stop button', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      expect(screen.getByLabelText('Stop recording')).toBeInTheDocument()
    })
  })

  describe('Paused State', () => {
    it('should show resume and stop buttons when paused', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      expect(screen.getByText('Resume')).toBeInTheDocument()
      expect(screen.getByText('Stop')).toBeInTheDocument()
    })

    it('should not show pause button when paused', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      expect(screen.queryByText('Pause')).not.toBeInTheDocument()
    })

    it('should show paused status text', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      expect(screen.getByText('Paused')).toBeInTheDocument()
    })

    it('should show paused instruction text', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      expect(
        screen.getByText(/Recording paused/)
      ).toBeInTheDocument()
    })

    it('should have correct aria-label for resume button', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      expect(screen.getByLabelText('Resume recording')).toBeInTheDocument()
    })
  })

  describe('Button Callbacks', () => {
    it('should call onStart when start button is clicked', async () => {
      const onStart = vi.fn()
      const user = userEvent.setup()

      render(
        <RecordingControls
          {...defaultProps}
          recordingState="idle"
          onStart={onStart}
        />
      )

      await user.click(screen.getByText('Start Recording'))
      expect(onStart).toHaveBeenCalledTimes(1)
    })

    it('should call onPause when pause button is clicked', async () => {
      const onPause = vi.fn()
      const user = userEvent.setup()

      render(
        <RecordingControls
          {...defaultProps}
          recordingState="recording"
          onPause={onPause}
        />
      )

      await user.click(screen.getByText('Pause'))
      expect(onPause).toHaveBeenCalledTimes(1)
    })

    it('should call onResume when resume button is clicked', async () => {
      const onResume = vi.fn()
      const user = userEvent.setup()

      render(
        <RecordingControls
          {...defaultProps}
          recordingState="paused"
          onResume={onResume}
        />
      )

      await user.click(screen.getByText('Resume'))
      expect(onResume).toHaveBeenCalledTimes(1)
    })

    it('should call onStop when stop button is clicked', async () => {
      const onStop = vi.fn()
      const user = userEvent.setup()

      render(
        <RecordingControls
          {...defaultProps}
          recordingState="recording"
          onStop={onStop}
        />
      )

      await user.click(screen.getByText('Stop'))
      expect(onStop).toHaveBeenCalledTimes(1)
    })
  })

  describe('Audio Level Indicator', () => {
    it('should display audio level label', () => {
      render(<RecordingControls {...defaultProps} />)

      expect(screen.getByText('Audio Level')).toBeInTheDocument()
    })

    it('should reflect audio level in the progress bar', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} audioLevel={0.5} />
      )

      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle({ width: '50%' })
    })

    it('should cap audio level at 100%', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} audioLevel={1.5} />
      )

      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle({ width: '100%' })
    })

    it('should show 0% when audio level is 0', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} audioLevel={0} />
      )

      const progressBar = container.querySelector('[style*="width"]')
      expect(progressBar).toHaveStyle({ width: '0%' })
    })
  })

  describe('Error Display', () => {
    it('should display error message when error prop is provided', () => {
      render(
        <RecordingControls
          {...defaultProps}
          error="Microphone access denied"
        />
      )

      expect(screen.getByText('Microphone access denied')).toBeInTheDocument()
    })

    it('should not display error section when no error', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} error={null} />
      )

      const errorSection = container.querySelector('.bg-red-50')
      expect(errorSection).not.toBeInTheDocument()
    })

    it('should apply error styling to error message', () => {
      render(
        <RecordingControls
          {...defaultProps}
          error="Some error"
        />
      )

      const errorElement = screen.getByText('Some error').closest('div')
      expect(errorElement?.className).toContain('bg-red')
      expect(errorElement?.className).toContain('text-red')
    })
  })

  describe('Disabled State', () => {
    it('should disable start button when disabled prop is true', () => {
      render(
        <RecordingControls
          {...defaultProps}
          recordingState="idle"
          disabled
        />
      )

      expect(screen.getByText('Start Recording')).toBeDisabled()
    })

    it('should disable pause button when disabled', () => {
      render(
        <RecordingControls
          {...defaultProps}
          recordingState="recording"
          disabled
        />
      )

      expect(screen.getByText('Pause')).toBeDisabled()
    })

    it('should disable stop button when disabled', () => {
      render(
        <RecordingControls
          {...defaultProps}
          recordingState="recording"
          disabled
        />
      )

      expect(screen.getByText('Stop')).toBeDisabled()
    })

    it('should disable resume button when disabled', () => {
      render(
        <RecordingControls
          {...defaultProps}
          recordingState="paused"
          disabled
        />
      )

      expect(screen.getByText('Resume')).toBeDisabled()
    })

    it('should not call callbacks when buttons are disabled', () => {
      const onStart = vi.fn()

      render(
        <RecordingControls
          {...defaultProps}
          recordingState="idle"
          onStart={onStart}
          disabled
        />
      )

      fireEvent.click(screen.getByText('Start Recording'))
      expect(onStart).not.toHaveBeenCalled()
    })
  })

  describe('Card Styling', () => {
    it('should be wrapped in a card container', () => {
      const { container } = render(<RecordingControls {...defaultProps} />)

      expect(container.querySelector('.card')).toBeInTheDocument()
    })
  })

  describe('Button Styling', () => {
    it('should have success styling for start button', () => {
      render(<RecordingControls {...defaultProps} recordingState="idle" />)

      const startButton = screen.getByText('Start Recording')
      expect(startButton.className).toContain('btn-success')
    })

    it('should have secondary styling for pause button', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      const pauseButton = screen.getByText('Pause')
      expect(pauseButton.className).toContain('btn-secondary')
    })

    it('should have primary styling for resume button', () => {
      render(<RecordingControls {...defaultProps} recordingState="paused" />)

      const resumeButton = screen.getByText('Resume')
      expect(resumeButton.className).toContain('btn-primary')
    })

    it('should have danger styling for stop button', () => {
      render(<RecordingControls {...defaultProps} recordingState="recording" />)

      const stopButton = screen.getByText('Stop')
      expect(stopButton.className).toContain('btn-danger')
    })
  })

  describe('Icons', () => {
    it('should render microphone icon in start button', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} recordingState="idle" />
      )

      const button = screen.getByText('Start Recording').closest('button')
      const svg = button?.querySelector('svg')
      expect(svg).toBeInTheDocument()
    })

    it('should render icons in control buttons', () => {
      const { container } = render(
        <RecordingControls {...defaultProps} recordingState="recording" />
      )

      const pauseButton = screen.getByText('Pause').closest('button')
      const stopButton = screen.getByText('Stop').closest('button')

      expect(pauseButton?.querySelector('svg')).toBeInTheDocument()
      expect(stopButton?.querySelector('svg')).toBeInTheDocument()
    })
  })
})
