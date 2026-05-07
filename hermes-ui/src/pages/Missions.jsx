/* hermes-ui/src/pages/Missions.jsx — Phase 15: Autonomous Mission Planner */
import { useState, useEffect, useRef } from "react"
import axios from "axios"

// ── Tool badge (same pattern as Chat.jsx) ──────────────────────────────
const TOOL_COLORS = {
  fs_write: "#ffd93d", fs_delete: "#ffd93d", fs_list: "#ffd93d", fs_read: "#ffd93d",
  search_web: "#6bcb77", weather_current: "#6bcb77",
  browser_go: "#4ecdc4", browser_read: "#4ecdc4",
  gmail_send: "#ff6b6b", gmail_list: "#ff6b6b",
  calendar_create: "#ff922b", calendar_list: "#ff922b",
  telegram_send: "#74c0fc",
  notion_list: "#f5a623", notion_create: "#f5a623", notion_read: "#f5a623",
  slack_send: "#e01e5a", slack_channels: "#e01e5a", slack_read: "#e01e5a",
  spotify_play: "#1db954", spotify_current: "#1db954",
  whatsapp_send: "#25d366",
  github_repos: "#a78bfa", github_issues: "#a78bfa",
}
function ToolBadge({ tool }) {
  if (!tool) return null
  const color = TOOL_COLORS[tool] || "#888"
  return (
    <span style={{
      display: "inline-block", padding: "1px 7px", marginRight: 4,
      background: `${color}22`, border: `1px solid ${color}55`,
      color, fontSize: 8, fontFamily: "Space Mono,monospace",
      letterSpacing: 1, borderRadius: 2, textTransform: "uppercase",
    }}>
      {tool.replace(/_/g, " ")}
    </span>
  )
}

// ── Event type config ──────────────────────────────────────────────────
const EVENT_CFG = {
  mission_started:    { label: "STARTED",   color: "#c8ff00" },
  mission_plan_ready: { label: "PLANNED",   color: "#74c0fc" },
  mission_step_start: { label: "STEP",      color: "#ffd93d" },
  mission_step_done:  { label: "DONE",      color: "#6bcb77" },
  mission_complete:   { label: "COMPLETE",  color: "#c8ff00" },
  mission_failed:     { label: "FAILED",    color: "#ff6b6b" },
}

// ── Status badge ───────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const cfg = {
    queued:  { color: "#888",    label: "QUEUED"  },
    running: { color: "#c8ff00", label: "RUNNING" },
    done:    { color: "#6bcb77", label: "DONE"    },
    failed:  { color: "#ff6b6b", label: "FAILED"  },
  }[status] || { color: "#888", label: status.toUpperCase() }
  return (
    <span style={{
      padding: "1px 7px", fontSize: 7, fontFamily: "Space Mono,monospace",
      letterSpacing: 2, border: `1px solid ${cfg.color}55`,
      color: cfg.color, background: `${cfg.color}18`, borderRadius: 2,
      animation: status === "running" ? "pulse 1s infinite" : "none",
    }}>
      {cfg.label}
    </span>
  )
}

// ── Save-template modal ────────────────────────────────────────────────
function SaveModal({ prompt, onSave, onClose }) {
  const [name, setName] = useState("")
  const [desc, setDesc] = useState("")
  const inp = { background: "transparent", border: "1px solid var(--border2)",
    color: "var(--white)", fontFamily: "Space Mono,monospace", fontSize: 11,
    padding: "8px 12px", width: "100%", outline: "none", boxSizing: "border-box", marginBottom: 8 }
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,.7)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 999,
    }}>
      <div style={{
        background: "var(--black2)", border: "1px solid var(--border2)",
        padding: 24, width: 400, fontFamily: "Space Mono,monospace",
      }}>
        <div style={{ fontSize: 10, letterSpacing: 2, color: "var(--accent)", marginBottom: 16 }}>
          SAVE TEMPLATE
        </div>
        <input style={inp} placeholder="Template name..." value={name} onChange={e => setName(e.target.value)} />
        <input style={inp} placeholder="Short description..." value={desc} onChange={e => setDesc(e.target.value)} />
        <div style={{ fontSize: 9, color: "var(--dim2)", marginBottom: 12 }}>
          Prompt: {prompt.slice(0, 80)}{prompt.length > 80 ? "..." : ""}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => { if (name.trim()) onSave(name.trim(), desc.trim()) }}
            style={{ flex: 1, padding: "8px 0", background: "var(--accent)", color: "#000",
              border: "none", fontFamily: "Space Mono,monospace", fontSize: 9, letterSpacing: 2,
              textTransform: "uppercase", cursor: "pointer" }}
          >SAVE</button>
          <button
            onClick={onClose}
            style={{ flex: 1, padding: "8px 0", background: "transparent", color: "var(--dim2)",
              border: "1px solid var(--border2)", fontFamily: "Space Mono,monospace", fontSize: 9,
              letterSpacing: 2, textTransform: "uppercase", cursor: "pointer" }}
          >CANCEL</button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────
