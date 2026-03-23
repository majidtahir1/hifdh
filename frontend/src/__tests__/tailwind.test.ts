import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

/**
 * FE-001: Tailwind Setup Tests
 * Verifies that Tailwind CSS is properly configured for the project
 */

describe('Tailwind CSS Configuration', () => {
  const projectRoot = path.resolve(__dirname, '../../..')

  it('should have tailwind.config.js file', () => {
    const configPath = path.join(projectRoot, 'tailwind.config.js')
    expect(fs.existsSync(configPath)).toBe(true)
  })

  it('should have correct content paths configured', () => {
    // Read the config file
    const configPath = path.join(projectRoot, 'tailwind.config.js')
    const configContent = fs.readFileSync(configPath, 'utf-8')

    // Check for expected content patterns
    expect(configContent).toContain('./index.html')
    expect(configContent).toContain('./src/**/*.{js,ts,jsx,tsx}')
  })

  it('should have custom font families configured', () => {
    const configPath = path.join(projectRoot, 'tailwind.config.js')
    const configContent = fs.readFileSync(configPath, 'utf-8')

    // Check for Arabic font configuration
    expect(configContent).toContain('amiri')
    expect(configContent).toContain('arabic')
    expect(configContent).toContain('Amiri')
  })

  it('should have postcss.config.js file', () => {
    const configPath = path.join(projectRoot, 'postcss.config.js')
    expect(fs.existsSync(configPath)).toBe(true)
  })

  it('should have index.css with Tailwind directives', () => {
    const cssPath = path.join(projectRoot, 'src/index.css')
    const cssContent = fs.readFileSync(cssPath, 'utf-8')

    // Check for Tailwind directives
    expect(cssContent).toContain('@tailwind base')
    expect(cssContent).toContain('@tailwind components')
    expect(cssContent).toContain('@tailwind utilities')
  })

  it('should have custom component classes defined', () => {
    const cssPath = path.join(projectRoot, 'src/index.css')
    const cssContent = fs.readFileSync(cssPath, 'utf-8')

    // Check for custom components
    expect(cssContent).toContain('.btn')
    expect(cssContent).toContain('.btn-primary')
    expect(cssContent).toContain('.btn-secondary')
    expect(cssContent).toContain('.card')
  })

  it('should have Arabic text styling classes', () => {
    const cssPath = path.join(projectRoot, 'src/index.css')
    const cssContent = fs.readFileSync(cssPath, 'utf-8')

    // Check for Arabic-specific styles
    expect(cssContent).toContain('.arabic-text')
    expect(cssContent).toContain('.quran-text')
    expect(cssContent).toContain('direction: rtl')
  })

  it('should have word status classes for transcript display', () => {
    const cssPath = path.join(projectRoot, 'src/index.css')
    const cssContent = fs.readFileSync(cssPath, 'utf-8')

    // Check for word status classes
    expect(cssContent).toContain('.word-confirmed')
    expect(cssContent).toContain('.word-tentative')
    expect(cssContent).toContain('.word-mistake')
  })

  it('should have recording indicator animation', () => {
    const cssPath = path.join(projectRoot, 'src/index.css')
    const cssContent = fs.readFileSync(cssPath, 'utf-8')

    // Check for recording indicator
    expect(cssContent).toContain('.recording-indicator')
    expect(cssContent).toContain('@keyframes pulse')
  })
})
