"use client";

import React, { useRef, useState, useEffect } from "react";
import {
  FileSearch,
  Upload,
  FileText,
  X,
  CheckCircle2,
  AlertTriangle,
  FileWarning,
  Lightbulb,
  Download,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  Filter,
  ArrowRight,
  Clock,
  Calendar,
  Building2,
  DollarSign,
  Scale,
  RefreshCw,
  Loader2,
  ShieldCheck,
  FileDown
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge, RISK_LABELS_AR } from "@/components/ui/badge";
import { useTheme } from "@/components/theme-provider";
import { analyzeContract, ApiError } from "@/lib/api";
import type { ContractAnalysisResponse, RiskLevel, ClauseAnalysis, MissingClause } from "@/types/api";
import { cn } from "@/lib/utils";

// Check reduced motion
const getPrefersReducedMotion = () => {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
};

// Simulated processing steps
const TIMELINE_STEPS = [
  "رفع المستند إلى الخادم الآمن...",
  "قراءة صفحات المستند واستخراج النصوص...",
  "تقسيم النصوص إلى مقاطع سياقية (Chunks)...",
  "التعرف على البنود والالتزامات التعاقدية...",
  "البحث في القوانين والقرارات المصرية ذات الصلة...",
  "تحليل المخاطر القانونية والشرط الجزائية...",
  "إنشاء الملخص التنفيذي للأطراف والتواريخ...",
  "إعداد وصياغة التقرير النهائي بالذكاء الاصطناعي...",
];

