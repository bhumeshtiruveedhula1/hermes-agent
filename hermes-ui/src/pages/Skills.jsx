/* hermes-ui/src/pages/Skills.jsx — Phase 17: Skill Browser */
import { useState, useEffect, useRef } from "react"
import axios from "axios"

const API = "http://localhost:8000"

// ── Tool badge — same TOOL_COLORS as Missions/History ─────────────────────
const TOOL_COLORS = {
  fs_write: "#ffd93d", fs_delete: "#ffd93d", fs_list: "#ffd93d", fs_read: "#ffd93d",
  search_web: "#6bcb77", weather_current: "#6bcb77",
  browser_go: "#4ecdc4", browser_read: "#4ecdc4",
  gmail_send: "#ff6b6b", gmail_list: "#ff6b6b",
  calendar_create: "#ff922b", calendar_list: "#ff922b",
  telegram_send: "#74c0fc",
  notion_list: "#f5a623", notion_create: "#f5a623",
  slack_send: "#e01e5a", slack_channels: "#e01e5a",
  spotify_play: "#1db954", spotify_current: "#1db954",
  whatsapp_send: "#25d366",
  github_repos: "#a78bfa", github_issues: "#a78bfa",
  skill_loaded: "#c8ff00",
}

function ToolBadge({ tool }) {
  if (!tool) return null
  const color = TOOL_COLORS[tool] || "#888"
  return (
    <span style={{
      display: "inline-block", padding: "2px 7px", marginRight: 4, marginBottom: 4,
      background: `${color}22`, border: `1px solid ${color}55`,
      color, fontSize: 8, fontFamily: "Space Mono,monospace",
      letterSpacing: 1, borderRadius: 2, textTransform: "uppercase",
    }}>
      {tool.replace(/_/g, " ")}
    </span>
  )
}

// ── Trigger phrase badge ──────────────────────────────────────────────────
function TriggerBadge({ phrase }) {
  return (
    <span style={{
      display: "inline-block", padding: "2px 9px", marginRight: 5, marginBottom: 4,
      background: "rgba(200,255,0,.06)", border: "1px solid rgba(200,255,0,.2)",
      color: "var(--accent)", fontSize: 8, fontFamily: "Space Mono,monospace",
      letterSpacing: 1, borderRadius: 2,
    }}>
      "{phrase}"
    </span>
  )
}

// ── Inline confirm delete ─────────────────────────────────────────────────
function DeleteBtn({ onConfirm }) {
  const [ask, setAsk] = useState(false)
  if (ask) return (
    <div style={{ display: "flex", gap: 6 }}>
      <button onClick={onConfirm} style={{
        padding: "5px 12px", background: "var(--red)", color: "#fff",
        border: "none", fontFamily: "Space Mono,monospace", fontSize: 9,
        cursor: "pointer", letterSpacing: 1,
      }}>CONFIRM DELETE</button>
      <button onClick={() => setAsk(false)} style={{
        padding: "5px 12px", background: "transparent", color: "var(--dim2)",
        border: "1px solid var(--border2)", fontFamily: "Space Mono,monospace",
        fontSize: 9, cursor: "pointer",
      }}>CANCEL</button>
    </div>
  )
  return (
    <button
      onClick={() => setAsk(true)}
      style={{
        padding: "5px 14px", background: "transparent", color: "var(--dim2)",
        border: "1px solid var(--border)", fontFamily: "Space Mono,monospace",
        fontSize: 9, cursor: "pointer", letterSpacing: 1, textTransform: "uppercase",
        transition: "all .15s",
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--red)"; e.currentTarget.style.color = "var(--red)" }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.color = "var(--dim2)" }}
    >Delete</button>
  )
}

// ── Skill card ────────────────────────────────────────────────────────────
function SkillCard({ skill, onDelete }) {
  const steps    = skill.steps || []
  const triggers = skill.trigger_phrases || []
  const tools    = [...new Set(steps.map(s => s.tool).filter(Boolean))]

  return (
    <div style={{
      background: "var(--black)", border: "1px solid var(--border)",
      padding: "22px 24px", position: "relative", overflow: "hidden",
      transition: "border-color .2s, background .2s",
    }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--border2)"; e.currentTarget.style.background = "var(--black3)" }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--border)"; e.currentTarget.style.background = "var(--black)" }}
    >
      {/* Left accent bar */}
      <div style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: 2,
        background: "var(--accent)",
      }} />

      {/* Header row */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <div style={{
            fontFamily: "Bebas Neue,sans-serif", fontSize: 18, letterSpacing: 2,
            color: "var(--white)", marginBottom: 4,
          }}>
            {skill.name.replace(/_/g, " ").toUpperCase()}
          </div>
          <div style={{
            fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim2)",
            lineHeight: 1.6,
          }}>
            {skill.description}
          </div>
        </div>
        {/* Use count badge */}
        <div style={{
          display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6, flexShrink: 0, marginLeft: 16,
        }}>
          <span style={{
            padding: "3px 10px",
            background: skill.use_count > 0 ? "rgba(200,255,0,.12)" : "rgba(255,255,255,.04)",
            border: `1px solid ${skill.use_count > 0 ? "rgba(200,255,0,.3)" : "var(--border)"}`,
            color: skill.use_count > 0 ? "var(--accent)" : "var(--dim2)",
            fontFamily: "Space Mono,monospace", fontSize: 9, letterSpacing: 1,
            borderRadius: 2,
          }}>
            {skill.use_count} USE{skill.use_count !== 1 ? "S" : ""}
          </span>
        </div>
      </div>

      {/* Trigger phrases */}
      {triggers.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)",
            letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>
            TRIGGER PHRASES
          </div>
          <div>{triggers.map((p, i) => <TriggerBadge key={i} phrase={p} />)}</div>
        </div>
      )}

      {/* Tools */}
      {tools.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)",
            letterSpacing: 2, textTransform: "uppercase", marginBottom: 6 }}>
            TOOLS — {steps.length} STEPS
          </div>
          <div>{tools.map((t, i) => <ToolBadge key={i} tool={t} />)}</div>
        </div>
      )}

      {/* Footer: last used + delete */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
        <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim)" }}>
          {skill.last_used
            ? `Last used: ${skill.last_used.slice(0, 16).replace("T", " ")}`
            : `Created: ${(skill.created_at || "").slice(0, 10)}`}
        </div>
        <DeleteBtn onConfirm={() => onDelete(skill.name)} />
      </div>
    </div>
  )
}

