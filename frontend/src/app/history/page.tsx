"use client";

import { useChatHistory } from "@/lib/use-chat-history";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CitationCard } from "@/components/citation-card";
import { History, Trash2, AlertTriangle, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

export default function HistoryPage() {
  const { history, clearHistory } = useChatHistory();

  return (
    <main className="px-3 sm:px-4 md:px-6 py-6 sm:py-8 max-w-3xl mx-auto pb-24" aria-label="سجل المحادثات">
      <header className="mb-6 sm:mb-8 flex items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-lg sm:text-xl font-extrabold flex items-center gap-2">
            <History className="h-5 w-5 sm:h-6 sm:w-6 text-primary shrink-0" aria-hidden="true" />
            سجل المحادثات
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            آخر الأسئلة والإجابات المحفوظة على هذا الجهاز.
          </p>
        </div>
        {history.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearHistory}
            aria-label="مسح جميع المحادثات المحفوظة"
            className="shrink-0"
          >
            <Trash2 className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">مسح السجل</span>
          </Button>
        )}
      </header>

      {history.length === 0 ? (
        <Card>
          <CardContent className="p-8 sm:p-12 flex flex-col items-center text-center gap-4">
            <div className="h-14 w-14 rounded-full bg-muted flex items-center justify-center">
              <MessageSquare className="h-7 w-7 text-muted-foreground" aria-hidden="true" />
            </div>
            <div>
              <p className="font-semibold text-sm text-foreground">لا يوجد سجل محادثات حتى الآن</p>
              <p className="text-xs text-muted-foreground mt-1">
                ابدأ محادثة جديدة من صفحة &quot;المساعد القانوني&quot; وستظهر هنا تلقائياً.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {history.map((entry) => (
            <Card key={entry.id} className={cn(entry.is_fallback && "border-amber-400/50")}>
              <CardContent className="p-4 sm:p-5 space-y-3">
                <div>
                  <p className="text-xs font-bold text-muted-foreground mb-1">السؤال</p>
                  <p className="text-sm font-semibold leading-relaxed">{entry.question}</p>
                </div>
                <div>
                  <p className="text-xs font-bold text-muted-foreground mb-1 flex items-center gap-1">
                    الإجابة
                    {entry.is_fallback && (
                      <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                        <AlertTriangle className="h-3 w-3" aria-hidden="true" /> احتياطية
                      </span>
                    )}
                  </p>
                  <p className="text-sm leading-relaxed">{entry.answer}</p>
                </div>
                {entry.citations.length > 0 && (
                  <div className="space-y-2">
                    {entry.citations.map((c, i) => (
                      <CitationCard key={c.chunk_id + i} citation={c} index={i} />
                    ))}
                  </div>
                )}
                <p className="text-[11px] text-muted-foreground border-t border-border/40 pt-2 mt-2">
                  {new Date(entry.timestamp).toLocaleString("ar-EG")}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </main>
  );
}
