import { AlertTriangle, CheckCircle2, FileWarning, Lightbulb } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge, RISK_LABELS_AR } from "@/components/ui/badge";
import type { ContractAnalysisResponse, RiskLevel } from "@/types/api";
import { cn } from "@/lib/utils";

export function ContractReport({ data }: { data: ContractAnalysisResponse }) {
  return (
    <div className="space-y-6">
      {/* Overall risk banner */}
      <Card className={cn("border-2", riskBorderClass(data.overall_risk_level))}>
        <CardContent className="flex items-center justify-between p-5">
          <div>
            <p className="text-xs font-bold text-muted-foreground mb-1">المستوى العام لخطورة العقد</p>
            <p className="text-lg font-extrabold">{RISK_LABELS_AR[data.overall_risk_level]}</p>
          </div>
          <Badge variant={data.overall_risk_level} className="text-sm px-3 py-1">
            {RISK_LABELS_AR[data.overall_risk_level]}
          </Badge>
        </CardContent>
      </Card>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle>ملخص العقد</CardTitle>
          <CardDescription>{data.summary.contract_type}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm leading-relaxed">{data.summary.overview_ar}</p>
          <div className="flex flex-wrap gap-4 text-sm">
            {data.summary.parties.length > 0 && (
              <div>
                <span className="font-bold">الأطراف: </span>
                {data.summary.parties.join("، ")}
              </div>
            )}
            {data.summary.duration && (
              <div>
                <span className="font-bold">المدة: </span>
                {data.summary.duration}
              </div>
            )}
            <div>
              <span className="font-bold">عدد البنود: </span>
              {data.summary.total_clauses}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Risks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            المخاطر المرصودة ({data.risks.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.risks.length === 0 && (
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" /> لم يتم رصد مخاطر جوهرية في هذا العقد.
            </p>
          )}
          {data.risks.map((r) => (
            <div key={r.clause_id} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <p className="text-sm font-bold">{r.clause_type}</p>
                <Badge variant={r.risk_level}>{RISK_LABELS_AR[r.risk_level]}</Badge>
              </div>
              <p className="text-sm text-muted-foreground mb-2">{r.simple_explanation_ar}</p>
              {r.risk_reason && <p className="text-xs text-amber-600 dark:text-amber-400 font-medium">{r.risk_reason}</p>}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Missing clauses */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileWarning className="h-5 w-5 text-orange-500" />
            بنود ناقصة ({data.missing_clauses.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.missing_clauses.length === 0 && (
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" /> جميع البنود الأساسية موجودة في العقد.
            </p>
          )}
          {data.missing_clauses.map((m, i) => (
            <div key={i} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <p className="text-sm font-bold">{m.clause_type}</p>
                <Badge variant={m.importance}>{RISK_LABELS_AR[m.importance]}</Badge>
              </div>
              <p className="text-sm text-muted-foreground">{m.description_ar}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lightbulb className="h-5 w-5 text-primary" />
            التوصيات
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm list-disc pr-5">
            {data.recommendations_ar.map((rec, i) => (
              <li key={i}>{rec}</li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* All clauses */}
      <Card>
        <CardHeader>
          <CardTitle>تحليل جميع البنود ({data.clauses.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.clauses.map((c) => (
            <div key={c.clause_id} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-2 gap-2">
                <p className="text-sm font-bold">{c.clause_type}</p>
                <Badge variant={c.risk_level}>{RISK_LABELS_AR[c.risk_level]}</Badge>
              </div>
              <p className="text-xs text-muted-foreground mb-2 leading-relaxed">{c.original_text}</p>
              <p className="text-sm leading-relaxed">{c.simple_explanation_ar}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function riskBorderClass(level: RiskLevel) {
  switch (level) {
    case "critical":
      return "border-red-400/60";
    case "high":
      return "border-orange-400/60";
    case "medium":
      return "border-amber-400/60";
    default:
      return "border-emerald-400/60";
  }
}
