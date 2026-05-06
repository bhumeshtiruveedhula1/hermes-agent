/* hermes-ui/src/pages/Login.jsx — Phase 11: Auth Gate */
import { useState } from "react"
import axios from "axios"

export default function Login({ onLogin }) {
  const [name, setName]         = useState("")
  const [password, setPassword] = useState("")
  const [error, setError]       = useState("")
  const [loading, setLoading]   = useState(false)

  const submit = async (e) => {
    e?.preventDefault()
    if (!name.trim() || !password.trim()) {
      setError("Enter username and password")
      return
    }
    setLoading(true)
    setError("")
    try {
      const res = await axios.post("http://localhost:8000/api/auth/login", {
        name: name.trim(),
        password: password.trim()
      })
      if (res.data.ok) {
        const user = res.data.user
        localStorage.setItem("hermes_user", JSON.stringify(user))
        onLogin(user)
      } else {
        setError(res.data.error || "Login failed")
      }
    } catch {
      setError("Cannot reach Hermes backend — is it running?")
    }
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#050505",
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center",
      position: "relative", overflow: "hidden",
      fontFamily: "Space Mono, monospace",
    }}>

      {/* Scanline */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0,
        backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.18) 2px, rgba(0,0,0,0.18) 4px)",
        pointerEvents: "none",
      }} />

      {/* Grid bg */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, opacity: 0.04,
        backgroundImage: "linear-gradient(var(--accent,#c8ff00) 1px, transparent 1px), linear-gradient(90deg, var(--accent,#c8ff00) 1px, transparent 1px)",
        backgroundSize: "40px 40px",
        pointerEvents: "none",
      }} />

      <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 400, padding: "0 24px" }}>

        {/* Logo */}
        <div style={{
          textAlign: "center", marginBottom: 8,
          fontFamily: "Bebas Neue, Impact, sans-serif",
          fontSize: 72, letterSpacing: 8,
          color: "#ffffff", lineHeight: 1,
          textShadow: "0 0 40px rgba(200,255,0,0.3)",
        }}>
          HERMES<span style={{ color: "#c8ff00" }}>.</span>
        </div>

        <div style={{
          textAlign: "center", marginBottom: 48,
          fontSize: 9, letterSpacing: 4, color: "#444",
          textTransform: "uppercase",
        }}>
          Autonomous Agent Platform
        </div>

        {/* Form */}
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <input
            id="login-username"
            type="text"
            placeholder="USERNAME"
            autoComplete="username"
            value={name}
            onChange={e => setName(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid #222",
              color: "#fff",
              padding: "14px 18px",
              fontFamily: "Space Mono, monospace",
              fontSize: 11, letterSpacing: 2,
              outline: "none",
              transition: "border-color .2s",
            }}
            onFocus={e => e.target.style.borderColor = "#c8ff00"}
            onBlur={e => e.target.style.borderColor = "#222"}
          />

          <input
            id="login-password"
            type="password"
            placeholder="PASSWORD"
            autoComplete="current-password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid #222",
              color: "#fff",
              padding: "14px 18px",
              fontFamily: "Space Mono, monospace",
              fontSize: 11, letterSpacing: 2,
              outline: "none",
              transition: "border-color .2s",
            }}
            onFocus={e => e.target.style.borderColor = "#c8ff00"}
            onBlur={e => e.target.style.borderColor = "#222"}
          />

          {/* Error */}
          {error && (
            <div style={{
              background: "rgba(255,50,50,0.08)",
              border: "1px solid rgba(255,50,50,0.3)",
              color: "#ff5555", padding: "10px 14px",
              fontSize: 10, letterSpacing: 1,
            }}>
              ⚠ {error}
            </div>
          )}

          {/* Login button */}
          <button
            id="login-btn"
            type="submit"
            disabled={loading}
            style={{
              marginTop: 8,
              background: loading ? "rgba(200,255,0,0.06)" : "rgba(200,255,0,0.1)",
              border: "1px solid #c8ff00",
              color: "#c8ff00",
              padding: "14px",
              fontFamily: "Space Mono, monospace",
              fontSize: 10, letterSpacing: 4,
              textTransform: "uppercase",
              cursor: loading ? "not-allowed" : "pointer",
              transition: "all .2s",
            }}
            onMouseEnter={e => { if (!loading) { e.target.style.background = "rgba(200,255,0,0.18)"; e.target.style.boxShadow = "0 0 20px rgba(200,255,0,0.2)" } }}
            onMouseLeave={e => { e.target.style.background = "rgba(200,255,0,0.1)"; e.target.style.boxShadow = "none" }}
          >
            {loading ? "AUTHENTICATING..." : "LOGIN"}
          </button>
        </form>

        {/* Footer hint */}
        <div style={{ marginTop: 32, textAlign: "center", fontSize: 8, color: "#2a2a2a", letterSpacing: 1 }}>
          DEFAULT: admin / hermes2026
        </div>
      </div>
    </div>
  )
}
