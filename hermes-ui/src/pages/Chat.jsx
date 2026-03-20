/* hermes-ui/src/pages/Chat.jsx */
import { useState, useRef, useEffect } from "react"
import axios from "axios"

export default function Chat() {
  const [messages, setMessages] = useState([
    { role: "hermes", text: "System online. I can list files, read files, write files, search the web, and run background agents. What do you need?" }
  ])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const send = async () => {
    const val = input.trim()
    if (!val || loading) return
    setInput("")
    setMessages(prev => [...prev, { role: "you", text: val }])
    setLoading(true)
    try {
      const res = await axios.post("http://localhost:8000/api/chat", { message: val })
      const { plan, result } = res.data
      setMessages(prev => [...prev, { role: "hermes", text: result, plan }])
    } catch {
      setMessages(prev => [...prev, { role: "hermes", text: "[ERROR] Could not reach Hermes backend." }])
    }
    setLoading(false)
  }

  return (
    <div className="chat-wrap">
      <div className="chat-msgs">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            <div className="chat-who">{m.role === "you" ? "You" : "Hermes"}</div>
            <div className="chat-text">{m.text}</div>
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
            <div className="chat-text" style={{color:"var(--dim2)"}}>Thinking...</div>
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
          placeholder="list files in /documents"
          disabled={loading}
        />
        <button className="chat-send" onClick={send} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  )
}
