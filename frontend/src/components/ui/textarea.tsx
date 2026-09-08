import * as React from "react";
import { cn } from "@/lib/utils";

export const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        // Layout
        "flex min-h-[52px] w-full",
        // Appearance
        "rounded-lg border border-border bg-background",
        "px-4 py-3 text-sm",
        // Resize behavior — vertical only for chat, can be overridden
        "resize-none",
        // Placeholder
        "placeholder:text-muted-foreground",
        // Focus — matches Input focus ring exactly
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:border-accent/60",
        // Disabled
        "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-muted",
        // Smooth transitions
        "transition-all duration-150",
        className
      )}
      {...props}
    />
  )
);
Textarea.displayName = "Textarea";
