import * as React from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface AudioVisualizerProps {
  audioLevel: number
  isRecording: boolean
  className?: string
  barCount?: number
}

export function AudioVisualizer({ 
  audioLevel, 
  isRecording, 
  className,
  barCount = 20 
}: AudioVisualizerProps) {
  // Generate bars based on audio level
  const bars = React.useMemo(() => {
    return Array.from({ length: barCount }, (_, i) => {
      // Create a wave pattern that responds to audio level
      const baseHeight = 20
      const maxHeight = 100
      const normalizedLevel = Math.min(audioLevel / 100, 1)
      
      // Add some randomness and wave effect
      const wave = Math.sin((i / barCount) * Math.PI * 2) * 0.3 + 0.7
      const random = Math.random() * 0.2 + 0.8
      
      const height = isRecording 
        ? baseHeight + (maxHeight - baseHeight) * normalizedLevel * wave * random
        : baseHeight * 0.5

      return {
        height: Math.max(8, Math.min(height, maxHeight)),
        delay: i * 0.03,
      }
    })
  }, [audioLevel, isRecording, barCount])

  return (
    <div className={cn("flex items-center justify-center gap-1 h-24", className)}>
      {bars.map((bar, index) => (
        <motion.div
          key={index}
          className={cn(
            "w-1.5 rounded-full transition-colors duration-150",
            isRecording 
              ? "bg-gradient-to-t from-emerald-500 to-teal-400" 
              : "bg-slate-300 dark:bg-slate-700"
          )}
          initial={{ height: 8 }}
          animate={{ 
            height: bar.height,
            opacity: isRecording ? 1 : 0.5,
          }}
          transition={{
            height: {
              type: "spring",
              stiffness: 300,
              damping: 20,
              delay: bar.delay,
            },
            opacity: {
              duration: 0.2,
            }
          }}
        />
      ))}
    </div>
  )
}

// Circular audio visualizer variant
interface CircularAudioVisualizerProps {
  audioLevel: number
  isRecording: boolean
  size?: number
  className?: string
}

export function CircularAudioVisualizer({
  audioLevel,
  isRecording,
  size = 120,
  className,
}: CircularAudioVisualizerProps) {
  const normalizedLevel = Math.min(audioLevel / 100, 1)
  
  return (
    <div 
      className={cn("relative flex items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      {/* Outer ring */}
      <motion.div
        className="absolute inset-0 rounded-full border-2 border-emerald-200 dark:border-emerald-800"
        animate={{
          scale: isRecording ? [1, 1.05, 1] : 1,
          opacity: isRecording ? [0.5, 0.8, 0.5] : 0.3,
        }}
        transition={{
          duration: 1.5,
          repeat: Infinity,
          ease: "easeInOut",
        }}
      />
      
      {/* Middle ring - responds to audio */}
      <motion.div
        className="absolute rounded-full bg-gradient-to-br from-emerald-400/30 to-teal-500/30 backdrop-blur-sm"
        animate={{
          width: size * (0.5 + normalizedLevel * 0.4),
          height: size * (0.5 + normalizedLevel * 0.4),
          opacity: isRecording ? 0.6 : 0.2,
        }}
        transition={{
          type: "spring",
          stiffness: 200,
          damping: 15,
        }}
      />
      
      {/* Inner circle */}
      <motion.div
        className={cn(
          "absolute rounded-full flex items-center justify-center",
          isRecording 
            ? "bg-gradient-to-br from-emerald-500 to-teal-600" 
            : "bg-slate-300 dark:bg-slate-700"
        )}
        animate={{
          width: size * 0.35,
          height: size * 0.35,
        }}
        transition={{
          type: "spring",
          stiffness: 300,
          damping: 20,
        }}
      >
        <motion.div
          className="w-3 h-3 rounded-full bg-white"
          animate={{
            scale: isRecording ? [1, 1.2, 1] : 1,
            opacity: isRecording ? [1, 0.7, 1] : 0.5,
          }}
          transition={{
            duration: 0.8,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      </motion.div>
    </div>
  )
}
