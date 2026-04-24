import { NextResponse } from "next/server";

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

type ForwardJsonOptions = {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  payload?: unknown;
};

function getBackendUrl(): string {
  return (process.env.BACKEND_URL || DEFAULT_BACKEND_URL).replace(/\/$/, "");
}

export async function forwardJson(path: string, { method = "GET", payload }: ForwardJsonOptions = {}) {
  try {
    const response = await fetch(`${getBackendUrl()}${path}`, {
      method,
      headers: payload ? { "content-type": "application/json" } : undefined,
      body: payload ? JSON.stringify(payload) : undefined,
      cache: "no-store"
    });

    const text = await response.text();
    return new Response(text, {
      status: response.status,
      headers: {
        "content-type": response.headers.get("content-type") || "application/json"
      }
    });
  } catch (error) {
    return NextResponse.json(
      {
        detail: `Unable to reach the FastAPI backend at ${getBackendUrl()}.`,
        error: String(error)
      },
      { status: 503 }
    );
  }
}
