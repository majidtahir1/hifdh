import { motion, AnimatePresence } from 'framer-motion';
import { Button } from './ui/button';
import { AudioVisualizer, CircularAudioVisualizer } from './ui/audio-visualizer';
import { AnimatedCard, AnimatedCardContent } from './ui/animated-card';
import { 
  Mic, 
  Square, 
  Pause, 
  Play, 
  AlertCircle,
  Activity
} from 'lucide-react';

interface RecordingControlsProps {
  recordingState: 'idle' | 'recording' | 'paused';
  audioLevel: number;
  onStart: () => void;
  onStop: () => void;
  onPause: () => void;
  onResume: () => void;
  error?: string | null;
  disabled?: boolean;
}

export function RecordingControls({
  recordingState,
  audioLevel,
  onStart,
  onStop,
  onPause,
  onResume,
  error,
  disabled = false,
}: RecordingControlsProps) {
  const isRecording = recordingState === 'recording';
  const isIdle = recordingState === 'idle';

  return (
    <AnimatePresence mode="wait">
      {isIdle ? (
        <motion.div
          key="idle"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="flex justify-center"
        >
          <Button
            onClick={onStart}
            disabled={disabled}
            variant="gradient"
            size="xl"
            className="group"
          >
            <Mic className="w-5 h-5 mr-2 transition-transform group-hover:scale-110" />
            Start Recording
          </Button>
        </motion.div>
      ) : (
        <motion.div
          key="active"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.3 }}
        >
          <AnimatedCard variant="glass" className="overflow-hidden">
            <AnimatedCardContent className="p-6">
              {/* Status Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <motion.div
                    className={`w-3 h-3 rounded-full ${
                      isRecording ? 'bg-red-500' : 'bg-amber-500'
                    }`}
                    animate={
                      isRecording
                        ? {
                            scale: [1, 1.2, 1],
                            opacity: [1, 0.7, 1],
                          }
                        : {}
                    }
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                  <span className="font-medium">
                    {isRecording ? 'Recording...' : 'Paused'}
                  </span>
                </div>
                
                {isRecording && (
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <Activity className="w-4 h-4 text-emerald-500" />
                    <span>Listening</span>
                  </motion.div>
                )}
              </div>

              {/* Audio Visualizer */}
              <div className="py-6">
                <div className="hidden sm:block">
                  <AudioVisualizer 
                    audioLevel={audioLevel} 
                    isRecording={isRecording}
                    barCount={24}
                  />
                </div>
                <div className="sm:hidden flex justify-center">
                  <CircularAudioVisualizer
                    audioLevel={audioLevel}
                    isRecording={isRecording}
                    size={100}
                  />
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-4 p-3 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400 text-sm"
                >
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{error}</span>
                </motion.div>
              )}

              {/* Control Buttons */}
              <div className="flex items-center justify-center gap-3">
                {isRecording ? (
                  <>
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        onClick={onPause}
                        disabled={disabled}
                        variant="outline"
                        size="lg"
                        className="rounded-full px-6"
                      >
                        <Pause className="w-4 h-4 mr-2" />
                        Pause
                      </Button>
                    </motion.div>
                    
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        onClick={onStop}
                        disabled={disabled}
                        variant="destructive"
                        size="lg"
                        className="rounded-full px-8"
                      >
                        <Square className="w-4 h-4 mr-2" />
                        Stop
                      </Button>
                    </motion.div>
                  </>
                ) : (
                  <>
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        onClick={onStop}
                        disabled={disabled}
                        variant="outline"
                        size="lg"
                        className="rounded-full px-6"
                      >
                        <Square className="w-4 h-4 mr-2" />
                        Finish
                      </Button>
                    </motion.div>
                    
                    <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                      <Button
                        onClick={onResume}
                        disabled={disabled}
                        variant="gradient"
                        size="lg"
                        className="rounded-full px-8"
                      >
                        <Play className="w-4 h-4 mr-2" />
                        Resume
                      </Button>
                    </motion.div>
                  </>
                )}
              </div>

              {/* Tips */}
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
                className="text-center text-sm text-muted-foreground mt-4"
              >
                {isRecording 
                  ? 'Speak clearly. The app will detect mistakes in real-time.'
                  : 'Recording paused. Click Resume to continue.'}
              </motion.p>
            </AnimatedCardContent>
          </AnimatedCard>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default RecordingControls;
