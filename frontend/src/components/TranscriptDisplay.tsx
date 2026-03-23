import type { WordStatus, Mistake, AyahText } from '../types';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Badge } from './ui/badge';

interface TranscriptDisplayProps {
  expectedAyahs: AyahText[];
  confirmedWords: WordStatus[];
  tentativeWords: WordStatus[];
  mistakes?: Mistake[];
  isRecording?: boolean;
  isProcessing?: boolean;
}

/**
 * TranscriptDisplay component shows the expected verse with word-by-word highlighting
 * as the user recites. Colors: green=correct, red=error, gray=not yet recited
 */
export function TranscriptDisplay({
  expectedAyahs,
  confirmedWords,
  tentativeWords,
  mistakes = [],
  isRecording = false,
  isProcessing = false,
}: TranscriptDisplayProps) {
  // Create sets for quick lookup
  const confirmedIndices = new Set(confirmedWords.map((w) => w.index));
  const tentativeIndices = new Set(tentativeWords.map((w) => w.index));
  const mistakeIndices = new Set(mistakes.map((m) => m.word_index));

  // Build flat list of all expected words with their indices
  const allExpectedWords: { word: string; index: number; ayahRef: string }[] = [];
  let wordIndex = 0;
  for (const ayah of expectedAyahs) {
    const tokens = ayah.text_uthmani.split(/\s+/);
    for (const token of tokens) {
      if (token.trim()) {
        allExpectedWords.push({
          word: token,
          index: wordIndex,
          ayahRef: `${ayah.surah}:${ayah.ayah}`,
        });
        wordIndex++;
      }
    }
  }

  const getWordClassName = (index: number): string => {
    // Faster transitions for more responsive feel
    const baseClass = 'inline-block mx-1 px-1 py-0.5 rounded transition-all duration-100';

    // Check if this word has an associated mistake (highest priority)
    if (mistakeIndices.has(index)) {
      return `${baseClass} text-red-600 font-bold underline decoration-wavy decoration-red-500 animate-in fade-in duration-150`;
    }

    // Check if confirmed (recited correctly)
    if (confirmedIndices.has(index)) {
      return `${baseClass} text-gray-900 font-bold animate-in fade-in duration-150`;
    }

    // Check if tentative (being processed) - show with pulse to indicate activity
    if (tentativeIndices.has(index)) {
      return `${baseClass} text-emerald-600 font-medium bg-emerald-50 animate-pulse`;
    }

    // Not yet recited - light gray
    return `${baseClass} text-gray-400`;
  };

  // Find current position (first non-confirmed word)
  const currentPosition = confirmedWords.length > 0
    ? Math.max(...confirmedWords.map(w => w.index)) + 1
    : 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Your Recitation</CardTitle>
          <div className="flex items-center gap-2">
            {isProcessing && (
              <Badge variant="outline" className="animate-pulse border-amber-400 text-amber-600">
                Processing...
              </Badge>
            )}
            {isRecording && (
              <>
                <div className="recording-indicator"></div>
                <Badge variant="destructive">Recording</Badge>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Expected Verse with Highlighting */}
        <div
          className="min-h-[120px] p-6 bg-white rounded-lg quran-text border border-gray-100"
          dir="rtl"
        >
          {allExpectedWords.length > 0 ? (
            <>
              {allExpectedWords.map(({ word, index }) => (
                <span key={index} className={getWordClassName(index)}>
                  {word}
                  {/* Show cursor after current position when recording */}
                  {isRecording && index === currentPosition - 1 && (
                    <span className="inline-block w-0.5 h-5 bg-foreground animate-pulse mr-1 align-middle"></span>
                  )}
                </span>
              ))}
              {/* Show cursor at start when no words confirmed yet */}
              {isRecording && currentPosition === 0 && (
                <span className="inline-block w-0.5 h-5 bg-foreground animate-pulse mr-1 align-middle"></span>
              )}
            </>
          ) : (
            <p className="text-gray-400 text-center text-base" dir="ltr">
              {isRecording
                ? 'Listening... Start reciting.'
                : 'Start a session to see the expected verse.'}
            </p>
          )}
        </div>

        {/* Progress indicator */}
        {allExpectedWords.length > 0 && (
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>Progress: {confirmedWords.length} / {allExpectedWords.length} words</span>
            <span>{Math.round((confirmedWords.length / allExpectedWords.length) * 100)}%</span>
          </div>
        )}

        {/* Mistake Notifications */}
        {mistakes.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Recent Issues:</h4>
            <div className="space-y-2">
              {mistakes.slice(-3).map((mistake, idx) => (
                <MistakeNotification key={idx} mistake={mistake} />
              ))}
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="flex items-center justify-center gap-6 pt-3 border-t text-xs">
          <span className="font-bold text-gray-900">● Recited</span>
          <span className="text-red-600">● Error</span>
          <span className="text-gray-400">○ Pending</span>
        </div>
      </CardContent>
    </Card>
  );
}

interface MistakeNotificationProps {
  mistake: Mistake;
}

function MistakeNotification({ mistake }: MistakeNotificationProps) {
  const getTypeLabel = (type: string): string => {
    switch (type) {
      case 'wrong_word':
        return 'Wrong word';
      case 'skipped':
        return 'Skipped';
      case 'added':
        return 'Extra word';
      case 'repetition':
        return 'Repetition';
      case 'out_of_order':
        return 'Out of order';
      case 'jumped_ahead':
        return 'Jumped ahead';
      case 'self_corrected':
        return 'Self-corrected';
      case 'low_confidence':
        return 'Unclear';
      default:
        return 'Issue';
    }
  };

  const getTypeVariant = (type: string): 'destructive' | 'warning' | 'blue' | 'secondary' => {
    switch (type) {
      case 'self_corrected':
        return 'blue';
      case 'repetition':
      case 'low_confidence':
        return 'warning';
      default:
        return 'destructive';
    }
  };

  const isSelfCorrected = mistake.mistake_type === 'self_corrected';
  // variant available for future use with Badge
  void getTypeVariant(mistake.mistake_type);

  return (
    <div className="p-3 rounded-lg border text-sm">
      <div className="flex items-center justify-between">
        <Badge variant="outline">{getTypeLabel(mistake.mistake_type)}</Badge>
        {!mistake.is_penalty && (
          <span className="text-xs text-muted-foreground">No penalty</span>
        )}
      </div>
      {!isSelfCorrected && mistake.expected && (
        <div className="mt-2 text-sm arabic-text" dir="rtl">
          <span className="text-muted-foreground">Expected: </span>
          <span className="font-medium">{mistake.expected}</span>
          {mistake.received && (
            <>
              <span className="text-muted-foreground"> | Said: </span>
              <span className="font-medium text-destructive">{mistake.received}</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default TranscriptDisplay;
