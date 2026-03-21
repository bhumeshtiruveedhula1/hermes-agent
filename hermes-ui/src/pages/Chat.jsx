/* hermes-ui/src/pages/Chat.jsx */
import { useState, useRef, useEffect } from "react"
import axios from "axios"

const TOOL_COLORS = {
  gmail_list: "#ff6b6b", gmail_send: "#ff6b6b", gmail_read: "#ff6b6b",
  browser_go: "#4ecdc4", browser_read: "#4ecdc4",
  github_repos: "#a78bfa", github_commits: "#a78bfa",
  fs_list: "#ffd93d", fs_write: "#ffd93d", fs_delete: "#ffd93d",
  search_web: "#6bcb77", weather_current: "#6bcb77",
  calendar_today: "#ff922b", calendar_create: "#ff922b",
  telegram_send: "#74c0fc",
}

const TOOL_SHORT = {
  gmail_list: "GMAIL", gmail_send: "GMAIL", gmail_read: "GMAIL",
  browser_go: "BROWSER", browser_read: "BROWSER",
  github_repos: "GITHUB", github_commits: "GITHUB", github_issues: "GITHUB",
  fs_list: "FILES", fs_write: "FILES", fs_delete: "FILES",
  search_web: "SEARCH", weather_current: "WEATHER", weather_forecast: "WEATHER",
  calendar_today: "CALENDAR", calendar_create: "CALENDAR",
  telegram_send: "TELEGRAM",
}

function ToolBadge({ tool }) {
  const color = TOOL_COLORS[tool] || "var(--dim2)"
  const label = TOOL_SHORT[tool] || tool.toUpperCase().replace("_", " ")
  return (
    <span style={{
      display:"inline-block", padding:"1px 6px", marginRight:4,
      background: `${color}22`, border: `1px solid ${color}44`,
      color, fontSize:8, fontFamily:"Space Mono,monospace",
      letterSpacing:1, borderRadius:2
    }}>
      {label}
    </span>
  )
}

