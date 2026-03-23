import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AyahDisplay } from '../../components/AyahDisplay'
import type { AyahText, WordStatus } from '../../types'

/**
 * FE-005: AyahDisplay Component Tests
 * Tests rendering, word highlighting, and reference display
 */

const mockAyah: AyahText = {
  surah: 1,
  ayah: 2,
  juz: 1,
  audio_url: 'https://example.com/audio.mp3',
  text_uthmani: 'الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ',
  text_normalized: 'الحمد لله رب العالمين',
  text_tokens: ['الحمد', 'لله', 'رب', 'العالمين'],
}

describe('AyahDisplay Component', () => {
  describe('Basic Rendering', () => {
    it('should render the ayah text', () => {
      render(<AyahDisplay ayah={mockAyah} />)

      expect(screen.getByText(/الْحَمْدُ/)).toBeInTheDocument()
    })

    it('should render in RTL direction', () => {
      render(<AyahDisplay ayah={mockAyah} />)

      const textContainer = screen.getByText(/الْحَمْدُ/).closest('div')
      expect(textContainer).toHaveAttribute('dir', 'rtl')
    })

    it('should apply quran-text class for proper styling', () => {
      render(<AyahDisplay ayah={mockAyah} />)

      const textContainer = screen.getByText(/الْحَمْدُ/).closest('.quran-text')
      expect(textContainer).toBeInTheDocument()
    })
  })

  describe('Reference Display', () => {
    it('should show reference when showReference is true', () => {
      render(<AyahDisplay ayah={mockAyah} showReference />)

      expect(screen.getByText(/Al-Fatihah/)).toBeInTheDocument()
      expect(screen.getByText(/1:2/)).toBeInTheDocument()
    })

    it('should show juz number', () => {
      render(<AyahDisplay ayah={mockAyah} showReference />)

      expect(screen.getByText('Juz 1')).toBeInTheDocument()
    })

    it('should not show reference when showReference is false', () => {
      render(<AyahDisplay ayah={mockAyah} showReference={false} />)

      expect(screen.queryByText(/Al-Fatihah/)).not.toBeInTheDocument()
    })

    it('should display correct surah name for different surahs', () => {
      const ayahBaqarah: AyahText = {
        ...mockAyah,
        surah: 2,
        ayah: 255,
        text_uthmani: 'اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ',
      }

      render(<AyahDisplay ayah={ayahBaqarah} showReference />)

      expect(screen.getByText(/Al-Baqarah/)).toBeInTheDocument()
    })
  })

  describe('Prompt Label', () => {
    it('should show PROMPT label when isPrompt is true', () => {
      render(<AyahDisplay ayah={mockAyah} isPrompt showReference />)

      expect(screen.getByText('PROMPT')).toBeInTheDocument()
    })

    it('should not show PROMPT label when isPrompt is false', () => {
      render(<AyahDisplay ayah={mockAyah} isPrompt={false} showReference />)

      expect(screen.queryByText('PROMPT')).not.toBeInTheDocument()
    })
  })

  describe('Word Highlighting', () => {
    it('should render words without highlighting by default', () => {
      render(<AyahDisplay ayah={mockAyah} />)

      // Each word should be rendered
      const words = mockAyah.text_uthmani.split(' ')
      words.forEach((word) => {
        expect(screen.getByText(word)).toBeInTheDocument()
      })
    })

    it('should apply correct class for confirmed correct words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(<AyahDisplay ayah={mockAyah} confirmedWords={confirmedWords} />)

      const word = screen.getByText('الْحَمْدُ')
      expect(word.className).toContain('word-confirmed')
    })

    it('should apply correct class for incorrect words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'incorrect', index: 0 },
      ]

      render(<AyahDisplay ayah={mockAyah} confirmedWords={confirmedWords} />)

      const word = screen.getByText('الْحَمْدُ')
      expect(word.className).toContain('word-mistake')
    })

    it('should apply correct class for tentative words', () => {
      const tentativeWords: WordStatus[] = [
        { word: 'لله', status: 'tentative', index: 1 },
      ]

      render(<AyahDisplay ayah={mockAyah} tentativeWords={tentativeWords} />)

      const word = screen.getByText('لِلَّهِ')
      expect(word.className).toContain('word-tentative')
    })

    it('should prioritize confirmed over tentative for same word', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]
      const tentativeWords: WordStatus[] = [
        { word: 'الحمد', status: 'tentative', index: 0 },
      ]

      render(
        <AyahDisplay
          ayah={mockAyah}
          confirmedWords={confirmedWords}
          tentativeWords={tentativeWords}
        />
      )

      const word = screen.getByText('الْحَمْدُ')
      expect(word.className).toContain('word-confirmed')
      expect(word.className).not.toContain('word-tentative')
    })

    it('should highlight multiple words correctly', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
        { word: 'لله', status: 'correct', index: 1 },
        { word: 'رب', status: 'incorrect', index: 2 },
      ]

      render(<AyahDisplay ayah={mockAyah} confirmedWords={confirmedWords} />)

      expect(screen.getByText('الْحَمْدُ').className).toContain('word-confirmed')
      expect(screen.getByText('لِلَّهِ').className).toContain('word-confirmed')
      expect(screen.getByText('رَبِّ').className).toContain('word-mistake')
    })
  })

  describe('Legend Display', () => {
    it('should not show legend when no words are highlighted', () => {
      render(<AyahDisplay ayah={mockAyah} />)

      expect(screen.queryByText('Correct')).not.toBeInTheDocument()
      expect(screen.queryByText('Processing')).not.toBeInTheDocument()
      expect(screen.queryByText('Mistake')).not.toBeInTheDocument()
    })

    it('should show legend when words are confirmed and not a prompt', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(<AyahDisplay ayah={mockAyah} confirmedWords={confirmedWords} isPrompt={false} />)

      expect(screen.getByText('Correct')).toBeInTheDocument()
      expect(screen.getByText('Processing')).toBeInTheDocument()
      expect(screen.getByText('Mistake')).toBeInTheDocument()
    })

    it('should not show legend for prompt ayah even with words', () => {
      const confirmedWords: WordStatus[] = [
        { word: 'الحمد', status: 'correct', index: 0 },
      ]

      render(<AyahDisplay ayah={mockAyah} confirmedWords={confirmedWords} isPrompt />)

      expect(screen.queryByText(/^Correct$/)).not.toBeInTheDocument()
    })
  })

  describe('Different Surahs', () => {
    it('should display Ya-Sin surah name correctly', () => {
      const yasinAyah: AyahText = {
        ...mockAyah,
        surah: 36,
        text_uthmani: 'يس',
      }

      render(<AyahDisplay ayah={yasinAyah} showReference />)

      expect(screen.getByText(/Ya-Sin/)).toBeInTheDocument()
    })

    it('should display An-Nas surah name correctly', () => {
      const nasAyah: AyahText = {
        ...mockAyah,
        surah: 114,
        text_uthmani: 'قُلْ أَعُوذُ بِرَبِّ النَّاسِ',
      }

      render(<AyahDisplay ayah={nasAyah} showReference />)

      expect(screen.getByText(/An-Nas/)).toBeInTheDocument()
    })

    it('should handle unknown surah number gracefully', () => {
      const unknownAyah: AyahText = {
        ...mockAyah,
        surah: 999,
        text_uthmani: 'Test text',
      }

      render(<AyahDisplay ayah={unknownAyah} showReference />)

      // Should fallback to "Surah 999"
      expect(screen.getByText(/Surah 999/)).toBeInTheDocument()
    })
  })

  describe('Card Styling', () => {
    it('should be wrapped in a card container', () => {
      const { container } = render(<AyahDisplay ayah={mockAyah} />)

      expect(container.querySelector('.card')).toBeInTheDocument()
    })
  })
})
