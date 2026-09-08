"use client";

import React, { useRef, useState, useEffect } from "react";
import {
  Send,
  AlertTriangle,
  Loader2,
  ThumbsUp,
  ThumbsDown,
  Sparkles,
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  Copy,
  Share2,
  RotateCcw,
  FileDown,
  Paperclip,
  Mic,
  Square,
  CheckCircle2,
  BookOpen,
  Check,
  ChevronDown,
  History,
  FileText,
  Sliders,
  Moon,
  Sun
} from "lucide-react";
import Image from "next/image";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { useTheme } from "@/components/theme-provider";
import { streamChatMessage, submitFeedback } from "@/lib/api";
import { useChatHistory } from "@/lib/use-chat-history";
import { renderMarkdown } from "@/lib/markdown";
import type { Citation, LegalDomain } from "@/types/api";
import { cn } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  domain?: LegalDomain;
  isFallback?: boolean;
  isStreaming?: boolean;
  question?: string; // associated user question
  feedback?: "up" | "down" | null;
  timestamp: number;
}

const STATIC_SUGGESTIONS = [
  "ما هي شروط توثيق عقد إيجار بالشهر العقاري؟",
  "هل يحق للمالك طرد المستأجر بعد انتهاء مدة العقد مباشرة؟",
  "ما هي عقوبة النصب والاحتيال الإلكتروني بالقانون المصري؟",
  "شروط استحقاق مكافأة نهاية الخدمة طبقاً لقانون العمل الجديد",
];

