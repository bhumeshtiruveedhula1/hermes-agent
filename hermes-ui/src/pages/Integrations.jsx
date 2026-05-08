/* hermes-ui/src/pages/Integrations.jsx — Phase 16: Auto-Integration Builder */
import { useState, useEffect, useRef } from "react"
import axios from "axios"

// Integration brand colours — only hard-coded colours in the file
const BRAND = {
  spotify:        "#1db954",
  slack:          "#e01e5a",
  notion:         "#f5a623",
  whatsapp:       "#25d366",
  github:         "#a78bfa",
  telegram:       "#74c0fc",
  gmail:          "#ff6b6b",
  openweather:    "#6bcb77",
  weather:        "#6bcb77",
  crypto:         "#f7931a",
  jokes:          "#ffd93d",
  trivia:         "#ff9ff3",
  exchange_rates: "#00bfff",
}

const STATUS_META = {
  live:                { label: "LIVE",       color: "var(--accent)" },
  waiting_credentials: { label: "WAITING",    color: "#ffd93d" },
  building:            { label: "BUILDING",   color: "var(--blue)" },
  researching:         { label: "SEARCHING",  color: "var(--purple)" },
  failed:              { label: "FAILED",     color: "var(--red)" },
  installing:          { label: "INSTALLING", color: "#ff922b" },
}

const FEED_ICON = {
  integration_build_started:  "⚡",
  integration_researching:    "🔍",
  integration_building:       "🔨",
  integration_installing:     "📦",
  integration_waiting_creds:  "⏳",
  integration_creds_detected: "🔑",
  integration_live:           "✅",
  integration_failed:         "❌",
  integration_cancelled:      "✕",
}

function feedColor(type) {
  if (type === "integration_live")           return "var(--accent)"
  if (type === "integration_failed")         return "var(--red)"
  if (type === "integration_waiting_creds")  return "#ffd93d"
  if (type === "integration_researching")    return "var(--purple)"
  if (type === "integration_building")       return "var(--blue)"
  return "var(--dim2)"
}

