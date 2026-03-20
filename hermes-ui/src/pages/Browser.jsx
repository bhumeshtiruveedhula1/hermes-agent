/* hermes-ui/src/pages/Browser.jsx */
import { useState } from "react"
import axios from "axios"

export default function Browser() {
  const [screenshot, setScreenshot] = useState(null)
  const [url, setUrl] = useState("")
  const [loading, setLoading] = useState(false)
  const [pageText, setPageText] = useState("")
  const [showText, setShowText] = useState(false)

  const takeScreenshot = async () => {
    setLoading(true)
    try {
      const res = await axios.post("http://localhost:8000/api/browser/screenshot")
      if (res.data.screenshot) {
        setScreenshot(res.data.screenshot)
      }
    } catch {
      alert("Browser not active — navigate somewhere first")
    }
    setLoading(false)
  }

  const navigate = async () => {
    if (!url.trim()) return
    setLoading(true)
    try {
      await axios.post("http://localhost:8000/api/browser/navigate", { url })
      setTimeout(takeScreenshot, 1500)
    } catch {
      setLoading(false)
    }
  }

  const readPage = async () => {
    setLoading(true)
    try {
      const res = await axios.post("http://localhost:8000/api/browser/read")
      setPageText(res.data.text || "")
      setShowText(true)
    } catch {}
    setLoading(false)
  }

  const closeBrowser = async () => {
    await axios.post("http://localhost:8000/api/browser/close")
    setScreenshot(null)
    setPageText("")
  }

  return (
    <div>
      <div className="section-label">Browser Control</div>

      {/* URL BAR */}
      <div style={{display:"flex", gap:0, marginBottom:16}}>
        <input
          className="chat-input"
          style={{flex:1, border:"1px solid var(--border2)", borderRight:"none", padding:"12px 18px"}}
          placeholder="https://google.com"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === "Enter" && navigate()}
        />
        <button className="chat-send" onClick={navigate} disabled={loading}>
          {loading ? "..." : "Go"}
        </button>
      </div>

      {/* CONTROLS */}
      <div style={{display:"flex", gap:8, marginBottom:24}}>
        <button className="file-btn" onClick={takeScreenshot} disabled={loading}>
          Screenshot
        </button>
        <button className="file-btn" onClick={readPage} disabled={loading}>
          Read Page
        </button>
        <button className="file-btn del" onClick={closeBrowser}>
          Close Browser
        </button>
      </div>

      {/* SCREENSHOT VIEWER */}
      {screenshot ? (
        <div style={{border:"1px solid var(--border)", marginBottom:24}}>
          <div className="file-path">
            <span className="file-path-accent">LIVE VIEW</span>
            <span style={{marginLeft:"auto", fontSize:10, color:"var(--dim)"}}>
              Click Screenshot to refresh
            </span>
          </div>
          <img
            src={`data:image/png;base64,${screenshot}`}
            style={{width:"100%", display:"block"}}
            alt="Browser view"
          />
        </div>
      ) : (
        <div style={{
          border:"1px solid var(--border)", padding:"60px 24px",
          textAlign:"center", fontFamily:"Space Mono,monospace",
          fontSize:11, color:"var(--dim)", marginBottom:24
        }}>
          No screenshot yet — navigate somewhere and click Screenshot
        </div>
      )}

      {/* PAGE TEXT */}
      {showText && pageText && (
        <div>
          <div className="section-label">Page Content</div>
          <div style={{
            border:"1px solid var(--border)", padding:"16px 20px",
            fontFamily:"Space Mono,monospace", fontSize:10,
            color:"var(--dim2)", lineHeight:1.9, maxHeight:300,
            overflowY:"auto", background:"rgba(255,255,255,0.02)"
          }}>
            {pageText}
          </div>
        </div>
      )}
    </div>
  )
}