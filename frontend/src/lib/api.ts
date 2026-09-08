import type { ChatResponse, ContractAnalysisResponse } from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function sendChatMessage(
  question: string,
  conversationId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || "حدث خطأ في الاتصال بالخادم", res.status);
  }

  return res.json();
}

export async function streamChatMessage(
  question: string,
  conversationId: string | undefined,
  onToken: (token: string) => void,
  onDone: (data: any) => void,
  onError: (message: string) => void
): Promise<void> {
  try {
    const res = await fetch(`${API_URL}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: conversationId, stream: true }),
    });

    if (!res.ok || !res.body) {
      onError("حدث خطأ في الاتصال بالخادم");
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const event of events) {
        const line = event.trim();
        if (!line.startsWith("data:")) continue;
        const jsonStr = line.slice(5).trim();
        try {
          const data = JSON.parse(jsonStr);
          if (data.type === "token") {
            onToken(data.content);
          } else if (data.type === "done") {
            onDone(data);
          } else if (data.type === "error") {
            onError(data.message);
          }
        } catch {
          // ignore malformed chunk
        }
      }
    }
  } catch (e) {
    onError("تعذر الاتصال بالخادم. حاول مرة أخرى.");
  }
}

export async function analyzeContract(file: File): Promise<ContractAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_URL}/contract-analysis`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail || "تعذر تحليل العقد", res.status);
  }

  return res.json();
}

export async function fetchHealth(): Promise<any> {
  const res = await fetch(`${API_URL}/health`);
  return res.json();
}

export async function submitFeedback(
  conversationId: string,
  question: string,
  answer: string,
  isCorrect: boolean
): Promise<void> {
  await fetch(`${API_URL}/chat/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      question,
      answer,
      is_correct: isCorrect,
    }),
  }).catch(() => {/* silent fail – feedback is best-effort */});
}
