import { Router, type IRouter, type Request, type Response } from "express";
import { spawn } from "child_process";
import { randomUUID } from "crypto";
import fs from "fs";
import path from "path";
import { logger } from "../lib/logger";
import { getProjectId } from "../lib/neon";
import { listBranches } from "./branches";

const router: IRouter = Router();

// ---------------------------------------------------------------------------
// Workspace root resolution (stable between dev and production)
// ---------------------------------------------------------------------------

const workspaceRoot = process.cwd().endsWith(path.join("artifacts", "api-server"))
  ? path.resolve(process.cwd(), "../..")
  : process.cwd();

const REGISTRY_PATH = path.join(workspaceRoot, "sysengage", "test_infrastructure", "snapshot_registry.json");
const INPUTS_DIR    = path.join(workspaceRoot, "verification_inputs");
const OUTPUTS_DIR   = path.join(workspaceRoot, "verification_outputs");
const DISPATCH_SCRIPT = path.join(workspaceRoot, "sysengage", "run_dispatch.py");

// ---------------------------------------------------------------------------
// In-memory run store
// ---------------------------------------------------------------------------

interface RunRecord {
  runId: string;
  startedAt: string;
  args: Record<string, unknown>;
  logs: string[];
  done: boolean;
  exitCode: number | null;
  subscribers: Set<Response>;
}

const runs = new Map<string, RunRecord>();

function broadcast(rec: RunRecord, event: string, data: string) {
  const payload = `event: ${event}\ndata: ${data}\n\n`;
  for (const res of rec.subscribers) {
    try { res.write(payload); } catch { /* client disconnected */ }
  }
}

// ---------------------------------------------------------------------------
// GET /api/snapshots
// ---------------------------------------------------------------------------

router.get("/snapshots", async (_req: Request, res: Response) => {
  try {
    // Load registry for state_description metadata (may be stale — used for enrichment only)
    let registryByName = new Map<string, { state_description?: string }>();
    try {
      const raw = fs.readFileSync(REGISTRY_PATH, "utf-8");
      const parsed = JSON.parse(raw) as { snapshots?: Array<{ name: string; state_description?: string }> };
      for (const s of parsed.snapshots ?? []) {
        registryByName.set(s.name, s);
      }
    } catch { /* registry missing or malformed — proceed without descriptions */ }

    // Neon is the source of truth: fetch live branches and filter to snap_* only
    const projectId = await getProjectId();
    const branches = await listBranches(projectId);
    const snapBranches = branches
      .filter(b => b.name.startsWith("snap_"))
      .sort((a, b) => a.name.localeCompare(b.name));

    // Join with registry for description
    const result = snapBranches.map(b => ({
      name: b.name,
      neon_branch_id: b.id,
      created_at: b.created_at,
      state_description: registryByName.get(b.name)?.state_description ?? null,
    }));

    res.json(result);
  } catch (err) {
    logger.error({ err }, "Failed to list snapshots");
    res.status(500).json({ error: String(err) });
  }
});

// ---------------------------------------------------------------------------
// GET /api/inputs
// ---------------------------------------------------------------------------

router.get("/inputs", (_req: Request, res: Response) => {
  try {
    const files = fs.readdirSync(INPUTS_DIR)
      .filter(f => !f.startsWith("."))
      .sort();
    res.json(files);
  } catch (err) {
    logger.error({ err }, "Failed to read inputs dir");
    res.status(500).json({ error: "Failed to read verification_inputs/" });
  }
});

// ---------------------------------------------------------------------------
// GET /api/outputs
// ---------------------------------------------------------------------------

router.get("/outputs", (_req: Request, res: Response) => {
  try {
    const files = fs.readdirSync(OUTPUTS_DIR)
      .filter(f => !f.startsWith(".") && f.endsWith(".json"))
      .sort()
      .reverse(); // newest first
    res.json(files);
  } catch (err) {
    logger.error({ err }, "Failed to read outputs dir");
    res.status(500).json({ error: "Failed to read verification_outputs/" });
  }
});

// ---------------------------------------------------------------------------
// GET /api/outputs/:filename  — download a specific output file
// ---------------------------------------------------------------------------

router.get("/outputs/:filename", (req: Request, res: Response) => {
  const filename = path.basename(String(req.params["filename"] ?? ""));
  if (!filename.endsWith(".json")) {
    res.status(400).json({ error: "Only .json files are served" });
    return;
  }
  const filepath = path.join(OUTPUTS_DIR, filename);
  if (!fs.existsSync(filepath)) {
    res.status(404).json({ error: "File not found" });
    return;
  }
  res.download(filepath);
});

