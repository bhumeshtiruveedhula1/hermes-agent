/* hermes-ui/src/App.jsx */
import { useState, useEffect } from "react"
import Overview from "./pages/Overview"
import Chat from "./pages/Chat"
import Agents from "./pages/Agents"
import Files from "./pages/Files"
import AuditLog from "./pages/AuditLog"
import "./App.css"
import Browser from "./pages/Browser"
import Plugins from "./pages/Plugins"
import History from "./pages/History"
import ApprovalModal from "./components/ApprovalModal"

const TABS = ["Overview", "Chat", "Agents", "Files", "Audit Log", "Browser", "Plugins", "History"]

export default function App() {
  const [tab, setTab] = useState("Overview")
  const [status, setStatus] = useState(null)
  const [clock, setClock] = useState("")
  const [ws, setWs] = useState(null)
  const [liveEvents, setLiveEvents] = useState([])
  const [pendingApprovals, setPendingApprovals] = useState([])

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
      if (data.type === "ping") return  // ← ignore pings
      console.log("[WS]", data.type, data)
      setLiveEvents(prev => [data, ...prev].slice(0, 100))
      if (data.type === "approval_required") {
        console.log("[APPROVAL] Modal should show!", data)
        setPendingApprovals(prev => [...prev, data])
      }
      if (data.type === "approval_resolved") {
        setPendingApprovals(prev => prev.filter(a => a.id !== data.id))
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
            <div>AUTONOMOUS AGENT PLATFORM v0.8</div>
            <div className="clock">{clock}</div>
          </div>
        </header>

        <div className="ticker">
          <div className="ticker-inner">
            {[
              ["PHASE", "8.5 COMPLETE — FRONTEND APPROVAL MODAL LIVE"],
              ["MODEL", "QWEN3:8B — RTX 4060"],
              ["AUDIT", "ALL ACTIONS LOGGED"],
              ["SANDBOX", "USER_1 — /DOCUMENTS MOUNTED"],
              ["SECURITY", "EXECUTION GATE ACTIVE"],
              ["PLUGINS", "WEATHER + TELEGRAM + JOKE_TELLER ACTIVE"],
              ["MISSIONS", "PERSISTENT CHAT HISTORY LIVE"],
              ["APPROVAL", "FRONTEND MODAL — NO TERMINAL PROMPTS"],
              ["PHASE", "8.5 COMPLETE — FRONTEND APPROVAL MODAL LIVE"],
              ["MODEL", "QWEN3:8B — RTX 4060"],
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
          {tab === "Chat"      && <Chat />}
          {tab === "Agents"    && <Agents liveEvents={liveEvents} />}
          {tab === "Files"     && <Files />}
          {tab === "Audit Log" && <AuditLog liveEvents={liveEvents} />}
          {tab === "Browser"   && <Browser />}
          {tab === "Plugins"   && <Plugins />}
          {tab === "History"   && <History />}
        </main>

      </div>

      {/* APPROVAL MODAL — outside wrapper so it covers full screen */}
      {pendingApprovals.length > 0 && (
        <ApprovalModal
          approval={pendingApprovals[0]}
          onResolved={handleApprovalResolved}
        />
      )}

    </div>
  )
}
