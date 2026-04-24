import type { NextRequest } from "next/server";

import { forwardJson } from "@/lib/backend";

export async function POST(request: NextRequest) {
  const payload = (await request.json()) as {
    history?: Array<{ role: string; content: string }>;
    message?: string;
  };

  return forwardJson("/api/v1/chat/completions", {
    method: "POST",
    payload
  });
}
