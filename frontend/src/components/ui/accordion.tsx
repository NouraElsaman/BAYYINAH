"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

interface AccordionContextValue {
  activeValue: string | null;
  toggleValue: (value: string) => void;
}

const AccordionContext = React.createContext<AccordionContextValue | null>(null);

export interface AccordionProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
}

export function Accordion({ defaultValue = "", className, children, ...props }: AccordionProps) {
  const [activeValue, setActiveValue] = React.useState<string | null>(defaultValue || null);

  const toggleValue = React.useCallback((value: string) => {
    setActiveValue((prev) => (prev === value ? null : value));
  }, []);

  return (
    <AccordionContext.Provider value={{ activeValue, toggleValue }}>
      <div className={cn("space-y-2", className)} {...props}>
        {children}
      </div>
    </AccordionContext.Provider>
  );
}

export interface AccordionItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export function AccordionItem({ value, className, children, ...props }: AccordionItemProps) {
  return (
    <div
      className={cn("rounded-lg border border-border bg-card overflow-hidden transition-all duration-300", className)}
      data-state={value}
      {...props}
    >
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, { value });
        }
        return child;
      })}
    </div>
  );
}

export interface AccordionTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value?: string;
}

export function AccordionTrigger({ value, className, children, ...props }: AccordionTriggerProps) {
  const context = React.useContext(AccordionContext);
  if (!context) throw new Error("AccordionTrigger must be used inside Accordion");

  const isOpen = context.activeValue === value;

  return (
    <button
      type="button"
      onClick={() => value && context.toggleValue(value)}
      className={cn(
        "flex w-full items-center justify-between px-5 py-4 text-right font-medium text-foreground hover:bg-muted/50 transition-all",
        className
      )}
      {...props}
    >
      {children}
      <ChevronDown
        className={cn("h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-300", isOpen && "rotate-180")}
      />
    </button>
  );
}

export interface AccordionContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
}

export function AccordionContent({ value, className, children, ...props }: AccordionContentProps) {
  const context = React.useContext(AccordionContext);
  if (!context) throw new Error("AccordionContent must be used inside Accordion");

  const isOpen = context.activeValue === value;

  return (
    <div
      className={cn(
        "transition-all duration-300 ease-in-out",
        isOpen ? "max-h-[500px] border-t border-border/50 opacity-100" : "max-h-0 opacity-0 pointer-events-none"
      )}
      {...props}
    >
      <div className={cn("px-5 py-4 text-sm text-muted-foreground leading-relaxed", className)}>
        {children}
      </div>
    </div>
  );
}