export default function Integrations({ liveEvents = [] }) {
  const [input, setInput]           = useState("")
  const [building, setBuilding]     = useState(false)
  const [feedEvents, setFeedEvents] = useState([])
  const [watchingList, setWatchingList] = useState([])
  const [knownList, setKnownList]   = useState([])
  const [statuses, setStatuses]     = useState({})
  // statuses: { [name]: { status, env_vars, required_vars, tools, message } }

  const feedRef = useRef(null)

  // ── Mount: load catalog + watching list ─────────────────────────────
  useEffect(() => {
    axios.get("http://localhost:8000/api/integrations/known")
      .then(r => setKnownList(r.data))
      .catch(() => {})
    loadWatching()
  }, [])

  const loadWatching = () => {
    axios.get("http://localhost:8000/api/integrations/watching")
      .then(r => setWatchingList(r.data))
      .catch(() => {})
  }

  // ── Live WS events ───────────────────────────────────────────────────
  useEffect(() => {
    if (!liveEvents || liveEvents.length === 0) return
    const ev = liveEvents[0]
    if (!ev?.type?.startsWith("integration_")) return

    const name = ev.name || ""
    const ts   = new Date().toLocaleTimeString()

    setFeedEvents(prev => {
      const key = `${ev.type}-${name}-${ts}`
      if (prev[0]?.key === key) return prev
      return [{ ...ev, ts, key }, ...prev].slice(0, 100)
    })

    if (name) {
      setStatuses(prev => {
        const s = { ...(prev[name] || {}) }

        if (ev.type === "integration_build_started") {
          s.status  = "building"
          s.message = ev.message || "Starting build..."
        } else if (ev.type === "integration_researching") {
          s.status  = "researching"
          s.message = ev.message || "Searching API docs..."
        } else if (ev.type === "integration_building") {
          s.status  = "building"
          s.message = ev.message || "Writing code..."
        } else if (ev.type === "integration_installing") {
          s.status  = "installing"
          s.message = ev.message || "Installing packages..."
        } else if (ev.type === "integration_waiting_creds") {
          s.status        = "waiting_credentials"
          s.env_vars      = ev.env_vars || {}
          s.required_vars = ev.required_vars || []
          s.message       = ev.message || "Waiting for credentials..."
          loadWatching()
        } else if (ev.type === "integration_creds_detected") {
          s.status  = "building"
          s.message = "Credentials detected — activating..."
        } else if (ev.type === "integration_live") {
          s.status  = "live"
          s.tools   = ev.tools || []
          s.message = `Live with ${(ev.tools||[]).length} tool${(ev.tools||[]).length !== 1 ? "s" : ""}`
          setBuilding(false)
          loadWatching()
        } else if (ev.type === "integration_failed") {
          s.status  = "failed"
          s.message = ev.error || "Build failed"
          setBuilding(false)
        } else if (ev.type === "integration_cancelled") {
          return prev  // remove handled below in handleCancel
        }

        return { ...prev, [name]: s }
      })
    }

    if (feedRef.current) feedRef.current.scrollTop = 0
  }, [liveEvents])

  // ── Build ─────────────────────────────────────────────────────────────
  const handleBuild = async () => {
    const name = input.trim().toLowerCase()
    if (!name || building) return
    setBuilding(true)
    setInput("")

    // Optimistic UI: show building card immediately
    setStatuses(prev => ({
      ...prev,
      [name]: { status: "building", message: "Sending to Hermes..." }
    }))

    try {
      const { data } = await axios.post(
        "http://localhost:8000/api/integrations/build", { name }
      )
      setStatuses(prev => ({
        ...prev,
        [name]: {
          status:    data.status,
          env_vars:  data.env_vars || {},
          tools:     data.tools || [],
          required_vars: data.required_vars || [],
          message:   data.message || ""
        }
      }))
      if (data.status === "live" || data.status === "failed") setBuilding(false)
    } catch {
      setStatuses(prev => ({
        ...prev,
        [name]: { status: "failed", message: "Request failed — is the backend running?" }
      }))
      setBuilding(false)
    }
  }

  // ── Cancel watcher ────────────────────────────────────────────────────
  const handleCancel = async (name) => {
    await axios.post(`http://localhost:8000/api/integrations/${name}/cancel`)
    setStatuses(prev => {
      const next = { ...prev }
      delete next[name]
      return next
    })
    loadWatching()
  }

  // ── Copy env var names to clipboard ──────────────────────────────────
  const copyVarNames = (env_vars) => {
    const text = Object.entries(env_vars)
      .map(([k, info]) => `${k}=${typeof info === "object" && info.fixed_value ? info.fixed_value : ""}`)
      .join("\n")
    navigator.clipboard.writeText(text).catch(() => {})
  }

  // ── Render ─────────────────────────────────────────────────────────────
  return (
    <div style={{
      display: "flex", gap: 24,
      height: "calc(100vh - 200px)",
      fontFamily: "Space Mono, monospace"
    }}>

      {/* ──────── LEFT COLUMN ──────── */}
      <div style={{
        width: 440, display: "flex", flexDirection: "column",
        gap: 16, overflowY: "auto"
      }}>

        {/* Build Input Card */}
        <div style={{ border: "1px solid var(--border)", padding: 20 }}>
          <div style={{
            fontFamily: "Bebas Neue, sans-serif", fontSize: 16,
            letterSpacing: 3, color: "var(--accent)", marginBottom: 14
          }}>
            ⚡ ADD INTEGRATION
          </div>
          <div style={{
            fontSize: 10, color: "var(--dim2)", letterSpacing: 1,
            marginBottom: 10, textTransform: "uppercase"
          }}>
            Say what to add — Hermes builds it automatically
          </div>

          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !building && handleBuild()}
            placeholder="spotify / crypto / tomorrow.io weather"
            style={{
              width: "100%", padding: "10px 12px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid var(--border)",
              color: "var(--white)", fontSize: 12,
              fontFamily: "Space Mono, monospace",
              outline: "none", boxSizing: "border-box", marginBottom: 10
            }}
          />

          <button
            id="integration-build-btn"
            onClick={handleBuild}
            disabled={building || !input.trim()}
            style={{
              width: "100%", padding: 11,
              background: building ? "rgba(200,255,0,0.08)" : "var(--accent)",
              color:      building ? "var(--accent)" : "#000",
              border:     building ? "1px solid var(--accent)" : "none",
              cursor: building ? "not-allowed" : "pointer",
              fontFamily: "Space Mono, monospace", fontSize: 11,
              fontWeight: 700, letterSpacing: 2, textTransform: "uppercase",
              transition: "all 0.15s"
            }}
          >
            {building ? "BUILDING..." : "BUILD INTEGRATION"}
          </button>

          {/* Quick-pick pills from known catalog */}
          <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 6 }}>
            {knownList.map(name => (
              <button
                key={name}
                onClick={() => setInput(name)}
                title={`Add ${name} integration`}
                style={{
                  padding: "3px 9px", fontSize: 9, letterSpacing: 1,
                  background: "transparent",
                  border: `1px solid ${BRAND[name] || "var(--border)"}`,
                  color:  BRAND[name] || "var(--dim2)",
                  cursor: "pointer", textTransform: "uppercase",
                  fontFamily: "Space Mono, monospace",
                  transition: "opacity 0.15s"
                }}
                onMouseEnter={e => e.currentTarget.style.opacity = "0.7"}
                onMouseLeave={e => e.currentTarget.style.opacity = "1"}
              >
                {name}
              </button>
            ))}
          </div>
        </div>

        {/* ── Status cards for each active integration ── */}
        {Object.entries(statuses).map(([name, info]) => {
          const borderColor =
            info.status === "live"                ? "var(--accent)"         :
            info.status === "failed"              ? "var(--red)"            :
            info.status === "waiting_credentials" ? "rgba(255,211,29,0.35)":
            "var(--border)"

          const barColor = STATUS_META[info.status]?.color || "var(--dim2)"
          const isActive = info.status !== "live" && info.status !== "failed"

          return (
            <div key={name} style={{
              border: `1px solid ${borderColor}`,
              padding: 16, position: "relative"
            }}>
              {/* Animated top bar */}
              <div style={{
                position: "absolute", top: 0, left: 0, right: 0, height: 2,
                background: barColor,
                animation: isActive ? "intPulse 2s ease-in-out infinite" : "none"
              }} />

              <div style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "flex-start", marginBottom: 10
              }}>
                <div>
                  <div style={{
                    fontFamily: "Bebas Neue, sans-serif", fontSize: 18,
                    letterSpacing: 2,
                    color: BRAND[name] || "var(--white)"
                  }}>
                    {name.toUpperCase()}
                  </div>
                  <div style={{
                    fontSize: 9, letterSpacing: 2, textTransform: "uppercase",
                    color: barColor, marginTop: 2
                  }}>
                    {STATUS_META[info.status]?.label || info.status}
                  </div>
                </div>

                {info.status !== "live" && (
                  <button
                    onClick={() => handleCancel(name)}
                    style={{
                      background: "transparent",
                      border: "1px solid var(--dim2)",
                      color: "var(--dim2)", cursor: "pointer",
                      padding: "3px 8px", fontSize: 9, letterSpacing: 1,
                      fontFamily: "Space Mono, monospace", textTransform: "uppercase"
                    }}
                  >
                    CANCEL
                  </button>
                )}
              </div>

              <div style={{ fontSize: 10, color: "var(--dim2)", marginBottom: 10 }}>
                {info.message}
              </div>

              {/* Credential instructions card */}
              {info.status === "waiting_credentials" && info.env_vars && Object.keys(info.env_vars).length > 0 && (
                <div style={{
                  background: "rgba(255,211,29,0.04)",
                  border: "1px solid rgba(255,211,29,0.2)",
                  padding: 12, marginBottom: 10
                }}>
                  <div style={{
                    fontSize: 9, letterSpacing: 2, color: "#ffd93d",
                    marginBottom: 10, textTransform: "uppercase"
                  }}>
                    🔑 Add to .env — Hermes auto-activates when detected
                  </div>

                  {Object.entries(info.env_vars).map(([varName, varInfo]) => {
                    const where   = typeof varInfo === "object" ? varInfo.where || varInfo.description : varInfo
                    const fixed   = typeof varInfo === "object" ? varInfo.fixed_value : null
                    return (
                      <div key={varName} style={{ marginBottom: 10 }}>
                        <div style={{
                          fontSize: 10, color: "var(--accent)", fontWeight: 700,
                          fontFamily: "Space Mono, monospace"
                        }}>
                          {varName}=
                        </div>
                        {where && (
                          <div style={{ fontSize: 9, color: "var(--dim2)", marginTop: 3, lineHeight: 1.6 }}>
                            {where}
                          </div>
                        )}
                        {fixed && (
                          <div style={{ fontSize: 9, color: "#6bcb77", marginTop: 3 }}>
                            Use exactly: <span style={{ fontWeight: 700 }}>{fixed}</span>
                          </div>
                        )}
                      </div>
                    )
                  })}

                  <button
                    onClick={() => copyVarNames(info.env_vars)}
                    style={{
                      marginTop: 4, padding: "4px 10px", fontSize: 9,
                      background: "transparent",
                      border: "1px solid #ffd93d", color: "#ffd93d",
                      cursor: "pointer", letterSpacing: 1,
                      fontFamily: "Space Mono, monospace",
                      textTransform: "uppercase", transition: "all 0.15s"
                    }}
                  >
                    Copy Var Names
                  </button>
                </div>
              )}

              {/* Live tools list */}
              {info.status === "live" && info.tools && info.tools.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
                  {info.tools.map(tool => (
                    <span key={tool} style={{
                      padding: "2px 7px", fontSize: 9, letterSpacing: 1,
                      background: `${BRAND[name] || "var(--accent)"}18`,
                      color:      BRAND[name] || "var(--accent)",
                      border:     `1px solid ${BRAND[name] || "var(--accent)"}44`,
                      textTransform: "uppercase"
                    }}>
                      {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )
        })}

        {/* ── Currently watching card ── */}
        {watchingList.length > 0 && (
          <div style={{ border: "1px solid var(--border)", padding: 16 }}>
            <div style={{
              fontSize: 9, letterSpacing: 2, color: "var(--dim2)",
              textTransform: "uppercase", marginBottom: 10
            }}>
              ⏳ Watching for credentials ({watchingList.length})
            </div>

            {watchingList.map((w, i) => (
              <div key={w.name} style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "center", padding: "7px 0",
                borderBottom: i < watchingList.length - 1 ? "1px solid var(--border)" : "none"
              }}>
                <div>
                  <div style={{ fontSize: 11, color: "var(--white)", letterSpacing: 1 }}>
                    {w.name}
                  </div>
                  <div style={{ fontSize: 9, color: "var(--dim2)", marginTop: 2 }}>
                    Check #{w.checks} · {w.waiting_seconds}s elapsed
                  </div>
                </div>
                <div style={{
                  fontSize: 9, color: "#ffd93d", letterSpacing: 1,
                  animation: "intPulse 2s ease-in-out infinite"
                }}>
                  WAITING
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ──────── RIGHT COLUMN — LIVE FEED ──────── */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <div style={{
          fontFamily: "Bebas Neue, sans-serif", fontSize: 16,
          letterSpacing: 3, color: "var(--accent)", marginBottom: 14
        }}>
          📡 LIVE BUILD FEED
        </div>

        <div
          ref={feedRef}
          style={{
            flex: 1, overflowY: "auto",
            border: "1px solid var(--border)",
            padding: "8px 16px"
          }}
        >
          {feedEvents.length === 0 ? (
            <div style={{
              color: "var(--dim2)", fontSize: 11, letterSpacing: 1,
              textAlign: "center", paddingTop: 48, lineHeight: 2
            }}>
              Say <span style={{ color: "var(--accent)" }}>"add spotify"</span> in Chat<br />
              or use the builder on the left.<br /><br />
              Hermes researches the API, installs packages,<br />
              and watches for your credentials automatically.
            </div>
          ) : (
            feedEvents.map((ev, i) => (
              <div key={ev.key || i} style={{
                display: "flex", gap: 10, padding: "9px 0",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                animation: i === 0 ? "intFadeIn 0.3s ease" : "none"
              }}>
                <div style={{
                  fontSize: 14, flexShrink: 0, width: 22,
                  textAlign: "center", paddingTop: 1
                }}>
                  {FEED_ICON[ev.type] || "•"}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    alignItems: "baseline", marginBottom: 3
                  }}>
                    <div style={{
                      fontSize: 10, fontWeight: 700, letterSpacing: 1,
                      textTransform: "uppercase",
                      color: feedColor(ev.type)
                    }}>
                      {ev.name?.toUpperCase() || "SYSTEM"}
                    </div>
                    <div style={{ fontSize: 9, color: "var(--dim2)", flexShrink: 0 }}>
                      {ev.ts}
                    </div>
                  </div>

                  <div style={{
                    fontSize: 10, color: "var(--dim2)", lineHeight: 1.6,
                    wordBreak: "break-word"
                  }}>
                    {ev.message || ev.type?.replace("integration_", "").replace(/_/g, " ")}
                  </div>

                  {ev.tools && ev.tools.length > 0 && (
                    <div style={{
                      fontSize: 9, color: "var(--accent)", marginTop: 4,
                      letterSpacing: 1
                    }}>
                      Tools: {ev.tools.join(" · ")}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <style>{`
        @keyframes intPulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.3; }
        }
        @keyframes intFadeIn {
          from { opacity: 0; transform: translateY(-4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
