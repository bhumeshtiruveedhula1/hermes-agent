/* hermes-ui/src/pages/Memory.jsx — Phase 17: User Memory & Personality */
import { useState, useEffect, useRef } from "react"
import axios from "axios"

const API = "http://localhost:8000"

// ── Shared input style ────────────────────────────────────────────────────
const inputStyle = {
  background: "transparent",
  border: "1px solid var(--border2)",
  color: "var(--white)",
  fontFamily: "Space Mono,monospace",
  fontSize: 11,
  padding: "9px 14px",
  outline: "none",
  width: "100%",
  boxSizing: "border-box",
}

const btnStyle = (accent = false, danger = false) => ({
  padding: "9px 20px",
  background: accent ? "var(--accent)" : "transparent",
  color: accent ? "var(--black)" : danger ? "var(--red)" : "var(--white)",
  border: `1px solid ${accent ? "var(--accent)" : danger ? "var(--red)" : "var(--border2)"}`,
  fontFamily: "Space Mono,monospace",
  fontSize: 10,
  letterSpacing: 1,
  textTransform: "uppercase",
  cursor: "pointer",
  transition: "opacity .15s",
})

// ── Category badge ────────────────────────────────────────────────────────
const CAT_COLORS = {
  preference: "#c8ff00",
  fact:       "#74c0fc",
  correction: "#ff922b",
  general:    "#888880",
}
function CatBadge({ cat }) {
  const c = CAT_COLORS[cat] || "#888"
  return (
    <span style={{
      display: "inline-block", padding: "2px 8px",
      background: `${c}18`, border: `1px solid ${c}40`,
      color: c, fontSize: 8, fontFamily: "Space Mono,monospace",
      letterSpacing: 1, textTransform: "uppercase", borderRadius: 2,
    }}>
      {cat}
    </span>
  )
}

// ── Inline confirmation delete ────────────────────────────────────────────
function DeleteBtn({ onConfirm }) {
  const [ask, setAsk] = useState(false)
  if (ask) return (
    <span style={{ display: "flex", gap: 6 }}>
      <button onClick={onConfirm} style={{ ...btnStyle(false, true), padding: "4px 10px", fontSize: 8 }}>Yes</button>
      <button onClick={() => setAsk(false)} style={{ ...btnStyle(), padding: "4px 10px", fontSize: 8 }}>No</button>
    </span>
  )
  return (
    <button onClick={() => setAsk(true)} style={{
      background: "none", border: "none", cursor: "pointer",
      color: "var(--dim2)", fontFamily: "Space Mono,monospace", fontSize: 10,
      padding: "2px 6px",
    }}
      onMouseEnter={e => e.currentTarget.style.color = "var(--red)"}
      onMouseLeave={e => e.currentTarget.style.color = "var(--dim2)"}
    >✕</button>
  )
}

