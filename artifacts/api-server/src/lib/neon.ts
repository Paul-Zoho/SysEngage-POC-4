const NEON_API_BASE = "https://console.neon.tech/api/v2";

function neonApiKey(): string {
  const key = process.env["NEON_API_KEY"];
  if (!key) throw new Error("NEON_API_KEY is not set");
  return key;
}

export async function neonGet(path: string): Promise<unknown> {
  const resp = await fetch(`${NEON_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${neonApiKey()}`, "Content-Type": "application/json" },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Neon API ${path} → ${resp.status}: ${body}`);
  }
  return resp.json();
}

export async function neonDelete(path: string): Promise<void> {
  const resp = await fetch(`${NEON_API_BASE}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${neonApiKey()}` },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Neon DELETE ${path} → ${resp.status}: ${body}`);
  }
}

let _cachedProjectId: string | null = null;

export async function getProjectId(): Promise<string> {
  if (_cachedProjectId) return _cachedProjectId;
  const fromEnv = process.env["NEON_PROJECT_ID"];
  if (fromEnv) { _cachedProjectId = fromEnv; return fromEnv; }

  const resp = await fetch(`${NEON_API_BASE}/projects`, {
    headers: { Authorization: `Bearer ${neonApiKey()}`, "Content-Type": "application/json" },
  });
  const body = await resp.text();

  if (!resp.ok) {
    const match = body.match(/subject_project_id[^a-z0-9-]*([a-z0-9-]+)/);
    if (match?.[1]) { _cachedProjectId = match[1]; return match[1]; }
    throw new Error(`Cannot determine Neon project ID. Set NEON_PROJECT_ID. (${body})`);
  }

  const data = JSON.parse(body) as { projects?: Array<{ id: string }> };
  const projects = data.projects ?? [];
  if (projects.length === 0) throw new Error("No Neon projects found");
  if (projects.length > 1) throw new Error("Multiple Neon projects — set NEON_PROJECT_ID");
  _cachedProjectId = projects[0].id;
  return _cachedProjectId;
}
