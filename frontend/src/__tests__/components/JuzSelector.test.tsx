import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { JuzSelector } from '../../components/JuzSelector'

/**
 * FE-004: JuzSelector Component Tests
 * Tests rendering, selection functionality, and API integration
 */

// Mock the API module
vi.mock('../../services/api', () => ({
  getAllJuzInfo: vi.fn(),
}))

import { getAllJuzInfo } from '../../services/api'

const mockJuzInfo = [
  { juz_number: 1, start_surah: 1, start_ayah: 1, end_surah: 2, end_ayah: 141, total_ayahs: 148 },
  { juz_number: 2, start_surah: 2, start_ayah: 142, end_surah: 2, end_ayah: 252, total_ayahs: 111 },
  { juz_number: 3, start_surah: 2, start_ayah: 253, end_surah: 3, end_ayah: 92, total_ayahs: 126 },
]

describe('JuzSelector Component', () => {
  const mockOnSelect = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getAllJuzInfo).mockResolvedValue(mockJuzInfo)
  })

  describe('Rendering', () => {
    it('should render the component title', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByText('Select Your Review Range')).toBeInTheDocument()
    })

    it('should render juz start and end selectors', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByLabelText('From Juz')).toBeInTheDocument()
      expect(screen.getByLabelText('To Juz')).toBeInTheDocument()
    })

    it('should render number of ayahs selector', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByLabelText('Number of Ayahs to Recite')).toBeInTheDocument()
    })

    it('should render start button', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByText('Start Review Session')).toBeInTheDocument()
    })

    it('should render selection summary', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByText(/You will be tested/)).toBeInTheDocument()
    })
  })

  describe('Default Values', () => {
    it('should default to Juz 1 for both start and end', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      const startSelect = screen.getByLabelText('From Juz') as HTMLSelectElement
      const endSelect = screen.getByLabelText('To Juz') as HTMLSelectElement

      expect(startSelect.value).toBe('1')
      expect(endSelect.value).toBe('1')
    })

    it('should default to 3 ayahs', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      const ayahsSelect = screen.getByLabelText('Number of Ayahs to Recite') as HTMLSelectElement

      expect(ayahsSelect.value).toBe('3')
    })
  })

  describe('Selection Functionality', () => {
    it('should update start juz when selected', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const startSelect = screen.getByLabelText('From Juz')
      await user.selectOptions(startSelect, '2')

      expect((startSelect as HTMLSelectElement).value).toBe('2')
    })

    it('should update end juz when selected', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const endSelect = screen.getByLabelText('To Juz')
      await user.selectOptions(endSelect, '3')

      expect((endSelect as HTMLSelectElement).value).toBe('3')
    })

    it('should update number of ayahs when selected', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      const ayahsSelect = screen.getByLabelText('Number of Ayahs to Recite')
      await user.selectOptions(ayahsSelect, '5')

      expect((ayahsSelect as HTMLSelectElement).value).toBe('5')
    })

    it('should ensure end juz is not less than start juz', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Set start to 2
      const startSelect = screen.getByLabelText('From Juz')
      await user.selectOptions(startSelect, '2')

      // End should automatically update to be >= start
      const endSelect = screen.getByLabelText('To Juz') as HTMLSelectElement

      // The end select should only show options >= start
      const options = Array.from(endSelect.options)
      const values = options.map((opt) => parseInt(opt.value))

      // All values should be >= 2
      expect(values.every((v) => v >= 2)).toBe(true)
    })
  })

  describe('Start Session', () => {
    it('should call onSelect with correct values when start button is clicked', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const startButton = screen.getByText('Start Review Session')
      await user.click(startButton)

      expect(mockOnSelect).toHaveBeenCalledWith(1, 1, 3)
    })

    it('should pass updated values to onSelect', async () => {
      const user = userEvent.setup()
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      // Change selections
      await user.selectOptions(screen.getByLabelText('From Juz'), '2')
      await user.selectOptions(screen.getByLabelText('To Juz'), '3')
      await user.selectOptions(screen.getByLabelText('Number of Ayahs to Recite'), '5')

      const startButton = screen.getByText('Start Review Session')
      await user.click(startButton)

      expect(mockOnSelect).toHaveBeenCalledWith(2, 3, 5)
    })
  })

  describe('Disabled State', () => {
    it('should disable all controls when disabled prop is true', () => {
      render(<JuzSelector onSelect={mockOnSelect} disabled />)

      expect(screen.getByLabelText('From Juz')).toBeDisabled()
      expect(screen.getByLabelText('To Juz')).toBeDisabled()
      expect(screen.getByLabelText('Number of Ayahs to Recite')).toBeDisabled()
      expect(screen.getByText('Start Review Session')).toBeDisabled()
    })

    it('should not call onSelect when button is disabled', () => {
      render(<JuzSelector onSelect={mockOnSelect} disabled />)

      const startButton = screen.getByText('Start Review Session')
      fireEvent.click(startButton)

      expect(mockOnSelect).not.toHaveBeenCalled()
    })
  })

  describe('API Integration', () => {
    it('should fetch juz info on mount', async () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(getAllJuzInfo).toHaveBeenCalled()
      })
    })

    it('should show error message when API fails', async () => {
      vi.mocked(getAllJuzInfo).mockRejectedValue(new Error('API Error'))

      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.getByText('Using default juz data')).toBeInTheDocument()
      })
    })

    it('should still work with default data when API fails', async () => {
      vi.mocked(getAllJuzInfo).mockRejectedValue(new Error('API Error'))
      const user = userEvent.setup()

      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      const startButton = screen.getByText('Start Review Session')
      await user.click(startButton)

      expect(mockOnSelect).toHaveBeenCalled()
    })
  })

  describe('Selection Summary Display', () => {
    it('should display single juz in summary', async () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      await waitFor(() => {
        expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
      })

      expect(screen.getByText(/Juz 1/)).toBeInTheDocument()
    })

    it('should display number of ayahs in summary', () => {
      render(<JuzSelector onSelect={mockOnSelect} />)

      expect(screen.getByText(/3 ayahs/)).toBeInTheDocument()
    })
  })
})
