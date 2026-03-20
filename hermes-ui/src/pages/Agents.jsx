/* hermes-ui/src/pages/Agents.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

export default function Agents({ liveEvents }) {
  const [agents, setAgents] = useState([])
  const [running, setRunning] = useState(false)

  const load = () => axios.get("http://localhost:8000/api/agents").then(r => setAgents(r.data)).catch(() => {})

  useEffect(() => { load() }, [])

  useEffect(() => {
    const ev = liveEvents[0]
    if (ev?.type === "agent_update" || ev?.type === "scheduler_tick") load()
  }, [liveEvents])

  const toggle = async (agent) => {
    const url = `http://localhost:8000/api/agents/${agent.name}/${agent.enabled ? "disable" : "enable"}`
    await axios.post(url)
    load()
  }

  const runScheduler = async () => {
    setRunning(true)
    await axios.post("http://localhost:8000/api/scheduler/run").catch(() => {})
    setTimeout(() => { setRunning(false); load() }, 1800)
  }

  return (
    <div>
      <button className={`run-btn ${running ? "running" : ""}`} onClick={runScheduler}>
        {running ? "Running..." : "Run Scheduler Tick"}
      </button>

      <div className="section-label">Registered Agents</div>

      {agents.length === 0 ? (
        <div style={{fontFamily:"Space Mono,monospace",fontSize:11,color:"var(--dim2)",padding:"24px 0"}}>No agents registered.</div>
      ) : (
        <div className="agent-grid">
          {agents.map(a => (
            <div key={a.name} className={`agent-card ${a.enabled ? "enabled" : "disabled"}`}>
              <div className="agent-head">
                <div className="agent-name">{a.name}</div>
                <div className={`badge ${a.enabled ? "on" : "off"}`}>{a.enabled ? "ON" : "OFF"}</div>
              </div>
              <div className="agent-meta">
                <div>tool: {a.tool_name}</div>
                <div>schedule: {a.schedule}</div>
                <div>last run: {a.last_run_at ? a.last_run_at.replace("T", " ").substring(0, 19) : "never"}</div>
                {a.metadata?.path && <div>path: {a.metadata.path}</div>}
              </div>
              <button className="agent-btn" onClick={() => toggle(a)}>
                {a.enabled ? "Disable" : "Enable"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
