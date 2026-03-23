import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { JuzInfo } from '../types';
import { getAllJuzInfo } from '../services/api';
import { Button } from './ui/button';
import { Slider } from './ui/slider';
import { AnimatedCard, AnimatedCardHeader, AnimatedCardTitle, AnimatedCardDescription, AnimatedCardContent } from './ui/animated-card';
import { ProgressRing } from './ui/progress-ring';
import { BookOpen, ArrowRight, Sparkles, Target, Clock, BarChart3 } from 'lucide-react';

interface JuzSelectorProps {
  onSelect: (juzStart: number, juzEnd: number, numAyahs?: number) => void;
  disabled?: boolean;
}

// Default juz info for offline/fallback use
const DEFAULT_JUZ_INFO: JuzInfo[] = Array.from({ length: 30 }, (_, i) => ({
  juz_number: i + 1,
  start_surah: 1,
  start_ayah: 1,
  end_surah: 114,
  end_ayah: 6,
  total_ayahs: 0,
}));

// Quick select presets
const PRESETS = [
  { name: 'Last Juz', start: 30, end: 30, icon: BookOpen, desc: 'Amma Yatasa\'aloon' },
  { name: 'Juz 29-30', start: 29, end: 30, icon: Target, desc: 'Tabarak + Amma' },
  { name: 'Juz 1-3', start: 1, end: 3, icon: Clock, desc: 'Beginning of Quran' },
];

