// frontend/lib/agentApi.ts
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export interface AgentResponse {
  query: string;
  response: string;
  steps_taken: number;
}

export async function askAuditAgent(query: string): Promise<AgentResponse> {
  const res = await fetch(`${BACKEND_URL}/api/v1/agent/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!res.ok) {
    throw new Error(`Agent request failed: ${res.statusText}`);
  }
  return res.json();
}

export async function getTelemetryMetrics() {
  const res = await fetch(`${BACKEND_URL}/api/v1/observability/metrics`);
  if (!res.ok) throw new Error("Failed to fetch telemetry");
  return res.json();
}