// ── Memory Entries tab ────────────────────────────────────────────────────
function MemoryEntriesTab() {
  const [entries, setEntries]   = useState([])
  const [content, setContent]   = useState("")
  const [cat, setCat]           = useState("preference")
  const [search, setSearch]     = useState("")
  const [searchRes, setSearchRes] = useState(null)
  const [saving, setSaving]     = useState(false)
  const [error, setError]       = useState("")
  const [ok, setOk]             = useState("")

  const load = async () => {
    try {
      const res = await axios.get(`${API}/api/memory`)
      setEntries(res.data)
    } catch { setError("Failed to load memory") }
  }

  useEffect(() => { load() }, [])

  const add = async () => {
    if (!content.trim()) return
    setSaving(true); setError(""); setOk("")
    try {
      const res = await axios.post(`${API}/api/memory`, { content: content.trim(), category: cat })
      if (res.data.error) { setError(res.data.error); return }
      if (res.data.duplicate) { setError("Already saved: this exact fact exists."); return }
      setContent("")
      setOk("Saved ✓")
      setTimeout(() => setOk(""), 2000)
      load()
    } catch { setError("Save failed") }
    finally { setSaving(false) }
  }

  const del = async (id) => {
    try {
      await axios.delete(`${API}/api/memory/${id}`)
      load()
    } catch { setError("Delete failed") }
  }

  const doSearch = async () => {
    if (!search.trim()) { setSearchRes(null); return }
    try {
      const res = await axios.get(`${API}/api/memory/search?q=${encodeURIComponent(search)}&limit=15`)
      setSearchRes(res.data)
    } catch { setError("Search failed") }
  }

  // Group by category
  const grouped = entries.reduce((acc, e) => {
    const c = e.category || "general"
    if (!acc[c]) acc[c] = []
    acc[c].push(e)
    return acc
  }, {})

  return (
    <div>
      {/* Add new entry */}
      <div style={{
        background: "rgba(255,255,255,.02)", border: "1px solid var(--border)",
        padding: "18px 20px", marginBottom: 20,
      }}>
        <div style={{ fontSize: 9, fontFamily: "Space Mono,monospace", letterSpacing: 2,
          color: "var(--dim2)", textTransform: "uppercase", marginBottom: 12 }}>
          ADD MEMORY ENTRY
        </div>
        <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
          <input
            id="memory-content-input"
            style={{ ...inputStyle, flex: 1 }}
            placeholder="E.g. User prefers concise responses without bullet points"
            value={content}
            onChange={e => setContent(e.target.value)}
            onKeyDown={e => e.key === "Enter" && add()}
          />
          <select
            value={cat}
            onChange={e => setCat(e.target.value)}
            style={{ ...inputStyle, width: 120, cursor: "pointer" }}
          >
            <option value="preference">Preference</option>
            <option value="fact">Fact</option>
            <option value="correction">Correction</option>
            <option value="general">General</option>
          </select>
          <button onClick={add} disabled={saving} style={btnStyle(true)}>
            {saving ? "..." : "Save"}
          </button>
        </div>
        {error && <div style={{ color: "var(--red)", fontFamily: "Space Mono,monospace", fontSize: 10, marginTop: 6 }}>{error}</div>}
        {ok    && <div style={{ color: "var(--accent)", fontFamily: "Space Mono,monospace", fontSize: 10, marginTop: 6 }}>{ok}</div>}
      </div>

      {/* FTS Search */}
      <div style={{ display: "flex", gap: 8, marginBottom: 20 }}>
        <input
          id="memory-search-input"
          style={{ ...inputStyle, flex: 1 }}
          placeholder="Search all message history (FTS5)..."
          value={search}
          onChange={e => { setSearch(e.target.value); if (!e.target.value) setSearchRes(null) }}
          onKeyDown={e => e.key === "Enter" && doSearch()}
        />
        <button onClick={doSearch} style={btnStyle()}>Search</button>
        {searchRes && <button onClick={() => { setSearchRes(null); setSearch("") }} style={btnStyle()}>Clear</button>}
      </div>

      {/* Search results */}
      {searchRes !== null && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 9, fontFamily: "Space Mono,monospace", letterSpacing: 2,
            color: "var(--accent)", marginBottom: 10 }}>
            SEARCH RESULTS — {searchRes.length} MATCHES
          </div>
          {searchRes.length === 0 && (
            <div style={{ color: "var(--dim2)", fontFamily: "Space Mono,monospace", fontSize: 11, padding: "16px 0" }}>
              No messages found for "{search}"
            </div>
          )}
          {searchRes.map((r, i) => (
            <div key={i} style={{
              padding: "12px 16px", marginBottom: 6,
              background: "rgba(200,255,0,.03)", border: "1px solid var(--border)",
              fontFamily: "Space Mono,monospace",
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 9, color: "var(--dim2)", letterSpacing: 1 }}>
                  {r.session_title || r.session_id} · {r.role?.toUpperCase()}
                </span>
                <span style={{ fontSize: 9, color: "var(--dim)" }}>
                  {(r.ts || r.session_date || "").slice(0, 16).replace("T", " ")}
                </span>
              </div>
              <div style={{ fontSize: 11, color: "var(--white)", lineHeight: 1.6 }}>
                {(r.content || "").slice(0, 300)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Memory entries grouped */}
      {searchRes === null && (
        <>
          {entries.length === 0 && (
            <div style={{ padding: "40px 0", textAlign: "center" }}>
              <div style={{ fontFamily: "Bebas Neue,sans-serif", fontSize: 28, color: "var(--dim)", letterSpacing: 3, marginBottom: 8 }}>
                NO MEMORY YET
              </div>
              <div style={{ fontFamily: "Space Mono,monospace", fontSize: 11, color: "var(--dim2)" }}>
                Add facts above or chat with Hermes — memory is extracted automatically.
              </div>
            </div>
          )}
          {Object.entries(grouped).map(([catKey, items]) => (
            <div key={catKey} style={{ marginBottom: 24 }}>
              <div className="section-label">{catKey.toUpperCase()}</div>
              {items.map(e => (
                <div key={e.id} style={{
                  display: "flex", alignItems: "flex-start", gap: 12,
                  padding: "10px 14px", marginBottom: 4,
                  background: "rgba(255,255,255,.015)", border: "1px solid var(--border)",
                  transition: "background .15s",
                }}
                  onMouseEnter={el => el.currentTarget.style.background = "rgba(255,255,255,.03)"}
                  onMouseLeave={el => el.currentTarget.style.background = "rgba(255,255,255,.015)"}
                >
                  <CatBadge cat={e.category} />
                  <div style={{ flex: 1, fontFamily: "Space Mono,monospace", fontSize: 11, lineHeight: 1.6 }}>
                    {e.content}
                  </div>
                  <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim)", whiteSpace: "nowrap", paddingTop: 2 }}>
                    {(e.created_at || "").slice(0, 10)}
                  </div>
                  <DeleteBtn onConfirm={() => del(e.id)} />
                </div>
              ))}
            </div>
          ))}
        </>
      )}
    </div>
  )
}

// ── Profile tab ───────────────────────────────────────────────────────────
function ProfileTab() {
  const [profileMd, setProfileMd] = useState("")
  const [saved, setSaved]         = useState("")
  const [error, setError]         = useState("")
  const [loading, setLoading]     = useState(true)
  const [lastSaved, setLastSaved] = useState("")

  useEffect(() => {
    axios.get(`${API}/api/profile`)
      .then(r => { setProfileMd(r.data.profile_md || ""); setLoading(false) })
      .catch(() => { setError("Failed to load profile"); setLoading(false) })
  }, [])

  const save = async () => {
    setError(""); setSaved("")
    try {
      await axios.post(`${API}/api/profile`, { profile_md: profileMd })
      setSaved("Saved ✓")
      setLastSaved(new Date().toLocaleTimeString())
      setTimeout(() => setSaved(""), 2500)
    } catch { setError("Save failed") }
  }

  return (
    <div>
      <div style={{
        fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim2)",
        lineHeight: 1.8, marginBottom: 20,
        padding: "12px 16px", background: "rgba(200,255,0,.04)",
        border: "1px solid rgba(200,255,0,.15)",
      }}>
        <span style={{ color: "var(--accent)", marginRight: 8 }}>ℹ</span>
        This profile is injected into every planning request.
        Tell Hermes your name, location, work context, and preferences.
      </div>

      {loading ? (
        <div style={{ fontFamily: "Space Mono,monospace", fontSize: 11, color: "var(--dim2)" }}>Loading...</div>
      ) : (
        <>
          <textarea
            id="profile-md-textarea"
            value={profileMd}
            onChange={e => setProfileMd(e.target.value)}
            placeholder={"What should Hermes know about you?\n\nExamples:\n  My name is Bhumesh. I'm a developer based in Bangalore.\n  I prefer concise responses without bullet points.\n  My GitHub username is bhumeshtiruveedhula1.\n  I work on AI agent systems and FastAPI backends."}
            style={{
              ...inputStyle,
              height: 240,
              resize: "vertical",
              lineHeight: 1.8,
              display: "block",
              marginBottom: 12,
            }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <button id="profile-save-btn" onClick={save} style={btnStyle(true)}>Save Profile</button>
            {saved && <span style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--accent)" }}>{saved}</span>}
            {error && <span style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--red)" }}>{error}</span>}
            {lastSaved && (
              <span style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim)", marginLeft: "auto" }}>
                Last saved {lastSaved}
              </span>
            )}
          </div>
        </>
      )}
    </div>
  )
}

