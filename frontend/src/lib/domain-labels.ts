import type { LegalDomain } from "@/types/api";

export const DOMAIN_LABELS_AR: Record<LegalDomain, string> = {
  labor_law: "قانون العمل",
  tenancy_law: "قانون الإيجارات",
  family_law: "الأحوال الشخصية",
  civil_law: "القانون المدني",
  criminal_law: "القانون الجنائي",
  commercial_law: "القانون التجاري",
  administrative_law: "القانون الإداري",
  unknown: "عام",
};
