import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TranscriptDisplay } from '../../components/TranscriptDisplay'
import type { WordStatus, Mistake } from '../../types'

/**
 * FE-006: TranscriptDisplay Component Tests
 * Tests transcription display, word styling, and mistake notifications
 */

describe('TranscriptDisplay Component', () => {
  describe('Basic Rendering', () => {
    it('should render component title', () => {
      render(<TranscriptDisplay confirmedWords={[]} tentativeWords={[]} />)

      expect(screen.getByText('Your Recitation')).toBeInTheDocument()
    })

    it('should render placeholder text when no words', () => {
      render(<TranscriptDisplay confirmedWords={[]} tentativeWords={[]} />)

      expect(screen.getByText('Your transcription will appear here.')).toBeInTheDocument()
    })

    it('should be wrapped in a card container', () => {
      const { container } = render(
        <TranscriptDisplay confirmedWords={[]} tentativeWords={[]} />
      )

      expect(container.querySelector('.card')).toBeInTheDocument()
    })
  })

  describe('Recording State', () => {
    it('should show recording indicator when recording', () => {
      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          isRecording
        />
      )

      expect(screen.getByText('Recording')).toBeInTheDocument()
    })

    it('should show listening message when recording with no words', () => {
      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          isRecording
        />
      )

      expect(screen.getByText('Listening... Start reciting.')).toBeInTheDocument()
    })

    it('should not show recording indicator when not recording', () => {
      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          isRecording={false}
        />
      )

      expect(screen.queryByText('Recording')).not.toBeInTheDocument()
    })
  })

  describe('Confirmed Words Display', () => {
    it('should display confirmed words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
        { word: 'لله', status: 'correct', index: 1 },
      ]

      render(
        <TranscriptDisplay confirmedWords={confirmedWords} tentativeWords={[]} />
      )

      expect(screen.getByText('الحمد')).toBeInTheDocument()
      expect(screen.getByText('لله')).toBeInTheDocument()
    })

    it('should apply correct styling for correct words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(
        <TranscriptDisplay confirmedWords={confirmedWords} tentativeWords={[]} />
      )

      const word = screen.getByText('الحمد')
      expect(word.className).toContain('text-green')
      expect(word.className).toContain('bg-green')
    })

    it('should apply incorrect styling for incorrect words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'خطأ', status: 'incorrect', index: 0 },
      ]

      render(
        <TranscriptDisplay confirmedWords={confirmedWords} tentativeWords={[]} />
      )

      const word = screen.getByText('خطأ')
      expect(word.className).toContain('text-red')
      expect(word.className).toContain('bg-red')
    })
  })

  describe('Tentative Words Display', () => {
    it('should display tentative words', () => {
      const tentativeWords: WordStatus[] = [
        { word: 'رب', status: 'tentative', index: 2 },
      ]

      render(
        <TranscriptDisplay confirmedWords={[]} tentativeWords={tentativeWords} />
      )

      expect(screen.getByText('رب')).toBeInTheDocument()
    })

    it('should apply tentative styling', () => {
      const tentativeWords: WordStatus[] = [
        { word: 'رب', status: 'tentative', index: 2 },
      ]

      render(
        <TranscriptDisplay confirmedWords={[]} tentativeWords={tentativeWords} />
      )

      const word = screen.getByText('رب')
      expect(word.className).toContain('text-gray')
      expect(word.className).toContain('italic')
    })
  })

  describe('Combined Words Display', () => {
    it('should display both confirmed and tentative words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
        { word: 'لله', status: 'correct', index: 1 },
      ]
      const tentativeWords: WordStatus[] = [
        { word: 'رب', status: 'tentative', index: 2 },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={confirmedWords}
          tentativeWords={tentativeWords}
        />
      )

      expect(screen.getByText('الحمد')).toBeInTheDocument()
      expect(screen.getByText('لله')).toBeInTheDocument()
      expect(screen.getByText('رب')).toBeInTheDocument()
    })

    it('should render in RTL direction', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(
        <TranscriptDisplay confirmedWords={confirmedWords} tentativeWords={[]} />
      )

      const container = screen.getByText('الحمد').closest('div[dir="rtl"]')
      expect(container).toBeInTheDocument()
    })
  })

  describe('Mistake Notifications', () => {
    it('should display mistake notifications', () => {
      const mistakes: Mistake[] = [
        {
          mistake_type: 'wrong_word',
          ayah: [1, 2],
          word_index: 0,
          expected: 'الحمد',
          received: 'الكلمة',
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 1000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      expect(screen.getByText('Wrong word')).toBeInTheDocument()
      expect(screen.getByText('Recent Issues:')).toBeInTheDocument()
    })

    it('should display expected and received words in mistake', () => {
      const mistakes: Mistake[] = [
        {
          mistake_type: 'wrong_word',
          ayah: [1, 2],
          word_index: 0,
          expected: 'الحمد',
          received: 'الكلمة',
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 1000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      expect(screen.getByText(/Expected: الحمد/)).toBeInTheDocument()
      expect(screen.getByText(/Said: الكلمة/)).toBeInTheDocument()
    })

    it('should show "No penalty" label for non-penalty mistakes', () => {
      const mistakes: Mistake[] = [
        {
          mistake_type: 'repetition',
          ayah: [1, 2],
          word_index: 0,
          expected: 'الحمد',
          received: 'الحمد',
          confidence: 0.9,
          is_penalty: false,
          timestamp_ms: 1000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      expect(screen.getByText('No penalty')).toBeInTheDocument()
    })

    it('should only show last 3 mistakes', () => {
      const mistakes: Mistake[] = [
        {
          mistake_type: 'wrong_word',
          ayah: [1, 1],
          word_index: 0,
          expected: 'كلمة1',
          received: 'خطأ1',
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 1000,
        },
        {
          mistake_type: 'skipped',
          ayah: [1, 2],
          word_index: 1,
          expected: 'كلمة2',
          received: null,
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 2000,
        },
        {
          mistake_type: 'added',
          ayah: [1, 3],
          word_index: 2,
          expected: '',
          received: 'زيادة',
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 3000,
        },
        {
          mistake_type: 'repetition',
          ayah: [1, 4],
          word_index: 3,
          expected: 'كلمة4',
          received: 'كلمة4',
          confidence: 0.8,
          is_penalty: false,
          timestamp_ms: 4000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      // Should show last 3 mistakes (indices 1, 2, 3)
      const mistakeLabels = screen.getAllByText(
        /Skipped|Extra word|Repetition/
      )
      expect(mistakeLabels.length).toBe(3)
    })

    it('should display different mistake types correctly', () => {
      const testCases = [
        { type: 'wrong_word', expected: 'Wrong word' },
        { type: 'skipped', expected: 'Skipped' },
        { type: 'added', expected: 'Extra word' },
        { type: 'repetition', expected: 'Repetition' },
        { type: 'out_of_order', expected: 'Out of order' },
        { type: 'jumped_ahead', expected: 'Jumped ahead' },
        { type: 'self_corrected', expected: 'Self-corrected' },
        { type: 'low_confidence', expected: 'Unclear' },
      ]

      for (const testCase of testCases) {
        const mistakes: Mistake[] = [
          {
            mistake_type: testCase.type as any,
            ayah: [1, 1],
            word_index: 0,
            expected: 'test',
            received: 'test',
            confidence: 0.8,
            is_penalty: true,
            timestamp_ms: 1000,
          },
        ]

        const { unmount } = render(
          <TranscriptDisplay
            confirmedWords={[]}
            tentativeWords={[]}
            mistakes={mistakes}
          />
        )

        expect(screen.getByText(testCase.expected)).toBeInTheDocument()
        unmount()
      }
    })

    it('should apply special styling for self-corrected mistakes', () => {
      const mistakes: Mistake[] = [
        {
          mistake_type: 'self_corrected',
          ayah: [1, 2],
          word_index: 0,
          expected: '',
          received: null,
          confidence: 1,
          is_penalty: false,
          timestamp_ms: 1000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={[]}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      const notification = screen.getByText('Self-corrected').closest('div')
      expect(notification?.className).toContain('blue')
    })
  })

  describe('Legend Display', () => {
    it('should display legend with correct, error, and processing labels', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(
        <TranscriptDisplay confirmedWords={confirmedWords} tentativeWords={[]} />
      )

      expect(screen.getByText('Correct')).toBeInTheDocument()
      expect(screen.getByText('Error')).toBeInTheDocument()
      expect(screen.getByText('Processing')).toBeInTheDocument()
    })
  })

  describe('Mistake Word Highlighting', () => {
    it('should apply mistake styling to words with associated mistakes', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'خطأ', status: 'incorrect', index: 0 },
      ]
      const mistakes: Mistake[] = [
        {
          mistake_type: 'wrong_word',
          ayah: [1, 2],
          word_index: 0,
          expected: 'الحمد',
          received: 'خطأ',
          confidence: 0.8,
          is_penalty: true,
          timestamp_ms: 1000,
        },
      ]

      render(
        <TranscriptDisplay
          confirmedWords={confirmedWords}
          tentativeWords={[]}
          mistakes={mistakes}
        />
      )

      const word = screen.getByText('خطأ')
      expect(word.className).toContain('text-red')
      expect(word.className).toContain('underline')
    })
  })

  describe('Cursor Indicator', () => {
    it('should show cursor when recording with content', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      const { container } = render(
        <TranscriptDisplay
          confirmedWords={confirmedWords}
          tentativeWords={[]}
          isRecording
        />
      )

      // Check for pulsing cursor element
      const cursor = container.querySelector('.animate-pulse')
      expect(cursor).toBeInTheDocument()
    })

    it('should not show cursor when not recording', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      const { container } = render(
        <TranscriptDisplay
          confirmedWords={confirmedWords}
          tentativeWords={[]}
          isRecording={false}
        />
      )

      const cursor = container.querySelector('.animate-pulse')
      expect(cursor).not.toBeInTheDocument()
    })
  })
})
