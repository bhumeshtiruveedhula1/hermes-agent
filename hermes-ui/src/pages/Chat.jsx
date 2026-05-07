/* hermes-ui/src/pages/Chat.jsx */
import { useState, useRef, useEffect } from "react"
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
}

const TOOL_SHORT = {
  gmail_list: "GMAIL", gmail_send: "GMAIL", gmail_read: "GMAIL", gmail_search: "GMAIL",
  browser_go: "BROWSER", browser_read: "BROWSER", browser_click: "BROWSER",
  browser_fill: "BROWSER", browser_shot: "BROWSER", browser_scroll: "BROWSER",
  github_repos: "GITHUB", github_commits: "GITHUB", github_issues: "GITHUB",
  github_prs: "GITHUB", github_search: "GITHUB", github_create_issue: "GITHUB",
  fs_list: "FILES", fs_write: "FILES", fs_delete: "FILES", fs_read: "FILES",
  search_web: "SEARCH", weather_current: "WEATHER", weather_forecast: "WEATHER",
  calendar_today: "CALENDAR", calendar_create: "CALENDAR",
  calendar_list: "CALENDAR", calendar_search: "CALENDAR",
  telegram_send: "TELEGRAM", telegram_read: "TELEGRAM",
  // Phase 14
  notion_list: "NOTION",  notion_read: "NOTION",
  notion_create: "NOTION", notion_append: "NOTION",
  slack_channels: "SLACK", slack_send: "SLACK", slack_read: "SLACK",
  spotify_current: "SPOTIFY", spotify_search: "SPOTIFY", spotify_play: "SPOTIFY",
  spotify_pause: "SPOTIFY", spotify_resume: "SPOTIFY", spotify_next: "SPOTIFY",
  spotify_playlists: "SPOTIFY",
  whatsapp_send: "WHATSAPP", whatsapp_list: "WHATSAPP",
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
  // Phase 10 Task 4 — screenshot panel
  const [liveScreenshot, setLiveScreenshot] = useState(null)
  const [showPanel, setShowPanel] = useState(false)
  // Phase 12 — Voice I/O
  const [isListening, setIsListening]     = useState(false)   // mic active
  const [voiceOn, setVoiceOn]             = useState(false)   // TTS enabled
  const [speakingIdx, setSpeakingIdx]     = useState(null)    // which msg is "speaking"

  useEffect(() => { loadConvList() }, [])

  // Phase 12: fetch voice status on mount
  useEffect(() => {
    axios.get("http://localhost:8000/api/voice/status")
      .then(r => setVoiceOn(r.data.voice_enabled))
      .catch(() => {})
  }, [])

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

      // Phase 10 Task 4: extract screenshot from result if present
      let cleanResult = result
      if (result && result.includes("[SCREENSHOT_B64]")) {
        const b64 = result.replace("[SCREENSHOT_B64]", "").trim()
        setLiveScreenshot(b64)
        setShowPanel(true)
        cleanResult = "[Screenshot captured — see Browser View panel →]"
      }

      setMessages(prev => [...prev, {
        role: "hermes", text: cleanResult,
        plan, tools: tools_used || [],
        speaking: voiceOn   // Phase 12: flag for speaking indicator
      }])
      // Phase 12: show SPEAKING... for 3s if voice enabled
      if (voiceOn) {
        const idx = Date.now()
        setSpeakingIdx(idx)
        setTimeout(() => setSpeakingIdx(null), 3000)
      }
      loadConvList()
    } catch {
      setMessages(prev => [...prev, {
        role: "hermes", text: "[ERROR] Could not reach Hermes backend."
      }])
    }
    setLoading(false)
  }

  // Phase 12 Task 3 — Voice output toggle
  const toggleVoice = async () => {
    const next = !voiceOn
    try {
      await axios.post("http://localhost:8000/api/voice/toggle", { enabled: next })
      setVoiceOn(next)
    } catch { /* backend unreachable — toggle locally anyway */ setVoiceOn(next) }
  }

  // Phase 12 Task 2 — Microphone / Web Speech API
  // Auto-sends after recognition so user doesn't need to manually press Send.
  // Uses a direct call to the send logic rather than setInput to avoid stale closure.
  const startListening = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) {
      alert("Voice input requires Chrome or Edge.")
      return
    }
    const recognition = new SR()
    recognition.lang            = "en-US"
    recognition.interimResults  = false
    recognition.maxAlternatives = 1
    setIsListening(true)
    recognition.start()
    recognition.onresult = async (e) => {
      const transcript = e.results[0][0].transcript
      setInput(transcript)        // show in input box
      setIsListening(false)
      // Auto-send: build the send payload directly instead of relying on state
      if (!transcript.trim()) return
      let conv = activeConv
      if (!conv) {
        const res = await axios.post("http://localhost:8000/api/conversations")
        conv = res.data
        setActiveConv(conv)
      }
      setMessages(prev => [...prev, { role: "you", text: transcript }])
      setLoading(true)
      setInput("")  // clear input now
      try {
        const res = await axios.post("http://localhost:8000/api/chat/mission", {
          conv_id: conv.id,
          message: transcript
        })
        const { plan, result, tools_used, corrections } = res.data
        if (corrections?.length > 0) {
          setMessages(prev => [...prev, { role: "system", text: `✏️ Autocorrected: ${corrections.join(", ")}` }])
        }
        let cleanResult = result
        if (result?.includes("[SCREENSHOT_B64]")) {
          setLiveScreenshot(result.replace("[SCREENSHOT_B64]", "").trim())
          setShowPanel(true)
          cleanResult = "[Screenshot captured — see Browser View panel →]"
        }
        setMessages(prev => [...prev, {
          role: "hermes", text: cleanResult, plan, tools: tools_used || [], speaking: voiceOn
        }])
        if (voiceOn) { const idx = Date.now(); setSpeakingIdx(idx); setTimeout(() => setSpeakingIdx(null), 3000) }
        loadConvList()
      } catch {
        setMessages(prev => [...prev, { role: "hermes", text: "[ERROR] Could not reach Hermes backend." }])
      }
      setLoading(false)
    }
    recognition.onerror = () => setIsListening(false)
    recognition.onend   = () => setIsListening(false)
  }

  const pinnedConvs = convList.filter(c => c.pinned)
  const unpinnedConvs = convList.filter(c => !c.pinned)

  return (
    <>
    {/* Phase 12: inject keyframes for waveform + mic pulse */}
    <style>{`
      @keyframes wave {
        from { transform: scaleY(0.4); }
        to   { transform: scaleY(1.0); }
      }
      @keyframes micPulse {
        0%,100% { box-shadow: 0 0 0 0 rgba(255,85,85,0.4); }
        50%      { box-shadow: 0 0 0 8px rgba(255,85,85,0); }
      }
    `}</style>
    <div style={{display:"flex", gap:0, height:"600px", border:"1px solid var(--border)", position:"relative"}}>

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
            {/* Phase 12 Task 3 — Voice output toggle */}
            <button
              id="voice-toggle-btn"
              onClick={toggleVoice}
              title={voiceOn ? "Voice ON — click to mute" : "Voice OFF — click to enable"}
              style={{
                background:"none", border:"none", cursor:"pointer",
                fontSize:18, lineHeight:1, padding:"2px 6px",
                color: voiceOn ? "var(--accent)" : "var(--dim)",
                filter: voiceOn ? "drop-shadow(0 0 6px var(--accent))" : "none",
                transition:"all .2s"
              }}
            >{voiceOn ? "🔊" : "🔇"}</button>
          </div>
        )}

        <div style={{flex:1, overflowY:"auto", display:"flex", flexDirection:"column",
          scrollbarWidth:"thin", scrollbarColor:"var(--border) transparent"}}>
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role === "you" ? "you" : m.role === "system" ? "system" : "hermes"}`}>
              <div className="chat-who" style={{display:"flex", alignItems:"center", gap:8}}>
                {m.role === "you" ? "You" : m.role === "system" ? "System" : "Hermes"}
                {/* Phase 12 Task 4 — SPEAKING indicator on latest hermes message */}
                {m.role === "hermes" && m.speaking && speakingIdx && i === messages.length - 1 && (
                  <span style={{
                    fontFamily:"Space Mono,monospace", fontSize:7,
                    letterSpacing:2, color:"var(--accent)",
                    animation:"pulse 1.2s ease-in-out infinite"
                  }}>SPEAKING</span>
                )}
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
          {/* Phase 12 Task 4 — Waveform / LISTENING indicator */}
          {isListening && (
            <div style={{
              position:"absolute", bottom:56, left:280, right:0,
              display:"flex", alignItems:"center", justifyContent:"center",
              gap:10, padding:"10px 0",
              background:"linear-gradient(0deg,rgba(5,5,5,0.95),transparent)",
              pointerEvents:"none",
            }}>
              <div style={{display:"flex", alignItems:"flex-end", gap:3, height:24}}>
                {[0,1,2,3,4].map(i => (
                  <div key={i} style={{
                    width:3, background:"var(--accent)",
                    borderRadius:2,
                    animation:`wave 0.8s ease-in-out ${i*0.1}s infinite alternate`,
                    height: [14,22,18,24,16][i],
                  }} />
                ))}
              </div>
              <span style={{
                fontFamily:"Space Mono,monospace", fontSize:9,
                letterSpacing:3, color:"var(--accent)", textTransform:"uppercase"
              }}>Listening...</span>
            </div>
          )}
          <input
            className="chat-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && send()}
            placeholder={isListening ? "Listening..." : activeConv ? "Continue mission..." : "Start a new mission..."}
            disabled={loading}
          />
          {/* Phase 12 Task 2 — Microphone button: flat, sharp, matches Hermes theme */}
          <button
            id="mic-btn"
            onClick={startListening}
            disabled={loading || isListening}
            title={isListening ? "Listening..." : "Voice input"}
            style={{
              padding: "0 16px",
              background: isListening ? "rgba(255,85,85,0.12)" : "transparent",
              border: "none",
              borderRight: "1px solid var(--border2)",
              color: isListening ? "#ff5555" : "var(--dim)",
              cursor: loading || isListening ? "not-allowed" : "pointer",
              fontFamily: "Space Mono, monospace",
              fontSize: 9,
              letterSpacing: 1,
              textTransform: "uppercase",
              whiteSpace: "nowrap",
              flexShrink: 0,
              animation: isListening ? "micPulse 1s ease-in-out infinite" : "none",
              transition: "all .2s",
              display: "flex", alignItems: "center", gap: 6,
            }}
          >
            <span style={{fontSize:13}}>🎤</span>
            {isListening ? "MIC" : ""}
          </button>
          <button className="chat-send" onClick={send} disabled={loading}>
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>

      {/* Phase 10 Task 4 — Collapsible Browser View Panel */}
      {showPanel && (
        <div style={{
          width:320, borderLeft:"1px solid var(--border)",
          display:"flex", flexDirection:"column",
          background:"var(--black2)", flexShrink:0
        }}>
          <div style={{
            padding:"10px 14px", borderBottom:"1px solid var(--border)",
            display:"flex", alignItems:"center", justifyContent:"space-between"
          }}>
            <span style={{
              fontFamily:"Space Mono,monospace", fontSize:8,
              letterSpacing:2, color:"var(--accent)", textTransform:"uppercase"
            }}>Browser View</span>
            <button
              onClick={() => setShowPanel(false)}
              style={{
                background:"none", border:"none", cursor:"pointer",
                color:"var(--dim)", fontSize:14, lineHeight:1
              }}
              title="Close panel"
            >×</button>
          </div>
          <div style={{flex:1, overflowY:"auto", padding:8}}>
            {liveScreenshot
              ? <img
                  src={`data:image/png;base64,${liveScreenshot}`}
                  style={{width:"100%", border:"1px solid var(--border)"}}
                  alt="Browser screenshot"
                />
              : <div style={{
                  fontFamily:"Space Mono,monospace", fontSize:9,
                  color:"var(--dim)", padding:"20px 8px", textAlign:"center"
                }}>No screenshot yet</div>
            }
          </div>
        </div>
      )}

      {/* Panel open toggle when closed */}
      {!showPanel && liveScreenshot && (
        <button
          onClick={() => setShowPanel(true)}
          title="Show Browser View"
          style={{
            position:"absolute", right:0, top:"50%", transform:"translateY(-50%)",
            background:"var(--black2)", border:"1px solid var(--border)",
            borderRight:"none", color:"var(--accent)", cursor:"pointer",
            fontFamily:"Space Mono,monospace", fontSize:8, letterSpacing:1,
            padding:"12px 6px", writingMode:"vertical-rl", textTransform:"uppercase"
          }}
        >
          Browser View
        </button>
      )}
    </div>
    </>
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
