/* hermes-ui/src/components/ApprovalModal.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

const ACTION_ICONS = {
  fs_write: "✍",
  fs_delete: "🗑",
  gmail_send: "✉",
  calendar_create: "📅",
  telegram_send: "✈",
  github_create_issue: "⚡",
}

const ACTION_COLORS = {
  fs_write: "#ffd93d",
  fs_delete: "#ff3b3b",
  gmail_send: "#ff6b6b",
  calendar_create: "#ff922b",
  telegram_send: "#74c0fc",
  github_create_issue: "#a78bfa",
}

export default function ApprovalModal({ approval, onResolved }) {
  const [state, setState] = useState("pending") // pending | approved | rejected
  const [countdown, setCountdown] = useState(60)

  const color = ACTION_COLORS[approval.tool] || "var(--accent)"
  const icon  = ACTION_ICONS[approval.tool] || "⚡"

  useEffect(() => {
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          handleReject()
          return 0
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const handleApprove = async () => {
    console.log("[MODAL] Approving:", approval.id)
    setState("approved")
    const res = await axios.post(`http://localhost:8000/api/approvals/${approval.id}/approve`)
    console.log("[MODAL] Approve response:", res.data)
    setTimeout(() => onResolved(approval.id, true), 800)
  }

  const handleReject = async () => {
    if (state !== "pending") return
    setState("rejected")
    await axios.post(`http://localhost:8000/api/approvals/${approval.id}/reject`)
    setTimeout(() => onResolved(approval.id, false), 600)
  }

  return (
    <div style={{
      position:"fixed", inset:0,
      background:"rgba(0,0,0,0.85)",
      display:"flex", alignItems:"center", justifyContent:"center",
      zIndex:1000,
      animation:"fadeIn 0.15s ease"
    }}>
      <div style={{
        background:"#0a0a0a",
        border:`1px solid ${color}`,
        width:460, maxWidth:"92vw",
        animation:"slideUp 0.2s cubic-bezier(0.16,1,0.3,1)",
        position:"relative", overflow:"hidden"
      }}>
        {/* Top accent line */}
        <div style={{
          height:2, background:color,
          animation: state === "pending" ? "pulse-bar 2s infinite" : "none"
        }} />

        {/* Countdown bar */}
        <div style={{
          height:2, background:`${color}33`,
          position:"relative", overflow:"hidden"
        }}>
          <div style={{
            height:"100%", background:color,
            width:`${(countdown/60)*100}%`,
            transition:"width 1s linear",
            opacity: state === "pending" ? 1 : 0
          }} />
        </div>

        <div style={{padding:"28px 32px"}}>
          {/* Header */}
          <div style={{display:"flex", alignItems:"center", gap:14, marginBottom:20}}>
            <div style={{
              width:44, height:44,
              background:`${color}15`,
              border:`1px solid ${color}40`,
              display:"flex", alignItems:"center", justifyContent:"center",
              fontSize:20,
              animation: state === "pending" ? "iconPulse 2s infinite" : "none"
            }}>
              {icon}
            </div>
            <div>
              <div style={{
                fontFamily:"Bebas Neue,sans-serif",
                fontSize:22, letterSpacing:3,
                color: state === "approved" ? "var(--accent)" :
                       state === "rejected" ? "var(--red)" : "var(--white)"
              }}>
                {state === "approved" ? "APPROVED" :
                 state === "rejected" ? "REJECTED" :
                 "APPROVAL REQUIRED"}
              </div>
              <div style={{
                fontFamily:"Space Mono,monospace", fontSize:9,
                letterSpacing:2, textTransform:"uppercase",
                color
              }}>
                {approval.tool?.replace(/_/g," ")} · {countdown}s remaining
              </div>
            </div>
          </div>

          {/* Details */}
          <div style={{
            background:"rgba(255,255,255,0.03)",
            border:"1px solid rgba(255,255,255,0.08)",
            padding:"14px 16px", marginBottom:24
          }}>
            <div style={{
              fontFamily:"Space Mono,monospace", fontSize:9,
              letterSpacing:2, textTransform:"uppercase",
              color:"var(--dim2)", marginBottom:8
            }}>
              Action Details
            </div>
            <div style={{
              fontFamily:"Space Mono,monospace", fontSize:11,
              color:"var(--white)", lineHeight:1.8
            }}>
              {approval.details?.description || "No details provided"}
            </div>
          </div>

          {/* Buttons */}
          {state === "pending" && (
            <div style={{display:"flex", gap:10}}>
              <button
                onClick={handleApprove}
                style={{
                  flex:1, padding:"13px",
                  background:color, color:"#000",
                  border:"none", cursor:"pointer",
                  fontFamily:"Space Mono,monospace",
                  fontSize:11, fontWeight:700,
                  letterSpacing:2, textTransform:"uppercase",
                  transition:"all 0.15s",
                  animation:"approveGlow 2s infinite"
                }}
                onMouseEnter={e => e.target.style.opacity = "0.85"}
                onMouseLeave={e => e.target.style.opacity = "1"}
              >
                Approve
              </button>
              <button
                onClick={handleReject}
                style={{
                  flex:1, padding:"13px",
                  background:"transparent", color:"var(--red)",
                  border:"1px solid var(--red)", cursor:"pointer",
                  fontFamily:"Space Mono,monospace",
                  fontSize:11, letterSpacing:2, textTransform:"uppercase",
                  transition:"all 0.15s"
                }}
                onMouseEnter={e => { e.target.style.background="var(--red)"; e.target.style.color="#000" }}
                onMouseLeave={e => { e.target.style.background="transparent"; e.target.style.color="var(--red)" }}
              >
                Reject
              </button>
            </div>
          )}

          {state === "approved" && (
            <div style={{
              textAlign:"center", padding:"12px",
              fontFamily:"Space Mono,monospace", fontSize:11,
              color:"var(--accent)", letterSpacing:2,
              animation:"fadeIn 0.3s ease"
            }}>
              ✓ ACTION APPROVED — EXECUTING
            </div>
          )}

          {state === "rejected" && (
            <div style={{
              textAlign:"center", padding:"12px",
              fontFamily:"Space Mono,monospace", fontSize:11,
              color:"var(--red)", letterSpacing:2,
              animation:"shake 0.3s ease"
            }}>
              ✕ ACTION REJECTED
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity:0 }
          to   { opacity:1 }
        }
        @keyframes slideUp {
          from { opacity:0; transform:translateY(24px) scale(0.97) }
          to   { opacity:1; transform:translateY(0) scale(1) }
        }
        @keyframes shake {
          0%,100% { transform:translateX(0) }
          20%     { transform:translateX(-6px) }
          40%     { transform:translateX(6px) }
          60%     { transform:translateX(-4px) }
          80%     { transform:translateX(4px) }
        }
        @keyframes pulse-bar {
          0%,100% { opacity:1 }
          50%     { opacity:0.4 }
        }
        @keyframes iconPulse {
          0%,100% { transform:scale(1) }
          50%     { transform:scale(1.08) }
        }
        @keyframes approveGlow {
          0%,100% { box-shadow:none }
          50%     { box-shadow:0 0 20px ${ACTION_COLORS[approval?.tool] || "#c8ff00"}40 }
        }
      `}</style>
    </div>
  )
}