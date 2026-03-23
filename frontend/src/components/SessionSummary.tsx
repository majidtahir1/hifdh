import { motion } from 'framer-motion';
import type { SessionSummary as SessionSummaryType, Mistake } from '../types';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { AnimatedCard, AnimatedCardContent } from './ui/animated-card';
import { ProgressRing, AnimatedProgress } from './ui/progress-ring';
import { 
  RotateCcw, 
  Plus, 
  Trophy, 
  Target, 
  CheckCircle2, 
  AlertCircle,
  XCircle,
  TrendingUp,
  BookOpen
} from 'lucide-react';

interface SessionSummaryProps {
  summary: SessionSummaryType;
  onRetry?: () => void;
  onNewSession?: () => void;
  onClose?: () => void;
}

/**
 * SessionSummary component displays session statistics after completion
 * Shows accuracy, mistakes, and time
 */
export function SessionSummary({
  summary,
  onRetry,
  onNewSession,
  onClose,
}: SessionSummaryProps) {
  const { ayahs_tested, ayahs_correct, total_words, words_correct, mistakes } = summary;

  // Calculate accuracy
  const wordAccuracy = total_words > 0 ? (words_correct / total_words) * 100 : 0;
  const ayahAccuracy = ayahs_tested > 0 ? (ayahs_correct / ayahs_tested) * 100 : 0;

  // Group mistakes by type
  const mistakesByType = mistakes.reduce<Record<string, number>>((acc, mistake) => {
    const type = mistake.mistake_type;
    acc[type] = (acc[type] || 0) + 1;
    return acc;
  }, {});

  // Determine grade based on accuracy
  const getGrade = (accuracy: number): { 
    label: string; 
    color: string; 
    bgColor: string;
    message: string;
    icon: typeof Trophy;
  } => {
    if (accuracy >= 95) {
      return {
        label: 'Excellent',
        color: 'text-emerald-600',
        bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
        message: 'MashaAllah! Outstanding recitation. Your memorization is strong.',
        icon: Trophy,
      };
    }
    if (accuracy >= 85) {
      return {
        label: 'Very Good',
        color: 'text-teal-600',
        bgColor: 'bg-teal-50 dark:bg-teal-950/30',
        message: 'Great job! Just a few areas to review.',
        icon: CheckCircle2,
      };
    }
    if (accuracy >= 70) {
      return {
        label: 'Good',
        color: 'text-amber-600',
        bgColor: 'bg-amber-50 dark:bg-amber-950/30',
        message: 'Good effort. Consider reviewing the highlighted sections.',
        icon: Target,
      };
    }
    return {
      label: 'Keep Practicing',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50 dark:bg-orange-950/30',
      message: 'Keep practicing! Review the ayahs and try again.',
      icon: BookOpen,
    };
  };

  const grade = getGrade(wordAccuracy);
  const GradeIcon = grade.icon;

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 },
  };

  return (
    <motion.div 
      className="max-w-2xl mx-auto space-y-6"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      {/* Grade Card */}
      <motion.div variants={itemVariants}>
        <AnimatedCard variant="elevated" className="overflow-hidden">
          <div className={`p-8 text-center ${grade.bgColor}`}>
            <motion.div
              initial={{ scale: 0, rotate: -180 }}
              animate={{ scale: 1, rotate: 0 }}
              transition={{ type: "spring", stiffness: 200, damping: 15 }}
              className={`w-20 h-20 mx-auto mb-4 rounded-2xl ${grade.color} bg-white dark:bg-slate-900 flex items-center justify-center shadow-lg`}
            >
              <GradeIcon className="w-10 h-10" />
            </motion.div>
            
            <motion.h2 
              className={`text-3xl font-bold ${grade.color} mb-2`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              {grade.label}
            </motion.h2>
            
            <motion.p 
              className="text-muted-foreground"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
            >
              {grade.message}
            </motion.p>
          </div>
        </AnimatedCard>
      </motion.div>

      {/* Stats Grid */}
      <motion.div variants={itemVariants}>
        <div className="grid grid-cols-2 gap-4">
          {/* Word Accuracy */}
          <AnimatedCard variant="default" className="p-6 text-center">
            <ProgressRing 
              progress={wordAccuracy} 
              size={80} 
              strokeWidth={6}
              showPercentage
              variant={wordAccuracy >= 85 ? 'success' : wordAccuracy >= 70 ? 'warning' : 'danger'}
            />
            <div className="mt-3">
              <div className="font-medium">Word Accuracy</div>
              <div className="text-sm text-muted-foreground">
                {words_correct} / {total_words} words
              </div>
            </div>
          </AnimatedCard>

          {/* Ayah Accuracy */}
          <AnimatedCard variant="default" className="p-6 text-center">
            <ProgressRing 
              progress={ayahAccuracy} 
              size={80} 
              strokeWidth={6}
              showPercentage
              variant={ayahAccuracy >= 85 ? 'success' : ayahAccuracy >= 70 ? 'warning' : 'danger'}
            />
            <div className="mt-3">
              <div className="font-medium">Ayah Accuracy</div>
              <div className="text-sm text-muted-foreground">
                {ayahs_correct} / {ayahs_tested} ayahs
              </div>
            </div>
          </AnimatedCard>
        </div>
      </motion.div>

      {/* Detailed Progress */}
      <motion.div variants={itemVariants}>
        <AnimatedCard variant="default">
          <AnimatedCardContent className="p-6 space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              <h3 className="font-semibold">Detailed Progress</h3>
            </div>
            
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Words Correct</span>
                  <span className="font-medium">{wordAccuracy.toFixed(0)}%</span>
                </div>
                <AnimatedProgress 
                  value={words_correct} 
                  max={total_words}
                  showValue
                />
              </div>
              
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Ayahs Correct</span>
                  <span className="font-medium">{ayahAccuracy.toFixed(0)}%</span>
                </div>
                <AnimatedProgress 
                  value={ayahs_correct} 
                  max={ayahs_tested}
                  showValue
                />
              </div>
            </div>
          </AnimatedCardContent>
        </AnimatedCard>
      </motion.div>

      {/* Mistake Summary */}
      {mistakes.length > 0 && (
        <motion.div variants={itemVariants}>
          <AnimatedCard variant="default">
            <AnimatedCardContent className="p-6 space-y-4">
              <div className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-500" />
                <h3 className="font-semibold">Mistake Summary</h3>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {Object.entries(mistakesByType).map(([type, count]) => (
                  <MistakeTypeBadge key={type} type={type} count={count} />
                ))}
              </div>
            </AnimatedCardContent>
          </AnimatedCard>
        </motion.div>
      )}

      {/* Detailed Mistakes */}
      {mistakes.length > 0 && (
        <motion.div variants={itemVariants}>
          <AnimatedCard variant="default">
            <AnimatedCardContent className="p-6 space-y-4">
              <h3 className="font-semibold">Details</h3>
              <div className="max-h-60 overflow-y-auto space-y-2 pr-1 no-scrollbar">
                {mistakes.map((mistake, idx) => (
                  <MistakeDetail key={idx} mistake={mistake} index={idx} />
                ))}
              </div>
            </AnimatedCardContent>
          </AnimatedCard>
        </motion.div>
      )}

      {/* Action Buttons */}
      <motion.div variants={itemVariants} className="flex flex-col sm:flex-row gap-3 pt-4">
        {onRetry && (
          <Button 
            onClick={onRetry} 
            variant="outline"
            size="lg"
            className="flex-1 rounded-xl"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Retry Same Test
          </Button>
        )}
        {onNewSession && (
          <Button 
            onClick={onNewSession} 
            variant="gradient"
            size="lg"
            className="flex-1 rounded-xl"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Session
          </Button>
        )}
        {onClose && (
          <Button 
            onClick={onClose} 
            variant="ghost"
            size="lg"
            className="flex-1 rounded-xl"
          >
            Close
          </Button>
        )}
      </motion.div>
    </motion.div>
  );
}

