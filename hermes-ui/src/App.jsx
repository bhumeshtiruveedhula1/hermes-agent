/* hermes-ui/src/App.jsx — Phase 11: Auth Gate */
import { useState, useEffect } from "react"
import axios from "axios"
import Overview from "./pages/Overview"
import Chat from "./pages/Chat"
import Agents from "./pages/Agents"
import Files from "./pages/Files"
import AuditLog from "./pages/AuditLog"
import Browser from "./pages/Browser"
import Plugins from "./pages/Plugins"
import History from "./pages/History"
import Login from "./pages/Login"
import Admin from "./pages/Admin"
import Missions from "./pages/Missions"
import Memory from "./pages/Memory"
import Skills from "./pages/Skills"
import "./App.css"
import ApprovalModal from "./components/ApprovalModal"

// Phase 11: Set X-User-Id on every axios request globally
function applyUserHeader(userId) {
  if (userId) {
    axios.defaults.headers.common["X-User-Id"] = userId
  } else {
    delete axios.defaults.headers.common["X-User-Id"]
  }
}

const BASE_TABS = ["Overview", "Chat", "Missions", "Agents", "Files", "Audit Log", "Browser", "Plugins", "History", "Memory", "Skills"]

export default function App() {
  const [tab, setTab]                     = useState("Overview")
  const [status, setStatus]               = useState(null)
  const [clock, setClock]                 = useState("")
  const [ws, setWs]                       = useState(null)
  const [liveEvents, setLiveEvents]       = useState([])
  const [pendingApprovals, setPendingApprovals] = useState([])
  const [missionEvents, setMissionEvents]  = useState([])   // Phase 15
  const [queueTick, setQueueTick]          = useState(0)    // Phase 15: WS queue push
  const [memoryEvents, setMemoryEvents]    = useState([])   // Phase 17
  const [skillCandidate, setSkillCandidate] = useState(null) // Phase 17

  // Phase 11: Auth state
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("hermes_user") || "null") }
    catch { return null }
  })

  // Apply header on mount and when user changes
  useEffect(() => {
    applyUserHeader(user?.id)
  }, [user])

  const handleLogin = (u) => {
    setUser(u)
    applyUserHeader(u.id)
  }

  const handleLogout = () => {
    localStorage.removeItem("hermes_user")
    setUser(null)
    applyUserHeader(null)
    setTab("Overview")
  }

  // ── Auth gate ─────────────────────────────────────────────────────────
  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  // Build tab list: add Admin only for admin role
  const TABS = user.role === "admin" ? [...BASE_TABS, "Admin"] : BASE_TABS

  useEffect(() => {
    fetch("http://localhost:8000/api/status")
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus({ online: false }))
  }, [])

  useEffect(() => {
    const tick = () => setClock(new Date().toISOString().replace("T", " ").substring(0, 19) + " UTC")
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/ws/stream")
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data)
      if (data.type === "ping") return
      setLiveEvents(prev => [data, ...prev].slice(0, 100))
      if (data.type.startsWith("mission_")) {
        setMissionEvents(prev => [data, ...prev].slice(0, 200))
      }
      if (data.type === "queue_updated") {          // Phase 15: instant queue push
        setQueueTick(t => t + 1)
      }
      if (data.type === "approval_required") {
        setPendingApprovals(prev => [...prev, data])
      }
      if (data.type === "approval_resolved") {
        setPendingApprovals(prev => prev.filter(a => a.id !== data.id))
      }
      if (data.type === "skill_candidate") {         // Phase 17
        setSkillCandidate(data)
      }
      if (data.type === "skill_saved" || data.type === "skill_loaded") {
        setMemoryEvents(prev => [data, ...prev].slice(0, 50))
      }
    }
    setWs(socket)
    return () => socket.close()
  }, [])

  const handleApprovalResolved = (id) => {
    setPendingApprovals(prev => prev.filter(a => a.id !== id))
  }

  const online = status?.online

  return (
    <div className="app">
      <div className="scanline" />
      <div className="wrapper">

        <header className="header">
          <div className="logo">HERMES<span className="logo-dot">.</span></div>
          <div className="header-meta">
            <div><span className={`status-dot ${online ? "on" : "off"}`} />{online ? "SYSTEM ONLINE" : "CONNECTING..."}</div>
            <div>AUTONOMOUS AGENT PLATFORM v0.9</div>
            <div className="clock">{clock}</div>
          </div>
          {/* Phase 11: User badge + logout */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginLeft: "auto" }}>
            <span style={{
              fontFamily: "Space Mono,monospace", fontSize: 8, letterSpacing: 1,
              color: "var(--dim)", paddingRight: 8, borderRight: "1px solid var(--border)"
            }}>
              {user.name}
              {user.role === "admin" && (
                <span style={{
                  marginLeft: 6, color: "var(--accent)", fontSize: 7, letterSpacing: 2
                }}>ADMIN</span>
              )}
            </span>
            <button
              id="logout-btn"
              onClick={handleLogout}
              style={{
                background: "none", border: "1px solid var(--border2)",
                color: "var(--dim)", cursor: "pointer",
                fontFamily: "Space Mono,monospace", fontSize: 7,
                letterSpacing: 2, padding: "4px 10px", textTransform: "uppercase",
              }}
              onMouseEnter={e => e.target.style.borderColor = "var(--accent)"}
              onMouseLeave={e => e.target.style.borderColor = "var(--border2)"}
            >
              Logout
            </button>
          </div>
        </header>

        <div className="ticker">
          <div className="ticker-inner">
            {[
              ["PHASE",    "17 COMPLETE — MEMORY + SKILLS + USER INTELLIGENCE"],
              ["MEMORY",   "SQLITE FTS5 · USER PROFILE · SOUL.MD · SKILL MEMORY"],
              ["MODEL",    "QWEN2.5-CODER:14B — RTX 4060 HYBRID"],
              ["MISSIONS", "MULTI-STEP · QUEUE · TEMPLATES · LIVE FEED"],
              ["AUDIT",    "ALL ACTIONS LOGGED"],
              ["SANDBOX",  `${user.name.toUpperCase()} — /DOCUMENTS MOUNTED`],
              ["SECURITY", "EXECUTION GATE ACTIVE"],
              ["PLUGINS",  "WHATSAPP · NOTION · SPOTIFY · SLACK · TELEGRAM · GMAIL"],
              ["AUTH",     `LOGGED IN AS ${user.name.toUpperCase()} (${user.role.toUpperCase()})`],
              ["BROWSER",  "SMART FILL + AUTO ENTER + LIVE MODE"],
              ["VOICE",    "MIC INPUT + TTS OUTPUT — PHASE 12"],
            ].map(([k, v], i) => (
              <div className="ticker-item" key={i}>
                <span className="ticker-key">{k}</span>{v}
              </div>
            ))}
          </div>
        </div>

        <nav className="nav">
          {TABS.map(t => (
            <button key={t} className={`nav-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>

        <main className="main">
          {tab === "Overview"  && <Overview status={status} liveEvents={liveEvents} />}
          {tab === "Chat"      && <Chat user={user} />}
          {tab === "Missions"  && <Missions liveEvents={missionEvents} queueTick={queueTick} />}
          {tab === "Agents"    && <Agents liveEvents={liveEvents} />}
          {tab === "Files"     && <Files user={user} />}
          {tab === "Audit Log" && <AuditLog liveEvents={liveEvents} />}
          {tab === "Browser"   && <Browser />}
          {tab === "Plugins"   && <Plugins />}
          {tab === "History"   && <History />}
          {tab === "Memory"   && <Memory skillCandidate={skillCandidate} onSkillSaved={() => setSkillCandidate(null)} />}
          {tab === "Skills"   && <Skills liveEvents={memoryEvents} />}
          {tab === "Admin" && user.role === "admin" && <Admin user={user} />}
        </main>

      </div>

      {pendingApprovals.length > 0 && (
        <ApprovalModal
          approval={pendingApprovals[0]}
          onResolved={handleApprovalResolved}
        />
      )}
    </div>
  )
}
