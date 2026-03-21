/* hermes-ui/src/pages/Plugins.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

export default function Plugins() {
  const [data, setData] = useState({ active: [], pending: [] })
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState("")
  const [designInput, setDesignInput] = useState("")
  const [designing, setDesigning] = useState(false)
  const [designResult, setDesignResult] = useState(null)

  const load = () =>
    axios.get("http://localhost:8000/api/plugins")
      .then(r => setData(r.data))
      .catch(() => {})

  useEffect(() => { load() }, [])

  const flash = (text) => {
    setMsg(text)
    setTimeout(() => setMsg(""), 3000)
  }

  
  

  const reject = async (name) => {
    setLoading(true)
    await axios.post(`http://localhost:8000/api/plugins/${name}/reject`)
    flash(`❌ Plugin '${name}' rejected.`)
    load()
    setLoading(false)
  }

  const disable = async (name) => {
    setLoading(true)
    await axios.post(`http://localhost:8000/api/plugins/${name}/disable`)
    flash(`Plugin '${name}' disabled.`)
    load()
    setLoading(false)
  }

  const designPlugin = async () => {
    if (!designInput.trim()) return
    setDesigning(true)
    setDesignResult(null)
    try {
      const res = await axios.post("http://localhost:8000/api/plugins/design", {
        description: designInput
      })
      setDesignResult(res.data)
      setDesignInput("")
      load()
    } catch (e) {
      setDesignResult({ error: "Design failed — check backend logs" })
    }
    setDesigning(false)
  }


  const approve = async (name) => {
    setLoading(true)
    const res = await axios.post(`http://localhost:8000/api/plugins/${name}/approve`)
    if (res.data.ok) {
      flash(`✅ Plugin '${name}' approved and active!`)
    } else {
      flash(`❌ Approval failed: ${res.data.error}`)
    }
    load()
    setLoading(false)
  }

  return (
    <div>

      {/* AI PLUGIN DESIGNER */}
      <div style={{marginBottom:32}}>
        <div className="section-label">AI Plugin Designer</div>
        <div style={{
          border:"1px solid var(--border2)", padding:"20px 24px",
          background:"var(--black)"
        }}>
          <div style={{
            fontFamily:"Space Mono,monospace", fontSize:10,
            color:"var(--dim2)", marginBottom:12
          }}>
            Describe a new integration in plain English — Hermes will design it
          </div>
          <div style={{display:"flex", gap:0}}>
            <input
              className="chat-input"
              style={{flex:1, border:"1px solid var(--border2)",
                borderRight:"none", padding:"12px 18px"}}
              placeholder="a Spotify plugin that shows what's playing and controls playback"
              value={designInput}
              onChange={e => setDesignInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && designPlugin()}
              disabled={designing}
            />
            <button
              className="chat-send"
              onClick={designPlugin}
              disabled={designing}
            >
              {designing ? "Designing..." : "Design"}
            </button>
          </div>

          {designResult && (
            <div style={{marginTop:16}}>
              {designResult.error ? (
                <div style={{
                  padding:"14px 16px",
                  background:"rgba(255,59,59,0.08)",
                  border:"1px solid var(--red)",
                  fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--red)"
                }}>❌ {designResult.error}</div>
              ) : (
                <div>
                  <div style={{
                    padding:"14px 16px", marginBottom:8,
                    background:"rgba(200,255,0,0.05)",
                    border:"1px solid rgba(200,255,0,0.3)",
                    fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--accent)"
                  }}>
                    ✅ Plugin '{designResult.plugin_name}' designed — review below then approve from Pending
                  </div>

                  {/* SPEC PREVIEW */}
                  <div style={{marginBottom:8}}>
                    <div style={{fontFamily:"Space Mono,monospace", fontSize:9,
                      letterSpacing:2, textTransform:"uppercase", color:"var(--dim2)",
                      marginBottom:6}}>Plugin Spec</div>
                    <pre style={{
                      background:"rgba(255,255,255,0.02)", border:"1px solid var(--border)",
                      padding:"12px 16px", fontFamily:"Space Mono,monospace", fontSize:9,
                      color:"var(--dim2)", overflowX:"auto", lineHeight:1.8,
                      maxHeight:200, overflowY:"auto"
                    }}>
                      {JSON.stringify(designResult.spec, null, 2)}
                    </pre>
                  </div>

                  {/* CODE PREVIEW */}
                  <div>
                    <div style={{fontFamily:"Space Mono,monospace", fontSize:9,
                      letterSpacing:2, textTransform:"uppercase", color:"var(--dim2)",
                      marginBottom:6}}>Generated Python Code</div>
                    <pre style={{
                      background:"rgba(255,255,255,0.02)", border:"1px solid var(--border)",
                      padding:"12px 16px", fontFamily:"Space Mono,monospace", fontSize:9,
                      color:"var(--dim2)", overflowX:"auto", lineHeight:1.8,
                      maxHeight:300, overflowY:"auto"
                    }}>
                      {designResult.code}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* FLASH MESSAGE */}
      {msg && (
        <div style={{
          padding:"12px 20px", marginBottom:24,
          background:"rgba(200,255,0,0.08)",
          border:"1px solid rgba(200,255,0,0.3)",
          fontFamily:"Space Mono,monospace", fontSize:11,
          color:"var(--accent)"
        }}>
          {msg}
        </div>
      )}

      {/* STATS */}
      <div className="stat-strip" style={{gridTemplateColumns:"repeat(3,1fr)", marginBottom:32}}>
        <div className="stat-cell">
          <div className="stat-label">Active Plugins</div>
          <div className="stat-value accent">{data.active.length}</div>
          <div className="stat-sub">running now</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Pending Approval</div>
          <div className="stat-value" style={{color: data.pending.length > 0 ? "var(--red)" : "var(--white)"}}>
            {data.pending.length}
          </div>
          <div className="stat-sub">awaiting review</div>
        </div>
        <div className="stat-cell">
          <div className="stat-label">Total Tools</div>
          <div className="stat-value">
            {data.active.reduce((sum, p) => sum + (p.tool_count || 0), 0)}
          </div>
          <div className="stat-sub">available to agents</div>
        </div>
      </div>

      {/* ACTIVE PLUGINS */}
      <div className="section-label">Active Plugins</div>
      {data.active.length === 0 ? (
        <div style={{fontFamily:"Space Mono,monospace", fontSize:11, color:"var(--dim2)", padding:"20px 0"}}>
          No active plugins.
        </div>
      ) : (
        <div style={{display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:1, background:"var(--border)", marginBottom:32}}>
          {data.active.map(p => (
            <div key={p.name} style={{
              background:"var(--black)", padding:"24px",
              position:"relative", borderLeft:"2px solid var(--accent)"
            }}>
              <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"Space Mono,monospace", fontSize:13, fontWeight:700, marginBottom:4}}>
                    {p.name.toUpperCase()}
                  </div>
                  <div style={{fontFamily:"Space Mono,monospace", fontSize:9, color:"var(--dim2)", letterSpacing:2}}>
                    v{p.version} — {p.tool_count} tools
                  </div>
                </div>
                <div className="badge on">ACTIVE</div>
              </div>

              <div style={{fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--dim2)", marginBottom:14}}>
                {p.description}
              </div>

              <div style={{
                background:"rgba(255,255,255,0.02)", border:"1px solid var(--border)",
                padding:"10px 14px", marginBottom:16
              }}>
                <div style={{fontFamily:"Space Mono,monospace", fontSize:9, letterSpacing:2,
                  textTransform:"uppercase", color:"var(--dim2)", marginBottom:8}}>
                  Tools
                </div>
                {(p.tools || []).map(t => (
                  <div key={t} style={{
                    fontFamily:"Space Mono,monospace", fontSize:10,
                    color:"var(--accent)", padding:"2px 0"
                  }}>
                    ▸ {t}
                  </div>
                ))}
              </div>

              <button className="file-btn del" onClick={() => disable(p.name)} disabled={loading}>
                Disable
              </button>
            </div>
          ))}
        </div>
      )}

      {/* PENDING PLUGINS */}
      <div className="section-label">Pending Approval</div>
      {data.pending.length === 0 ? (
        <div style={{fontFamily:"Space Mono,monospace", fontSize:11, color:"var(--dim2)", padding:"20px 0"}}>
          No plugins waiting for approval.
        </div>
      ) : (
        <div style={{display:"flex", flexDirection:"column", gap:1, background:"var(--border)"}}>
          {data.pending.map(p => (
            <div key={p.name} style={{
              background:"var(--black)", padding:"24px",
              borderLeft:"2px solid var(--red)"
            }}>
              <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:12}}>
                <div>
                  <div style={{fontFamily:"Space Mono,monospace", fontSize:13, fontWeight:700, marginBottom:4}}>
                    {p.name?.toUpperCase()}
                  </div>
                  <div style={{fontFamily:"Space Mono,monospace", fontSize:9, color:"var(--dim2)", letterSpacing:2}}>
                    v{p.version} — {p.tools?.length || 0} tools
                  </div>
                </div>
                <div className="badge off">PENDING</div>
              </div>

              <div style={{fontFamily:"Space Mono,monospace", fontSize:10, color:"var(--dim2)", marginBottom:14}}>
                {p.description}
              </div>

              <div style={{
                background:"rgba(255,255,255,0.02)", border:"1px solid var(--border)",
                padding:"12px 14px", marginBottom:16,
                fontFamily:"Space Mono,monospace", fontSize:10,
                color:"var(--dim2)", maxHeight:160, overflowY:"auto"
              }}>
                <div style={{color:"var(--dim2)", marginBottom:6, fontSize:9, letterSpacing:2, textTransform:"uppercase"}}>
                  Tools
                </div>
                {(p.tools || []).map(t => (
                  <div key={t.name} style={{padding:"2px 0", color:"var(--white)"}}>
                    ▸ {t.name} — {t.description}
                  </div>
                ))}
                <div style={{marginTop:10, color:"var(--dim2)", fontSize:9, letterSpacing:2, textTransform:"uppercase"}}>
                  Auth
                </div>
                <div style={{color:"var(--white)"}}>
                  {p.auth?.type || "none"}
                  {p.auth?.env_var ? ` (${p.auth.env_var})` : ""}
                </div>
              </div>

              <div style={{display:"flex", gap:8}}>
                <button
                  className="chat-send"
                  style={{padding:"10px 24px", fontSize:10, letterSpacing:2}}
                  onClick={() => approve(p.name)}
                  disabled={loading}
                >
                  Approve
                </button>
                <button
                  className="modal-reject"
                  style={{padding:"10px 24px", fontSize:10, letterSpacing:2, cursor:"pointer"}}
                  onClick={() => reject(p.name)}
                  disabled={loading}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* HOW TO ADD */}
      <div style={{marginTop:40}}>
        <div className="section-label">How to Add a Plugin</div>
        <div style={{
          border:"1px solid var(--border)", padding:"20px 24px",
          fontFamily:"Space Mono,monospace", fontSize:10,
          color:"var(--dim2)", lineHeight:2
        }}>
          <div style={{color:"var(--accent)", marginBottom:8}}>TO INSTALL A NEW PLUGIN:</div>
          <div>1. Describe it above — Hermes designs it automatically</div>
          <div>2. Review the spec and code shown after design</div>
          <div>3. It appears in Pending Approval — import is tested before activating</div>
          <div>4. Click Approve — only activates if import test passes</div>
          <div>5. New tools available in chat with zero code changes</div>
          <div style={{marginTop:12, color:"var(--accent)"}}>SAFETY:</div>
          <div>• Syntax checked before saving to pending</div>
          <div>• Import tested before activating</div>
          <div>• Backup created before disabling</div>
          <div>• Restore via API: POST /api/plugins/name/restore</div>
        </div>
      </div>

    </div>
  )
}