export default function Missions({ liveEvents = [], queueTick = 0 }) {
  const [prompt, setPrompt]           = useState("")
  const [priority, setPriority]       = useState("medium")  // high | medium | low
  const [running, setRunning]         = useState(false)
  const [steps, setSteps]             = useState([])
  const [queue, setQueue]             = useState([])
  const [templates, setTemplates]     = useState([])
  const [showSave, setShowSave]       = useState(false)
  const [missionEvents, setMissionEvents] = useState([])
  const feedRef = useRef(null)

  const user = (() => {
    try { return JSON.parse(localStorage.getItem("hermes_user") || "null") } catch { return null }
  })()
  const userId  = user?.id  || "user_1"
  const convId  = useRef(`mission_${Date.now()}`).current

  // ── Load queue + templates on mount; 5s fallback poll + WS-driven instant push ──
  useEffect(() => {
    loadQueue()
    loadTemplates()
    const interval = setInterval(loadQueue, 5000)  // fallback only
    return () => clearInterval(interval)
  }, [])

  // Instant queue refresh on WS push (queueTick increments every queue_updated event)
  useEffect(() => { loadQueue() }, [queueTick])

  // ── Ingest mission_* WS events from App.jsx ────────────────────────
  // liveEvents[0] is always the newest event (prepended in App.jsx)
  useEffect(() => {
    if (!liveEvents || liveEvents.length === 0) return
    const latest = liveEvents[0]
    if (!latest?.type?.startsWith("mission_")) return

    // Append to feed (newest first)
    setMissionEvents(prev => {
      // Dedup by ts + type
      const exists = prev.some(e => e.ts === latest.ts && e.type === latest.type)
      if (exists) return prev
      return [latest, ...prev].slice(0, 200)
    })

    // Mirror step_done into step progress panel
    if (latest.type === "mission_step_done") {
      setSteps(prev => {
        const exists = prev.find(s => s.step === latest.step)
        if (exists) return prev
        return [...prev, latest]
      })
    }

    // Auto-clear running state when mission ends
    if (latest.type === "mission_complete" || latest.type === "mission_failed") {
      setRunning(false)
    }
  }, [liveEvents])

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = 0
  }, [missionEvents.length])

  const loadQueue     = async () => {
    try { setQueue((await axios.get(`http://localhost:8000/api/queue?user_id=${userId}`)).data) } catch {}
  }
  const loadTemplates = async () => {
    try { setTemplates((await axios.get("http://localhost:8000/api/templates")).data) } catch {}
  }

  // ── Run mission (direct — runs what's in the textarea) ─────────────────
  const runMission = async () => {
    if (!prompt.trim() || running) return
    const missionPrompt = prompt.trim()
    setPrompt("")        // ✔ clear textarea immediately
    setRunning(true)
    setSteps([])
    setMissionEvents([]) // clear old feed for new run
    try {
      const res = await axios.post("http://localhost:8000/api/mission/run", {
        conv_id: convId, prompt: missionPrompt, user_id: userId,
      })
      // Populate steps from response (fallback if WS missed events)
      if (res.data.results?.length) {
        setSteps(res.data.results.map(r => ({
          step: r.step, tool: r.tool,
          description: r.description, result: r.result, type: "mission_step_done"
        })))
      }
    } catch (e) {
      setSteps([{ step: 1, tool: null, description: "Error", result: `[ERROR] ${e.message}`, type: "mission_step_done" }])
    } finally {
      setRunning(false)
      loadQueue()
    }
  }

  // Run next queued item (FIFO — oldest priority=0 first)
  const runNextQueued = async () => {
    if (running) return
    const nextItem = queue.find(m => m.status === "queued")
    if (!nextItem) return
    const missionPrompt = nextItem.prompt
    setRunning(true)
    setSteps([])
    setMissionEvents([])
    try {
      const res = await axios.post("http://localhost:8000/api/mission/run", {
        conv_id: nextItem.conv_id || convId, prompt: missionPrompt, user_id: userId,
      })
      if (res.data.results?.length) {
        setSteps(res.data.results.map(r => ({
          step: r.step, tool: r.tool,
          description: r.description, result: r.result, type: "mission_step_done"
        })))
      }
    } catch (e) {
      setSteps([{ step: 1, tool: null, description: "Error", result: `[ERROR] ${e.message}`, type: "mission_step_done" }])
    } finally {
      setRunning(false)
      loadQueue()
      // Auto-clear DONE items after 4s — user sees badge briefly then queue cleans itself
      setTimeout(async () => {
        await axios.post("http://localhost:8000/api/queue/clear")
        loadQueue()
      }, 4000)
    }
  }

  // ── Queue ops ────────────────────────────────────────────────────
  const PRIORITY_MAP = { high: 2, medium: 1, low: 0 }
  const addToQueue = async () => {
    if (!prompt.trim()) return
    await axios.post("http://localhost:8000/api/queue", {
      conv_id: convId, prompt: prompt.trim(), user_id: userId,
      priority: PRIORITY_MAP[priority],
    })
    setPrompt("")  // ✔ clear textarea after queuing
    loadQueue()
  }
  const deleteFromQueue = async (id) => {
    await axios.delete(`http://localhost:8000/api/queue/${id}`)
    loadQueue()
  }
  const clearDone = async () => {
    await axios.post("http://localhost:8000/api/queue/clear")
    loadQueue()
  }

  // ── Template ops ─────────────────────────────────────────────────
  const saveTemplate = async (name, description) => {
    await axios.post("http://localhost:8000/api/templates", { name, description, prompt: prompt.trim() })
    setShowSave(false)
    loadTemplates()
  }
  const deleteTemplate = async (id) => {
    await axios.delete(`http://localhost:8000/api/templates/${id}`)
    loadTemplates()
  }

  // ── Shared styles ─────────────────────────────────────────────────
  const S = {
    section: { marginBottom: 24 },
    heading: {
      fontFamily: "Space Mono,monospace", fontSize: 9,
      letterSpacing: 3, color: "var(--accent)",
      textTransform: "uppercase", marginBottom: 12,
      borderBottom: "1px solid var(--border)", paddingBottom: 6,
    },
    btn: (accent) => ({
      padding: "7px 16px", border: `1px solid ${accent || "var(--accent)"}`,
      background: "transparent", color: accent || "var(--accent)",
      fontFamily: "Space Mono,monospace", fontSize: 8,
      letterSpacing: 2, textTransform: "uppercase", cursor: "pointer",
      transition: "all .15s",
    }),
    card: {
      padding: "10px 14px", border: "1px solid var(--border)",
      marginBottom: 6, background: "var(--black2)",
    },
  }

  return (
    <div style={{ display: "flex", gap: 24, height: "calc(100vh - 180px)", overflow: "hidden" }}>

      {/* ── LEFT COLUMN ─────────────────────────────────────────── */}
      <div style={{ width: 420, display: "flex", flexDirection: "column", flexShrink: 0, overflowY: "auto",
        scrollbarWidth: "thin", scrollbarColor: "var(--border) transparent" }}>

        {/* SECTION 1: Run mission */}
        <div style={S.section}>
          <div style={S.heading}>⚡ Run Autonomous Mission</div>

          <textarea
            id="mission-prompt"
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder={"Describe the full mission...\n\nExample: Search the web for latest AI news, summarize the top 3 stories, save to /documents/ai_news.txt"}
            style={{
              width: "100%", height: 110, background: "transparent",
              border: "1px solid var(--border2)", color: "var(--white)",
              fontFamily: "Space Mono,monospace", fontSize: 10,
              padding: "10px 12px", boxSizing: "border-box", resize: "vertical",
              outline: "none", lineHeight: 1.6,
            }}
          />

          {/* Priority selector + action buttons */}
          <div style={{ marginTop: 8 }}>
            {/* Priority row */}
            <div style={{ display: "flex", gap: 4, marginBottom: 6 }}>
              <span style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)",
                alignSelf: "center", marginRight: 4, letterSpacing: 1 }}>PRIORITY</span>
              {["high", "medium", "low"].map(p => {
                const clr = p === "high" ? "#ff6b6b" : p === "medium" ? "#ffd93d" : "#6bcb77"
                const sel = priority === p
                return (
                  <button key={p} onClick={() => setPriority(p)} style={{
                    padding: "2px 10px", fontFamily: "Space Mono,monospace",
                    fontSize: 7, letterSpacing: 1, textTransform: "uppercase",
                    cursor: "pointer", border: `1px solid ${clr}`,
                    background: sel ? `${clr}33` : "transparent",
                    color: sel ? clr : "var(--dim2)",
                    transition: "all .15s",
                  }}>{p}</button>
                )
              })}
            </div>
            {/* Action buttons row */}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                id="run-mission-btn"
                onClick={runMission}
                disabled={running || !prompt.trim()}
                style={{
                  flex: 2, padding: "10px 0",
                  background: running ? "rgba(200,255,0,.1)" : "var(--accent)",
                  color: running ? "var(--accent)" : "#000",
                  border: `1px solid var(--accent)`,
                  fontFamily: "Space Mono,monospace", fontSize: 9,
                  letterSpacing: 2, textTransform: "uppercase", cursor: running ? "wait" : "pointer",
                  transition: "all .2s",
                }}
              >
                {running ? "RUNNING..." : "RUN MISSION"}
              </button>
              <button id="queue-mission-btn" onClick={addToQueue} style={S.btn()}>QUEUE</button>
              <button id="save-template-btn" onClick={() => setShowSave(true)} style={S.btn("#f5a623")}>SAVE</button>
            </div>
          </div>

          {/* Live step progress */}
          {steps.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {steps.map((s, i) => (
                <div key={i} style={{
                  padding: "8px 12px", marginBottom: 4,
                  background: "rgba(200,255,0,.03)",
                  border: "1px solid var(--border)",
                  borderLeft: `3px solid ${s.tool ? (TOOL_COLORS[s.tool] || "#888") : "var(--dim)"}`,
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <span style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)" }}>
                      STEP {s.step}
                    </span>
                    <ToolBadge tool={s.tool} />
                  </div>
                  <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim)", marginBottom: 4 }}>
                    {s.description?.slice(0, 80)}
                  </div>
                  <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--white)", lineHeight: 1.5 }}>
                    {String(s.result || "").slice(0, 200)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* SECTION 2: Queue */}
        <div style={S.section}>
          <div style={{ ...S.heading, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>📋 Mission Queue ({queue.length})</span>
            <div style={{ display: "flex", gap: 6 }}>
              {queue.some(m => m.status === "queued") && (
                <button
                  id="run-next-btn"
                  onClick={runNextQueued}
                  disabled={running}
                  title="Run oldest queued mission (FIFO)"
                  style={{ ...S.btn(), padding: "2px 10px", fontSize: 7,
                    background: running ? "transparent" : "rgba(200,255,0,.12)",
                  }}
                >
                  ▶ RUN NEXT
                </button>
              )}
              <button onClick={clearDone} style={{ ...S.btn("#ff6b6b"), padding: "2px 10px", fontSize: 7 }}>
                CLEAR DONE
              </button>
            </div>
          </div>

          {queue.length === 0 ? (
            <div style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim2)", padding: "8px 0" }}>
              No missions in queue
            </div>
          ) : queue.map(m => {
            const pDot = m.priority >= 2 ? "#ff6b6b" : m.priority === 1 ? "#ffd93d" : "#6bcb77"
            const pLabel = m.priority >= 2 ? "HIGH" : m.priority === 1 ? "MED" : "LOW"
            return (
            <div key={m.id} style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 4 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, flex: 1, overflow: "hidden" }}>
                  {/* Priority dot */}
                  <span title={`Priority: ${pLabel}`} style={{
                    width: 6, height: 6, borderRadius: "50%", flexShrink: 0,
                    background: pDot, display: "inline-block",
                  }} />
                  <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--white)",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", paddingRight: 8 }}>
                    {m.prompt.slice(0, 58)}{m.prompt.length > 58 ? "..." : ""}
                  </div>
                </div>
                <StatusBadge status={m.status} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)" }}>
                  {m.created_at?.substring(0, 16).replace("T", " ")} UTC
                </div>
                <button onClick={() => deleteFromQueue(m.id)}
                  style={{ background: "none", border: "none", color: "var(--dim2)", cursor: "pointer", fontSize: 14 }}>
                  ×
                </button>
              </div>
              {m.result && (
                <div style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim)", marginTop: 4 }}>
                  {m.result.slice(0, 80)}...
                </div>
              )}
            </div>
            )
          })}
        </div>

        {/* SECTION 3: Templates */}
        <div style={S.section}>
          <div style={S.heading}>🗂 Templates</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {templates.map(t => (
              <div key={t.id} style={{
                ...S.card,
                border: t.builtin ? "1px solid var(--border)" : "1px solid #f5a62344",
                cursor: "pointer", position: "relative",
              }}>
                <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--white)", marginBottom: 4 }}>
                  {t.name}
                  {t.builtin && (
                    <span style={{ marginLeft: 6, fontSize: 7, color: "var(--dim)", letterSpacing: 1 }}>BUILT-IN</span>
                  )}
                </div>
                <div style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)", marginBottom: 8 }}>
                  {t.description}
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  <button
                    id={`use-template-${t.id}`}
                    onClick={() => setPrompt(t.prompt)}
                    style={{ ...S.btn(), padding: "3px 10px", fontSize: 7 }}
                  >USE</button>
                  {!t.builtin && (
                    <button onClick={() => deleteTemplate(t.id)}
                      style={{ background: "none", border: "1px solid var(--border)", color: "var(--dim2)",
                        padding: "3px 8px", cursor: "pointer", fontSize: 10 }}>
                      ×
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── RIGHT COLUMN: Live Feed ──────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{ ...S.heading }}>📡 Live Mission Feed</div>
        <div
          ref={feedRef}
          style={{
            flex: 1, overflowY: "auto", scrollbarWidth: "thin",
            scrollbarColor: "var(--border) transparent",
            display: "flex", flexDirection: "column", gap: 4,
          }}
        >
          {missionEvents.length === 0 ? (
            <div style={{
              flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim2)",
              border: "1px dashed var(--border)", textAlign: "center", padding: 40,
            }}>
              No mission events yet.<br />
              <span style={{ fontSize: 9, marginTop: 8, display: "block" }}>
                Run a mission to see live updates here.
              </span>
            </div>
          ) : missionEvents.map((ev, i) => {
            const cfg = EVENT_CFG[ev.type] || { label: ev.type.toUpperCase(), color: "#888" }
            const ts  = ev.ts ? ev.ts.substring(11, 19) : ""

            let msg = ""
            if (ev.type === "mission_started")    msg = `Mission started: ${(ev.prompt || "").slice(0, 60)}`
            if (ev.type === "mission_plan_ready") msg = `Plan ready — ${ev.step_count} steps · ${(ev.goal || "").slice(0, 50)}`
            if (ev.type === "mission_step_start") msg = `Step ${ev.step}/${ev.total}: ${(ev.description || "").slice(0, 80)}`
            if (ev.type === "mission_step_done")  msg = `Step ${ev.step} done: ${(ev.result || "").slice(0, 100)}`
            if (ev.type === "mission_complete")   msg = `Mission complete in ${ev.steps_taken} steps`
            if (ev.type === "mission_failed")     msg = `Mission failed: ${ev.error || ""}`

            return (
              <div key={i} style={{
                padding: "8px 14px",
                border: "1px solid var(--border)",
                borderLeft: `3px solid ${cfg.color}`,
                background: i === 0 ? `${cfg.color}08` : "transparent",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                  <span style={{
                    fontFamily: "Space Mono,monospace", fontSize: 7, letterSpacing: 2,
                    color: cfg.color, padding: "1px 6px",
                    border: `1px solid ${cfg.color}44`, background: `${cfg.color}18`,
                  }}>{cfg.label}</span>
                  {ev.tool && <ToolBadge tool={ev.tool} />}
                  <span style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim)", marginLeft: "auto" }}>
                    {ts}
                  </span>
                </div>
                <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--white)", lineHeight: 1.5 }}>
                  {msg}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {showSave && (
        <SaveModal
          prompt={prompt}
          onSave={saveTemplate}
          onClose={() => setShowSave(false)}
        />
      )}
    </div>
  )
}
