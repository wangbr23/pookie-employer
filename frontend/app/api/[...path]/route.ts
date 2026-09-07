import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
const API_SECRET = process.env.API_SECRET;

const FORWARDED_HEADERS = ["content-type", "accept", "x-request-id"];

async function proxyToBackend(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> },
) {
  if (!API_SECRET) {
    return Response.json(
      { detail: { code: "misconfigured", message: "API_SECRET is not set." } },
      { status: 502 },
    );
  }

  const { path } = await params;
  const backendPath = `/api/${path.join("/")}`;
  const url = new URL(backendPath, BACKEND_URL);
  url.search = request.nextUrl.search;

  const headers = new Headers();
  headers.set("authorization", `Bearer ${API_SECRET}`);
  for (const name of FORWARDED_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.arrayBuffer()
      : undefined;

  const upstream = await fetch(url, {
    method: request.method,
    headers,
    body,
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      ...(upstream.headers.get("x-request-id")
        ? { "x-request-id": upstream.headers.get("x-request-id")! }
        : {}),
    },
  });
}

export const GET = proxyToBackend;
export const POST = proxyToBackend;
export const PUT = proxyToBackend;
export const PATCH = proxyToBackend;
export const DELETE = proxyToBackend;
