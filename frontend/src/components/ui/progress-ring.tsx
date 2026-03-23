import * as React from "react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface ProgressRingProps {
  progress: number
  size?: number
  strokeWidth?: number
  className?: string
  children?: React.ReactNode
  showPercentage?: boolean
  variant?: "default" | "success" | "warning" | "danger"
}

export function ProgressRing({
  progress,
  size = 120,
  strokeWidth = 8,
  className,
  children,
  showPercentage = false,
  variant = "default",
}: ProgressRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const offset = circumference - (Math.min(progress, 100) / 100) * circumference

  const variants = {
    default: "text-primary",
    success: "text-emerald-500",
    warning: "text-amber-500",
    danger: "text-red-500",
  }

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)}>
      <svg
        width={size}
        height={size}
        className="-rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          className="text-muted stroke-current"
          opacity={0.2}
        />
        {/* Progress circle */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className={cn("stroke-current", variants[variant])}
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </svg>
      
      {/* Center content */}
      <div className="absolute inset-0 flex items-center justify-center">
        {showPercentage ? (
          <span className={cn("text-2xl font-bold", variants[variant])}>
            {Math.round(progress)}%
          </span>
        ) : (
          children
        )}
      </div>
    </div>
  )
}

// Linear progress with animation
interface AnimatedProgressProps {
  value: number
  max?: number
  className?: string
  barClassName?: string
  showValue?: boolean
  size?: "sm" | "md" | "lg"
}

export function AnimatedProgress({
  value,
  max = 100,
  className,
  barClassName,
  showValue = false,
  size = "md",
}: AnimatedProgressProps) {
  const percentage = Math.min((value / max) * 100, 100)
  
  const sizes = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
  }

  return (
    <div className={cn("w-full", className)}>
      <div className={cn("w-full bg-muted rounded-full overflow-hidden", sizes[size])}>
        <motion.div
          className={cn(
            "h-full bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full",
            barClassName
          )}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
        />
      </div>
      {showValue && (
        <div className="flex justify-between mt-1 text-xs text-muted-foreground">
          <span>{Math.round(percentage)}%</span>
          <span>{value}/{max}</span>
        </div>
      )}
    </div>
  )
}
