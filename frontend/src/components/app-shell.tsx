"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X, ArrowRight, ArrowLeft, Sun, Moon, Sparkles, Calendar, LogIn, ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/theme-provider";

import { useEffect } from "react";

const NAV_ITEMS = [
  { href: "/", label: "الرئيسية" },
  { href: "/#services", label: "الخدمات" },
  { href: "/contract-analysis", label: "تحليل العقود" },
  { href: "/blog", label: "المدونة" },
  { href: "/#contact", label: "تواصل معنا" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const [activeSection, setActiveSection] = useState<string>("hero");

  useEffect(() => {
    if (pathname !== "/") {
      setActiveSection("");
      return;
    }

    // Track all currently-visible sections and pick the topmost one
    // This prevents flicker when two sections overlap in the viewport
    const visibleSet = new Set<string>();

    const handleIntersect = (entries: IntersectionObserverEntry[]) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          visibleSet.add(entry.target.id);
        } else {
          visibleSet.delete(entry.target.id);
        }
      });
      // Prioritise sections in page order
      const ordered = ["hero", "services", "contact"];
      const winner = ordered.find((id) => visibleSet.has(id));
      if (winner) setActiveSection(winner);
    };

    const observer = new IntersectionObserver(handleIntersect, {
      root: null,
      rootMargin: "-20% 0px -60% 0px",
      threshold: 0,
    });

    const sections = ["hero", "services", "contact"];
    sections.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [pathname]);

  const goBack = () => {
    if (typeof window !== "undefined") window.history.back();
  };
  const goForward = () => {
    if (typeof window !== "undefined") window.history.forward();
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-300">
      {/* Top Header Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/90 backdrop-blur-xl transition-colors duration-300">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          
          {/* Right Section: Brand Logo & Navigation */}
          <div className="flex items-center gap-6">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2 group" aria-label="بيّنة - الرئيسية">
              <Image
                src="/bayyinah-logo.png"
                alt="بيّنة Bayyinah"
                width={50}
                height={50}
                className="h-12 w-auto object-contain transition-transform group-hover:scale-105"
                priority
              />
            </Link>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-1">
              {NAV_ITEMS.map((item) => {
                let active = false;
                if (pathname === "/") {
                  if (item.href === "/") {
                    active = activeSection === "hero" || activeSection === "";
                  } else if (item.href.startsWith("/#")) {
                    active = activeSection === item.href.split("#")[1];
                  }
                } else {
                  if (item.href === "/") {
                    active = false;
                  } else if (item.href.startsWith("/#")) {
                    active = false;
                  } else {
                    active = pathname === item.href || pathname?.startsWith(item.href);
                  }
                }
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "relative rounded-md px-3 py-2 text-sm font-medium transition-colors hover:text-foreground/90",
                      active
                        ? "text-foreground font-semibold"
                        : "text-muted-foreground hover:bg-muted/40"
                    )}
                  >
                    {item.label}
                    {active && (
                      <span className="absolute inset-x-3 -bottom-[17px] h-0.5 bg-gradient-to-r from-accent to-accent/60" />
                    )}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Left Section: Actions & Utilities */}
          <div className="flex items-center gap-2">
            
            {/* History arrows (hidden on small mobile screens) */}
            <div className="hidden sm:flex items-center gap-0.5 rounded-md border border-border bg-card/60 p-0.5">
              <button
                onClick={goBack}
                aria-label="رجوع"
                title="الصفحة السابقة"
                className="inline-flex h-8 w-8 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={goForward}
                aria-label="تقدم"
                title="الصفحة التالية"
                className="inline-flex h-8 w-8 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
              </button>
            </div>

            {/* Theme switcher */}
            <button
              onClick={toggleTheme}
              aria-label="تبديل المظهر"
              className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-border bg-card/50 text-foreground hover:bg-muted transition-colors"
            >
              {theme === "light" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            </button>

            {/* Interactive Actions */}
            <div className="hidden md:flex items-center gap-2">
              <Link
                href="/#login"
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card/40 px-3 py-1.5 text-xs font-semibold text-foreground transition-all hover:bg-muted"
              >
                <LogIn className="h-3.5 w-3.5" /> تسجيل الدخول
              </Link>
              <Link
                href="/#consultation"
                className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card/40 px-3 py-1.5 text-xs font-semibold text-foreground transition-all hover:bg-muted"
              >
                <Calendar className="h-3.5 w-3.5" /> احجز استشارة
              </Link>
              <Link
                href="/chat"
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:opacity-90 active:scale-95"
              >
                <Sparkles className="h-3.5 w-3.5" /> ابدأ المحادثة
              </Link>
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setOpen(!open)}
              className="lg:hidden inline-flex h-9 w-9 items-center justify-center rounded-md text-foreground hover:bg-muted"
              aria-label="القائمة"
            >
              {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile menu drawer */}
        {open && (
          <div className="lg:hidden border-t border-border bg-background">
            <nav className="mx-auto max-w-7xl px-4 py-3 space-y-1">
              <div className="flex items-center gap-1 pb-2">
                <button
                  onClick={goBack}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:bg-muted"
                >
                  <ArrowRight className="h-3.5 w-3.5" /> رجوع
                </button>
                <button
                  onClick={goForward}
                  className="flex-1 inline-flex items-center justify-center gap-1.5 rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:bg-muted"
                >
                  تقدم <ArrowLeft className="h-3.5 w-3.5" />
                </button>
              </div>
              {NAV_ITEMS.map((item) => {
                let active = false;
                if (pathname === "/") {
                  if (item.href === "/") {
                    active = activeSection === "hero" || activeSection === "";
                  } else if (item.href.startsWith("/#")) {
                    active = activeSection === item.href.split("#")[1];
                  }
                } else {
                  if (item.href === "/") {
                    active = false;
                  } else if (item.href.startsWith("/#")) {
                    active = false;
                  } else {
                    active = pathname === item.href || pathname?.startsWith(item.href);
                  }
                }
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setOpen(false)}
                    className={cn(
                      "block rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "bg-primary text-primary-foreground font-semibold"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    {item.label}
                  </Link>
                );
              })}

              <div className="border-t border-border/60 my-2 pt-2 space-y-2">
                <Link
                  href="/#login"
                  onClick={() => setOpen(false)}
                  className="flex items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-center text-sm font-medium text-foreground"
                >
                  <LogIn className="h-4 w-4" /> تسجيل الدخول
                </Link>
                <Link
                  href="/#consultation"
                  onClick={() => setOpen(false)}
                  className="flex items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-center text-sm font-medium text-foreground"
                >
                  <Calendar className="h-4 w-4" /> احجز استشارة
                </Link>
                <Link
                  href="/chat"
                  onClick={() => setOpen(false)}
                  className="flex items-center justify-center gap-1.5 rounded-md bg-primary px-3 py-2 text-center text-sm font-medium text-primary-foreground"
                >
                  <Sparkles className="h-4 w-4" /> ابدأ المحادثة
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">{children}</main>

      {/* Reusable Global Footer */}
      <footer className="border-t border-border bg-card text-card-foreground">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8 lg:py-16">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
            
            {/* Column 1: About */}
            <div className="md:col-span-5 space-y-4">
              <div className="flex items-center gap-2">
                <Image
                  src="/bayyinah-logo.png"
                  alt="بينة Bayyinah"
                  width={40}
                  height={40}
                  className="h-10 w-auto object-contain"
                />
                <span className="font-extrabold text-lg text-foreground tracking-tight">بينة | BAYYINAH</span>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed max-w-md">
                بينة (BAYYINAH) هي منصة رائدة لحلول التكنولوجيا القانونية في مصر. تهدف إلى تبسيط القوانين وتسهيل الوصول للمعلومة القانونية ودعم المحامين والمؤسسات من خلال حلول الذكاء الاصطناعي الأكثر دقة وتخصيصاً بالأنظمة القضائية المحلية.
              </p>
            </div>

            {/* Column 2: Quick Links */}
            <div className="md:col-span-2 space-y-3">
              <h4 className="text-sm font-bold text-foreground">روابط سريعة</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {NAV_ITEMS.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className="hover:text-foreground transition-colors flex items-center gap-1">
                      <ChevronLeft className="h-3 w-3" /> {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>

            {/* Column 3: Legal Resources */}
            <div className="md:col-span-2 space-y-3">
              <h4 className="text-sm font-bold text-foreground">مصادر قانونية</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>
                  <a href="https://moj.gov.eg" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors flex items-center gap-1">
                    <ChevronLeft className="h-3 w-3" /> وزارة العدل المصرية
                  </a>
                </li>
                <li>
                  <a href="https://egylawyers.org" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors flex items-center gap-1">
                    <ChevronLeft className="h-3 w-3" /> نقابة المحامين المصرية
                  </a>
                </li>
                <li>
                  <a href="http://www.cc.gov.eg" target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors flex items-center gap-1">
                    <ChevronLeft className="h-3 w-3" /> المحكمة الدستورية العليا
                  </a>
                </li>
              </ul>
            </div>

            {/* Column 4: Contact */}
            <div className="md:col-span-3 space-y-3">
              <h4 className="text-sm font-bold text-foreground">تواصل معنا</h4>
              <ul className="space-y-2 text-sm text-muted-foreground leading-relaxed">
                <li>البريد الإلكتروني: <span className="font-semibold text-foreground">info@bayyinah.ai</span></li>
                <li>الهاتف: <span className="font-semibold text-foreground">+20 100 000 0000</span></li>
                <li>العنوان: القاهرة، جمهورية مصر العربية</li>
              </ul>
            </div>
          </div>

          {/* AI Disclaimer Section */}
          <div className="border-t border-border/60 mt-8 pt-8 text-xs text-muted-foreground leading-relaxed">
            <h5 className="font-bold text-foreground mb-2 flex items-center gap-1">
              ⚠️ إخلاء مسؤولية وإقرار الذكاء الاصطناعي:
            </h5>
            <p>
              منصة بينة (BAYYINAH) هي مساعد رقمي ذكي مبني على تقنيات استرجاع المعلومات RAG ونماذج اللغات الكبيرة المدعومة بنصوص القوانين المصرية الرسمية. كافة المعلومات والإجابات التي يوفرها النظام مخصصة للأغراض التثقيفية والإرشادية فقط، ولا يُعد استشارة قانونية رسمية ولا تغني عن استشارة محامٍ مرخص ومختص. لا يتحمل النظام أو القائمون عليه أي مسؤولية ناتجة عن قرارات تُتخذ بناءً على إجابات المنصة.
            </p>
          </div>

          {/* Footer Sub-bar */}
          <div className="border-t border-border/40 mt-8 pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
            <div>
              &copy; {new Date().getFullYear()} بينة | BAYYINAH. جميع الحقوق محفوظة.
            </div>
            <div className="flex gap-4">
              <Link href="/#" className="hover:text-foreground transition-colors">سياسة الخصوصية</Link>
              <Link href="/#" className="hover:text-foreground transition-colors">شروط الاستخدام</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