// Helper to check prefers-reduced-motion
const getPrefersReducedMotion = () => {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchHistoryQuery, setSearchHistoryQuery] = useState("");
  const [characterCount, setCharacterCount] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  
  // Custom states for simulated/detailed thinking progress
  const [thinkingStep, setThinkingStep] = useState(0);
  const [showThinking, setShowThinking] = useState(false);

  // Suggested follow-up questions state
  const [currentFollowUps, setCurrentFollowUps] = useState<string[]>([]);

  // Abort controller ref for client-side generation cancellation
  const abortControllerRef = useRef<boolean>(false);

  const { theme, toggleTheme } = useTheme();
  const { addEntry, history, clearHistory } = useChatHistory();
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const prefersReduced = getPrefersReducedMotion();

  // Show status toasts
  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Scroll messages to bottom safely
  const scrollToBottom = React.useCallback(() => {
    if (prefersReduced) {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
      return;
    }
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
  }, [prefersReduced]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, showThinking, thinkingStep, scrollToBottom]);

  // Keep track of characters count
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    if (val.length <= 1000) {
      setInput(val);
      setCharacterCount(val.length);
    }
  };

  // Auto-resize input textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
    }
  }, [input]);

  // Stop current active streaming response
  const handleStopGeneration = () => {
    if (loading) {
      abortControllerRef.current = true;
      setLoading(false);
      setShowThinking(false);
      triggerToast("تم إيقاف توليد الإجابة");
    }
  };

  // Start a completely new chat session
  const startNewConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    setCurrentFollowUps([]);
    setInput("");
    setCharacterCount(0);
    setShowThinking(false);
    triggerToast("بدء محادثة جديدة");
  };

  // Load a conversation from locally saved history list
  const loadHistoryEntry = (entry: any) => {
    startNewConversation();
    const userMsg: Message = {
      id: `history-u-${entry.id}`,
      role: "user",
      content: entry.question,
      timestamp: entry.timestamp - 1000,
    };
    const assistantMsg: Message = {
      id: entry.id,
      role: "assistant",
      content: entry.answer,
      citations: entry.citations,
      domain: entry.domain,
      isFallback: entry.is_fallback,
      feedback: null,
      timestamp: entry.timestamp,
    };
    setMessages([userMsg, assistantMsg]);
    setConversationId(entry.id);
    
    // Generate follow-ups based on the loaded domain/history
    setCurrentFollowUps(generateFollowUpQuestions(entry.question, entry.answer));
    triggerToast("تم تحميل الاستشارة من السجل");
  };

  // Core messaging dispatcher
  const sendMessage = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;

    setInput("");
    setCharacterCount(0);
    abortControllerRef.current = false;
    setCurrentFollowUps([]);

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: Date.now(),
    };
    
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [...prev, userMsg]);
    
    // Show thinking phase first
    setLoading(true);
    setShowThinking(true);
    setThinkingStep(0);

    // Dynamic step animation delays
    const stepTimes = [600, 1200, 1800, 2400];
    for (let i = 0; i < stepTimes.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, prefersReduced ? 100 : stepTimes[i] - (i > 0 ? stepTimes[i-1] : 0)));
      if (abortControllerRef.current) return;
      setThinkingStep(i + 1);
    }

    setShowThinking(false);

    // Insert placeholders for response
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        isStreaming: true,
        question,
        timestamp: Date.now(),
      },
    ]);

    let fullAnswer = "";

    await streamChatMessage(
      question,
      conversationId,
      (token) => {
        if (abortControllerRef.current) return;
        fullAnswer += token;
        setMessages((prev) =>
          prev.map((m) => (m.id === assistantId ? { ...m, content: fullAnswer } : m))
        );
      },
      (data) => {
        if (abortControllerRef.current) return;
        setConversationId(data.conversation_id);
        const finalAnswer = data.final_answer ?? fullAnswer;
        const citations: Citation[] = data.citations ?? [];
        
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: finalAnswer,
                  citations,
                  isFallback: data.is_fallback,
                  isStreaming: false,
                  feedback: null,
                }
              : m
          )
        );

        // Add to local history hook
        addEntry({
          id: assistantId,
          question,
          answer: finalAnswer,
          domain: data.domain || "unknown",
          citations,
          is_fallback: !!data.is_fallback,
          timestamp: Date.now(),
        });

        // Setup suggested follow-ups
        setCurrentFollowUps(generateFollowUpQuestions(question, finalAnswer));
        setLoading(false);
      },
      (errorMsg) => {
        if (abortControllerRef.current) return;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: errorMsg, isFallback: true, isStreaming: false, feedback: null }
              : m
          )
        );
        setLoading(false);
      }
    );
  };

  // Generate domain-relevant follow ups
  const generateFollowUpQuestions = (q: string, a: string) => {
    if (q.includes("إيجار") || a.includes("إيجار") || a.includes("مؤجر") || a.includes("مستأجر")) {
      return [
        "ما هي أقصى مدة قانونية لعقد الإيجار المدني؟",
        "هل تبطل شروط الصيانة الاستثنائية المتفق عليها؟",
        "كيفية إثبات سداد الأجرة في حال رفض المؤجر الاستلام؟",
      ];
    }
    if (q.includes("عمل") || a.includes("عمل") || a.includes("عامل") || a.includes("صاحب العمل")) {
      return [
        "هل يجوز مد فترة الاختبار لأكثر من ٣ أشهر؟",
        "ما هي شروط الفصل التعسفي والتعويض المستحق؟",
        "كيف تحسب ساعات العمل الإضافية طبقاً للقانون المصري؟",
      ];
    }
    return [
      "ما هي الإجراءات القانونية اللازمة لرفع دعوى قضائية؟",
      "هل يجب وجود محامٍ مرخص لمتابعة هذه الحالة بالشهر العقاري؟",
      "كيف تختلف العقوبة إذا تم ارتكاب الفعل بشكل جماعي؟",
    ];
  };

  // Handle message rating feedback
  const handleFeedback = async (msgId: string, isCorrect: boolean) => {
    const msg = messages.find((m) => m.id === msgId);
    if (!msg || msg.feedback !== null) return;

    setMessages((prev) =>
      prev.map((m) =>
        m.id === msgId ? { ...m, feedback: isCorrect ? "up" : "down" } : m
      )
    );

    if (conversationId && msg.question) {
      await submitFeedback(conversationId, msg.question, msg.content, isCorrect);
      triggerToast("نشكرك على إرسال تقييمك");
    }
  };

  // Copy text utility
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    triggerToast("تم نسخ النص بنجاح");
  };

  // Share conversation utility
  const shareConversation = () => {
    const shareUrl = typeof window !== "undefined" ? window.location.href : "";
    navigator.clipboard.writeText(shareUrl);
    triggerToast("تم نسخ رابط المحادثة لمشاركته");
  };

  // Mock Export wrappers
  const triggerExport = (format: "pdf" | "docx") => {
    triggerToast(`جاري تصدير المحادثة بصيغة ${format.toUpperCase()}...`);
  };

  // Filter history based on search query
  const filteredHistory = history.filter(
    (item) =>
      item.question.toLowerCase().includes(searchHistoryQuery.toLowerCase()) ||
      item.answer.toLowerCase().includes(searchHistoryQuery.toLowerCase())
  );

  return (
    <div className="flex flex-1 h-screen-dvh overflow-hidden relative font-sans text-foreground bg-background">
      {/* Toast Notification Container */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="absolute top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2 bg-slate-900 text-slate-100 dark:bg-slate-800 rounded-xl shadow-lg border border-slate-800 text-xs sm:text-sm font-semibold flex items-center gap-2"
          >
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 1. SIDEBAR (RTL Right side) */}
      <aside
        className={cn(
          "h-full shrink-0 border-l border-border bg-card/45 backdrop-blur-md flex flex-col transition-all duration-300 z-30",
          sidebarOpen ? "w-80" : "w-0 overflow-hidden border-l-0"
        )}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-border flex items-center justify-between gap-2 shrink-0">
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-accent" />
            <span className="font-bold text-sm">سجل الاستشارات</span>
          </div>
          <Button
            onClick={startNewConversation}
            variant="outline"
            size="sm"
            className="rounded-xl border-accent/20 bg-accent/5 text-accent font-bold hover:bg-accent/10 gap-1"
          >
            <Plus className="h-3.5 w-3.5" />
            جديدة
          </Button>
        </div>

        {/* Sidebar Search */}
        <div className="p-3 border-b border-border/60 shrink-0">
          <div className="relative">
            <Search className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchHistoryQuery}
              onChange={(e) => setSearchHistoryQuery(e.target.value)}
              placeholder="ابحث في سجل المحادثات..."
              className="w-full h-9 rounded-lg border border-border bg-background/50 pr-9 pl-3 text-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
            />
          </div>
        </div>

        {/* Sidebar List */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
          {filteredHistory.length === 0 ? (
            <div className="text-center py-8 text-xs text-muted-foreground px-4">
              {searchHistoryQuery ? "لا توجد نتائج مطابقة لجهود البحث" : "لا يوجد سجل استشارات حتى الآن."}
            </div>
          ) : (
            filteredHistory.map((item) => (
              <button
                key={item.id}
                onClick={() => loadHistoryEntry(item)}
                className="w-full text-right p-3 rounded-xl border border-transparent hover:border-border hover:bg-muted/40 transition-all flex flex-col gap-1 text-xs"
              >
                <div className="flex items-center justify-between gap-1 w-full text-[10px] text-muted-foreground font-semibold">
                  <span>{new Date(item.timestamp).toLocaleDateString("ar-EG")}</span>
                  <Badge variant="outline" className="scale-90 opacity-80 text-[9px] px-1 py-0.5">
                    {item.domain === "labor_law" ? "عمل" : item.domain === "tenancy_law" ? "إيجار" : "عام"}
                  </Badge>
                </div>
                <p className="font-bold text-foreground line-clamp-1 truncate leading-snug">
                  {item.question}
                </p>
                <p className="text-muted-foreground line-clamp-1 truncate">
                  {item.answer}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Sidebar Footer Controls */}
        <div className="p-3 border-t border-border shrink-0 flex items-center justify-between bg-muted/20">
          <Button
            onClick={clearHistory}
            variant="ghost"
            size="sm"
            disabled={history.length === 0}
            className="text-xs text-destructive hover:bg-destructive/10 hover:text-destructive rounded-xl"
          >
            مسح الكل
          </Button>
          <span className="text-[10px] text-muted-foreground font-medium">
            مجموع المحفوظات: {history.length}
          </span>
        </div>
      </aside>

      {/* 2. MAIN CHAT AREA */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-background relative z-10">
        
        {/* Chat Area Top Navbar Header */}
        <header className="h-16 border-b border-border flex items-center justify-between px-4 sm:px-6 shrink-0 bg-card/25 backdrop-blur-sm relative z-20">
          <div className="flex items-center gap-3">
            {/* Sidebar toggle control */}
            <Button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              variant="outline"
              size="icon"
              className="rounded-xl h-10 w-10 border-border/80"
              aria-label={sidebarOpen ? "إخفاء القائمة الجانبية" : "إظهار القائمة الجانبية"}
            >
              <Sliders className="h-4 w-4 text-muted-foreground" />
            </Button>

            <div className="flex items-center gap-2">
              <div className="relative h-9 w-9 rounded-xl overflow-hidden bg-primary/5 flex items-center justify-center border border-border/60">
                <Image
                  src="/bayyinah-logo.png"
                  alt="بيّنة"
                  width={24}
                  height={24}
                  className="object-contain"
                />
              </div>
              <div>
                <h2 className="font-bold text-sm sm:text-base leading-none flex items-center gap-1.5">
                  بينة المساعد الذكي
                  <span className="inline-block h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                </h2>
                <p className="text-[10px] text-muted-foreground mt-0.5 font-medium">
                  مدعوم بالتشريع والدستور المصري
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Dark Mode toggle */}
            <Button
              onClick={toggleTheme}
              variant="outline"
              size="icon"
              className="rounded-xl h-10 w-10 border-border/80"
              aria-label="تبديل مظهر الإضاءة"
            >
              {theme === "light" ? <Moon className="h-4.5 w-4.5" /> : <Sun className="h-4.5 w-4.5" />}
            </Button>
          </div>
        </header>

        {/* Scrollable conversation window */}
        <div
          ref={scrollRef}
          role="log"
          aria-label="سجل المحادثة"
          aria-live="polite"
          className="flex-1 overflow-y-auto scrollbar-thin px-4 sm:px-6 py-6 space-y-6"
        >
          {messages.length === 0 ? (
            /* Welcome State / Empty State */
            <div className="max-w-2xl mx-auto py-12 text-center space-y-8">
              <div className="space-y-4">
                <motion.div
                  initial={prefersReduced ? {} : { scale: 0.9, opacity: 0 }}
                  animate={prefersReduced ? {} : { scale: 1, opacity: 1 }}
                  transition={{ duration: 0.5 }}
                  className="mx-auto h-20 w-20 rounded-3xl bg-accent/5 border border-accent/25 flex items-center justify-center"
                >
                  <Sparkles className="h-10 w-10 text-accent" />
                </motion.div>
                <div className="space-y-2">
                  <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                    أهلاً بك في منصة بينة القانونية
                  </h1>
                  <p className="text-sm text-muted-foreground max-w-lg mx-auto leading-relaxed">
                    مستشارك القانوني الذكي المؤهل للإجابة الفورية وتأصيل العقود بموجب تشريعات جمهورية مصر العربية الرسمية.
                  </p>
                </div>
              </div>

              {/* Grid of suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-xl mx-auto pt-4 text-right">
                {STATIC_SUGGESTIONS.map((s, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(s)}
                    className="p-4 rounded-xl border border-border/60 bg-card hover:border-accent/40 hover:bg-accent/5 transition-all text-xs font-semibold leading-relaxed shadow-sm hover:shadow-md"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Message Feed */
            <div className="max-w-3xl mx-auto space-y-6">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={prefersReduced ? {} : { opacity: 0, y: 15 }}
                  animate={prefersReduced ? {} : { opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    "flex flex-col gap-2 w-full",
                    m.role === "user" ? "items-start" : "items-end"
                  )}
                >
                  {/* Chat bubble wrapper */}
                  <div
                    className={cn(
                      "w-full max-w-[85%] rounded-2xl p-5 shadow-sm leading-relaxed border relative",
                      m.role === "user"
                        ? "bg-primary border-primary text-primary-foreground select-text"
                        : "bg-card border-border text-foreground select-text"
                    )}
                  >
                    {/* Timestamp */}
                    <span
                      className={cn(
                        "absolute top-2 left-3 text-[9px] opacity-60 font-semibold select-none",
                        m.role === "user" ? "text-primary-foreground" : "text-muted-foreground"
                      )}
                    >
                      {new Date(m.timestamp).toLocaleTimeString("ar-EG", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>

                    {/* Legal Assistant Fallback Banner */}
                    {m.isFallback && m.role === "assistant" && (
                      <div className="flex items-center gap-2 mb-3 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-600 dark:text-amber-400 text-xs font-bold w-fit">
                        <AlertTriangle className="h-4 w-4 shrink-0" />
                        <span>إجابة احتياطية – خارج النطاق التشريعي المغلق</span>
                      </div>
                    )}

                    {/* Domain badge */}
                    {m.role === "assistant" && m.domain && m.domain !== "unknown" && (
                      <Badge variant="outline" className="mb-3 border-accent/30 bg-accent/5 text-accent font-bold">
                        {m.domain === "labor_law"
                          ? "قانون العمل المصري"
                          : m.domain === "tenancy_law"
                          ? "قوانين الإيجار المدنية"
                          : "تشريعات عامة"}
                      </Badge>
                    )}

                    {/* Response body */}
                    <div className="text-sm space-y-2">
                      {m.role === "user" ? (
                        <p className="whitespace-pre-wrap">{m.content}</p>
                      ) : (
                        renderMarkdown(m.content)
                      )}
                      {m.isStreaming && m.content && (
                        <span className="inline-block w-1.5 h-4 bg-current animate-pulse mr-1 align-middle" />
                      )}
                    </div>

                    {/* Sources Collapsible Card */}
                    {m.role === "assistant" && m.citations && m.citations.length > 0 && (
                      <div className="mt-4 border-t border-border/40 pt-4">
                        <details className="group space-y-3">
                          <summary className="list-none flex items-center justify-between text-xs font-bold text-accent cursor-pointer select-none">
                            <span className="flex items-center gap-1.5">
                              <BookOpen className="h-3.5 w-3.5" />
                              المصادر القانونية والدستورية المعتمدة ({m.citations.length})
                            </span>
                            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                          </summary>

                          <div className="pt-2 space-y-2.5">
                            {m.citations.map((c, cIdx) => (
                              <div
                                key={c.chunk_id + cIdx}
                                className="p-3.5 rounded-xl border border-border/80 bg-muted/40 text-xs leading-relaxed space-y-2 relative overflow-hidden"
                              >
                                <div className="absolute top-0 right-0 h-full w-1.5 bg-accent" />
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex items-center gap-2">
                                    <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-accent/15 text-accent font-bold text-[10px]">
                                      {c.article_number || cIdx + 1}
                                    </div>
                                    <span className="font-bold text-foreground">
                                      {c.article_number ? `المادة ${c.article_number}` : `سند تشريعي ${cIdx + 1}`}
                                    </span>
                                  </div>
                                  <Badge variant="outline" className="text-[9px] px-1 py-0 border-accent/20 text-accent bg-accent/5 font-semibold">
                                    مطابقة: {(c.score * 100).toFixed(0)}%
                                  </Badge>
                                </div>

                                <div className="text-muted-foreground font-semibold text-[10px]">
                                  {[
                                    c.law_name,
                                    c.law_number && `رقم ${c.law_number}`,
                                    c.law_year && `لسنة ${c.law_year}`,
                                  ]
                                    .filter(Boolean)
                                    .join(" ")}
                                </div>
                                <p className="text-[11px] text-foreground/90 font-medium leading-relaxed bg-background/50 p-2.5 rounded-lg border border-border/40">
                                  {c.text}
                                </p>
                              </div>
                            ))}
                          </div>
                        </details>
                      </div>
                    )}
                  </div>

                  {/* Actions / Feedback below Assistant responses */}
                  {m.role === "assistant" && !m.isStreaming && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-1 text-xs text-muted-foreground">
                      <Button
                        onClick={() => copyToClipboard(m.content)}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-muted"
                        title="نسخ الإجابة"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                      
                      {/* Feedback buttons */}
                      {m.feedback === null ? (
                        <>
                          <Button
                            onClick={() => handleFeedback(m.id, true)}
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg hover:bg-muted hover:text-emerald-600"
                            title="إجابة دقيقة"
                          >
                            <ThumbsUp className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            onClick={() => handleFeedback(m.id, false)}
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 rounded-lg hover:bg-muted hover:text-destructive"
                            title="غير دقيقة"
                          >
                            <ThumbsDown className="h-3.5 w-3.5" />
                          </Button>
                        </>
                      ) : (
                        <span className={cn(
                          "px-2 py-0.5 rounded-lg text-[10px] font-semibold border flex items-center gap-1 select-none",
                          m.feedback === "up" 
                            ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-600 dark:text-emerald-400" 
                            : "border-destructive/20 bg-destructive/5 text-destructive"
                        )}>
                          {m.feedback === "up" ? "نشكرك على التقييم الإيجابي" : "شكراً لملاحظتك"}
                        </span>
                      )}

                      <Button
                        onClick={() => sendMessage(m.question)}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-muted"
                        title="إعادة التوليد"
                      >
                        <RotateCcw className="h-3.5 w-3.5" />
                      </Button>

                      <Button
                        onClick={shareConversation}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-muted"
                        title="مشاركة"
                      >
                        <Share2 className="h-3.5 w-3.5" />
                      </Button>

                      {/* PDF / DOCX Export */}
                      <Button
                        onClick={() => triggerExport("pdf")}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-muted"
                        title="تصدير كـ PDF"
                      >
                        <FileDown className="h-3.5 w-3.5" />
                      </Button>

                      <Button
                        onClick={() => triggerExport("docx")}
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 rounded-lg hover:bg-muted"
                        title="تصدير كـ DOCX"
                      >
                        <FileText className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Thinking State Panel */}
              {showThinking && (
                <div className="flex flex-col gap-2 items-end w-full">
                  <div className="w-full max-w-[85%] rounded-2xl p-5 shadow-sm border bg-muted/30 border-border/80 flex flex-col gap-4 text-sm">
                    <div className="flex items-center gap-3">
                      <Loader2 className="h-4.5 w-4.5 animate-spin text-accent" />
                      <span className="font-bold text-foreground/80">المساعد الذكي يفكر...</span>
                    </div>
                    
                    {/* Stepper details */}
                    <div className="space-y-2.5 border-r-2 border-border pr-4">
                      {[
                        "البحث عن المستندات والقوانين ذات الصلة بقاعدة البيانات...",
                        "تحليل نصوص المواد وتحديد الأحكام القانونية المناسبة...",
                        "التحقق المرجعي وصياغة التقرير الاستشاري النهائي...",
                        "إنشاء وتنقيح الإجابة القانونية الموثقة...",
                      ].map((step, idx) => {
                        const isDone = thinkingStep > idx;
                        const isCurrent = thinkingStep === idx;
                        return (
                          <div
                            key={idx}
                            className={cn(
                              "flex items-center gap-2 text-xs font-semibold transition-colors duration-200",
                              isDone ? "text-emerald-600 dark:text-emerald-400" : isCurrent ? "text-accent" : "text-muted-foreground/60"
                            )}
                          >
                            {isDone ? (
                              <CheckCircle2 className="h-4 w-4 shrink-0" />
                            ) : isCurrent ? (
                              <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                            ) : (
                              <div className="h-2 w-2 rounded-full bg-current shrink-0 mr-1" />
                            )}
                            <span>{step}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Suggested follow-up list */}
        {messages.length > 0 && currentFollowUps.length > 0 && !loading && (
          <div className="px-4 sm:px-6 py-2 shrink-0 bg-background border-t border-border/40">
            <div className="max-w-3xl mx-auto flex flex-col gap-2">
              <span className="text-[10px] text-muted-foreground font-bold flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-accent" />
                الأسئلة المقترحة لمتابعة استشارتك:
              </span>
              <div className="flex flex-wrap gap-2 justify-start pb-2">
                {currentFollowUps.map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => sendMessage(q)}
                    className="px-3.5 py-2 text-xs font-semibold text-accent rounded-xl border border-accent/25 bg-accent/5 hover:bg-accent/10 hover:border-accent/40 transition-all text-right shadow-sm"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Input box block */}
        <div className="border-t border-border px-4 py-4 shrink-0 bg-card/45 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto">
            
            {/* Input area border container */}
            <div className="rounded-2xl border border-border bg-background focus-within:ring-2 focus-within:ring-accent/40 focus-within:border-accent/40 overflow-hidden transition-all shadow-sm">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="اكتب سؤالك أو استشارتك القانونية هنا..."
                className="w-full min-h-[50px] max-h-[180px] py-3.5 px-4 bg-transparent border-0 focus-visible:ring-0 focus-visible:border-0 rounded-none shadow-none text-sm resize-none"
                aria-label="سؤالك القانوني"
                disabled={loading}
              />

              {/* Utility tray inside input component */}
              <div className="flex items-center justify-between px-3 py-2 bg-muted/20 border-t border-border/40 shrink-0">
                <div className="flex items-center gap-1.5">
                  {/* UI placeholder actions */}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 rounded-lg text-muted-foreground hover:bg-muted"
                    title="أرفق ملف مستند"
                    onClick={() => triggerToast("مرفقات الملف متاحة في نافذة تحليل العقود")}
                  >
                    <Paperclip className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 rounded-lg text-muted-foreground hover:bg-muted"
                    title="الإدخال الصوتي"
                    onClick={() => triggerToast("الإدخال الصوتي غير متاح في المتصفح حالياً")}
                  >
                    <Mic className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex items-center gap-3">
                  {/* Character Counter */}
                  <span className="text-[10px] text-muted-foreground/60 font-semibold select-none">
                    {characterCount} / 1000
                  </span>

                  {/* Dynamic Send / Stop trigger */}
                  {loading ? (
                    <Button
                      onClick={handleStopGeneration}
                      variant="destructive"
                      size="sm"
                      className="rounded-lg h-8 gap-1.5 px-3 font-semibold text-xs"
                      title="إيقاف التوليد"
                    >
                      <Square className="h-3 w-3 fill-current" />
                      إيقاف
                    </Button>
                  ) : (
                    <Button
                      onClick={() => sendMessage()}
                      disabled={!input.trim()}
                      size="sm"
                      className="rounded-lg h-8 gap-1.5 px-3 font-semibold text-xs bg-primary text-primary-foreground shadow"
                      title="إرسال"
                    >
                      <Send className="h-3 w-3 shrink-0" />
                      إرسال
                    </Button>
                  )}
                </div>
              </div>
            </div>
            
            {/* Disclaimer disclaimer */}
            <p className="text-center text-[10px] text-muted-foreground/80 mt-2 leading-relaxed">
              الإجابات صادرة آلياً ولا تعتبر بديلاً عن الاستشارة القانونية الرسمية مع محامٍ مرخص.
            </p>
          </div>
        </div>

      </main>
    </div>
  );
}