// ── Soul tab ──────────────────────────────────────────────────────────────
const DEFAULT_SOUL = `You are Hermes, an autonomous AI agent.
Be direct and concise. Never pad responses with filler.
Never use bullet points unless explicitly asked.
Always confirm before sending messages to people.
Call the user by their first name when you know it.
Prefer showing results over explaining what you will do.`

function SoulTab() {
  const [soulMd, setSoulMd]   = useState("")
  const [saved, setSaved]     = useState("")
  const [error, setError]     = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios.get(`${API}/api/profile`)
      .then(r => { setSoulMd(r.data.soul_md || ""); setLoading(false) })
      .catch(() => { setError("Failed to load soul config"); setLoading(false) })
  }, [])

  const save = async () => {
    setError(""); setSaved("")
    try {
      await axios.post(`${API}/api/profile`, { soul_md: soulMd })
      setSaved("Saved ✓")
      setTimeout(() => setSaved(""), 2500)
    } catch { setError("Save failed") }
  }

  const reset = () => {
    setSoulMd(DEFAULT_SOUL)
    setSaved("")
  }

  return (
    <div>
      <div style={{
        fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim2)",
        lineHeight: 1.8, marginBottom: 20,
        padding: "12px 16px", background: "rgba(255,59,59,.04)",
        border: "1px solid rgba(255,59,59,.2)",
      }}>
        <span style={{ color: "var(--red)", marginRight: 8 }}>⚠</span>
        This overrides Hermes's default personality. Changes take effect on next message.
      </div>

      {loading ? (
        <div style={{ fontFamily: "Space Mono,monospace", fontSize: 11, color: "var(--dim2)" }}>Loading...</div>
      ) : (
        <>
          <textarea
            id="soul-md-textarea"
            value={soulMd}
            onChange={e => setSoulMd(e.target.value)}
            placeholder={DEFAULT_SOUL}
            style={{
              ...inputStyle,
              height: 220,
              resize: "vertical",
              lineHeight: 1.9,
              display: "block",
              marginBottom: 12,
              borderColor: soulMd ? "rgba(200,255,0,.3)" : "var(--border2)",
            }}
          />
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <button id="soul-save-btn" onClick={save} style={btnStyle(true)}>Save Personality</button>
            <button onClick={reset} style={btnStyle()}>Reset to Default</button>
            {saved && <span style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--accent)" }}>{saved}</span>}
            {error && <span style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--red)" }}>{error}</span>}
          </div>
        </>
      )}
    </div>
  )
}

