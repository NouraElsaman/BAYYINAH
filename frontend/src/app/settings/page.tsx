"use client";

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, Moon, Sun, Server, CheckCircle2, XCircle, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useTheme } from "@/components/theme-provider";
import { useChatHistory } from "@/lib/use-chat-history";
import { Button } from "@/components/ui/button";
import { fetchHealth } from "@/lib/api";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const { clearHistory, history } = useChatHistory();
  const [health, setHealth] = useState<any>(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  return (
    <main
      className="px-3 sm:px-4 md:px-6 py-6 sm:py-8 max-w-2xl mx-auto pb-24 space-y-5 sm:space-y-6"
      aria-label="صفحة الإعدادات"
    >
      <header>
        <h1 className="text-lg sm:text-xl font-extrabold flex items-center gap-2">
          <SettingsIcon className="h-5 w-5 sm:h-6 sm:w-6 text-primary shrink-0" aria-hidden="true" />
          الإعدادات
        </h1>
      </header>

      {/* Appearance */}
      <Card>
        <CardHeader>
          <CardTitle>المظهر</CardTitle>
          <CardDescription>التبديل بين الوضع النهاري والليلي</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="outline"
            onClick={toggleTheme}
            aria-label={theme === "light" ? "تفعيل الوضع الليلي" : "تفعيل الوضع النهاري"}
            className="gap-2"
          >
            {theme === "light" ? (
              <Moon className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Sun className="h-4 w-4" aria-hidden="true" />
            )}
            {theme === "light" ? "تفعيل الوضع الليلي" : "تفعيل الوضع النهاري"}
          </Button>
        </CardContent>
      </Card>

      {/* Chat History */}
      <Card>
        <CardHeader>
          <CardTitle>سجل المحادثات</CardTitle>
          <CardDescription>
            عدد المحادثات المحفوظة محلياً:{" "}
            <span className="font-bold text-foreground">{history.length}</span>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            variant="destructive"
            onClick={clearHistory}
            disabled={history.length === 0}
            aria-label="مسح جميع المحادثات المحفوظة"
            className="gap-2"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            مسح كل السجل
          </Button>
        </CardContent>
      </Card>

      {/* Service Health */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5 shrink-0" aria-hidden="true" />
            حالة الخدمة
          </CardTitle>
          <CardDescription>حالة الاتصال بالخادم الخلفي</CardDescription>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          {healthError ? (
            <div className="flex items-center gap-2 text-destructive" role="alert">
              <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
              تعذر الاتصال بالخادم
            </div>
          ) : health ? (
            <dl className="space-y-2">
              <div className="flex items-center gap-2">
                {health.status === "ok" ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" aria-hidden="true" />
                ) : (
                  <XCircle className="h-4 w-4 text-amber-500 shrink-0" aria-hidden="true" />
                )}
                <dt className="text-muted-foreground">الحالة:</dt>
                <dd className="font-semibold">{health.status}</dd>
              </div>
              <div className="flex items-center gap-2">
                <dt className="text-muted-foreground">البيئة:</dt>
                <dd className="font-semibold">{health.environment}</dd>
              </div>
              <div className="flex items-center gap-2">
                <dt className="text-muted-foreground">مدة التشغيل:</dt>
                <dd className="font-semibold">{Math.round(health.uptime_seconds)} ثانية</dd>
              </div>
              {health.dependencies && (
                <div className="flex items-center gap-2">
                  <dt className="text-muted-foreground">Qdrant:</dt>
                  <dd className="font-semibold">{health.dependencies.qdrant}</dd>
                </div>
              )}
            </dl>
          ) : (
            <p className="text-muted-foreground animate-pulse" role="status" aria-live="polite">
              جاري التحميل...
            </p>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
