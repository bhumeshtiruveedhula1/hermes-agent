/* hermes-ui/src/pages/AuditLog.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

export default function AuditLog({ liveEvents }) {
  const [events, setEvents] = useState([])

  const load = () =>
    axios.get("http://localhost:8000/api/audit?limit=100").then(r => setEvents(r.data)).catch(() => {})

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (liveEvents.length > 0) load()
  }, [liveEvents])

  const decisionClass = (d) => {
    const map = { allowed:"allowed", blocked:"blocked", executed:"executed", completed:"completed", attempted:"attempted", failed:"failed" }
    return `decision-${map[d] || ""}`
  }

  return (
    <div>
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:18}}>
        <div className="section-label" style={{marginBottom:0}}>Audit Stream</div>
        <button className="file-btn" onClick={load}>Refresh</button>
      </div>

      <div className="audit-wrap" style={{maxHeight:520, overflowY:"auto"}}>
        <div className="audit-head">
          <div className="audit-cell">Timestamp</div>
          <div className="audit-cell">Phase</div>
          <div className="audit-cell">Action</div>
          <div className="audit-cell">Decision</div>
          <div className="audit-cell">Tool</div>
        </div>
        {events.length === 0 ? (
          <div style={{padding:"20px 14px", fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--dim2)"}}>
            No audit events yet.
          </div>
        ) : (
          events.map((e, i) => (
            <div className="audit-row-item" key={i}>
              <div className="audit-cell">{e.ts ? e.ts.replace("T"," ").substring(0,19) : ""}</div>
              <div className="audit-cell">{e.phase}</div>
              <div className="audit-cell">{e.action}</div>
              <div className={`audit-cell ${decisionClass(e.decision)}`}>{e.decision}</div>
              <div className="audit-cell">{e.tool}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
