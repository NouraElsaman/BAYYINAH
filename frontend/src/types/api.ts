export type LegalDomain =
  | "labor_law"
  | "tenancy_law"
  | "family_law"
  | "civil_law"
  | "criminal_law"
  | "commercial_law"
  | "administrative_law"
  | "unknown";

export interface Citation {
  chunk_id: string;
  doc_id: string;
  law_name: string;
  law_number?: string | null;
  law_year?: string | null;
  law_type?: string | null;
  category?: string | null;
  article_number?: string | null;
  text: string;
  score: number;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  domain: LegalDomain;
  faithfulness_score?: number | null;
  is_fallback: boolean;
  warnings: string[];
  request_id?: string | null;
}

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface ClauseAnalysis {
  clause_id: string;
  original_text: string;
  simple_explanation_ar: string;
  clause_type: string;
  risk_level: RiskLevel;
  risk_reason?: string | null;
}

export interface MissingClause {
  clause_type: string;
  description_ar: string;
  importance: RiskLevel;
}

export interface ContractSummary {
  overview_ar: string;
  parties: string[];
  contract_type: string;
  duration?: string | null;
  total_clauses: number;
}

export interface ContractAnalysisResponse {
  document_id: string;
  filename: string;
  summary: ContractSummary;
  clauses: ClauseAnalysis[];
  risks: ClauseAnalysis[];
  missing_clauses: MissingClause[];
  recommendations_ar: string[];
  overall_risk_level: RiskLevel;
  warnings: string[];
  request_id?: string | null;
}

export interface ChatHistoryEntry {
  id: string;
  question: string;
  answer: string;
  domain: LegalDomain;
  citations: Citation[];
  is_fallback: boolean;
  timestamp: number;
}
