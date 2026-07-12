export const dynamic = "force-dynamic";

const BACKEND_URL = (process.env.BACKEND_URL || "http://localhost:8000").replace(/\/$/, "");

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/health`, { cache: "no-store" });
    return Response.json({ online: response.ok }, { status: response.ok ? 200 : 503 });
  } catch {
    return Response.json({ online: false }, { status: 503 });
  }
}