export default function Chat() {
  const [convList, setConvList] = useState([])
  const [activeConv, setActiveConv] = useState(null)
  const [messages, setMessages] = useState([
    { role: "hermes", text: "System online. I can list files, read files, write files, search the web, and run background agents. What do you need?" }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState("")
  const bottomRef = useRef(null)

  useEffect(() => { loadConvList() }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const loadConvList = async () => {
    const res = await axios.get(`http://localhost:8000/api/conversations?search=${search}`)
    setConvList(res.data)
  }

  const newConversation = async () => {
    const res = await axios.post("http://localhost:8000/api/conversations")
    setActiveConv(res.data)
    setMessages([{ role: "hermes", text: "New mission started. What do you need?" }])
    loadConvList()
  }

  const openConversation = async (convId) => {
    const res = await axios.get(`http://localhost:8000/api/conversations/${convId}`)
    const conv = res.data
    setActiveConv(conv)
    if (conv.messages && conv.messages.length > 0) {
      setMessages(conv.messages.map(m => ({
        role: m.role, text: m.text, tools: m.tools || []
      })))
    } else {
      setMessages([{ role: "hermes", text: "Mission resumed. What do you need?" }])
    }
  }

  const deleteConv = async (e, convId) => {
    e.stopPropagation()
    await axios.delete(`http://localhost:8000/api/conversations/${convId}`)
    if (activeConv?.id === convId) {
      setActiveConv(null)
      setMessages([{ role: "hermes", text: "System online. What do you need?" }])
    }
    loadConvList()
  }

  const pinConv = async (e, convId, pinned) => {
    e.stopPropagation()
    await axios.post(`http://localhost:8000/api/conversations/${convId}/pin`, { pinned: !pinned })
    loadConvList()
  }

  const send = async () => {
    const val = input.trim()
    if (!val || loading) return
    setInput("")

    let conv = activeConv
    if (!conv) {
      const res = await axios.post("http://localhost:8000/api/conversations")
      conv = res.data
      setActiveConv(conv)
    }

    setMessages(prev => [...prev, { role: "you", text: val }])
    setLoading(true)

    try {
      const res = await axios.post("http://localhost:8000/api/chat/mission", {
        conv_id: conv.id,
        message: val
      })
      const { plan, result, tools_used, corrections } = res.data

      if (corrections && corrections.length > 0) {
        setMessages(prev => [...prev, {
          role: "system",
          text: `✏️ Autocorrected: ${corrections.join(", ")}`
        }])
      }

      setMessages(prev => [...prev, {
        role: "hermes", text: result,
        plan, tools: tools_used || []
      }])
      loadConvList()
    } catch {
      setMessages(prev => [...prev, {
        role: "hermes", text: "[ERROR] Could not reach Hermes backend."
      }])
    }
    setLoading(false)
  }

  const pinnedConvs = convList.filter(c => c.pinned)
  const unpinnedConvs = convList.filter(c => !c.pinned)

  return (
    <div style={{display:"flex", gap:0, height:"600px", border:"1px solid var(--border)"}}>

      {/* SIDEBAR */}
      <div style={{
        width:260, borderRight:"1px solid var(--border)",
        display:"flex", flexDirection:"column",
        background:"var(--black2)"
      }}>
        <button
          onClick={newConversation}
          style={{
            margin:12, padding:"10px 16px",
            background:"var(--accent)", color:"var(--black)",
            border:"none", cursor:"pointer",
            fontFamily:"Space Mono,monospace", fontSize:10,
            fontWeight:700, letterSpacing:2, textTransform:"uppercase"
          }}
        >
          + New Mission
        </button>

        <div style={{padding:"0 12px 8px"}}>
          <input
            style={{
              width:"100%", background:"transparent",
              border:"1px solid var(--border)", padding:"8px 12px",
              fontFamily:"Space Mono,monospace", fontSize:10,
              color:"var(--white)", outline:"none", boxSizing:"border-box"
            }}
            placeholder="Search missions..."
            value={search}
            onChange={e => { setSearch(e.target.value); loadConvList() }}
          />
        </div>

        <div style={{flex:1, overflowY:"auto", scrollbarWidth:"thin", scrollbarColor:"var(--border) transparent"}}>
          {pinnedConvs.length > 0 && (
            <>
              <div style={{padding:"6px 14px", fontFamily:"Space Mono,monospace",
                fontSize:8, letterSpacing:2, color:"var(--dim)", textTransform:"uppercase"}}>
                Pinned
              </div>
              {pinnedConvs.map(c => (
                <ConvItem key={c.id} conv={c} active={activeConv?.id === c.id}
                  onOpen={openConversation} onDelete={deleteConv} onPin={pinConv} />
              ))}
            </>
          )}

          {unpinnedConvs.length > 0 && (
            <>
              <div style={{padding:"6px 14px", fontFamily:"Space Mono,monospace",
                fontSize:8, letterSpacing:2, color:"var(--dim)", textTransform:"uppercase", marginTop:4}}>
                Recent
              </div>
              {unpinnedConvs.map(c => (
                <ConvItem key={c.id} conv={c} active={activeConv?.id === c.id}
                  onOpen={openConversation} onDelete={deleteConv} onPin={pinConv} />
              ))}
            </>
          )}

          {convList.length === 0 && (
            <div style={{padding:"20px 14px", fontFamily:"Space Mono,monospace",
              fontSize:10, color:"var(--dim)"}}>
              No missions yet.
            </div>
          )}
        </div>
      </div>

      {/* CHAT WINDOW */}
      <div style={{flex:1, display:"flex", flexDirection:"column"}}>

        {activeConv && (
          <div style={{padding:"10px 18px", borderBottom:"1px solid var(--border)",
            display:"flex", alignItems:"center", gap:12}}>
            <div style={{fontFamily:"Space Mono,monospace", fontSize:11,
              color:"var(--white)", flex:1}}>
              {activeConv.title || "New Mission"}
            </div>
            <div style={{display:"flex", flexWrap:"wrap", gap:4}}>
              {(activeConv.tools_used || []).map(t => <ToolBadge key={t} tool={t} />)}
            </div>
          </div>
        )}

        <div style={{flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
          scrollbarWidth:"thin", scrollbarColor:"var(--border) transparent"}}>
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role === "you" ? "you" : m.role === "system" ? "system" : "hermes"}`}>
              <div className="chat-who">
                {m.role === "you" ? "You" : m.role === "system" ? "System" : "Hermes"}
              </div>
              <div className="chat-text">
                {m.text && m.text.startsWith("[SCREENSHOT_B64]")
                  ? <img
                      src={`data:image/png;base64,${m.text.replace("[SCREENSHOT_B64]","")}`}
                      style={{maxWidth:"100%", border:"1px solid var(--border)", marginTop:8}}
                      alt="Browser screenshot"
                    />
                  : m.text
                }
              </div>
              {m.tools && m.tools.length > 0 && (
                <div style={{marginTop:8, display:"flex", flexWrap:"wrap", gap:4}}>
                  {m.tools.map(t => <ToolBadge key={t} tool={t} />)}
                </div>
              )}
              {m.plan && m.plan.steps?.length > 0 && (
                <div className="chat-plan">
                  {m.plan.steps.map((s, j) => (
                    <div key={j}>▸ [{s.tool || "reason"}] {s.description}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="chat-msg hermes">
              <div className="chat-who">Hermes</div>
              <div className="chat-text" style={{color:"var(--dim2)"}}>
                <span style={{animation:"pulse 1s infinite"}}>Processing mission...</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="chat-footer">
          <input
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder={activeConv ? "Continue mission..." : "Start a new mission..."}
            disabled={loading}
          />
          <button className="chat-send" onClick={send} disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  )
}

function ConvItem({ conv, active, onOpen, onDelete, onPin }) {
  const date = conv.updated_at
    ? new Date(conv.updated_at).toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"})
    : ""

  return (
    <div
      onClick={() => onOpen(conv.id)}
      style={{
        padding:"10px 14px", cursor:"pointer",
        background: active ? "rgba(200,255,0,0.06)" : "transparent",
        borderLeft: active ? "2px solid var(--accent)" : "2px solid transparent",
        borderBottom:"1px solid var(--border)",
        transition:"background .15s"
      }}
    >
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:4}}>
        <div style={{
          fontFamily:"Space Mono,monospace", fontSize:10,
          color: active ? "var(--accent)" : "var(--white)",
          flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", paddingRight:8
        }}>
          {conv.pinned ? "📌 " : ""}{conv.title || "New Mission"}
        </div>
        <div style={{fontFamily:"Space Mono,monospace", fontSize:8,
          color:"var(--dim)", flexShrink:0}}>{date}</div>
      </div>

      {conv.tools_used?.length > 0 && (
        <div style={{display:"flex", flexWrap:"wrap", gap:2, marginBottom:4}}>
          {conv.tools_used.slice(0,3).map(t => <ToolBadge key={t} tool={t} />)}
          {conv.tools_used.length > 3 && (
            <span style={{fontSize:8, color:"var(--dim)", fontFamily:"Space Mono,monospace"}}>
              +{conv.tools_used.length - 3}
            </span>
          )}
        </div>
      )}

      <div style={{display:"flex", justifyContent:"space-between", alignItems:"center"}}>
        <div style={{fontFamily:"Space Mono,monospace", fontSize:9, color:"var(--dim2)",
          overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap", flex:1}}>
          {conv.summary || `${conv.message_count || 0} messages`}
        </div>
        <div style={{display:"flex", gap:4, flexShrink:0, marginLeft:8}}>
          <button onClick={e => onPin(e, conv.id, conv.pinned)}
            style={{background:"none", border:"none", cursor:"pointer",
              color:"var(--dim)", fontSize:10, padding:"0 2px"}}
            title={conv.pinned ? "Unpin" : "Pin"}>
            {conv.pinned ? "★" : "☆"}
          </button>
          <button onClick={e => onDelete(e, conv.id)}
            style={{background:"none", border:"none", cursor:"pointer",
              color:"var(--dim)", fontSize:10, padding:"0 2px"}}
            title="Delete">
            ×
          </button>
        </div>
      </div>
    </div>
  )
}
