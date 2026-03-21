/* hermes-ui/src/pages/Overview.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

function SafeModeToggle() {
  const [safeMode, setSafeMode] = useState(true)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    axios.get("http://localhost:8000/api/settings")
      .then(r => setSafeMode(r.data.safe_mode))
      .catch(() => {})
  }, [])

  const toggle = async () => {
    setLoading(true)
    const newMode = !safeMode
    await axios.post("http://localhost:8000/api/settings/safemode", { enabled: newMode })
    setSafeMode(newMode)
    setLoading(false)
  }

  return (
    <div style={{marginTop: 32}}>
      <div className="section-label">Auto-Tool Builder</div>
      <div style={{
        background:"var(--black)", border:"1px solid var(--border2)",
        padding:"20px 24px", display:"flex", alignItems:"center", justifyContent:"space-between"
      }}>
        <div>
          <div style={{fontFamily:"Space Mono,monospace", fontSize:12, marginBottom:6}}>
            {safeMode ? "🔒 SAFE MODE" : "⚡ AUTO MODE"}
          </div>
          <div style={{fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--dim2)"}}>
            {safeMode
              ? "Unknown tools require your approval before running"
              : "Unknown tools are auto-built and run without approval"}
          </div>
        </div>
        <button
          onClick={toggle}
          disabled={loading}
          style={{
            padding:"10px 24px",
            background: safeMode ? "transparent" : "var(--accent)",
            border: safeMode ? "1px solid var(--border2)" : "none",
            color: safeMode ? "var(--dim2)" : "var(--black)",
            fontFamily:"Space Mono,monospace", fontSize:10,
            letterSpacing:2, textTransform:"uppercase", cursor:"pointer",
            transition:"all .2s"
          }}
        >
          {loading ? "..." : safeMode ? "Switch to Auto" : "Switch to Safe"}
        </button>
      </div>
    </div>
  )
}

export default function Overview({ status, liveEvents }) {
  const capabilities = [
    "fs_list","fs_read","fs_write","fs_delete",
    "search_web","check_inbox",
    "browser_go","browser_read","browser_click",
    "browser_fill","browser_shot","browser_scroll"
  ]

  const roadmap = [
  ["Phase 0 — Core Runtime",          "done"],
  ["Phase 1 — Scheduler",             "done"],
  ["Phase 2 — Filesystem Read",       "done"],
  ["Phase 3 — Filesystem Write",      "done"],
  ["Phase 4 — Dashboard UI",          "done"],
  ["Phase 5 — Browser Control",       "done"],
  ["Phase 6 — Gmail/Calendar/GitHub", "done"],
  ["Phase 7 — Plugin Architecture",   "done"],
  ["Phase 7.5 — AI Plugin Creator",   "done"],
  ["Phase 7.6 — Mission Log",         "done"],
  ["Phase 8 — Autocorrect",           "pending"],
  ["Phase 9 — Multi-user",            "pending"],
  ]

  return (
    <div>
      <div className="stat-strip">
        <div className="stat-cell">
          <div className="stat-label">Agents Active</div>
          <div className="stat-value accent">7.6</div>
          <div className="stat-sub">mission log complete</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Live Events</div>
          <div className="stat-value">{liveEvents.length}</div>
          <div className="stat-sub">this session</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Phase</div>
          <div className="stat-value accent">5.4</div>
          <div className="stat-sub">auto tool builder</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Security</div>
          <div className="stat-value accent">OK</div>
          <div className="stat-sub">all gates active</div>
        </div>
      </div>

      <div className="two-col">
        <div className="col-cell">
          <div className="section-label">Capabilities</div>
          {capabilities.map(c => (
            <div className="col-row" key={c}>
              <span className="col-row-key">{c}</span>
              <span className="col-row-val on">ACTIVE</span>
            </div>
          ))}
        </div>
        <div className="col-cell">
          <div className="section-label">Roadmap</div>
          {roadmap.map(([label, state]) => (
            <div className="col-row" key={label}>
              <span className="col-row-key">{label}</span>
              <span className={`col-row-val ${state}`}>
                {state === "done" ? "DONE" : "PENDING"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {liveEvents.length > 0 && (
        <>
          <div className="section-label">Live Stream</div>
          <div className="audit-wrap" style={{maxHeight:200, overflowY:"auto"}}>
            <div className="audit-head">
              <div className="audit-cell">Type</div>
              <div className="audit-cell">Detail</div>
              <div className="audit-cell">Time</div>
              <div className="audit-cell"></div>
              <div className="audit-cell"></div>
            </div>
            {liveEvents.slice(0,8).map((e,i) => (
              <div className="audit-row-item" key={i}>
                <div className="audit-cell">{e.type}</div>
                <div className="audit-cell">{e.name || e.path || e.message || ""}</div>
                <div className="audit-cell">{e.ts ? e.ts.substring(11,19) : ""}</div>
                <div className="audit-cell"></div>
                <div className="audit-cell"></div>
              </div>
            ))}
          </div>
        </>
      )}

      <SafeModeToggle />
    </div>
  )
}