// ---------------------------------------------------------------------------
// POST /api/runs  — start a new run
// ---------------------------------------------------------------------------

router.post("/runs", (req: Request, res: Response) => {
  const { project, rows, passes, snapshot, sourceDoc } = req.body as {
    project?: string;
    rows?: number[];
    passes?: string[];
    snapshot?: string;
    sourceDoc?: string;
  };

  if (!project || !rows?.length || !passes?.length) {
    res.status(400).json({ error: "project, rows, and passes are required" });
    return;
  }

  // Reject if another run is in progress
  for (const rec of runs.values()) {
    if (!rec.done) {
      res.status(409).json({ error: "A run is already in progress", runId: rec.runId });
      return;
    }
  }

  const runId = randomUUID();
  const rec: RunRecord = {
    runId,
    startedAt: new Date().toISOString(),
    args: { project, rows, passes, snapshot, sourceDoc },
    logs: [],
    done: false,
    exitCode: null,
    subscribers: new Set(),
  };
  runs.set(runId, rec);

  // Build argv for run_dispatch.py
  const argv: string[] = [
    "-u",
    DISPATCH_SCRIPT,
    "--project", project,
    "--rows", rows.join(","),
    "--passes", passes.join(","),
  ];
  if (snapshot) argv.push("--snapshot", snapshot);
  if (sourceDoc) argv.push("--source-doc", sourceDoc);

  // Inherit env (includes NEON_DATABASE_URL, ANTHROPIC_API_KEY, etc.)
  const child = spawn("python", argv, {
    cwd: workspaceRoot,
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
    stdio: ["ignore", "pipe", "pipe"],
  });

  function handleLine(line: string) {
    rec.logs.push(line);
    broadcast(rec, "log", JSON.stringify(line));
  }

  let stdoutBuf = "";
  let stderrBuf = "";

  child.stdout?.on("data", (chunk: Buffer) => {
    stdoutBuf += chunk.toString();
    const lines = stdoutBuf.split("\n");
    stdoutBuf = lines.pop() ?? "";
    for (const l of lines) handleLine(l);
  });

  child.stderr?.on("data", (chunk: Buffer) => {
    stderrBuf += chunk.toString();
    const lines = stderrBuf.split("\n");
    stderrBuf = lines.pop() ?? "";
    for (const l of lines) handleLine(`[stderr] ${l}`);
  });

  child.on("close", (code) => {
    if (stdoutBuf) { handleLine(stdoutBuf); stdoutBuf = ""; }
    if (stderrBuf) { handleLine(`[stderr] ${stderrBuf}`); stderrBuf = ""; }
    rec.done = true;
    rec.exitCode = code;
    broadcast(rec, "done", JSON.stringify({ exitCode: code }));
    for (const sub of rec.subscribers) {
      try { sub.end(); } catch { /* ignore */ }
    }
    rec.subscribers.clear();
    logger.info({ runId, code }, "Run finished");
  });

  logger.info({ runId, project, rows, passes }, "Run started");
  res.status(202).json({ runId });
});

// ---------------------------------------------------------------------------
// GET /api/runs/:id/logs  — SSE log stream
// ---------------------------------------------------------------------------

router.get("/runs/:id/logs", (req: Request, res: Response) => {
  const rec = runs.get(String(req.params["id"] ?? ""));
  if (!rec) {
    res.status(404).json({ error: "Run not found" });
    return;
  }

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.setHeader("X-Accel-Buffering", "no");
  res.flushHeaders();

  // Replay buffered logs
  for (const line of rec.logs) {
    res.write(`event: log\ndata: ${JSON.stringify(line)}\n\n`);
  }

  if (rec.done) {
    res.write(`event: done\ndata: ${JSON.stringify({ exitCode: rec.exitCode })}\n\n`);
    res.end();
    return;
  }

  rec.subscribers.add(res);
  req.on("close", () => { rec.subscribers.delete(res); });
});

// ---------------------------------------------------------------------------
// GET /api/runs  — list recent runs
// ---------------------------------------------------------------------------

router.get("/runs", (_req: Request, res: Response) => {
  const list = Array.from(runs.values())
    .map(({ runId, startedAt, args, done, exitCode, logs }) => ({
      runId,
      startedAt,
      args,
      done,
      exitCode,
      logLines: logs.length,
    }))
    .sort((a, b) => b.startedAt.localeCompare(a.startedAt));
  res.json(list);
});

export default router;
