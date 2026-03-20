/* hermes-ui/src/pages/Overview.jsx */
export default function Overview({ status, liveEvents }) {
  const capabilities = ["fs_list","fs_read","fs_write","fs_delete","search_web","check_inbox"]
  const roadmap = [
    ["Phase 0 — Core Runtime",      "done"],
    ["Phase 1 — Scheduler",         "done"],
    ["Phase 2 — Filesystem Read",   "done"],
    ["Phase 3 — Filesystem Write",  "done"],
    ["Phase 4 — Dashboard UI",      "done"],
    ["Phase 5 — Browser & APIs",    "pending"],
  ]

  return (
    <div>
      <div className="stat-strip">
        <div className="stat-cell">
          <div className="stat-label">Agents Active</div>
          <div className="stat-value accent">{status?.agents_enabled ?? "—"}</div>
          <div className="stat-sub">of {status?.agents_total ?? "—"} registered</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Live Events</div>
          <div className="stat-value">{liveEvents.length}</div>
          <div className="stat-sub">this session</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Phase</div>
          <div className="stat-value">{status?.phase ?? "—"}</div>
          <div className="stat-sub">filesystem write/delete</div>
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
              <span className={`col-row-val ${state}`}>{state === "done" ? "DONE" : "PENDING"}</span>
            </div>
          ))}
        </div>
      </div>

      {liveEvents.length > 0 && (
        <>
          <div className="section-label">Live Stream</div>
          <div className="audit-wrap" style={{maxHeight: 200, overflowY:"auto"}}>
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
    </div>
  )
}
