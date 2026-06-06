import { Router, type IRouter, type Request, type Response } from "express";
import { logger } from "../lib/logger";
import { neonGet, neonDelete, getProjectId } from "../lib/neon";

const router: IRouter = Router();

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

export async function listBranches(projectId: string): Promise<BranchInfo[]> {
  const data = await neonGet(`/projects/${projectId}/branches`) as { branches?: NeonBranch[] };
  const raw: NeonBranch[] = data.branches ?? [];

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
