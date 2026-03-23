import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  JuzSelector,
  AyahDisplay,
  TranscriptDisplay,
  RecordingControls,
  SessionSummary,
} from './components';
import { useWebSocket, useAudioRecorder } from './hooks';
import { startSession } from './services/api';
import type {
  AyahText,
  ServerMessage,
  WordStatus,
  Mistake,
  SessionSummary as SessionSummaryType,
  ConnectionState,
} from './types';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { AnimatedCard } from './components/ui/animated-card';
import { ProgressRing } from './components/ui/progress-ring';
import { 
  Volume2, 
  Mic, 
  WifiOff, 
  Loader2,
  BookOpen,
  ChevronLeft,
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import './index.css';

// App states
type AppView = 'select' | 'session' | 'summary';

// Surah names for display
const SURAH_NAMES: Record<number, string> = {
  1: 'Al-Fatiha', 2: 'Al-Baqarah', 3: 'Aal-Imran', 4: 'An-Nisa', 5: 'Al-Maidah',
  6: 'Al-Anam', 7: 'Al-Araf', 8: 'Al-Anfal', 9: 'At-Tawbah', 10: 'Yunus',
  11: 'Hud', 12: 'Yusuf', 13: 'Ar-Rad', 14: 'Ibrahim', 15: 'Al-Hijr',
  16: 'An-Nahl', 17: 'Al-Isra', 18: 'Al-Kahf', 19: 'Maryam', 20: 'Ta-Ha',
  21: 'Al-Anbiya', 22: 'Al-Hajj', 23: 'Al-Muminun', 24: 'An-Nur', 25: 'Al-Furqan',
  26: 'Ash-Shuara', 27: 'An-Naml', 28: 'Al-Qasas', 29: 'Al-Ankabut', 30: 'Ar-Rum',
  31: 'Luqman', 32: 'As-Sajdah', 33: 'Al-Ahzab', 34: 'Saba', 35: 'Fatir',
  36: 'Ya-Sin', 37: 'As-Saffat', 38: 'Sad', 39: 'Az-Zumar', 40: 'Ghafir',
  41: 'Fussilat', 42: 'Ash-Shura', 43: 'Az-Zukhruf', 44: 'Ad-Dukhan', 45: 'Al-Jathiyah',
  46: 'Al-Ahqaf', 47: 'Muhammad', 48: 'Al-Fath', 49: 'Al-Hujurat', 50: 'Qaf',
  51: 'Adh-Dhariyat', 52: 'At-Tur', 53: 'An-Najm', 54: 'Al-Qamar', 55: 'Ar-Rahman',
  56: 'Al-Waqiah', 57: 'Al-Hadid', 58: 'Al-Mujadila', 59: 'Al-Hashr', 60: 'Al-Mumtahina',
  61: 'As-Saff', 62: 'Al-Jumuah', 63: 'Al-Munafiqun', 64: 'At-Taghabun', 65: 'At-Talaq',
  66: 'At-Tahrim', 67: 'Al-Mulk', 68: 'Al-Qalam', 69: 'Al-Haqqah', 70: 'Al-Maarij',
  71: 'Nuh', 72: 'Al-Jinn', 73: 'Al-Muzzammil', 74: 'Al-Muddaththir', 75: 'Al-Qiyamah',
  76: 'Al-Insan', 77: 'Al-Mursalat', 78: 'An-Naba', 79: 'An-Naziat', 80: 'Abasa',
  81: 'At-Takwir', 82: 'Al-Infitar', 83: 'Al-Mutaffifin', 84: 'Al-Inshiqaq', 85: 'Al-Buruj',
  86: 'At-Tariq', 87: 'Al-Ala', 88: 'Al-Ghashiyah', 89: 'Al-Fajr', 90: 'Al-Balad',
  91: 'Ash-Shams', 92: 'Al-Layl', 93: 'Ad-Duha', 94: 'Ash-Sharh', 95: 'At-Tin',
  96: 'Al-Alaq', 97: 'Al-Qadr', 98: 'Al-Bayyinah', 99: 'Az-Zalzalah', 100: 'Al-Adiyat',
  101: 'Al-Qariah', 102: 'At-Takathur', 103: 'Al-Asr', 104: 'Al-Humazah', 105: 'Al-Fil',
  106: 'Quraysh', 107: 'Al-Maun', 108: 'Al-Kawthar', 109: 'Al-Kafirun', 110: 'An-Nasr',
  111: 'Al-Masad', 112: 'Al-Ikhlas', 113: 'Al-Falaq', 114: 'An-Nas',
};

function getSurahName(surahNumber: number): string {
  return SURAH_NAMES[surahNumber] || `Surah ${surahNumber}`;
}

function App() {
  // View state
  const [view, setView] = useState<AppView>('select');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Session state
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [promptAyah, setPromptAyah] = useState<AyahText | null>(null);
  const [expectedAyahs, setExpectedAyahs] = useState<AyahText[]>([]);
  const [currentAyahIndex, setCurrentAyahIndex] = useState(0);

  // Transcription state
  const [confirmedWords, setConfirmedWords] = useState<WordStatus[]>([]);
  const [tentativeWords, setTentativeWords] = useState<WordStatus[]>([]);
  const [mistakes, setMistakes] = useState<Mistake[]>([]);
  const [summary, setSummary] = useState<SessionSummaryType | null>(null);
  const [isProcessingAudio, setIsProcessingAudio] = useState(false);

  // Audio playback ref
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioPlaying, setAudioPlaying] = useState(false);

  // WebSocket message handler
  const handleMessage = useCallback((message: ServerMessage) => {
    console.log('[WS] Received message:', message.type, message);
    switch (message.type) {
      case 'transcription':
        console.log('[WS] Transcription update:', message.confirmed_words?.length, 'confirmed,', message.tentative_words?.length, 'tentative');
        setConfirmedWords(message.confirmed_words);
        setTentativeWords(message.tentative_words);
        setIsProcessingAudio(false); // Received response, no longer processing
        break;

      case 'mistake':
        setMistakes((prev) => [
          ...prev,
          {
            mistake_type: message.mistake_type,
            ayah: [0, 0],
            word_index: message.word_index,
            expected: message.expected,
            received: message.received,
            confidence: message.confidence,
            is_penalty: message.is_penalty,
            timestamp_ms: Date.now(),
          },
        ]);
        break;

      case 'self_correction':
        setMistakes((prev) => [
          ...prev,
          {
            mistake_type: 'self_corrected',
            ayah: [0, 0],
            word_index: message.word_index,
            expected: '',
            received: null,
            confidence: 1,
            is_penalty: false,
            timestamp_ms: Date.now(),
          },
        ]);
        break;

      case 'ayah_complete':
        setCurrentAyahIndex((prev) => prev + 1);
        break;

      case 'session_complete':
        setSummary(message.summary);
        setView('summary');
        break;
    }
  }, []);

  // WebSocket hook
  const {
    connectionState,
    connect,
    disconnect,
    sendMessage,
    sendBinary,
  } = useWebSocket({
    onMessage: handleMessage,
    onError: () => setError('WebSocket connection error'),
  });

  // Audio chunk handler
  const handleAudioChunk = useCallback(
    (chunk: ArrayBuffer, timestamp: number) => {
      setIsProcessingAudio(true);
      sendBinary(chunk);
      sendMessage({
        type: 'audio_chunk',
        data: '',
        timestamp_ms: timestamp,
        is_final: false,
      });
      // Clear processing state after a short delay (transcription should arrive by then)
      setTimeout(() => setIsProcessingAudio(false), 100);
    },
    [sendBinary, sendMessage]
  );

  // Audio recorder hook
  const {
    recordingState,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    error: recorderError,
    audioLevel,
  } = useAudioRecorder({
    onAudioChunk: handleAudioChunk,
    chunkInterval: 150,
  });

  // Start a new session
  const handleStartSession = async (juzStart: number, juzEnd: number, numAyahs?: number) => {
    setLoading(true);
    setError(null);

    try {
      const response = await startSession({
        juz_start: juzStart,
        juz_end: juzEnd,
        num_ayahs: numAyahs,
      });

      setSessionId(response.session_id);
      setPromptAyah(response.prompt_ayah);
      setExpectedAyahs(response.expected_ayahs);
      setCurrentAyahIndex(0);
      setConfirmedWords([]);
      setTentativeWords([]);
      setMistakes([]);
      setSummary(null);

      connect(response.session_id);

      if (response.prompt_ayah.audio_url) {
        playPromptAudio(response.prompt_ayah.audio_url);
      }

      setView('session');
    } catch (err) {
      console.error('Failed to start session:', err);
      setError('Failed to start session. Please check if the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  // Play the prompt ayah audio
  const playPromptAudio = (url: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(url);
    audioRef.current = audio;

    audio.onplay = () => setAudioPlaying(true);
    audio.onended = () => setAudioPlaying(false);
    audio.onerror = () => {
      setAudioPlaying(false);
      console.warn('Failed to play audio:', url);
    };

    audio.play().catch((err) => {
      console.warn('Audio playback failed:', err);
    });
  };

  // Handle recording start
  const handleStartRecording = async () => {
    sendMessage({ type: 'start_recording' });
    await startRecording();
  };

  // Handle recording stop
  const handleStopRecording = () => {
    sendMessage({ type: 'stop_recording' });
    stopRecording();
  };

  // Handle recording pause
  const handlePauseRecording = () => {
    sendMessage({ type: 'pause_recording' });
    pauseRecording();
  };

  // Handle recording resume
  const handleResumeRecording = () => {
    sendMessage({ type: 'start_recording' });
    resumeRecording();
  };

  // Handle retry
  const handleRetry = () => {
    if (promptAyah && promptAyah.audio_url) {
      setCurrentAyahIndex(0);
      setConfirmedWords([]);
      setTentativeWords([]);
      setMistakes([]);
      setSummary(null);
      setView('session');

      if (sessionId) {
        connect(sessionId);
      }
      playPromptAudio(promptAyah.audio_url);
    }
  };

  // Handle new session
  const handleNewSession = () => {
    disconnect();
    setSessionId(null);
    setPromptAyah(null);
    setExpectedAyahs([]);
    setCurrentAyahIndex(0);
    setConfirmedWords([]);
    setTentativeWords([]);
    setMistakes([]);
    setSummary(null);
    setView('select');
  };

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      disconnect();
    };
  }, [disconnect]);

  // Get current ayah being recited
  const currentAyah = expectedAyahs[currentAyahIndex] || null;
  const progress = expectedAyahs.length > 0 
    ? ((currentAyahIndex) / expectedAyahs.length) * 100 
    : 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-950 dark:to-slate-900">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-slate-950/80 backdrop-blur-lg border-b">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <motion.div 
              className="flex items-center gap-3"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
                  Hifdh Review
                </h1>
                <p className="text-xs text-muted-foreground">Strengthen Your Memorization</p>
              </div>
            </motion.div>

            <div className="flex items-center gap-3">
              {view === 'session' && (
                <ConnectionStatus state={connectionState} />
              )}
              {view !== 'select' && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleNewSession}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ChevronLeft className="w-4 h-4 mr-1" />
                  New Session
                </Button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <AnimatePresence mode="wait">
          {/* Global Error */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mb-6"
            >
              <div className="p-4 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-xl text-red-800 dark:text-red-400 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <AlertCircle className="w-5 h-5" />
                  <span>{error}</span>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setError(null)}
                  className="text-red-600 hover:text-red-800"
                >
                  Dismiss
                </Button>
              </div>
            </motion.div>
          )}

          {/* Select View */}
          {view === 'select' && (
            <motion.div
              key="select"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <JuzSelector onSelect={handleStartSession} disabled={loading} />
            </motion.div>
          )}

          {/* Session View */}
          {view === 'session' && (
            <motion.div
              key="session"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="space-y-6"
            >
              {/* Progress Bar */}
              <div className="flex items-center gap-4">
                <ProgressRing 
                  progress={progress} 
                  size={60} 
                  strokeWidth={5}
                  showPercentage
                  variant="success"
                />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium">Session Progress</span>
                    <span className="text-sm text-muted-foreground">
                      {currentAyahIndex + 1} / {expectedAyahs.length} ayahs
                    </span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: `${progress}%` }}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </div>
              </div>

              {/* Prompt Ayah */}
              {promptAyah && (
                <AnimatedCard variant="gradient" delay={0.1}>
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center">
                          <Volume2 className="w-4 h-4 text-emerald-600" />
                        </div>
                        <h2 className="font-semibold">Listen to this ayah</h2>
                      </div>
                      
                      {audioPlaying ? (
                        <Badge variant="default" className="animate-pulse bg-emerald-500">
                          Playing...
                        </Badge>
                      ) : promptAyah.audio_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => playPromptAudio(promptAyah.audio_url)}
                        >
                          <Volume2 className="w-4 h-4 mr-2" />
                          Replay
                        </Button>
                      )}
                    </div>
                    <AyahDisplay ayah={promptAyah} isPrompt showReference />
                  </div>
                </AnimatedCard>
              )}

              {/* Current Ayah Being Recited */}
              {currentAyah && (
                <AnimatedCard variant="elevated" delay={0.2}>
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
                          <Mic className="w-4 h-4 text-white" />
                        </div>
                        <div>
                          <h2 className="font-semibold">Now Recite</h2>
                          <p className="text-sm text-muted-foreground">
                            {getSurahName(currentAyah.surah)} ({currentAyah.surah}:{currentAyah.ayah})
                          </p>
                        </div>
                      </div>
                      <Badge variant="outline">Juz {currentAyah.juz}</Badge>
                    </div>

                    {/* Memory Prompt Box */}
                    <div className="py-8 px-6 bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-center">
                      <motion.div
                        animate={{ 
                          scale: recordingState === 'recording' ? [1, 1.02, 1] : 1,
                        }}
                        transition={{ duration: 2, repeat: Infinity }}
                      >
                        <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/30 dark:to-teal-900/30 flex items-center justify-center">
                          <Sparkles className="w-8 h-8 text-emerald-600" />
                        </div>
                        <p className="text-muted-foreground">
                          Recite this ayah from memory...
                        </p>
                        <p className="text-sm text-muted-foreground/70 mt-1">
                          ({currentAyah.text_tokens?.length || 0} words)
                        </p>
                      </motion.div>
                    </div>

                    {/* Quick Recording Controls */}
                    {recordingState === 'idle' && (
                      <motion.div 
                        className="mt-4 flex justify-center"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                      >
                        <Button
                          onClick={handleStartRecording}
                          disabled={connectionState !== 'connected'}
                          variant="gradient"
                          size="lg"
                          className="rounded-full px-8"
                        >
                          <Mic className="w-5 h-5 mr-2" />
                          Start Recording
                        </Button>
                      </motion.div>
                    )}
                  </div>
                </AnimatedCard>
              )}

              {/* Transcription Display */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
              >
                <TranscriptDisplay
                  expectedAyahs={expectedAyahs}
                  confirmedWords={confirmedWords}
                  tentativeWords={tentativeWords}
                  mistakes={mistakes}
                  isRecording={recordingState === 'recording'}
                  isProcessing={isProcessingAudio}
                />
              </motion.div>

              {/* Full Recording Controls */}
              {recordingState !== 'idle' && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                >
                  <RecordingControls
                    recordingState={recordingState}
                    audioLevel={audioLevel}
                    onStart={handleStartRecording}
                    onStop={handleStopRecording}
                    onPause={handlePauseRecording}
                    onResume={handleResumeRecording}
                    error={recorderError}
                    disabled={connectionState !== 'connected'}
                  />
                </motion.div>
              )}
            </motion.div>
          )}

          {/* Summary View */}
          {view === 'summary' && summary && (
            <motion.div
              key="summary"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              <SessionSummary
                summary={summary}
                onRetry={handleRetry}
                onNewSession={handleNewSession}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Footer */}
      <footer className="mt-auto py-8 text-center">
        <p className="text-sm text-muted-foreground">
          Hifdh Review App — Strengthen your Quran memorization
        </p>
      </footer>
    </div>
  );
}

// Connection status indicator
function ConnectionStatus({ state }: { state: ConnectionState }) {
  const config = {
    connecting: { 
      icon: Loader2, 
      text: 'Connecting', 
      className: 'text-amber-500',
      animate: 'spin'
    },
    connected: { 
      icon: CheckCircle2, 
      text: 'Connected', 
      className: 'text-emerald-500',
      animate: 'none'
    },
    disconnected: { 
      icon: WifiOff, 
      text: 'Offline', 
      className: 'text-slate-400',
      animate: 'none'
    },
    error: { 
      icon: AlertCircle, 
      text: 'Error', 
      className: 'text-red-500',
      animate: 'none'
    },
  };

  const { icon: Icon, text, className, animate } = config[state];

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
      <Icon className={`w-4 h-4 ${className} ${animate === 'spin' ? 'animate-spin' : ''}`} />
      <span className={`text-xs font-medium ${className}`}>{text}</span>
    </div>
  );
}

export default App;
