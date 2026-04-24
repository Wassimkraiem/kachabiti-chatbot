import type { NextRequest } from "next/server";

import { forwardJson } from "@/lib/backend";

type QuestionPayload = {
  question: string;
  answer: string;
};

export async function GET(request: NextRequest) {
  const search = request.nextUrl.searchParams.toString();
  return forwardJson(`/api/v1/qdrant/questions${search ? `?${search}` : ""}`);
}

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as QuestionPayload;
  return forwardJson("/api/v1/qdrant/questions", {
    method: "POST",
    payload
  });
}
