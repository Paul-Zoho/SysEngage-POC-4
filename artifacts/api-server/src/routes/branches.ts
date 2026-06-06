import { Router, type IRouter, type Request, type Response } from "express";
import { logger } from "../lib/logger";

const router: IRouter = Router();

const NEON_API_BASE = "https://console.neon.tech/api/v2";

// ---------------------------------------------------------------------------
// Neon API helpers
// ---------------------------------------------------------------------------

function neonApiKey(): string {
  const key = process.env["NEON_API_KEY"];
  if (!key) throw new Error("NEON_API_KEY is not set");
  return key;
}

async function neonGet(path: string): Promise<unknown> {
  const resp = await fetch(`${NEON_API_BASE}${path}`, {
    headers: { Authorization: `Bearer ${neonApiKey()}`, "Content-Type": "application/json" },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Neon API ${path} → ${resp.status}: ${body}`);
  }
  return resp.json();
}

async function neonDelete(path: string): Promise<void> {
  const resp = await fetch(`${NEON_API_BASE}${path}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${neonApiKey()}` },
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Neon DELETE ${path} → ${resp.status}: ${body}`);
  }
}

// ---------------------------------------------------------------------------
// Project-ID resolution — read NEON_PROJECT_ID or auto-detect from API
// ---------------------------------------------------------------------------

let _cachedProjectId: string | null = null;

async function getProjectId(): Promise<string> {
  if (_cachedProjectId) return _cachedProjectId;
  const fromEnv = process.env["NEON_PROJECT_ID"];
  if (fromEnv) { _cachedProjectId = fromEnv; return fromEnv; }

  // Project-scoped API keys cannot call /projects — but the 404 error body
  // contains the project ID as `subject_project_id:"<id>"`. Parse it.
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

// ---------------------------------------------------------------------------
// Branch shape
// ---------------------------------------------------------------------------

interface NeonBranch {
  id: string;
  name: string;
  parent_id?: string;
  primary?: boolean;
  default?: boolean;
  created_at: string;
  updated_at?: string;
  logical_size?: number;
}

interface BranchInfo extends NeonBranch {
  parentName: string | null;
  hasChildren: boolean;
  isPrimary: boolean;
}

async function listBranches(projectId: string): Promise<BranchInfo[]> {
  const data = await neonGet(`/projects/${projectId}/branches`) as { branches?: NeonBranch[] };
  const raw: NeonBranch[] = data.branches ?? [];

  // Index by id for parent-name lookup and child detection
  const byId = new Map(raw.map(b => [b.id, b]));
  const childCount = new Map<string, number>();
  for (const b of raw) {
    if (b.parent_id) childCount.set(b.parent_id, (childCount.get(b.parent_id) ?? 0) + 1);
  }

  return raw.map(b => ({
    ...b,
    parentName: b.parent_id ? (byId.get(b.parent_id)?.name ?? b.parent_id) : null,
    hasChildren: (childCount.get(b.id) ?? 0) > 0,
    isPrimary: !!(b.primary || b.default),
  }));
}

// ---------------------------------------------------------------------------
// GET /api/branches
// ---------------------------------------------------------------------------

router.get("/branches", async (_req: Request, res: Response) => {
  try {
    const projectId = await getProjectId();
    const branches = await listBranches(projectId);
    // Sort: primary first, then newest first
    branches.sort((a, b) => {
      if (a.isPrimary !== b.isPrimary) return a.isPrimary ? -1 : 1;
      return b.created_at.localeCompare(a.created_at);
    });
    res.json(branches);
  } catch (err) {
    logger.error({ err }, "Failed to list branches");
    res.status(500).json({ error: String(err) });
  }
});

// ---------------------------------------------------------------------------
// DELETE /api/branches/:id
// ---------------------------------------------------------------------------

router.delete("/branches/:id", async (req: Request, res: Response) => {
  const branchId = String(req.params["id"] ?? "");
  if (!branchId) { res.status(400).json({ error: "Branch ID required" }); return; }

  try {
    const projectId = await getProjectId();
    const branches = await listBranches(projectId);

    const target = branches.find(b => b.id === branchId);
    if (!target) { res.status(404).json({ error: "Branch not found" }); return; }

    if (target.isPrimary) {
      res.status(409).json({ error: "Cannot delete the primary branch" });
      return;
    }

    if (target.hasChildren) {
      const children = branches
        .filter(b => b.parent_id === branchId)
        .map(b => b.name);
      res.status(409).json({
        error: `Branch '${target.name}' has ${children.length} child branch${children.length === 1 ? "" : "es"} and cannot be deleted. Delete the children first.`,
        children,
      });
      return;
    }

    await neonDelete(`/projects/${projectId}/branches/${branchId}`);
    logger.info({ branchId, name: target.name }, "Branch deleted");
    res.json({ deleted: true, name: target.name });
  } catch (err) {
    logger.error({ err }, "Failed to delete branch");
    res.status(500).json({ error: String(err) });
  }
});

export default router;
