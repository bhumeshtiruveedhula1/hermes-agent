/* hermes-ui/src/App.jsx */
import { useState, useEffect } from "react"
import Overview from "./pages/Overview"
import Chat from "./pages/Chat"
import Agents from "./pages/Agents"
import Files from "./pages/Files"
import AuditLog from "./pages/AuditLog"
import "./App.css"

const TABS = ["Overview", "Chat", "Agents", "Files", "Audit Log"]

export default function App() {
  const [tab, setTab] = useState("Overview")
  const [status, setStatus] = useState(null)
  const [clock, setClock] = useState("")
  const [ws, setWs] = useState(null)
  const [liveEvents, setLiveEvents] = useState([])

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
      setLiveEvents(prev => [data, ...prev].slice(0, 100))
    }
    setWs(socket)
    return () => socket.close()
  }, [])

  const online = status?.online

  return (
    <div className="app">
      <div className="scanline" />
      <div className="wrapper">

        {/* HEADER */}
        <header className="header">
          <div className="logo">HERMES<span className="logo-dot">.</span></div>
          <div className="header-meta">
            <div><span className={`status-dot ${online ? "on" : "off"}`} />{online ? "SYSTEM ONLINE" : "CONNECTING..."}</div>
            <div>AUTONOMOUS AGENT PLATFORM v0.8</div>
            <div className="clock">{clock}</div>
          </div>
        </header>

        {/* TICKER */}
        <div className="ticker">
          <div className="ticker-inner">
            {[
              ["PHASE", "3 COMPLETE — FILESYSTEM R/W OPERATIONAL"],
              ["MODEL", "QWEN3:8B — RTX 4060"],
              ["AUDIT", "ALL ACTIONS LOGGED"],
              ["SANDBOX", "USER_1 — /DOCUMENTS MOUNTED"],
              ["SECURITY", "EXECUTION GATE ACTIVE"],
              ["SCHEDULER", "FOLDER MONITOR READY"],
              ["PHASE", "3 COMPLETE — FILESYSTEM R/W OPERATIONAL"],
              ["MODEL", "QWEN3:8B — RTX 4060"],
              ["AUDIT", "ALL ACTIONS LOGGED"],
            ].map(([k, v], i) => (
              <div className="ticker-item" key={i}>
                <span className="ticker-key">{k}</span>{v}
              </div>
            ))}
          </div>
        </div>

        {/* NAV */}
        <nav className="nav">
          {TABS.map(t => (
            <button key={t} className={`nav-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
              {t}
            </button>
          ))}
        </nav>

        {/* PANELS */}
        <main className="main">
          {tab === "Overview"  && <Overview status={status} liveEvents={liveEvents} />}
          {tab === "Chat"      && <Chat />}
          {tab === "Agents"    && <Agents liveEvents={liveEvents} />}
          {tab === "Files"     && <Files />}
          {tab === "Audit Log" && <AuditLog liveEvents={liveEvents} />}
        </main>

      </div>
    </div>
  )
}