// ── Skill Candidate Toast ─────────────────────────────────────────────────
function SkillCandidateToast({ candidate, onSaved, onDismiss }) {
  const [saving, setSaving] = useState(false)
  const [done, setDone]     = useState(false)
  const timerRef            = useRef(null)

  useEffect(() => {
    timerRef.current = setTimeout(onDismiss, 8000)
    return () => clearTimeout(timerRef.current)
  }, [])

  const save = async () => {
    setSaving(true)
    try {
      await axios.post(`${API}/api/skills`, {
        name:            candidate.name,
        description:     candidate.description,
        steps:           candidate.steps,
        trigger_phrases: candidate.trigger_phrases || [],
      })
      setDone(true)
      clearTimeout(timerRef.current)
      setTimeout(() => { onSaved(); onDismiss() }, 1200)
    } catch {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: "fixed", bottom: 28, right: 28, zIndex: 500,
      width: 320, background: "var(--black2)",
      border: "1px solid rgba(200,255,0,.4)",
      padding: "18px 20px",
      boxShadow: "0 4px 32px rgba(0,0,0,.6)",
      animation: "fadeUp .3s ease",
      fontFamily: "Space Mono,monospace",
    }}>
      <div style={{ fontSize: 9, letterSpacing: 2, color: "var(--accent)", marginBottom: 10, textTransform: "uppercase" }}>
        💾 Save as Skill?
      </div>
      <div style={{ fontSize: 12, color: "var(--white)", marginBottom: 4 }}>
        {candidate.name.replace(/_/g, " ")}
      </div>
      <div style={{ fontSize: 10, color: "var(--dim2)", lineHeight: 1.6, marginBottom: 14 }}>
        {candidate.description}
      </div>
      {done ? (
        <div style={{ color: "var(--accent)", fontSize: 11 }}>Skill saved ✓</div>
      ) : (
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={save} disabled={saving} style={{ ...btnStyle(true), flex: 1, fontSize: 9 }}>
            {saving ? "Saving..." : "Save Skill"}
          </button>
          <button onClick={onDismiss} style={{ ...btnStyle(), fontSize: 9, padding: "9px 14px" }}>
            Dismiss
          </button>
        </div>
      )}
      {/* Auto-dismiss progress bar */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, height: 2,
        background: "rgba(200,255,0,.3)",
        animation: "toastProgress 8s linear forwards",
      }} />
      <style>{`@keyframes toastProgress { from{width:100%} to{width:0} }`}</style>
    </div>
  )
}

