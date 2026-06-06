import { useEffect, useRef, useState, useCallback } from "react";

const API = "/api";

async function fetchWithRetry(url: string, retries = 5, delayMs = 800): Promise<Response> {
  for (let i = 0; i < retries; i++) {
    const resp = await fetch(url);
    if (resp.ok) return resp;
    if (i < retries - 1) await new Promise(r => setTimeout(r, delayMs * (i + 1)));
  }
  throw new Error(`Failed to fetch ${url} after ${retries} attempts`);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Snapshot {
  name: string;
  project_id: string;
  state_description: string;
  status: string;
}

interface BranchInfo {
  id: string;
  name: string;
  parent_id?: string;
  parentName: string | null;
  hasChildren: boolean;
  isPrimary: boolean;
  created_at: string;
  logical_size?: number;
}

interface RunState {
  runId: string | null;
  running: boolean;
  exitCode: number | null;
  logs: string[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ROWS = [1, 2, 3, 4, 5];
const PASSES = ["3a", "3b", "3c", "3d", "3e"];
const PASS_LABELS: Record<string, string> = {
  "3a": "3a — Source Capture + RLSRA",
  "3b": "3b — CCI Construction",
  "3c": "3c — Domain Derivation",
  "3d": "3d — Requirement Derivation",
  "3e": "3e — Requirement Matching",
};

// ---------------------------------------------------------------------------
// Shared styles
// ---------------------------------------------------------------------------

const labelStyle: React.CSSProperties = {
  display: "flex", flexDirection: "column", gap: 5,
  fontSize: 13, fontWeight: 600, color: "#374151",
};
const inputStyle: React.CSSProperties = {
  border: "1px solid #d1d5db", borderRadius: 6, padding: "7px 10px",
  fontSize: 13, color: "#111", background: "#fff", outline: "none",
};
const fieldsetStyle: React.CSSProperties = {
  border: "1px solid #e5e7eb", borderRadius: 8, padding: "12px 16px", margin: 0,
};
const legendStyle: React.CSSProperties = {
  fontSize: 12, fontWeight: 700, color: "#374151",
  textTransform: "uppercase", letterSpacing: "0.05em", padding: "0 6px",
};
const checkLabelStyle: React.CSSProperties = {
  display: "flex", alignItems: "center", fontSize: 13,
  color: "#1e293b", cursor: "pointer", userSelect: "none",
};

// ---------------------------------------------------------------------------
// LaunchPage
// ---------------------------------------------------------------------------

function LaunchPage() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [inputs, setInputs] = useState<string[]>([]);
  const [outputs, setOutputs] = useState<string[]>([]);

  const [project, setProject] = useState("PMT_E2E");
  const [selectedRows, setSelectedRows] = useState<Set<number>>(new Set([1]));
  const [selectedPasses, setSelectedPasses] = useState<Set<string>>(new Set(["3b"]));
  const [snapshot, setSnapshot] = useState("");
  const [sourceDoc, setSourceDoc] = useState("");

  const [run, setRun] = useState<RunState>({ runId: null, running: false, exitCode: null, logs: [] });

  const logRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  const fetchOutputs = useCallback(() => {
    fetchWithRetry(`${API}/outputs`).then(r => r.json()).then(setOutputs).catch(() => {});
  }, []);

  const reloadConfig = useCallback(() => {
    fetchWithRetry(`${API}/snapshots`).then(r => r.json()).then(setSnapshots).catch(() => {});
    fetchWithRetry(`${API}/inputs`).then(r => r.json()).then(setInputs).catch(() => {});
    fetchOutputs();
  }, [fetchOutputs]);

  useEffect(() => { reloadConfig(); }, [reloadConfig]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [run.logs]);

  function toggleRow(r: number) {
    setSelectedRows(prev => { const n = new Set(prev); n.has(r) ? n.delete(r) : n.add(r); return n; });
  }
  function togglePass(p: string) {
    setSelectedPasses(prev => { const n = new Set(prev); n.has(p) ? n.delete(p) : n.add(p); return n; });
  }

  async function startRun() {
    if (run.running) return;
    if (!selectedRows.size || !selectedPasses.size) { alert("Select at least one row and one pass."); return; }

    setRun({ runId: null, running: true, exitCode: null, logs: [] });

    try {
      const resp = await fetch(`${API}/runs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project, rows: Array.from(selectedRows).sort((a, b) => a - b),
          passes: PASSES.filter(p => selectedPasses.has(p)),
          snapshot: snapshot || undefined,
          sourceDoc: sourceDoc || undefined,
        }),
      });

      if (resp.status === 409) {
        const body = await resp.json() as { error: string; runId: string };
        alert(`A run is already in progress (${body.runId}). Wait for it to finish.`);
        setRun(prev => ({ ...prev, running: false }));
        return;
      }
      if (!resp.ok) {
        const body = await resp.json() as { error: string };
        alert(`Failed to start run: ${body.error}`);
        setRun(prev => ({ ...prev, running: false }));
        return;
      }

      const { runId } = await resp.json() as { runId: string };
      setRun(prev => ({ ...prev, runId }));

      const es = new EventSource(`${API}/runs/${runId}/logs`);
      esRef.current = es;

      es.addEventListener("log", (e) => {
        const line = JSON.parse((e as MessageEvent).data) as string;
        setRun(prev => ({ ...prev, logs: [...prev.logs, line] }));
      });
      es.addEventListener("done", (e) => {
        const { exitCode } = JSON.parse((e as MessageEvent).data) as { exitCode: number };
        setRun(prev => ({ ...prev, running: false, exitCode }));
        es.close(); esRef.current = null;
        fetchOutputs();
      });
      es.onerror = () => { setRun(prev => ({ ...prev, running: false })); es.close(); esRef.current = null; };
    } catch {
      setRun(prev => ({ ...prev, running: false }));
    }
  }

  const runStatus = run.running ? "⟳ Running…"
    : run.exitCode === null ? ""
    : run.exitCode === 0 ? "✓ Completed successfully"
    : `✗ Exited with code ${run.exitCode}`;

  const statusColor = run.running ? "#2563eb"
    : run.exitCode === 0 ? "#16a34a"
    : run.exitCode !== null ? "#dc2626"
    : "#6b7280";

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
        <label style={labelStyle}>
          Project ID
          <input style={inputStyle} value={project} onChange={e => setProject(e.target.value)} placeholder="e.g. PMT_E2E" />
        </label>
        <label style={labelStyle}>
          Source Document <span style={{ color: "#9ca3af", fontWeight: 400 }}>(required for pass 3a)</span>
          <select style={inputStyle} value={sourceDoc} onChange={e => setSourceDoc(e.target.value)}>
            <option value="">— none —</option>
            {inputs.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
        </label>
      </div>

      <label style={{ ...labelStyle, display: "block", marginBottom: 20 }}>
        Source Snapshot <span style={{ color: "#9ca3af", fontWeight: 400 }}>(leave blank to clone fresh from primary branch)</span>
        <select style={{ ...inputStyle, width: "100%" }} value={snapshot} onChange={e => setSnapshot(e.target.value)}>
          <option value="">— clone fresh branch from primary (safe default) —</option>
          {snapshots.map(s => (
            <option key={s.name} value={s.name} title={s.state_description}>
              {s.name} — {s.state_description.slice(0, 80)}{s.state_description.length > 80 ? "…" : ""}
            </option>
          ))}
        </select>
      </label>

      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <button onClick={reloadConfig} style={{ fontSize: 11, color: "#6b7280", background: "none", border: "none", cursor: "pointer", padding: "2px 0" }}>
          ↻ Reload dropdowns
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
        <fieldset style={fieldsetStyle}>
          <legend style={legendStyle}>Rows</legend>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {ROWS.map(r => (
              <label key={r} style={checkLabelStyle}>
                <input type="checkbox" checked={selectedRows.has(r)} onChange={() => toggleRow(r)} style={{ marginRight: 5 }} />
                Row {r}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset style={fieldsetStyle}>
          <legend style={legendStyle}>Passes</legend>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {PASSES.map(p => (
              <label key={p} style={checkLabelStyle}>
                <input type="checkbox" checked={selectedPasses.has(p)} onChange={() => togglePass(p)} style={{ marginRight: 6 }} />
                {PASS_LABELS[p]}
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 20 }}>
        <button
          onClick={startRun}
          disabled={run.running}
          style={{
            background: run.running ? "#9ca3af" : "#2563eb", color: "#fff",
            border: "none", borderRadius: 6, padding: "8px 24px",
            fontSize: 14, fontWeight: 600, cursor: run.running ? "not-allowed" : "pointer",
          }}
        >
          {run.running ? "Running…" : "▶ Run"}
        </button>
        {runStatus && <span style={{ fontSize: 13, fontWeight: 500, color: statusColor }}>{runStatus}</span>}
      </div>

      {(run.logs.length > 0 || run.running) && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.05em" }}>Live Output</div>
          <div ref={logRef} style={{ background: "#0f172a", color: "#e2e8f0", fontFamily: "Menlo, Monaco, 'Courier New', monospace", fontSize: 12, lineHeight: 1.6, padding: "12px 14px", borderRadius: 8, height: 380, overflowY: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
            {run.logs.map((line, i) => (
              <div key={i} style={{ color: line.startsWith("[stderr]") ? "#f87171" : "#e2e8f0" }}>{line}</div>
            ))}
            {run.running && <div style={{ color: "#60a5fa", opacity: 0.7 }}>▌</div>}
          </div>
        </div>
      )}

      <div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", textTransform: "uppercase", letterSpacing: "0.05em" }}>Output Files ({outputs.length})</div>
          <button onClick={fetchOutputs} style={{ fontSize: 11, color: "#2563eb", background: "none", border: "none", cursor: "pointer", padding: "2px 6px" }}>↻ Refresh</button>
        </div>
        {outputs.length === 0 ? (
          <p style={{ color: "#9ca3af", fontSize: 13 }}>No output files yet.</p>
        ) : (
          <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Filename</th>
                  <th style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: "#374151", width: 80 }}>Download</th>
                </tr>
              </thead>
              <tbody>
                {outputs.map((f, i) => (
                  <tr key={f} style={{ borderBottom: i < outputs.length - 1 ? "1px solid #f3f4f6" : "none" }}>
                    <td style={{ padding: "7px 12px", color: "#1e293b", fontFamily: "monospace", fontSize: 12 }}>{f}</td>
                    <td style={{ padding: "7px 12px", textAlign: "right" }}>
                      <a href={`${API}/outputs/${f}`} download={f} style={{ color: "#2563eb", fontSize: 12, textDecoration: "none", fontWeight: 500 }}>↓</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BranchesPage
// ---------------------------------------------------------------------------

function fmt(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString(undefined, { dateStyle: "short", timeStyle: "short" });
}
function fmtSize(bytes?: number) {
  if (!bytes) return "—";
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function BranchesPage() {
  const [branches, setBranches] = useState<BranchInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<Set<string>>(new Set());
  const [deleteError, setDeleteError] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const resp = await fetchWithRetry(`${API}/branches`);
      const data = await resp.json() as BranchInfo[];
      setBranches(data);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function deleteBranch(b: BranchInfo) {
    if (b.hasChildren) return; // button is disabled, but belt-and-suspenders
    const confirmed = window.confirm(
      `Delete branch "${b.name}"?\n\nThis is permanent and cannot be undone.`
    );
    if (!confirmed) return;

    setDeleting(prev => new Set([...prev, b.id]));
    setDeleteError(prev => { const n = { ...prev }; delete n[b.id]; return n; });

    try {
      const resp = await fetch(`${API}/branches/${b.id}`, { method: "DELETE" });
      const body = await resp.json() as { error?: string; children?: string[] };
      if (!resp.ok) {
        setDeleteError(prev => ({ ...prev, [b.id]: body.error ?? "Delete failed" }));
      } else {
        setBranches(prev => prev.filter(x => x.id !== b.id));
      }
    } catch (e) {
      setDeleteError(prev => ({ ...prev, [b.id]: String(e) }));
    } finally {
      setDeleting(prev => { const n = new Set(prev); n.delete(b.id); return n; });
    }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <p style={{ margin: 0, fontSize: 13, color: "#6b7280" }}>
          Manage Neon test branches. Branches with child branches cannot be deleted — remove the children first.
        </p>
        <button onClick={load} disabled={loading} style={{ flexShrink: 0, fontSize: 12, color: "#2563eb", background: "none", border: "none", cursor: loading ? "not-allowed" : "pointer", padding: "2px 6px" }}>
          {loading ? "Loading…" : "↻ Refresh"}
        </button>
      </div>

      {error && (
        <div style={{ background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 6, padding: "10px 14px", color: "#dc2626", fontSize: 13, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {branches.length === 0 && !loading && !error && (
        <p style={{ color: "#9ca3af", fontSize: 13 }}>No branches found.</p>
      )}

      {branches.length > 0 && (
        <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ background: "#f9fafb", borderBottom: "1px solid #e5e7eb" }}>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Branch</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Parent</th>
                <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600, color: "#374151" }}>Created</th>
                <th style={{ padding: "8px 12px", textAlign: "right", fontWeight: 600, color: "#374151" }}>Size</th>
                <th style={{ padding: "8px 12px", textAlign: "center", fontWeight: 600, color: "#374151", width: 80 }}>Delete</th>
              </tr>
            </thead>
            <tbody>
              {branches.map((b, i) => {
                const isDeleting = deleting.has(b.id);
                const err = deleteError[b.id];
                const canDelete = !b.isPrimary && !b.hasChildren;

                let deleteTitle = "";
                if (b.isPrimary) deleteTitle = "Cannot delete the primary branch";
                else if (b.hasChildren) deleteTitle = "This branch has children — delete them first";

                return (
                  <tr key={b.id} style={{ borderBottom: i < branches.length - 1 ? "1px solid #f3f4f6" : "none", background: b.isPrimary ? "#f0fdf4" : undefined }}>
                    <td style={{ padding: "8px 12px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: "monospace", fontSize: 12, color: "#1e293b" }}>{b.name}</span>
                        {b.isPrimary && <span style={{ background: "#dcfce7", color: "#16a34a", fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 10, textTransform: "uppercase" }}>primary</span>}
                        {b.hasChildren && <span style={{ background: "#fef9c3", color: "#92400e", fontSize: 10, fontWeight: 700, padding: "1px 6px", borderRadius: 10, textTransform: "uppercase" }}>has children</span>}
                      </div>
                      {err && <div style={{ color: "#dc2626", fontSize: 11, marginTop: 3 }}>{err}</div>}
                    </td>
                    <td style={{ padding: "8px 12px", color: "#6b7280", fontSize: 12, fontFamily: "monospace" }}>
                      {b.parentName ?? "—"}
                    </td>
                    <td style={{ padding: "8px 12px", color: "#6b7280", fontSize: 12, whiteSpace: "nowrap" }}>
                      {fmt(b.created_at)}
                    </td>
                    <td style={{ padding: "8px 12px", color: "#6b7280", fontSize: 12, textAlign: "right", whiteSpace: "nowrap" }}>
                      {fmtSize(b.logical_size)}
                    </td>
                    <td style={{ padding: "8px 12px", textAlign: "center" }}>
                      <button
                        onClick={() => deleteBranch(b)}
                        disabled={!canDelete || isDeleting}
                        title={deleteTitle || "Delete this branch"}
                        style={{
                          background: canDelete && !isDeleting ? "#fef2f2" : "none",
                          color: canDelete && !isDeleting ? "#dc2626" : "#d1d5db",
                          border: `1px solid ${canDelete && !isDeleting ? "#fecaca" : "#e5e7eb"}`,
                          borderRadius: 5,
                          padding: "3px 10px",
                          fontSize: 12,
                          fontWeight: 500,
                          cursor: canDelete && !isDeleting ? "pointer" : "not-allowed",
                        }}
                      >
                        {isDeleting ? "…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// App shell — tab navigation
// ---------------------------------------------------------------------------

type Tab = "launch" | "branches";

export default function App() {
  const [tab, setTab] = useState<Tab>("launch");

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "8px 18px",
    fontSize: 14,
    fontWeight: 600,
    border: "none",
    borderBottom: tab === t ? "2px solid #2563eb" : "2px solid transparent",
    background: "none",
    color: tab === t ? "#2563eb" : "#6b7280",
    cursor: "pointer",
    marginBottom: -1,
  });

  return (
    <div style={{ fontFamily: "system-ui, -apple-system, sans-serif", maxWidth: 960, margin: "0 auto", padding: "24px 16px", color: "#111" }}>
      <h1 style={{ fontSize: 22, fontWeight: 700, margin: "0 0 16px" }}>SysEngage Run Launcher</h1>

      {/* Tab bar */}
      <div style={{ display: "flex", borderBottom: "1px solid #e5e7eb", marginBottom: 24 }}>
        <button style={tabStyle("launch")} onClick={() => setTab("launch")}>▶ Run</button>
        <button style={tabStyle("branches")} onClick={() => setTab("branches")}>⑂ Branches</button>
      </div>

      {tab === "launch" && <LaunchPage />}
      {tab === "branches" && <BranchesPage />}
    </div>
  );
}
