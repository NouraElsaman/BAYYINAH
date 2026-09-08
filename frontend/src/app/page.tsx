"use client";

import Link from "next/link";
import Image from "next/image";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  Scale,
  FileText,
  Shield,
  Search,
  ArrowRight,
  CheckCircle,
  MessageSquare,
  Clock,
  BookOpen,
  Users,
  Check,
  ChevronLeft,
  ChevronRight,
  Briefcase,
  AlertCircle
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent
} from "@/components/ui/accordion";

// Detect reduced motion preference at module level (safe: evaluated at runtime)
const prefersReducedMotion =
  typeof window !== "undefined"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

// Smooth animation configurations — disabled when user prefers reduced motion
const fadeInUp = prefersReducedMotion
  ? { initial: {}, animate: {}, transition: {} }
  : {
      initial: { opacity: 0, y: 24 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.55, ease: [0.22, 1, 0.36, 1] },
    };

const staggerChildren = prefersReducedMotion
  ? { animate: {} }
  : {
      animate: {
        transition: { staggerChildren: 0.1, delayChildren: 0.05 },
      },
    };

// Animated Number Counter — skips animation if prefers-reduced-motion
function AnimatedCounter({ value, suffix = "" }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(prefersReducedMotion ? value : 0);

  useEffect(() => {
    if (prefersReducedMotion) {
      setCount(value);
      return;
    }
    let start = 0;
    const end = value;
    if (start === end) return;
    const totalDuration = 1500;
    const step = Math.ceil(end / (totalDuration / 30));
    const timer = setInterval(() => {
      start += step;
      if (start >= end) {
        clearInterval(timer);
        setCount(end);
      } else {
        setCount(start);
      }
    }, 30);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <span className="font-extrabold text-4xl text-accent tabular-nums" aria-label={`${value}${suffix}`}>
      {count.toLocaleString("ar-EG")}{suffix}
    </span>
  );
}

export default function HomePage() {
  const [formSubmitted, setFormSubmitted] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  const handleContactSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name && email && message) {
      setFormSubmitted(true);
      setName("");
      setEmail("");
      setMessage("");
    }
  };

  return (
    <div className="overflow-hidden bg-background text-foreground">
      
      {/* 1. HERO SECTION */}
      <section
        id="hero"
        aria-label="القسم الرئيسي"
        className="relative min-h-screen flex items-center justify-center py-16 md:py-24 px-4 sm:px-6 md:px-8 border-b border-border/40 bg-gradient-to-b from-card/30 via-background to-background"
      >
        {/* Decorative background glows */}
        <div className="absolute inset-0 opacity-30 dark:opacity-10 pointer-events-none overflow-hidden" aria-hidden="true">
          <div className="absolute -top-40 -left-40 w-72 sm:w-96 h-72 sm:h-96 rounded-full bg-accent/20 blur-3xl" />
          <div className="absolute top-60 -right-20 w-60 sm:w-80 h-60 sm:h-80 rounded-full bg-primary/20 blur-3xl" />
        </div>

        <div className="mx-auto max-w-7xl w-full grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Text Column */}
          <motion.div
            className="lg:col-span-7 text-right space-y-5 md:space-y-6 z-10 order-2 lg:order-1"
            initial="initial"
            animate="animate"
            variants={staggerChildren}
          >
            <motion.div variants={fadeInUp}>
              <Badge variant="outline" className="px-3 py-1.5 border-accent/30 bg-accent/5 text-accent font-semibold flex items-center gap-1.5 w-fit text-xs sm:text-sm">
                <Sparkles className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span>المساعد القانوني الأول بالذكاء الاصطناعي في مصر</span>
              </Badge>
            </motion.div>

            <motion.h1
              variants={fadeInUp}
              className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight leading-[1.2]"
            >
              مستشارك القانوني الذكي{" "}
              <span className="bg-gradient-to-r from-accent to-accent/70 bg-clip-text text-transparent block sm:inline">
                منصة بينة | BAYYINAH
              </span>
            </motion.h1>

            <motion.p
              variants={fadeInUp}
              className="text-muted-foreground text-sm sm:text-base md:text-lg max-w-xl leading-relaxed"
            >
              احصل على استشارات قانونية فورية مدعومة بنصوص التشريعات والقوانين المصرية الرسمية، وحلل عقودك بضغطة زر للكشف عن الثغرات والمخاطر، مع إمكانية التواصل المباشر مع نخبة من أفضل المحامين المرخصين.
            </motion.p>

            <motion.div
              variants={fadeInUp}
              className="flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 pt-2"
            >
              <Button asChild size="lg" className="rounded-xl shadow-md gap-2 font-semibold w-full sm:w-auto">
                <Link href="/chat" aria-label="ابدأ المحادثة مع المساعد القانوني">
                  <Sparkles className="h-5 w-5 shrink-0" aria-hidden="true" /> ابدأ المحادثة مجاناً
                </Link>
              </Button>
              <Button asChild variant="outline" size="lg" className="rounded-xl gap-2 font-semibold bg-card/60 backdrop-blur-sm w-full sm:w-auto">
                <Link href="/contract-analysis" aria-label="رفع عقد للتحليل">
                  <FileText className="h-5 w-5 text-accent shrink-0" aria-hidden="true" /> تحليل عقد جديد
                </Link>
              </Button>
            </motion.div>
          </motion.div>

          {/* Logo Card Column */}
          <motion.div
            className="lg:col-span-5 flex justify-center z-10 order-1 lg:order-2"
            initial={prefersReducedMotion ? {} : { opacity: 0, scale: 0.92 }}
            animate={prefersReducedMotion ? {} : { opacity: 1, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="relative p-6 sm:p-8 rounded-3xl border border-border/60 bg-card/50 shadow-lg backdrop-blur-sm w-full max-w-[280px] sm:max-w-sm flex flex-col items-center">
              <div className="absolute inset-0 bg-gradient-to-br from-accent/5 via-transparent to-transparent rounded-3xl pointer-events-none" aria-hidden="true" />
              <Image
                src="/bayyinah-logo.png"
                alt="بينة BAYYINAH — مساعد قانوني ذكي"
                width={200}
                height={200}
                className="w-36 sm:w-48 h-auto object-contain drop-shadow-md"
                priority
              />
              <span className="mt-4 sm:mt-6 font-extrabold text-xl sm:text-2xl tracking-wide text-foreground text-center">
                بينة | BAYYINAH
              </span>
              <span className="text-xs text-muted-foreground mt-1.5 text-center">
                نظام التحليل والاستشارات القانونية المتكامل
              </span>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 2. SERVICES SECTION */}
      <section id="services" aria-label="خدمات المنصة" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 border-b border-border/40 bg-card/20">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-14 md:mb-16 space-y-3 sm:space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">خدمات المنصة الذكية</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              نوفر لك باقة متكاملة من أدوات الذكاء الاصطناعي والحلول الرقمية لتلبية احتياجاتك القانونية بيسر وأمان.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6 lg:gap-8">
            {/* Card 1 */}
            <Card className="border border-border/60 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-6 space-y-4 text-right">
                <div className="p-3 bg-primary/10 text-primary dark:text-accent rounded-xl w-fit">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">المساعد القانوني التفاعلي</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  محادثة مباشرة ذكية تجيب على تساؤلاتك وتسترجع نصوص القوانين ذات الصلة بمرجعية رسمية دقيقة.
                </p>
              </CardContent>
            </Card>

            {/* Card 2 */}
            <Card className="border border-border/60 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-6 space-y-4 text-right">
                <div className="p-3 bg-primary/10 text-primary dark:text-accent rounded-xl w-fit">
                  <FileText className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">تحليل العقود الذكي</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  ارفع أي عقد بصيغة PDF أو Word، واكشف فوراً عن الثغرات، والبنود المفقودة، وتقييم مستويات المخاطر.
                </p>
              </CardContent>
            </Card>

            {/* Card 3 */}
            <Card className="border border-border/60 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-6 space-y-4 text-right">
                <div className="p-3 bg-primary/10 text-primary dark:text-accent rounded-xl w-fit">
                  <Users className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">الاستشارات القانونية المباشرة</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  تواصل مع أفضل الكوادر القانونية والمحامين المرخصين في مصر لمراجعة وتأكيد التحليلات القانونية المعقدة.
                </p>
              </CardContent>
            </Card>

            {/* Card 4 */}
            <Card className="border border-border/60 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-6 space-y-4 text-right">
                <div className="p-3 bg-primary/10 text-primary dark:text-accent rounded-xl w-fit">
                  <Search className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">البحث في القوانين</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  محرك بحث قانوني متطور يتيح لك الوصول للمواد القانونية والقرارات التشريعية الرسمية بسهولة.
                </p>
              </CardContent>
            </Card>

            {/* Card 5 */}
            <Card className="border border-border/60 hover:-translate-y-1 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-6 space-y-4 text-right">
                <div className="p-3 bg-primary/10 text-primary dark:text-accent rounded-xl w-fit">
                  <Scale className="h-6 w-6" />
                </div>
                <h3 className="text-lg font-bold">استخراج المعلومات والتشريعات</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  تحويل ملفات القضايا الكبيرة إلى ملخصات ذكية وتحديد البنود القانونية الأكثر تأثيراً على قضيتك.
                </p>
              </CardContent>
            </Card>

            {/* Card 6 (Promo to start) */}
            <Card className="border border-accent/20 bg-accent/5 hover:shadow-lg transition-all duration-300 flex flex-col justify-between">
              <CardContent className="p-6 space-y-4 text-right h-full flex flex-col justify-between">
                <div className="space-y-3">
                  <h3 className="text-lg font-bold text-accent">مستعد للبدء الآن؟</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    جرب المحادثة التفاعلية مجاناً واحصل على الإجابات القانونية والتشريعية في ثوانٍ معدودة.
                  </p>
                </div>
                <Button asChild className="rounded-xl w-full mt-4 gap-2">
                  <Link href="/chat">ابدأ استشارتك <ChevronLeft className="h-4 w-4" /></Link>
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* 3. WHY BAYYINAH */}
      <section aria-label="لماذا بينة" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 border-b border-border/40">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">لماذا منصة بينة؟</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              تنفرد منصة بينة بتقديم حلول متخصصة تم تصميمها لتلائم هيكل القانون والتشريع المصري بكل دقة.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">ذكاء اصطناعي موثوق</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  أنظمة متطورة خضعت لاختبارات جودة صارمة لمنع التزييف والهلوسة في الإجابات القانونية.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <Scale className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">مرجعية القوانين المصرية</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  تغطية كاملة وشاملة للقوانين المدنية، الإيجارات، الجنائية، الأحوال الشخصية، وتشريعات العمل.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <BookOpen className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">توثيق بمواد ومصادر رسمية</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  تُرفق مع كل إجابة نصوص البنود والمواد الرسمية لضمان أقصى درجات المصداقية.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">إجابات سريعة وفورية</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  وفر ساعات من البحث في المجلدات والملفات المكتوبة واحصل على المعلومة الدقيقة في ثوانٍ.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <Shield className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">سرية وأمان تام للبيانات</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  تشفير كامل لكافة العقود والمستندات المرفوعة للحفاظ على خصوصيتك ومعلومات قضيتك.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start text-right">
              <div className="p-2 bg-accent/10 text-accent rounded-lg shrink-0">
                <MessageSquare className="h-5 w-5" />
              </div>
              <div>
                <h4 className="font-bold text-lg mb-1">تصميم ودعم كامل للغة العربية</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  واجهات عربية متكاملة تفهم الاستفسارات المكتوبة باللغة الفصحى والعربية المصرية الدارجة.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. HOW IT WORKS */}
      <section aria-label="طريقة عمل المنصة" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 bg-card/20 border-b border-border/40">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto mb-10 sm:mb-14 md:mb-16 space-y-3 sm:space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">كيف تعمل منصة بينة؟</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              بأربع خطوات بسيطة وسريعة، احصل على التحليلات والإجابات والتقارير القانونية الموثقة.
            </p>
          </div>

          <div className="relative grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-5 sm:gap-6 lg:gap-8">
            <div className="hidden md:block absolute top-1/2 right-4 left-4 h-0.5 bg-border/40 -z-10 -translate-y-1/2" aria-hidden="true" />
            
            {/* Step 1 */}
            <div className="flex flex-col items-center text-center space-y-4 bg-background dark:bg-card p-6 rounded-2xl border border-border/60 shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-extrabold text-lg">
                ١
              </div>
              <h4 className="font-bold text-base">طرح السؤال أو رفع العقد</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                اكتب استشارتك القانونية في شريط البحث أو اسحب ملف العقد المراد تحليله.
              </p>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center space-y-4 bg-background dark:bg-card p-6 rounded-2xl border border-border/60 shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-extrabold text-lg">
                ٢
              </div>
              <h4 className="font-bold text-base">استرجاع التشريعات الفوري</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                يبحث محرك RAG الهجين في قاعدة البيانات الضخمة المحدثة بنصوص القوانين الرسمية.
              </p>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center space-y-4 bg-background dark:bg-card p-6 rounded-2xl border border-border/60 shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-primary-foreground font-extrabold text-lg">
                ٣
              </div>
              <h4 className="font-bold text-base">المطابقة والتحقق العقلي</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                يتحقق نظام التقييم من مطابقة الإجابة لنصوص المواد القانونية المسترجعة لمنع الهلوسة.
              </p>
            </div>

            {/* Step 4 */}
            <div className="flex flex-col items-center text-center space-y-4 bg-accent/10 border border-accent/20 p-6 rounded-2xl shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent text-accent-foreground font-extrabold text-lg">
                ٤
              </div>
              <h4 className="font-bold text-base text-accent">تقرير وإجابة موثقة</h4>
              <p className="text-xs text-muted-foreground leading-relaxed">
                احصل على النتيجة النهائية مع ذكر أرقام المواد الدستورية ونسب المخاطر بالتفصيل.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 5. STATISTICS SECTION */}
      <section aria-label="إحصائيات المنصة" className="py-12 sm:py-14 md:py-16 px-4 sm:px-6 md:px-8 border-b border-border/40 bg-gradient-to-r from-primary/5 via-card/5 to-primary/5">
        <div className="mx-auto max-w-7xl">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8 text-center">
            <div className="space-y-2">
              <AnimatedCounter value={25000} suffix="+" />
              <p className="text-sm text-muted-foreground font-semibold">مادة قانونية بقاعدة البيانات</p>
            </div>
            <div className="space-y-2">
              <AnimatedCounter value={98} suffix="%" />
              <p className="text-sm text-muted-foreground font-semibold">دقة استرجاع نصوص القوانين</p>
            </div>
            <div className="space-y-2">
              <AnimatedCounter value={1200} suffix="+" />
              <p className="text-sm text-muted-foreground font-semibold">عقد تم تحليله بنجاح</p>
            </div>
            <div className="space-y-2">
              <AnimatedCounter value={4500} suffix="+" />
              <p className="text-sm text-muted-foreground font-semibold">جلسة استشارية ذكية</p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. TESTIMONIALS */}
      <section aria-label="آراء المستخدمين" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 border-b border-border/40">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">آراء مستخدمي المنصة</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              ماذا يقول المحامون والشركات والأفراد الذين اختاروا بينة لمساعدتهم القانونية اليومية.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6 lg:gap-8">
            <Card className="border border-border/60 bg-card/40 backdrop-blur-sm text-right">
              <CardContent className="p-6 space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed italic">
                  &ldquo;ساعدتني منصة بينة كثيراً في أرشفة وتدقيق عقود الإيجار السكنية الخاصة بمؤسستي العقارية. تحديد البنود المفقودة والمخاطر وفر علينا وقتاً ومبالغ طائلة.&rdquo;
                </p>
                <div className="border-t border-border/40 pt-4 flex justify-between items-center">
                  <div>
                    <h5 className="font-bold text-sm">أ. محمد الشناوي</h5>
                    <p className="text-xs text-muted-foreground">رائد أعمال ومطور عقاري</p>
                  </div>
                  <Badge variant="outline" className="text-xs">عقارات</Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border/60 bg-card/40 backdrop-blur-sm text-right">
              <CardContent className="p-6 space-y-4">
                <p className="text-sm text-muted-foreground leading-relaxed italic">
                  &ldquo;كمحامٍ ممارس، كنت متخوفاً من استخدام الذكاء الاصطناعي، لكن مطابقة النصوص والتوثيق بمواد القانون المصري التي توفرها بينة جعلتها أداة مساعدة لا غنى عنها في مكتبي.&rdquo;
                </p>
                <div className="border-t border-border/40 pt-4 flex justify-between items-center">
                  <div>
                    <h5 className="font-bold text-sm">أ. سارة عبد الرحمن</h5>
                    <p className="text-xs text-muted-foreground">محامية بالاستئناف العالي</p>
                  </div>
                  <Badge variant="outline" className="text-xs">محاماة</Badge>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-border/60 bg-card/40 backdrop-blur-sm text-right flex flex-col justify-between">
              <CardContent className="p-6 space-y-4 h-full flex flex-col justify-between">
                <p className="text-sm text-muted-foreground leading-relaxed italic">
                  &ldquo;سهولة واجهة الاستخدام والرد باللغة العربية البسيطة ساعدتني على فهم حقوقي كمستأجر بدون تعقيد، مع ذكر مواد القانون التي استندت عليها الإجابة.&rdquo;
                </p>
                <div className="border-t border-border/40 pt-4 flex justify-between items-center">
                  <div>
                    <h5 className="font-bold text-sm">م. عمر دياب</h5>
                    <p className="text-xs text-muted-foreground">مستأجر شقة سكنية</p>
                  </div>
                  <Badge variant="outline" className="text-xs">أفراد</Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* 6.5. CONTACT SECTION */}
      <section id="contact" aria-label="تواصل معنا" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 border-b border-border/40">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">تواصل معنا</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              لديك استفسار أو ترغب في الحصول على دعم فني؟ فريقنا يسعد بخدمتك والرد عليك في أقرب وقت.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
            {/* Contact Details Column */}
            <div className="lg:col-span-5 space-y-6 text-right">
              <Card className="border border-border/60 bg-card/40 backdrop-blur-sm">
                <CardContent className="p-6 space-y-6">
                  <h3 className="font-bold text-lg border-b border-border/60 pb-3">معلومات الاتصال</h3>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-xs text-muted-foreground font-semibold">البريد الإلكتروني</h4>
                      <p className="font-bold text-sm text-foreground">info@bayyinah.ai</p>
                    </div>
                    <div>
                      <h4 className="text-xs text-muted-foreground font-semibold">الهاتف</h4>
                      <p className="font-bold text-sm text-foreground">+20 100 000 0000</p>
                    </div>
                    <div>
                      <h4 className="text-xs text-muted-foreground font-semibold">العنوان</h4>
                      <p className="font-bold text-sm text-foreground">القاهرة، جمهورية مصر العربية</p>
                    </div>
                    <div>
                      <h4 className="text-xs text-muted-foreground font-semibold">مواعيد العمل</h4>
                      <p className="font-bold text-sm text-foreground">من الأحد إلى الخميس، من ٩ صباحاً وحتى ٥ مساءً</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Form Column */}
            <div className="lg:col-span-7">
              <Card className="border border-border/60 bg-card">
                <CardContent className="p-6">
                  {formSubmitted ? (
                    <div className="text-center py-12 space-y-4">
                      <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400">
                        <CheckCircle className="h-6 w-6" />
                      </div>
                      <h3 className="font-bold text-lg text-foreground">تم إرسال رسالتك بنجاح!</h3>
                      <p className="text-sm text-muted-foreground max-w-md mx-auto">
                        نشكرك على تواصلك معنا. سنقوم بمراجعة استفسارك والرد عليك عبر بريدك الإلكتروني في أقرب فرصة ممكنة.
                      </p>
                      <Button variant="outline" onClick={() => setFormSubmitted(false)} className="rounded-xl mt-4">
                        إرسال رسالة أخرى
                      </Button>
                    </div>
                  ) : (
                    <form onSubmit={handleContactSubmit} className="space-y-4 text-right">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label htmlFor="contact-name" className="text-xs font-semibold text-muted-foreground">الاسم بالكامل</label>
                          <Input
                            id="contact-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="مثال: أحمد محمد"
                            required
                            className="rounded-xl"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label htmlFor="contact-email" className="text-xs font-semibold text-muted-foreground">البريد الإلكتروني</label>
                          <Input
                            id="contact-email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@example.com"
                            required
                            className="rounded-xl"
                          />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <label htmlFor="contact-message" className="text-xs font-semibold text-muted-foreground">الرسالة</label>
                        <Textarea
                          id="contact-message"
                          value={message}
                          onChange={(e) => setMessage(e.target.value)}
                          placeholder="اكتب استفسارك بالتفصيل هنا..."
                          rows={4}
                          required
                          className="rounded-xl min-h-[120px]"
                        />
                      </div>
                      <Button type="submit" className="rounded-xl w-full font-bold">
                        إرسال الرسالة
                      </Button>
                    </form>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* 7. FAQ SECTION */}
      <section id="faq" aria-label="الأسئلة الشائعة" className="py-14 sm:py-20 md:py-24 px-4 sm:px-6 md:px-8 bg-card/20 border-b border-border/40">
        <div className="mx-auto max-w-4xl">
          <div className="text-center mb-16 space-y-4">
            <h2 className="text-3xl font-extrabold tracking-tight">الأسئلة الشائعة</h2>
            <p className="text-muted-foreground text-sm md:text-base leading-relaxed">
              إجابات على الأسئلة والاستفسارات الأكثر تكراراً حول منصة بينة القانونية الذكية.
            </p>
          </div>

          <Accordion defaultValue="item-1">
            <AccordionItem value="item-1">
              <AccordionTrigger>هل تعتبر إجابات منصة بينة بديلاً عن المحامي المرخص؟</AccordionTrigger>
              <AccordionContent>
                لا، منصة بينة هي مساعد رقمي تثقيفي يوفر نصوص المواد والقرارات ويسهل عملية الفهم والوصول، لكنها لا تقدم استشارات رسمية بديلة عن المحامي. ننصح دائماً بطلب مراجعة بشرية من محامٍ مختص في القضايا ذات الحساسية العالية.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-2">
              <AccordionTrigger>ما هي القوانين والدستور المدعوم في قاعدة بيانات بينة حالياً؟</AccordionTrigger>
              <AccordionContent>
                تحتوي قاعدة بيانات المنصة على كافة نصوص القانون المدني المصري، وقوانين الإيجارات (القديم والجديد)، والتشريعات العمالية وقوانين العمل، والجريدة الرسمية، بالإضافة إلى الدستور المصري بشكل كامل.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-3">
              <AccordionTrigger>كيف تضمن بينة دقة الإجابات وعدم تزييف المعلومات؟</AccordionTrigger>
              <AccordionContent>
                تعتمد بينة على بنية استرجاع المعلومات RAG المتقدمة؛ حيث يتم إجبار النموذج الذكي على صياغة الإجابة نقلاً وحصراً من الوثائق المسترجعة من خوادمنا الرسمية، مع وجود مدقق داخلي يقارن نسب التشابه المعجمي بين الإجابة والمصدر.
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="item-4">
              <AccordionTrigger>هل بياناتي وعقودي التي أرفعها على المنصة آمنة؟</AccordionTrigger>
              <AccordionContent>
                بكل تأكيد. جميع الملفات والمستندات المرفوعة يتم تشفيرها وتخزينها في خوادم سحابية محمية ومقفلة، ولا يتم استخدام بياناتك أو وثائقك في تدريب النماذج العامة أو مشاركتها مع أطراف خارجية بأي شكل كان.
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </section>

      {/* 8. CTA BANNER */}
      <section aria-label="ابدأ الآن" className="py-14 sm:py-20 md:py-20 px-4 sm:px-6 md:px-8 bg-[#0b3c5d] text-white text-center relative overflow-hidden border-t border-border/40">
        <div className="absolute inset-0 opacity-10 pointer-events-none" aria-hidden="true">
          <div className="absolute -bottom-20 -left-20 w-80 h-80 rounded-full bg-[#bda054] blur-2xl animate-pulse" />
        </div>

        <div className="mx-auto max-w-4xl space-y-6 relative z-10">
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight">احصل على مستشارك القانوني الأول بمصر الآن</h2>
          <p className="text-white/80 text-sm md:text-base max-w-2xl mx-auto leading-relaxed">
            انضم إلى آلاف المحامين والشركات والأفراد الذين يثقون في بينة للحصول على إجابات سريعة، وتحليل العقود وحماية حقوقهم.
          </p>
          <div className="flex flex-col sm:flex-row flex-wrap gap-3 sm:gap-4 justify-center pt-4">
            <Button asChild size="lg" className="bg-[#bda054] text-[#0b3c5d] hover:bg-[#bda054]/90 rounded-xl font-bold shadow-md gap-2 border-0 w-full sm:w-auto">
              <Link href="/chat" aria-label="ابدأ استشارة تفاعلية مع المساعد القانوني">
                <Sparkles className="h-5 w-5 shrink-0" aria-hidden="true" /> ابدأ استشارة تفاعلية
              </Link>
            </Button>
            <Button asChild variant="outline" size="lg" className="border-white/30 text-white hover:bg-white/10 hover:text-white hover:border-white rounded-xl font-bold gap-2 bg-transparent w-full sm:w-auto">
              <Link href="/contract-analysis" aria-label="رفع عقد للتحليل">
                <FileText className="h-5 w-5 shrink-0" aria-hidden="true" /> حلل عقدك الآن
              </Link>
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
