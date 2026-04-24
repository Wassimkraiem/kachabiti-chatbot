import type { NextRequest } from "next/server";

import { forwardJson } from "@/lib/backend";

type RouteContext = {
  params: Promise<{
    questionId: string;
  }>;
};

type QuestionPayload = {
  question: string;
  answer: string;
};

export async function PUT(request: NextRequest, context: RouteContext) {
  const payload = (await request.json()) as QuestionPayload;
  const { questionId } = await context.params;

  return forwardJson(`/api/v1/qdrant/questions/${questionId}`, {
    method: "PUT",
    payload
  });
}

export async function DELETE(_: NextRequest, context: RouteContext) {
  const { questionId } = await context.params;

  return forwardJson(`/api/v1/qdrant/questions/${questionId}`, {
    method: "DELETE"
  });
}
