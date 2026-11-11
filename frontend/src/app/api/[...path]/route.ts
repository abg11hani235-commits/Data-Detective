import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8000";

async function proxyRequest(req: NextRequest, paramsPromise: Promise<{ path: string[] }>) {
  const { path } = await paramsPromise;
  const targetPath = path ? path.join("/") : "";
  const targetUrl = `${BACKEND_URL}/api/${targetPath}${req.nextUrl.search}`;

  const forwardHeaders = new Headers();
  req.headers.forEach((val, key) => {
    const lowerKey = key.toLowerCase();
    if (!["host", "connection", "keep-alive"].includes(lowerKey)) {
      forwardHeaders.set(key, val);
    }
  });

  const fetchOptions: RequestInit = {
    method: req.method,
    headers: forwardHeaders,
    cache: "no-store",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    const contentType = req.headers.get("content-type") || "";
    if (contentType.includes("multipart/form-data") || contentType.includes("application/json")) {
      fetchOptions.body = req.body;
      // @ts-ignore
      fetchOptions.duplex = "half";
    } else {
      const buffer = await req.arrayBuffer();
      if (buffer.byteLength > 0) {
        fetchOptions.body = buffer;
      }
    }
  }

  try {
    const res = await fetch(targetUrl, fetchOptions);
    const resHeaders = new Headers();
    res.headers.forEach((val, key) => {
      const lowerKey = key.toLowerCase();
      if (!["content-encoding", "content-length"].includes(lowerKey)) {
        resHeaders.set(key, val);
      }
    });

    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: resHeaders,
    });
  } catch (err: any) {
    return new Response(
      JSON.stringify({ detail: `Backend proxy error: ${err.message || String(err)}` }),
      {
        status: 502,
        headers: { "Content-Type": "application/json" },
      }
    );
  }
}

export async function GET(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, context.params);
}

export async function POST(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, context.params);
}

export async function PUT(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, context.params);
}

export async function DELETE(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, context.params);
}

export async function OPTIONS(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxyRequest(req, context.params);
}