export default function ContractAnalysisPage() {
  const [file, setFile] = useState<File | null>(null);
  const [fileProgress, setFileProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [result, setResult] = useState<ContractAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Filters state
  const [selectedRiskFilter, setSelectedRiskFilter] = useState<string>("all");
  const [selectedCategoryFilter, setSelectedCategoryFilter] = useState<string>("all");

  // Expandable clauses list
  const [expandedClauses, setExpandedClauses] = useState<Record<string, boolean>>({});

  // Mobile layout state (Accordion panels)
  const [mobileActivePanel, setMobileActivePanel] = useState<string>("summary");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { theme } = useTheme();
  const prefersReduced = getPrefersReducedMotion();

  const triggerToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  // Simulate file upload progress
  const handleFileSelect = (f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "docx" && ext !== "txt") {
      setError("يُرجى رفع ملف بصيغة PDF أو DOCX أو TXT فقط.");
      return;
    }
    if (f.size > 15 * 1024 * 1024) {
      setError("حجم الملف يتجاوز الحد الأقصى المسموح به (15 ميجابايت).");
      return;
    }

    setError(null);
    setFile(f);
    setIsUploading(true);
    setFileProgress(0);

    const interval = setInterval(() => {
      setFileProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          triggerToast("تم رفع الملف بنجاح");
          return 100;
        }
        return prev + 20;
      });
    }, 150);
  };

  // Start analysis trigger
  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setProcessingStep(0);

    // Simulate timeline steps sequentially
    const stepDelay = prefersReduced ? 150 : 500;
    for (let i = 0; i < TIMELINE_STEPS.length; i++) {
      await new Promise((resolve) => setTimeout(resolve, stepDelay));
      setProcessingStep(i + 1);
    }

    try {
      const data = await analyzeContract(file);
      setResult(data);
      // Auto expand first 2 clauses
      if (data.clauses.length > 0) {
        setExpandedClauses({
          [data.clauses[0].clause_id]: true,
          ...(data.clauses[1] ? { [data.clauses[1].clause_id]: true } : {}),
        });
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "حدث خطأ غير متوقع أثناء تحليل العقد. حاول مرة أخرى.");
    } finally {
      setLoading(false);
    }
  };

  // Reset uploader state
  const removeFile = () => {
    setFile(null);
    setFileProgress(0);
    setIsUploading(false);
    setResult(null);
    setError(null);
  };

  // Format file sizes helper
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Toggle single clause card details
  const toggleClause = (id: string) => {
    setExpandedClauses((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  // Dynamic filter function
  const getFilteredClauses = () => {
    if (!result) return [];
    return result.clauses.filter((c) => {
      // 1. Risk Filter
      if (selectedRiskFilter !== "all" && c.risk_level !== selectedRiskFilter) {
        return false;
      }
      // 2. Category / Domain Filter
      if (selectedCategoryFilter !== "all") {
        const type = c.clause_type.toLowerCase();
        if (selectedCategoryFilter === "financial" && !/مالي|دفع|سداد|قيمة|مبلغ|أجر/i.test(type)) return false;
        if (selectedCategoryFilter === "employment" && !/عمل|وظيفة|عامل|صاحب العمل|فسخ|إنهاء/i.test(type)) return false;
        if (selectedCategoryFilter === "commercial" && !/تجاري|بيع|شراء|إيجار|توريد/i.test(type)) return false;
        if (selectedCategoryFilter === "government" && !/حكومي|ترخيص|ضريبة|رسمي/i.test(type)) return false;
      }
      return true;
    });
  };

  // Risk Gauge Helpers
  const getRiskScorePercentage = (level: RiskLevel) => {
    switch (level) {
      case "critical": return 92;
      case "high": return 76;
      case "medium": return 48;
      default: return 18;
    }
  };

  const getRiskColor = (level: RiskLevel) => {
    switch (level) {
      case "critical": return "text-red-500 bg-red-500";
      case "high": return "text-orange-500 bg-orange-500";
      case "medium": return "text-amber-500 bg-amber-500";
      default: return "text-emerald-500 bg-emerald-500";
    }
  };

  // Export callbacks
  const handleExport = (format: string) => {
    triggerToast(`جاري تصدير التقرير بصيغة ${format.toUpperCase()}...`);
  };

  // Check if a clause is matching category filters
  const clauses = getFilteredClauses();

  return (
    <div className="min-h-screen pb-24 bg-background text-foreground font-sans relative">
      {/* Dynamic status toast notification */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-4 left-1/2 -translate-x-1/2 z-50 px-4 py-2.5 bg-slate-900 text-slate-100 dark:bg-slate-800 rounded-xl shadow-lg border border-slate-800 text-sm font-semibold flex items-center gap-2"
          >
            <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Header Container */}
      <header className="border-b border-border bg-card/30 py-6 px-4 sm:px-6 md:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold flex items-center gap-2">
              <FileSearch className="h-6 w-6 text-primary shrink-0" aria-hidden="true" />
              مساحة تحليل العقود الذكية
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1 leading-relaxed">
              ارفع عقودك بصيغ (PDF, DOCX, TXT) للحصول على تدقيق وتأصيل فوري للثغرات والمخاطر ومطابقتها بالقوانين المصرية.
            </p>
          </div>
          {result && (
            <div className="flex items-center gap-2 shrink-0 self-start md:self-auto">
              <Button onClick={removeFile} variant="outline" size="sm" className="rounded-xl">
                تحليل ملف جديد
              </Button>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-3 sm:px-4 md:px-6 lg:px-8 py-8">
        
        {/* ========================================================
            EMPTY STATE & INITIAL LOADING VIEWS
            ======================================================== */}
        {!result && !loading && (
          <div className="max-w-3xl mx-auto text-center space-y-8 py-10">
            <div className="space-y-3">
              <div className="mx-auto h-16 w-16 rounded-2xl bg-primary/5 border border-primary/20 flex items-center justify-center">
                <Upload className="h-8 w-8 text-primary" />
              </div>
              <h2 className="text-lg font-bold">ابدأ برفع عقد لتحليله</h2>
              <p className="text-sm text-muted-foreground max-w-md mx-auto leading-relaxed">
                يقوم محرك الذكاء الاصطناعي باستخراج البنود وتحديد أطراف العقد وتواريخه، والكشف عن أي مخاطر أو شروط مجحفة.
              </p>
            </div>

            {/* Dropzone Container */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                if (e.dataTransfer.files?.[0]) {
                  handleFileSelect(e.dataTransfer.files[0]);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-2xl p-8 sm:p-12 text-center cursor-pointer transition-all flex flex-col items-center gap-4",
                dragOver ? "border-accent bg-accent/5" : "border-border bg-card/40 hover:bg-card/85",
                isUploading && "pointer-events-none opacity-80"
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
              />

              {file ? (
                /* File selected and progress showing */
                <div className="w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
                  <div className="flex items-center gap-3 p-4 rounded-xl border bg-background text-right">
                    <FileText className="h-10 w-10 text-primary shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-sm truncate">{file.name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{formatFileSize(file.size)}</p>
                    </div>
                    <Button onClick={removeFile} variant="ghost" size="icon" className="rounded-full h-8 w-8 hover:bg-destructive/10 hover:text-destructive">
                      <X className="h-4 w-4" />
                    </Button>
                  </div>

                  {isUploading ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-xs font-semibold">
                        <span className="text-muted-foreground">جاري الرفع...</span>
                        <span>{fileProgress}%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-primary transition-all duration-150"
                          style={{ width: `${fileProgress}%` }}
                        />
                      </div>
                    </div>
                  ) : (
                    <Button onClick={handleAnalyze} className="w-full rounded-xl py-6 font-bold text-base shadow-md">
                      ابدأ تحليل العقد الآن
                    </Button>
                  )}
                </div>
              ) : (
                /* Empty dropzone state */
                <>
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                    <Upload className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-bold text-sm">اسحب ملف العقد هنا أو اضغط للتصفح</p>
                    <p className="text-xs text-muted-foreground mt-1.5">
                      الصيغ المدعومة: PDF, DOCX, TXT (الحد الأقصى ١٥ ميجابايت)
                    </p>
                  </div>
                </>
              )}
            </div>

            {error && (
              <div className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive flex items-center gap-2 justify-center">
                <AlertTriangle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            )}
          </div>
        )}

        {/* ========================================================
            AI PROCESSING / LOADING TIMELINE
            ======================================================== */}
        {loading && (
          <div className="max-w-2xl mx-auto py-12 space-y-8">
            <div className="text-center space-y-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto" />
              <h2 className="text-lg font-bold">جاري تحليل مستند العقد بالذكاء الاصطناعي</h2>
              <p className="text-xs text-muted-foreground">
                يستغرق هذا الإجراء بضع ثوانٍ؛ يرجى عدم إغلاق النافذة.
              </p>
            </div>

            {/* Steps Timeline Card */}
            <Card className="border border-border/80 bg-card/30">
              <CardContent className="p-6 space-y-4">
                {TIMELINE_STEPS.map((step, idx) => {
                  const isDone = processingStep > idx;
                  const isCurrent = processingStep === idx;
                  return (
                    <div
                      key={idx}
                      className={cn(
                        "flex items-center gap-3 text-sm font-semibold transition-colors duration-200",
                        isDone ? "text-emerald-600 dark:text-emerald-400" : isCurrent ? "text-primary font-bold" : "text-muted-foreground/50"
                      )}
                    >
                      {isDone ? (
                        <CheckCircle2 className="h-5 w-5 shrink-0" />
                      ) : isCurrent ? (
                        <Loader2 className="h-5 w-5 shrink-0 animate-spin" />
                      ) : (
                        <div className="h-2.5 w-2.5 rounded-full bg-current shrink-0 mr-1.5 ml-1" />
                      )}
                      <span>{step}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        )}

        {/* ========================================================
            DESKTOP WORKSPACE LAYOUT (3 columns)
            ======================================================== */}
        {result && (
          <div className="hidden lg:grid grid-cols-12 gap-8 items-start">
            
            {/* Column 1: Upload Panel (Right column in RTL, col-span-3) */}
            <aside className="col-span-3 space-y-6">
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-sm font-bold">الملف الجاري تحليله</CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-4">
                  <div className="p-3.5 rounded-xl border bg-muted/30 flex items-start gap-3">
                    <FileText className="h-9 w-9 text-primary shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-xs truncate text-foreground">{result.filename}</p>
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {file ? formatFileSize(file.size) : "حجم غير معروف"}
                      </p>
                    </div>
                  </div>
                  <Button onClick={removeFile} variant="outline" className="w-full text-xs h-9 rounded-lg">
                    إزالة الملف
                  </Button>
                </CardContent>
              </Card>

              {/* Legal Standards Card */}
              <Card className="border border-border/80 bg-card/60">
                <CardContent className="p-4 space-y-3">
                  <h4 className="font-bold text-xs text-foreground flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-emerald-500" />
                    التوثيق والامتثال
                  </h4>
                  <p className="text-[11px] text-muted-foreground leading-relaxed">
                    تمت مطابقة بنود هذا العقد مع أحدث التشريعات المصرية ذات الصلة مثل القانون المدني رقم ١٣١ لسنة ١٩٤٨ وقانون العمل رقم ١٢ لسنة ٢٠٠٣.
                  </p>
                </CardContent>
              </Card>
            </aside>

            {/* Column 2: Analysis Workspace (Middle column, col-span-6) */}
            <section className="col-span-6 space-y-6">
              
              {/* Executive Summary */}
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-base font-bold">الملخص التنفيذي للعقد</CardTitle>
                </CardHeader>
                <CardContent className="p-5 space-y-4">
                  <p className="text-sm leading-relaxed text-foreground/90">{result.summary.overview_ar}</p>
                  
                  {/* Grid fields */}
                  <div className="grid grid-cols-2 gap-4 text-xs border-t border-border/40 pt-4">
                    <div className="space-y-1">
                      <span className="text-muted-foreground font-semibold">نوع العقد:</span>
                      <p className="font-bold text-foreground">{result.summary.contract_type || "غير محدد"}</p>
                    </div>
                    <div className="space-y-1">
                      <span className="text-muted-foreground font-semibold">المدة الزمنية:</span>
                      <p className="font-bold text-foreground">{result.summary.duration || "غير محددة في العقد"}</p>
                    </div>
                    <div className="space-y-1">
                      <span className="text-muted-foreground font-semibold font-sans">عدد البنود المكتشفة:</span>
                      <p className="font-bold text-foreground">{result.summary.total_clauses} بند</p>
                    </div>
                    <div className="space-y-1">
                      <span className="text-muted-foreground font-semibold">التصنيف والالتزام:</span>
                      <p className="font-bold text-foreground">تدقيق متكامل</p>
                    </div>
                  </div>

                  {/* Parties detail list */}
                  {result.summary.parties.length > 0 && (
                    <div className="border-t border-border/40 pt-4 space-y-1.5">
                      <span className="text-xs text-muted-foreground font-semibold">أطراف التعاقد المدرجة:</span>
                      <div className="flex flex-wrap gap-2">
                        {result.summary.parties.map((p, idx) => (
                          <Badge key={idx} variant="outline" className="px-2.5 py-1 text-xs bg-muted/40 font-semibold text-foreground">
                            {p}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Interactive Filters Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-border/80 bg-muted/20">
                <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground">
                  <Filter className="h-4 w-4 shrink-0" />
                  <span>تصفية البنود والمخاطر:</span>
                </div>
                
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => setSelectedRiskFilter("all")}
                    variant={selectedRiskFilter === "all" ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs font-semibold rounded-lg"
                  >
                    الكل ({result.clauses.length})
                  </Button>
                  <Button
                    onClick={() => setSelectedRiskFilter("critical")}
                    variant={selectedRiskFilter === "critical" ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs font-semibold rounded-lg"
                  >
                    حرج
                  </Button>
                  <Button
                    onClick={() => setSelectedRiskFilter("high")}
                    variant={selectedRiskFilter === "high" ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs font-semibold rounded-lg text-orange-600 dark:text-orange-400"
                  >
                    عالٍ
                  </Button>
                  <Button
                    onClick={() => setSelectedRiskFilter("medium")}
                    variant={selectedRiskFilter === "medium" ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs font-semibold rounded-lg text-amber-600 dark:text-amber-400"
                  >
                    متوسط
                  </Button>
                  <Button
                    onClick={() => setSelectedRiskFilter("low")}
                    variant={selectedRiskFilter === "low" ? "default" : "outline"}
                    size="sm"
                    className="h-8 text-xs font-semibold rounded-lg text-emerald-600 dark:text-emerald-400"
                  >
                    منخفض
                  </Button>
                </div>
              </div>

              {/* Clause Cards List */}
              <div className="space-y-4">
                <h3 className="font-bold text-sm text-foreground">
                  البنود والفقرات التفصيلية ({clauses.length})
                </h3>

                {clauses.length === 0 ? (
                  <p className="text-center py-8 text-xs text-muted-foreground">
                    لا توجد بنود تطابق معايير التصفية الحالية.
                  </p>
                ) : (
                  clauses.map((c) => {
                    const isOpen = !!expandedClauses[c.clause_id];
                    return (
                      <Card
                        key={c.clause_id}
                        className={cn(
                          "border transition-all duration-200",
                          isOpen ? "border-primary/45 shadow-sm" : "border-border/60 hover:border-border"
                        )}
                      >
                        <div
                          onClick={() => toggleClause(c.clause_id)}
                          className="p-4 flex items-center justify-between gap-3 cursor-pointer select-none"
                        >
                          <div className="flex items-center gap-3">
                            <div className={cn("h-2 w-2 rounded-full", getRiskColor(c.risk_level).split(" ")[1])} />
                            <h4 className="font-bold text-sm text-foreground">{c.clause_type}</h4>
                          </div>

                          <div className="flex items-center gap-2">
                            <Badge variant={c.risk_level}>
                              {RISK_LABELS_AR[c.risk_level]}
                            </Badge>
                            {isOpen ? (
                              <ChevronUp className="h-4 w-4 text-muted-foreground" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </div>

                        {isOpen && (
                          <div className="px-4 pb-4 pt-1 border-t border-border/40 space-y-4">
                            {/* Original Text */}
                            <div className="space-y-1">
                              <span className="text-[10px] text-muted-foreground font-semibold">النص الأصلي من المستند:</span>
                              <p className="text-xs bg-muted/40 p-3 rounded-lg leading-relaxed text-muted-foreground font-sans">
                                {c.original_text}
                              </p>
                            </div>

                            {/* AI Explanation */}
                            <div className="space-y-1">
                              <span className="text-[10px] text-muted-foreground font-semibold">التفسير والمخاطر:</span>
                              <p className="text-xs text-foreground/90 leading-relaxed font-semibold">
                                {c.simple_explanation_ar}
                              </p>
                              {c.risk_reason && (
                                <p className="text-[11px] text-amber-600 dark:text-amber-400 font-medium">
                                  تنبيه: {c.risk_reason}
                                </p>
                              )}
                            </div>

                            {/* Simulated legal context based on type */}
                            <div className="space-y-1 bg-primary/5 p-3 rounded-lg border border-primary/10">
                              <span className="text-[10px] text-primary font-bold">السند التشريعي المحتمل:</span>
                              <p className="text-xs text-muted-foreground leading-relaxed mt-0.5">
                                متطابق مع أحكام المادتين ١٤٧ و ١٥٠ من القانون المدني المصري بشأن العقد شريعة المتعاقدين وتفسير النية المشتركة.
                              </p>
                            </div>
                          </div>
                        )}
                      </Card>
                    );
                  })
                )}
              </div>
            </section>

            {/* Column 3: AI Insights (Left column, col-span-3) */}
            <aside className="col-span-3 space-y-6">
              
              {/* Risk Gauge Panel */}
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-2 border-b border-border/40">
                  <CardTitle className="text-sm font-bold">مؤشر المخاطر العام</CardTitle>
                </CardHeader>
                <CardContent className="p-4 text-center space-y-4">
                  
                  {/* Gauge Display */}
                  <div className="relative flex items-center justify-center py-4">
                    <svg className="w-32 h-32 transform -rotate-90">
                      {/* Gray track */}
                      <circle
                        cx="64"
                        cy="64"
                        r="52"
                        stroke="currentColor"
                        strokeWidth="10"
                        fill="transparent"
                        className="text-muted/40"
                      />
                      {/* Score colored filled track */}
                      <circle
                        cx="64"
                        cy="64"
                        r="52"
                        stroke="currentColor"
                        strokeWidth="10"
                        fill="transparent"
                        strokeDasharray={326.7}
                        strokeDashoffset={326.7 - (326.7 * getRiskScorePercentage(result.overall_risk_level)) / 100}
                        className={cn("transition-all duration-500", getRiskColor(result.overall_risk_level).split(" ")[0])}
                      />
                    </svg>
                    
                    {/* Centered Score */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-2xl font-extrabold font-sans">
                        {getRiskScorePercentage(result.overall_risk_level)}%
                      </span>
                      <span className="text-[10px] text-muted-foreground font-semibold mt-0.5">خطورة عامة</span>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <h4 className="font-extrabold text-sm text-foreground">
                      مستوى {RISK_LABELS_AR[result.overall_risk_level]}
                    </h4>
                    <p className="text-[10px] text-muted-foreground leading-relaxed">
                      ينصح بمراجعة البنود ذات التقييم المرتفع وتعديلها لتجنب النزاع القضائي.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* AI Recommendations Panel */}
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-sm font-bold">التوصيات القانونية المقترحة</CardTitle>
                </CardHeader>
                <CardContent className="p-4 space-y-3">
                  {result.recommendations_ar.length === 0 ? (
                    <p className="text-xs text-muted-foreground">لا توجد توصيات تعديل إضافية حالياً.</p>
                  ) : (
                    result.recommendations_ar.map((rec, idx) => (
                      <div key={idx} className="p-3 rounded-lg border bg-muted/40 text-xs leading-relaxed space-y-1">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-bold text-foreground">توصية #{idx + 1}</span>
                          <Badge variant="medium" className="scale-90 font-bold px-1.5 py-0">هام</Badge>
                        </div>
                        <p className="text-muted-foreground font-semibold">{rec}</p>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Missing Clauses Section */}
              {result.missing_clauses.length > 0 && (
                <Card className="border border-border/80 bg-card">
                  <CardHeader className="pb-3 border-b border-border/40">
                    <CardTitle className="text-sm font-bold flex items-center gap-1.5 text-orange-600 dark:text-orange-400">
                      <FileWarning className="h-4.5 w-4.5 shrink-0" />
                      بنود مفقودة مألوفة ({result.missing_clauses.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-4 space-y-3">
                    {result.missing_clauses.map((mc, idx) => (
                      <div key={idx} className="p-3 rounded-lg border border-orange-500/20 bg-orange-500/5 text-xs leading-relaxed space-y-1">
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-bold text-foreground">{mc.clause_type}</span>
                          <Badge variant={mc.importance}>مفقود</Badge>
                        </div>
                        <p className="text-muted-foreground">{mc.description_ar}</p>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {/* Export Panel */}
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-sm font-bold">تصدير تقرير التحليل</CardTitle>
                </CardHeader>
                <CardContent className="p-3 space-y-2">
                  <Button onClick={() => handleExport("pdf")} variant="outline" className="w-full text-xs justify-between rounded-lg">
                    <span>تنزيل التقرير كـ PDF</span>
                    <Download className="h-4.5 w-4.5 text-muted-foreground" />
                  </Button>
                  <Button onClick={() => handleExport("docx")} variant="outline" className="w-full text-xs justify-between rounded-lg">
                    <span>تنزيل التقرير كـ DOCX</span>
                    <Download className="h-4.5 w-4.5 text-muted-foreground" />
                  </Button>
                  <Button onClick={() => handleExport("json")} variant="outline" className="w-full text-xs justify-between rounded-lg">
                    <span>تصدير البيانات كـ JSON</span>
                    <Download className="h-4.5 w-4.5 text-muted-foreground" />
                  </Button>
                </CardContent>
              </Card>
            </aside>
          </div>
        )}

        {/* ========================================================
            TABLET LAYOUT (2 columns)
            ======================================================== */}
        {result && (
          <div className="hidden md:grid lg:hidden grid-cols-12 gap-6 items-start">
            
            {/* Sidebar Column: Upload + general overall risk widgets (col-span-4) */}
            <aside className="col-span-4 space-y-6">
              <Card className="border border-border/80 bg-card">
                <CardHeader className="pb-3 border-b border-border/40">
                  <CardTitle className="text-xs font-bold">مستند العقد</CardTitle>
                </CardHeader>
                <CardContent className="p-3 space-y-3">
                  <p className="font-bold text-xs truncate">{result.filename}</p>
                  <Button onClick={removeFile} variant="outline" className="w-full text-xs h-9">
                    إزالة العقد
                  </Button>
                </CardContent>
              </Card>

              {/* Risk score details */}
              <Card className="border border-border/80 bg-card text-center p-4 space-y-2">
                <h4 className="font-bold text-xs text-muted-foreground">خطورة العقد الكلية</h4>
                <div className="text-3xl font-black text-accent">{getRiskScorePercentage(result.overall_risk_level)}%</div>
                <Badge variant={result.overall_risk_level}>{RISK_LABELS_AR[result.overall_risk_level]}</Badge>
              </Card>

              {/* Action Exports */}
              <Card className="border border-border/80 bg-card p-3 space-y-2">
                <Button onClick={() => handleExport("pdf")} variant="outline" className="w-full text-xs justify-between">
                  <span>تصدير PDF</span>
                  <Download className="h-4 w-4" />
                </Button>
                <Button onClick={() => handleExport("docx")} variant="outline" className="w-full text-xs justify-between">
                  <span>تصدير DOCX</span>
                  <Download className="h-4 w-4" />
                </Button>
              </Card>
            </aside>

            {/* Analysis main column: Summary and Clause cards (col-span-8) */}
            <section className="col-span-8 space-y-6">
              <Card className="border border-border/80 bg-card p-5 space-y-3">
                <h3 className="font-bold text-sm text-foreground">الملخص التنفيذي</h3>
                <p className="text-xs leading-relaxed text-muted-foreground">{result.summary.overview_ar}</p>
              </Card>

              <div className="space-y-3">
                <h3 className="font-bold text-sm text-foreground">تحليل البنود والخطورة</h3>
                {result.clauses.map((c) => (
                  <Card key={c.clause_id} className="border border-border/60">
                    <div className="p-4 flex items-center justify-between">
                      <span className="font-bold text-xs text-foreground">{c.clause_type}</span>
                      <Badge variant={c.risk_level}>{RISK_LABELS_AR[c.risk_level]}</Badge>
                    </div>
                  </Card>
                ))}
              </div>
            </section>

          </div>
        )}

        {/* ========================================================
            MOBILE LAYOUT (Accordion list views)
            ======================================================== */}
        {result && (
          <div className="block md:hidden space-y-4">
            
            {/* Summary Panel header */}
            <Card className="border border-border/60 overflow-hidden">
              <div
                onClick={() => setMobileActivePanel(mobileActivePanel === "summary" ? "" : "summary")}
                className="p-4 bg-muted/20 flex items-center justify-between cursor-pointer"
              >
                <span className="font-bold text-sm">١. الملخص والخطورة العامة</span>
                <ChevronDown className={cn("h-4 w-4 transition-transform", mobileActivePanel === "summary" && "rotate-180")} />
              </div>

              {mobileActivePanel === "summary" && (
                <CardContent className="p-4 border-t border-border/40 space-y-4 text-right">
                  <div className="text-center p-4 rounded-xl bg-muted/40 border">
                    <span className="text-xs text-muted-foreground font-semibold">مستوى الخطورة</span>
                    <h3 className="text-xl font-bold text-accent mt-1">{RISK_LABELS_AR[result.overall_risk_level]}</h3>
                  </div>
                  <p className="text-xs leading-relaxed text-foreground/90">{result.summary.overview_ar}</p>
                </CardContent>
              )}
            </Card>

            {/* Clauses List Mobile Panel */}
            <Card className="border border-border/60 overflow-hidden">
              <div
                onClick={() => setMobileActivePanel(mobileActivePanel === "clauses" ? "" : "clauses")}
                className="p-4 bg-muted/20 flex items-center justify-between cursor-pointer"
              >
                <span className="font-bold text-sm">٢. البنود والمخاطر التفصيلية ({result.clauses.length})</span>
                <ChevronDown className={cn("h-4 w-4 transition-transform", mobileActivePanel === "clauses" && "rotate-180")} />
              </div>

              {mobileActivePanel === "clauses" && (
                <CardContent className="p-4 border-t border-border/40 space-y-3">
                  {result.clauses.map((c) => (
                    <div key={c.clause_id} className="p-3.5 rounded-lg border border-border bg-card space-y-2">
                      <div className="flex items-center justify-between gap-1">
                        <span className="font-bold text-xs">{c.clause_type}</span>
                        <Badge variant={c.risk_level}>{RISK_LABELS_AR[c.risk_level]}</Badge>
                      </div>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">
                        {c.simple_explanation_ar}
                      </p>
                    </div>
                  ))}
                </CardContent>
              )}
            </Card>

            {/* Export and action options */}
            <Card className="border border-border/60 p-4 space-y-3">
              <h4 className="font-bold text-xs">خيارات وتصدير</h4>
              <Button onClick={() => handleExport("pdf")} variant="outline" className="w-full text-xs h-9">
                تنزيل تقرير PDF
              </Button>
              <Button onClick={removeFile} variant="ghost" className="w-full text-xs text-destructive">
                إزالة المستند
              </Button>
            </Card>

          </div>
        )}

      </div>
    </div>
  );
}
