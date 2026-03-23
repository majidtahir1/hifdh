import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { SessionSummary } from '../../components/SessionSummary'
import type { SessionSummary as SessionSummaryType, Mistake } from '../../types'

/**
 * FE-008: SessionSummary Component Tests
 * Tests stats display, grade calculation, and user interactions
 */

const createMockSummary = (overrides: Partial<SessionSummaryType> = {}): SessionSummaryType => ({
  ayahs_tested: 5,
  ayahs_correct: 4,
  total_words: 50,
  words_correct: 45,
  mistakes: [],
  ...overrides,
})

const createMockMistake = (overrides: Partial<Mistake> = {}): Mistake => ({
  mistake_type: 'wrong_word',
  ayah: [1, 2],
  word_index: 0,
  expected: 'الحمد',
  received: 'الكلمة',
  confidence: 0.8,
  is_penalty: true,
  timestamp_ms: 1000,
  ...overrides,
})

describe('SessionSummary Component', () => {
  describe('Basic Rendering', () => {
    it('should render session complete header', () => {
      render(<SessionSummary summary={createMockSummary()} />)

      expect(screen.getByText('Session Complete')).toBeInTheDocument()
    })

    it('should be wrapped in a card container', () => {
      const { container } = render(<SessionSummary summary={createMockSummary()} />)

      expect(container.querySelector('.card')).toBeInTheDocument()
    })
  })

  describe('Accuracy Display', () => {
    it('should display word accuracy percentage', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 85 })}
        />
      )

      expect(screen.getByText('85.0%')).toBeInTheDocument()
      expect(screen.getByText('Word Accuracy')).toBeInTheDocument()
    })

    it('should display word counts', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 85 })}
        />
      )

      expect(screen.getByText('85 / 100 words')).toBeInTheDocument()
    })

    it('should display ayah accuracy percentage', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ ayahs_tested: 10, ayahs_correct: 8 })}
        />
      )

      expect(screen.getByText('80.0%')).toBeInTheDocument()
      expect(screen.getByText('Ayah Accuracy')).toBeInTheDocument()
    })

    it('should display ayah counts', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ ayahs_tested: 10, ayahs_correct: 8 })}
        />
      )

      expect(screen.getByText('8 / 10 ayahs')).toBeInTheDocument()
    })

    it('should handle zero total words', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 0, words_correct: 0 })}
        />
      )

      expect(screen.getByText('0.0%')).toBeInTheDocument()
    })

    it('should handle zero ayahs tested', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ ayahs_tested: 0, ayahs_correct: 0 })}
        />
      )

      // Should show 0% for ayah accuracy
      const accuracyTexts = screen.getAllByText('0.0%')
      expect(accuracyTexts.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('Grade Display', () => {
    it('should show Excellent grade for 95%+ accuracy', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 96 })}
        />
      )

      expect(screen.getByText('Excellent')).toBeInTheDocument()
      expect(screen.getByText(/Outstanding recitation/)).toBeInTheDocument()
    })

    it('should show Very Good grade for 85-94% accuracy', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 90 })}
        />
      )

      expect(screen.getByText('Very Good')).toBeInTheDocument()
      expect(screen.getByText(/Great job/)).toBeInTheDocument()
    })

    it('should show Good grade for 70-84% accuracy', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 75 })}
        />
      )

      expect(screen.getByText('Good')).toBeInTheDocument()
      expect(screen.getByText(/Good effort/)).toBeInTheDocument()
    })

    it('should show Needs Practice grade for <70% accuracy', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 60 })}
        />
      )

      expect(screen.getByText('Needs Practice')).toBeInTheDocument()
      expect(screen.getByText(/Keep practicing/)).toBeInTheDocument()
    })
  })

  describe('Progress Bar', () => {
    it('should display overall progress label', () => {
      render(<SessionSummary summary={createMockSummary()} />)

      expect(screen.getByText('Overall Progress')).toBeInTheDocument()
    })

    it('should show correct percentage in progress bar', () => {
      render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 75 })}
        />
      )

      expect(screen.getByText('75%')).toBeInTheDocument()
    })

    it('should apply green color for high accuracy', () => {
      const { container } = render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 90 })}
        />
      )

      const progressBar = container.querySelector('[style*="width: 90%"]')
      expect(progressBar?.className).toContain('bg-green')
    })

    it('should apply yellow color for medium accuracy', () => {
      const { container } = render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 75 })}
        />
      )

      const progressBar = container.querySelector('[style*="width: 75%"]')
      expect(progressBar?.className).toContain('bg-yellow')
    })

    it('should apply orange color for low accuracy', () => {
      const { container } = render(
        <SessionSummary
          summary={createMockSummary({ total_words: 100, words_correct: 50 })}
        />
      )

      const progressBar = container.querySelector('[style*="width: 50%"]')
      expect(progressBar?.className).toContain('bg-orange')
    })
  })

  describe('Mistake Summary', () => {
    it('should not show mistake section when no mistakes', () => {
      render(<SessionSummary summary={createMockSummary({ mistakes: [] })} />)

      expect(screen.queryByText('Mistake Summary')).not.toBeInTheDocument()
    })

    it('should show mistake summary when there are mistakes', () => {
      const mistakes = [createMockMistake()]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText('Mistake Summary')).toBeInTheDocument()
    })

    it('should group and count mistakes by type', () => {
      const mistakes = [
        createMockMistake({ mistake_type: 'wrong_word' }),
        createMockMistake({ mistake_type: 'wrong_word' }),
        createMockMistake({ mistake_type: 'skipped' }),
      ]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText('Wrong Words')).toBeInTheDocument()
      expect(screen.getByText('Skipped Words')).toBeInTheDocument()
    })

    it('should display correct mistake type labels', () => {
      const mistakeTypes = [
        { type: 'wrong_word', label: 'Wrong Words' },
        { type: 'skipped', label: 'Skipped Words' },
        { type: 'added', label: 'Extra Words' },
        { type: 'repetition', label: 'Repetitions' },
        { type: 'out_of_order', label: 'Out of Order' },
        { type: 'jumped_ahead', label: 'Jumped Ahead' },
        { type: 'self_corrected', label: 'Self-Corrected' },
        { type: 'low_confidence', label: 'Unclear' },
      ]

      for (const { type, label } of mistakeTypes) {
        const mistakes = [createMockMistake({ mistake_type: type as any })]
        const { unmount } = render(
          <SessionSummary summary={createMockSummary({ mistakes })} />
        )

        expect(screen.getByText(label)).toBeInTheDocument()
        unmount()
      }
    })
  })

  describe('Mistake Details', () => {
    it('should show details section when there are mistakes', () => {
      const mistakes = [createMockMistake()]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText('Details')).toBeInTheDocument()
    })

    it('should display ayah reference in mistake details', () => {
      const mistakes = [createMockMistake({ ayah: [2, 255] })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText(/2:255/)).toBeInTheDocument()
    })

    it('should display word index in mistake details', () => {
      const mistakes = [createMockMistake({ word_index: 5 })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText(/Word 6/)).toBeInTheDocument() // 0-indexed to 1-indexed
    })

    it('should display expected word', () => {
      const mistakes = [createMockMistake({ expected: 'الحمد' })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText(/Expected:/)).toBeInTheDocument()
      expect(screen.getByText('الحمد')).toBeInTheDocument()
    })

    it('should display received word when present', () => {
      const mistakes = [createMockMistake({ received: 'الكلمة' })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText(/Said:/)).toBeInTheDocument()
      expect(screen.getByText('الكلمة')).toBeInTheDocument()
    })

    it('should show no penalty label when is_penalty is false', () => {
      const mistakes = [createMockMistake({ is_penalty: false })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.getByText('No penalty')).toBeInTheDocument()
    })

    it('should not show no penalty label when is_penalty is true', () => {
      const mistakes = [createMockMistake({ is_penalty: true })]
      render(<SessionSummary summary={createMockSummary({ mistakes })} />)

      expect(screen.queryByText('No penalty')).not.toBeInTheDocument()
    })
  })

  describe('Action Buttons', () => {
    it('should show retry button when onRetry is provided', () => {
      render(
        <SessionSummary
          summary={createMockSummary()}
          onRetry={() => {}}
        />
      )

      expect(screen.getByText('Retry Same Test')).toBeInTheDocument()
    })

    it('should not show retry button when onRetry is not provided', () => {
      render(<SessionSummary summary={createMockSummary()} />)

      expect(screen.queryByText('Retry Same Test')).not.toBeInTheDocument()
    })

    it('should show new session button when onNewSession is provided', () => {
      render(
        <SessionSummary
          summary={createMockSummary()}
          onNewSession={() => {}}
        />
      )

      expect(screen.getByText('New Session')).toBeInTheDocument()
    })

    it('should show close button when onClose is provided', () => {
      render(
        <SessionSummary
          summary={createMockSummary()}
          onClose={() => {}}
        />
      )

      expect(screen.getByText('Close')).toBeInTheDocument()
    })

    it('should call onRetry when retry button is clicked', async () => {
      const onRetry = vi.fn()
      const user = userEvent.setup()

      render(
        <SessionSummary
          summary={createMockSummary()}
          onRetry={onRetry}
        />
      )

      await user.click(screen.getByText('Retry Same Test'))
      expect(onRetry).toHaveBeenCalledTimes(1)
    })

    it('should call onNewSession when new session button is clicked', async () => {
      const onNewSession = vi.fn()
      const user = userEvent.setup()

      render(
        <SessionSummary
          summary={createMockSummary()}
          onNewSession={onNewSession}
        />
      )

      await user.click(screen.getByText('New Session'))
      expect(onNewSession).toHaveBeenCalledTimes(1)
    })

    it('should call onClose when close button is clicked', async () => {
      const onClose = vi.fn()
      const user = userEvent.setup()

      render(
        <SessionSummary
          summary={createMockSummary()}
          onClose={onClose}
        />
      )

      await user.click(screen.getByText('Close'))
      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })

  describe('Button Styling', () => {
    it('should have primary styling for retry button', () => {
      render(
        <SessionSummary
          summary={createMockSummary()}
          onRetry={() => {}}
        />
      )

      const retryButton = screen.getByText('Retry Same Test')
      expect(retryButton.className).toContain('btn-primary')
    })

    it('should have secondary styling for new session button', () => {
      render(
        <SessionSummary
          summary={createMockSummary()}
          onNewSession={() => {}}
        />
      )

      const newSessionButton = screen.getByText('New Session')
      expect(newSessionButton.className).toContain('btn-secondary')
    })
  })

  describe('Scrollable Details', () => {
    it('should have max height on details section for scrolling', () => {
      const mistakes = Array.from({ length: 20 }, (_, i) =>
        createMockMistake({ word_index: i })
      )

      const { container } = render(
        <SessionSummary summary={createMockSummary({ mistakes })} />
      )

      const detailsSection = container.querySelector('.max-h-60')
      expect(detailsSection).toBeInTheDocument()
    })

    it('should have overflow-y-auto for scrolling', () => {
      const mistakes = Array.from({ length: 20 }, (_, i) =>
        createMockMistake({ word_index: i })
      )

      const { container } = render(
        <SessionSummary summary={createMockSummary({ mistakes })} />
      )

      const detailsSection = container.querySelector('.overflow-y-auto')
      expect(detailsSection).toBeInTheDocument()
    })
  })
})
