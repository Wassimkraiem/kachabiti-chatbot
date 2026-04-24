type ErrorPayload = {
  detail?: string;
};

type QuestionItem = {
  id: string;
  question: string;
  answer: string;
  updated_at?: string | null;
};

export function sortQuestions(items: QuestionItem[]): QuestionItem[] {
  return [...items].sort((left, right) => {
    const leftTime = left.updated_at ? new Date(left.updated_at).getTime() : 0;
    const rightTime = right.updated_at ? new Date(right.updated_at).getTime() : 0;
    if (leftTime !== rightTime) {
      return rightTime - leftTime;
    }
    return left.question.localeCompare(right.question);
  });
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (!error) {
    return fallback;
  }
  if (typeof error === "string") {
    return error;
  }
  if (error instanceof Error) {
    return error.message || fallback;
  }
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = (error as ErrorPayload).detail;
    return typeof detail === "string" && detail ? detail : fallback;
  }
  return fallback;
}

export async function readJson<T>(response: Response): Promise<T> {
  const body = (await response.json().catch(() => ({}))) as ErrorPayload & T;
  if (!response.ok) {
    throw new Error(getErrorMessage(body, "The request failed."));
  }
  return body;
}

export function formatTimestamp(timestamp?: string | null): string {
  if (!timestamp) {
    return "No timestamp";
  }
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "No timestamp";
  }
  return date.toLocaleString();
}