// ── Skill loaded banner ───────────────────────────────────────────────────
function SkillLoadedBanner({ name, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2000)
    return () => clearTimeout(t)
  }, [])
  return (
    <div style={{
      padding: "10px 18px", marginBottom: 18,
      background: "rgba(200,255,0,.08)", border: "1px solid rgba(200,255,0,.3)",
      fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--accent)",
      letterSpacing: 1, animation: "fadeUp .2s ease",
      display: "flex", alignItems: "center", gap: 10,
    }}>
      <span>⚡</span>
      <span>SKILL LOADED — <strong>{name}</strong> — replanning skipped</span>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────
export default function Skills({ liveEvents }) {
  const [skills, setSkills]         = useState([])
  const [loading, setLoading]       = useState(true)
  const [banner, setBanner]         = useState(null)     // { name }
  const seenEvents                  = useRef(new Set())

  const load = async () => {
    try {
      const res = await axios.get(`${API}/api/skills`)
      setSkills(res.data)
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  // React to live WebSocket events without re-mounting
  useEffect(() => {
    if (!liveEvents || liveEvents.length === 0) return
    const latest = liveEvents[0]
    const evKey  = `${latest.type}_${latest.name}_${latest.ts || ""}`
    if (seenEvents.current.has(evKey)) return
    seenEvents.current.add(evKey)

    if (latest.type === "skill_saved") {
      load()
    }
    if (latest.type === "skill_loaded" && latest.name) {
      setBanner({ name: latest.name })
    }
  }, [liveEvents])

  const deleteSkill = async (name) => {
    try {
      await axios.delete(`${API}/api/skills/${name}`)
      load()
    } catch {}
  }

  // Stats
  const totalUses = skills.reduce((s, sk) => s + (sk.use_count || 0), 0)
  const lastUsed  = skills
    .filter(sk => sk.last_used)
    .sort((a, b) => b.last_used.localeCompare(a.last_used))[0]

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "baseline", gap: 18, marginBottom: 6 }}>
          <div style={{ fontFamily: "Bebas Neue,sans-serif", fontSize: 32, letterSpacing: 4 }}>
            SKILLS
          </div>
          <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim2)", letterSpacing: 2 }}>
            PHASE 17 · PROCEDURAL MEMORY
          </div>
        </div>
        <div style={{ height: 1, background: "var(--border2)", marginBottom: 24 }} />
      </div>

      {/* Skill loaded banner */}
      {banner && (
        <SkillLoadedBanner name={banner.name} onDone={() => setBanner(null)} />
      )}

      {/* Stats bar */}
      {skills.length > 0 && (
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: 1, background: "var(--border2)",
          border: "1px solid var(--border2)", marginBottom: 28,
        }}>
          {[
            { label: "SKILLS SAVED",  value: skills.length,  accent: true },
            { label: "TOTAL USES",    value: totalUses,       accent: totalUses > 0 },
            { label: "LAST USED",     value: lastUsed ? lastUsed.name.replace(/_/g, " ").slice(0, 20) : "—", accent: false },
          ].map(({ label, value, accent }) => (
            <div key={label} style={{ background: "var(--black)", padding: "18px 22px" }}>
              <div style={{
                fontFamily: "Space Mono,monospace", fontSize: 8, letterSpacing: 2,
                textTransform: "uppercase", color: "var(--dim2)", marginBottom: 8,
              }}>{label}</div>
              <div style={{
                fontFamily: "Bebas Neue,sans-serif", fontSize: 32, lineHeight: 1,
                color: accent ? "var(--accent)" : "var(--white)",
              }}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{ fontFamily: "Space Mono,monospace", fontSize: 11, color: "var(--dim2)", padding: "24px 0" }}>
          Loading skills...
        </div>
      )}

      {/* Empty state */}
      {!loading && skills.length === 0 && (
        <div style={{ padding: "60px 0", textAlign: "center" }}>
          <div style={{
            fontFamily: "Bebas Neue,sans-serif", fontSize: 36, letterSpacing: 4,
            color: "var(--dim)", marginBottom: 12,
          }}>NO SKILLS YET</div>
          <div style={{
            fontFamily: "Space Mono,monospace", fontSize: 11, color: "var(--dim2)",
            lineHeight: 2, maxWidth: 400, margin: "0 auto",
          }}>
            Complete an autonomous mission with 3+ steps.<br />
            Hermes will offer to save it as a reusable skill.
          </div>
        </div>
      )}

      {/* Skill card grid */}
      {!loading && skills.length > 0 && (
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
          gap: 1, background: "var(--border)",
        }}>
          {skills.map(sk => (
            <SkillCard key={sk.id || sk.name} skill={sk} onDelete={deleteSkill} />
          ))}
        </div>
      )}
    </div>
  )
}
