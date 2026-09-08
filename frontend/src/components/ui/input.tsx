import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = "text", ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          // Layout
          "flex h-10 w-full",
          // Appearance
          "rounded-lg border border-border bg-background",
          "px-4 py-2 text-sm",
          // Placeholder
          "placeholder:text-muted-foreground",
          // File input reset
          "file:border-0 file:bg-transparent file:text-sm file:font-medium",
          // Focus ring
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 focus-visible:border-accent/60",
          // Disabled
          "disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-muted",
          // Smooth transitions
          "transition-all duration-150",
          // RTL support — text direction inherits from html[dir=rtl]
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
