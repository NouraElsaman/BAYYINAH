import { Citation } from "@/types/api";
import { ScrollText } from "lucide-react";

export function CitationCard({ citation, index }: { citation: Citation; index: number }) {
  const lawRef = [citation.law_name, citation.law_number && `رقم ${citation.law_number}`, citation.law_year && `لسنة ${citation.law_year}`]
    .filter(Boolean)
    .join(" ");

  return (
    <div className="relative rounded-lg border border-border bg-muted/40 overflow-hidden">
      <div className="absolute top-0 right-0 h-full w-1.5 bg-primary" />
      <div className="p-4 pr-5">
        <div className="flex items-start justify-between gap-3 mb-2">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border-2 border-primary/40 text-primary font-extrabold text-sm shrink-0">
              {citation.article_number || index + 1}
            </div>
            <div>
              <p className="text-sm font-bold leading-tight">
                {citation.article_number ? `المادة ${citation.article_number}` : `مصدر ${index + 1}`}
              </p>
              <p className="text-xs text-muted-foreground">{lawRef}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 text-xs text-muted-foreground shrink-0">
            <ScrollText className="h-3.5 w-3.5" />
            {(citation.score * 100).toFixed(0)}%
          </div>
        </div>
        <p className="text-sm leading-relaxed text-foreground/90">{citation.text}</p>
      </div>
    </div>
  );
}
