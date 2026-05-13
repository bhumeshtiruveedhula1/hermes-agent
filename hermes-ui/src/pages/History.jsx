/* hermes-ui/src/pages/History.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

const TOOL_COLORS = {
  gmail_list: "#ff6b6b", gmail_send: "#ff6b6b", gmail_read: "#ff6b6b", gmail_search: "#ff6b6b",
  browser_go: "#4ecdc4", browser_read: "#4ecdc4", browser_click: "#4ecdc4",
  browser_fill: "#4ecdc4", browser_shot: "#4ecdc4", browser_scroll: "#4ecdc4",
  github_repos: "#a78bfa", github_commits: "#a78bfa", github_issues: "#a78bfa",
  github_prs: "#a78bfa", github_search: "#a78bfa", github_create_issue: "#a78bfa",
  fs_list: "#ffd93d", fs_write: "#ffd93d", fs_delete: "#ffd93d", fs_read: "#ffd93d",
  search_web: "#6bcb77", weather_current: "#6bcb77", weather_forecast: "#6bcb77",
  calendar_today: "#ff922b", calendar_create: "#ff922b",
  calendar_list: "#ff922b", calendar_search: "#ff922b",
  telegram_send: "#74c0fc", telegram_read: "#74c0fc",
  // Phase 14
  notion_list: "#f5a623",  notion_read: "#f5a623",
  notion_create: "#f5a623", notion_append: "#f5a623",
  slack_channels: "#e01e5a", slack_send: "#e01e5a", slack_read: "#e01e5a",
  spotify_current: "#1db954", spotify_search: "#1db954", spotify_play: "#1db954",
  spotify_pause: "#1db954", spotify_resume: "#1db954", spotify_next: "#1db954",
  spotify_playlists: "#1db954",
  whatsapp_send: "#25d366", whatsapp_list: "#25d366",
  // Phase 17
  skill_loaded: "#c8ff00",
}

function ToolBadge({ tool }) {
  const color = TOOL_COLORS[tool] || "var(--dim2)"
  return (
    <span style={{
      display:"inline-block", padding:"2px 8px", marginRight:4,
      background:`${color}22`, border:`1px solid ${color}44`,
      color, fontSize:9, fontFamily:"Space Mono,monospace",
      letterSpacing:1, borderRadius:2
    }}>
      {tool.toUpperCase().replace(/_/g," ")}
    </span>
  )
}

export default function History() {
  const [convs, setConvs] = useState([])
  const [search, setSearch] = useState("")
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState("all")

  const load = async () => {
    const res = await axios.get(`http://localhost:8000/api/conversations?search=${search}`)
    setConvs(res.data)
  }

  useEffect(() => { load() }, [search])

  const deleteConv = async (id) => {
    await axios.delete(`http://localhost:8000/api/conversations/${id}`)
    if (selected?.id === id) setSelected(null)
    load()
  }

  const pinConv = async (id, pinned) => {
    await axios.post(`http://localhost:8000/api/conversations/${id}/pin`, { pinned: !pinned })
    load()
  }

  const openConv = async (id) => {
    const res = await axios.get(`http://localhost:8000/api/conversations/${id}`)
    setSelected(res.data)
  }

  // Group by date
  const groupByDate = (list) => {
    const groups = {}
    list.forEach(c => {
      const date = c.updated_at ? c.updated_at.substring(0,10) : "unknown"
      if (!groups[date]) groups[date] = []
      groups[date].push(c)
    })
    return groups
  }

  const filtered = filter === "pinned"
    ? convs.filter(c => c.pinned)
    : filter === "browser"
    ? convs.filter(c => c.tools_used?.some(t => t.startsWith("browser")))
    : filter === "gmail"
    ? convs.filter(c => c.tools_used?.some(t => t.startsWith("gmail")))
    : convs

  const groups = groupByDate(filtered)

  return (
    <div style={{display:"flex", gap:24, height:"600px"}}>

      {/* LEFT — Mission List */}
      <div style={{width:420, display:"flex", flexDirection:"column", flexShrink:0}}>

        {/* Search + Filter */}
        <div style={{marginBottom:16}}>
          <input
            style={{
              width:"100%", background:"transparent",
              border:"1px solid var(--border2)", padding:"10px 16px",
              fontFamily:"Space Mono,monospace", fontSize:11,
              color:"var(--white)", outline:"none",
              boxSizing:"border-box", marginBottom:8
            }}
            placeholder="Search missions by title, tool, or outcome..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <div style={{display:"flex", gap:4}}>
            {["all","pinned","browser","gmail"].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  padding:"4px 12px", background:"transparent",
                  border:`1px solid ${filter===f ? "var(--accent)" : "var(--border)"}`,
                  color: filter===f ? "var(--accent)" : "var(--dim2)",
                  fontFamily:"Space Mono,monospace", fontSize:9,
                  letterSpacing:1, textTransform:"uppercase", cursor:"pointer"
                }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Stats */}
        <div style={{
          display:"grid", gridTemplateColumns:"repeat(3,1fr)",
          gap:1, background:"var(--border)", marginBottom:16
        }}>
          {[
            ["Total", convs.length],
            ["Pinned", convs.filter(c=>c.pinned).length],
            ["Tools Used", [...new Set(convs.flatMap(c=>c.tools_used||[]))].length]
          ].map(([label, val]) => (
            <div key={label} style={{background:"var(--black)", padding:"12px 16px"}}>
              <div style={{fontFamily:"Space Mono,monospace", fontSize:8, letterSpacing:2,
                textTransform:"uppercase", color:"var(--dim2)", marginBottom:4}}>{label}</div>
              <div style={{fontFamily:"Bebas Neue,sans-serif", fontSize:28, color:"var(--accent)"}}>{val}</div>
            </div>
          ))}
        </div>

        {/* Mission Groups */}
        <div style={{flex:1, overflowY:"auto", scrollbarWidth:"thin", scrollbarColor:"var(--border) transparent"}}>
          {Object.entries(groups).sort(([a],[b]) => b.localeCompare(a)).map(([date, items]) => (
            <div key={date}>
              <div style={{
                padding:"6px 0", fontFamily:"Space Mono,monospace",
                fontSize:9, letterSpacing:2, color:"var(--dim)",
                textTransform:"uppercase", borderBottom:"1px solid var(--border)",
                marginBottom:4
              }}>
                {date === new Date().toISOString().substring(0,10) ? "Today" :
                 date === new Date(Date.now()-86400000).toISOString().substring(0,10) ? "Yesterday" : date}
              </div>
              {items.map(c => (
                <div
                  key={c.id}
                  onClick={() => openConv(c.id)}
                  style={{
                    padding:"12px 14px", cursor:"pointer",
                    background: selected?.id===c.id ? "rgba(200,255,0,0.06)" : "transparent",
                    borderLeft: selected?.id===c.id ? "2px solid var(--accent)" : "2px solid transparent",
                    borderBottom:"1px solid var(--border)",
                    transition:"background .15s", marginBottom:1
                  }}
                >
                  <div style={{display:"flex", justifyContent:"space-between", marginBottom:6}}>
                    <div style={{
                      fontFamily:"Space Mono,monospace", fontSize:11,
                      color: selected?.id===c.id ? "var(--accent)" : "var(--white)",
                      flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"
                    }}>
                      {c.pinned ? "📌 " : ""}{c.title || "New Mission"}
                    </div>
                    <div style={{display:"flex", gap:6, flexShrink:0, marginLeft:8}}>
                      <button onClick={e=>{e.stopPropagation();pinConv(c.id,c.pinned)}}
                        style={{background:"none",border:"none",cursor:"pointer",color:"var(--dim)",fontSize:12}}>
                        {c.pinned ? "★" : "☆"}
                      </button>
                      <button onClick={e=>{e.stopPropagation();deleteConv(c.id)}}
                        style={{background:"none",border:"none",cursor:"pointer",color:"var(--dim)",fontSize:14}}>
                        ×
                      </button>
                    </div>
                  </div>
                  {c.tools_used?.length > 0 && (
                    <div style={{display:"flex", flexWrap:"wrap", gap:2, marginBottom:4}}>
                      {c.tools_used.slice(0,4).map(t => <ToolBadge key={t} tool={t} />)}
                    </div>
                  )}
                  <div style={{
                    fontFamily:"Space Mono,monospace", fontSize:9, color:"var(--dim2)",
                    overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap"
                  }}>
                    {c.summary || `${c.message_count||0} messages`}
                  </div>
                </div>
              ))}
            </div>
          ))}
          {filtered.length === 0 && (
            <div style={{padding:"20px 0", fontFamily:"Space Mono,monospace", fontSize:11, color:"var(--dim2)"}}>
              No missions found.
            </div>
          )}
        </div>
      </div>

      {/* RIGHT — Mission Detail */}
      <div style={{flex:1, border:"1px solid var(--border)", display:"flex", flexDirection:"column"}}>
        {selected ? (
          <>
            <div style={{
              padding:"16px 20px", borderBottom:"1px solid var(--border)",
              background:"var(--black2)"
            }}>
              <div style={{fontFamily:"Space Mono,monospace", fontSize:13, fontWeight:700, marginBottom:6}}>
                {selected.pinned ? "📌 " : ""}{selected.title}
              </div>
              <div style={{display:"flex", flexWrap:"wrap", gap:4, marginBottom:6}}>
                {selected.tools_used?.map(t => <ToolBadge key={t} tool={t} />)}
              </div>
              <div style={{fontFamily:"Space Mono,monospace", fontSize:9, color:"var(--dim2)"}}>
                {selected.created_at?.substring(0,19).replace("T"," ")} UTC
                · {selected.messages?.length || 0} messages
              </div>
            </div>
            <div style={{flex:1, overflowY:"auto", padding:"0",
              scrollbarWidth:"thin", scrollbarColor:"var(--border) transparent"}}>
              {selected.messages?.map((m, i) => (
                <div key={i} style={{
                  padding:"14px 20px",
                  borderBottom:"1px solid var(--border)",
                  background: m.role === "hermes" ? "rgba(200,255,0,0.02)" : "transparent"
                }}>
                  <div style={{
                    fontFamily:"Space Mono,monospace", fontSize:9,
                    letterSpacing:2, textTransform:"uppercase",
                    color: m.role === "hermes" ? "var(--accent)" : "var(--dim2)",
                    marginBottom:6
                  }}>
                    {m.role === "hermes" ? "Hermes" : "You"}
                    <span style={{color:"var(--dim)", marginLeft:8}}>
                      {m.ts?.substring(11,19)}
                    </span>
                  </div>
                  <div style={{fontSize:13, lineHeight:1.75}}>{m.text}</div>
                  {m.tools?.length > 0 && (
                    <div style={{marginTop:8, display:"flex", flexWrap:"wrap", gap:4}}>
                      {m.tools.map(t => <ToolBadge key={t} tool={t} />)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        ) : (
          <div style={{
            flex:1, display:"flex", alignItems:"center", justifyContent:"center",
            fontFamily:"Space Mono,monospace", fontSize:11, color:"var(--dim2)"
          }}>
            Select a mission to view details
          </div>
        )}
      </div>
    </div>
  )
}