export function JuzSelector({ onSelect, disabled = false }: JuzSelectorProps) {
  const [, setJuzList] = useState<JuzInfo[]>(DEFAULT_JUZ_INFO);
  const [juzStart, setJuzStart] = useState<number>(30);
  const [juzEnd, setJuzEnd] = useState<number>(30);
  const [numAyahs, setNumAyahs] = useState<number>(3);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch juz info on mount
  useEffect(() => {
    async function fetchJuzInfo() {
      setLoading(true);
      try {
        const info = await getAllJuzInfo();
        setJuzList(info);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch juz info:', err);
        setError('Using default juz data');
      } finally {
        setLoading(false);
      }
    }

    fetchJuzInfo();
  }, []);

  // Ensure juzEnd is >= juzStart
  useEffect(() => {
    if (juzEnd < juzStart) {
      setJuzEnd(juzStart);
    }
  }, [juzStart, juzEnd]);

  const handleStartSession = () => {
    onSelect(juzStart, juzEnd, numAyahs);
  };

  const handlePresetSelect = (start: number, end: number) => {
    setJuzStart(start);
    setJuzEnd(end);
  };

  const totalJuzSelected = juzEnd - juzStart + 1;
  const progressPercentage = (totalJuzSelected / 30) * 100;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-8">
      {/* Hero Section */}
      <motion.div 
        className="text-center space-y-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.4 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-emerald-100 to-teal-100 text-emerald-800 text-sm font-medium"
        >
          <Sparkles className="w-4 h-4" />
          Strengthen Your Memorization
        </motion.div>
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
          Hifdh Review
        </h1>
        <p className="text-muted-foreground text-lg max-w-md mx-auto">
          Test your Quran memorization with random ayah prompts and real-time feedback
        </p>
      </motion.div>

      {/* Quick Presets */}
      <motion.div 
        className="grid grid-cols-3 gap-3"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.4 }}
      >
        {PRESETS.map((preset, index) => (
          <motion.button
            key={preset.name}
            onClick={() => handlePresetSelect(preset.start, preset.end)}
            className={`p-4 rounded-xl border-2 transition-all duration-200 text-left ${
              juzStart === preset.start && juzEnd === preset.end
                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30'
                : 'border-border bg-card hover:border-emerald-200 hover:bg-emerald-50/50'
            }`}
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 + index * 0.1 }}
          >
            <preset.icon className={`w-5 h-5 mb-2 ${
              juzStart === preset.start && juzEnd === preset.end
                ? 'text-emerald-600'
                : 'text-muted-foreground'
            }`} />
            <div className="font-medium text-sm">{preset.name}</div>
            <div className="text-xs text-muted-foreground mt-0.5">{preset.desc}</div>
          </motion.button>
        ))}
      </motion.div>

      {/* Main Selection Card */}
      <AnimatedCard variant="elevated" delay={0.5}>
        <AnimatedCardHeader className="pb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <AnimatedCardTitle className="text-xl">Select Review Range</AnimatedCardTitle>
              <AnimatedCardDescription>Choose which Juz to practice</AnimatedCardDescription>
            </div>
          </div>
        </AnimatedCardHeader>
        
        <AnimatedCardContent className="space-y-6">
          {error && (
            <motion.div 
              className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-sm flex items-center gap-2"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
            >
              <span className="font-medium">Note:</span> {error}
            </motion.div>
          )}

          {/* Range Display */}
          <div className="flex items-center justify-center gap-6 py-4">
            <motion.div 
              className="text-center"
              key={juzStart}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <div className="text-4xl font-bold text-emerald-600">{juzStart}</div>
              <div className="text-sm text-muted-foreground">From Juz</div>
            </motion.div>
            
            <div className="flex flex-col items-center gap-1">
              <div className="w-16 h-0.5 bg-gradient-to-r from-emerald-300 to-teal-300 rounded-full" />
              <span className="text-xs text-muted-foreground">{totalJuzSelected} Juz</span>
            </div>
            
            <motion.div 
              className="text-center"
              key={juzEnd}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <div className="text-4xl font-bold text-teal-600">{juzEnd}</div>
              <div className="text-sm text-muted-foreground">To Juz</div>
            </motion.div>
          </div>

          {/* Range Slider */}
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center justify-between">
                <span>Starting Juz</span>
                <span className="text-emerald-600 font-bold">{juzStart}</span>
              </label>
              <Slider
                value={[juzStart]}
                onValueChange={(value) => setJuzStart(value[0])}
                min={1}
                max={30}
                step={1}
                disabled={disabled || loading}
              />
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-medium flex items-center justify-between">
                <span>Ending Juz</span>
                <span className="text-teal-600 font-bold">{juzEnd}</span>
              </label>
              <Slider
                value={[juzEnd]}
                onValueChange={(value) => setJuzEnd(Math.max(value[0], juzStart))}
                min={juzStart}
                max={30}
                step={1}
                disabled={disabled || loading}
              />
            </div>
          </div>

          {/* Visual Progress */}
          <div className="flex items-center gap-4 p-4 bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 rounded-xl">
            <ProgressRing 
              progress={progressPercentage} 
              size={70} 
              strokeWidth={6}
              showPercentage
              variant="success"
            />
            <div className="flex-1">
              <div className="font-medium">Selected Range</div>
              <div className="text-sm text-muted-foreground">
                You will be tested on {totalJuzSelected} Juz from the Quran
              </div>
            </div>
          </div>
        </AnimatedCardContent>
      </AnimatedCard>

      {/* Ayah Count Selection */}
      <AnimatedCard variant="default" delay={0.6}>
        <AnimatedCardContent className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-emerald-600" />
            </div>
            <div>
              <div className="font-medium">Number of Ayahs to Recite</div>
              <div className="text-sm text-muted-foreground">How many ayahs after the prompt?</div>
            </div>
          </div>
          
          <div className="grid grid-cols-4 gap-2">
            {[1, 3, 5, 10].map((count) => (
              <motion.button
                key={count}
                onClick={() => setNumAyahs(count)}
                className={`py-3 px-4 rounded-lg font-medium transition-all duration-200 ${
                  numAyahs === count
                    ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white shadow-lg shadow-emerald-500/25'
                    : 'bg-muted hover:bg-emerald-100 dark:hover:bg-emerald-900/30'
                }`}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {count}
              </motion.button>
            ))}
          </div>
        </AnimatedCardContent>
      </AnimatedCard>

      {/* Start Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
      >
        <Button
          onClick={handleStartSession}
          disabled={disabled || loading}
          variant="gradient"
          size="xl"
          className="w-full group"
          isLoading={loading}
        >
          <span>Start Review Session</span>
          <ArrowRight className="w-5 h-5 ml-2 transition-transform group-hover:translate-x-1" />
        </Button>
        
        <p className="text-center text-sm text-muted-foreground mt-3">
          After hearing the prompt, recite the next {numAyahs} ayah{numAyahs > 1 ? 's' : ''} from memory
        </p>
      </motion.div>
    </div>
  );
}

export default JuzSelector;