// ── Page sub-tab nav ──────────────────────────────────────────────────────
const PAGE_TABS = ["MEMORY ENTRIES", "PROFILE", "SOUL"]

// ── Main export ───────────────────────────────────────────────────────────
export default function Memory({ skillCandidate, onSkillSaved }) {
  const [activeTab, setActiveTab] = useState("MEMORY ENTRIES")
  const [showToast, setShowToast] = useState(false)
  const prevCandidate = useRef(null)

  // Show toast when new skill_candidate arrives
  useEffect(() => {
    if (skillCandidate && skillCandidate !== prevCandidate.current) {
      prevCandidate.current = skillCandidate
      setShowToast(true)
    }
  }, [skillCandidate])

  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: 28 }}>
        <div style={{
          display: "flex", alignItems: "baseline", gap: 18, marginBottom: 6,
        }}>
          <div style={{ fontFamily: "Bebas Neue,sans-serif", fontSize: 32, letterSpacing: 4 }}>
            MEMORY
          </div>
          <div style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim2)", letterSpacing: 2 }}>
            PHASE 17 · PERSISTENT USER INTELLIGENCE
          </div>
        </div>
        <div style={{ height: 1, background: "var(--border2)", marginBottom: 24 }} />
      </div>

      {/* Sub-tab nav */}
      <div style={{
        display: "flex", borderBottom: "1px solid var(--border)", marginBottom: 28,
      }}>
        {PAGE_TABS.map(t => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            style={{
              padding: "10px 20px",
              background: "none", border: "none",
              borderBottom: `2px solid ${activeTab === t ? "var(--accent)" : "transparent"}`,
              color: activeTab === t ? "var(--accent)" : "var(--dim2)",
              fontFamily: "Space Mono,monospace", fontSize: 9,
              letterSpacing: 2, textTransform: "uppercase",
              cursor: "pointer", marginBottom: -1,
              transition: "color .15s, border-color .15s",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "MEMORY ENTRIES" && <MemoryEntriesTab />}
      {activeTab === "PROFILE"        && <ProfileTab />}
      {activeTab === "SOUL"           && <SoulTab />}

      {/* Skill candidate toast */}
      {showToast && skillCandidate && (
        <SkillCandidateToast
          candidate={skillCandidate}
          onSaved={() => { onSkillSaved?.(); setShowToast(false) }}
          onDismiss={() => setShowToast(false)}
        />
      )}
    </div>
  )
}