interface MistakeTypeBadgeProps {
  type: string;
  count: number;
}

function MistakeTypeBadge({ type, count }: MistakeTypeBadgeProps) {
  const getLabel = (mistakeType: string): string => {
    switch (mistakeType) {
      case 'wrong_word': return 'Wrong Words';
      case 'skipped': return 'Skipped';
      case 'added': return 'Extra Words';
      case 'repetition': return 'Repetitions';
      case 'out_of_order': return 'Out of Order';
      case 'jumped_ahead': return 'Jumped Ahead';
      case 'self_corrected': return 'Self-Corrected';
      case 'low_confidence': return 'Unclear';
      default: return type;
    }
  };

  const getVariant = (mistakeType: string) => {
    if (mistakeType === 'self_corrected') return 'success';
    if (mistakeType === 'wrong_word' || mistakeType === 'skipped') return 'destructive';
    return 'warning';
  };

  return (
    <Badge variant={getVariant(type)} className="text-sm">
      {getLabel(type)}: {count}
    </Badge>
  );
}

interface MistakeDetailProps {
  mistake: Mistake;
  index: number;
}

function MistakeDetail({ mistake, index }: MistakeDetailProps) {
  const [surah, ayah] = mistake.ayah;

  return (
    <motion.div 
      className="p-4 rounded-xl border bg-card"
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium px-2 py-1 bg-muted rounded-full">
            {surah}:{ayah}
          </span>
          <span className="text-xs text-muted-foreground">
            Word {mistake.word_index + 1}
          </span>
        </div>
        {!mistake.is_penalty ? (
          <Badge variant="success" className="text-xs">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            No penalty
          </Badge>
        ) : (
          <Badge variant="destructive" className="text-xs">
            <XCircle className="w-3 h-3 mr-1" />
            Mistake
          </Badge>
        )}
      </div>
      
      <div className="arabic-text text-lg" dir="rtl">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">Expected:</span>
          <span className="font-medium text-emerald-600">{mistake.expected}</span>
        </div>
        {mistake.received && (
          <div className="flex items-center gap-2 flex-wrap mt-1">
            <span className="text-sm text-muted-foreground">Said:</span>
            <span className="font-medium text-red-500">{mistake.received}</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}

export default SessionSummary;
