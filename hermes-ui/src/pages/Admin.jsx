/* hermes-ui/src/pages/Admin.jsx — Phase 11: Admin Panel */
import { useState, useEffect } from "react"
import axios from "axios"

const S = {
  label: {
    fontFamily: "Space Mono,monospace", fontSize: 8,
    letterSpacing: 3, color: "var(--dim)", textTransform: "uppercase",
    marginBottom: 8, display: "block",
  },
  input: {
    background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)",
    color: "#fff", padding: "10px 14px",
    fontFamily: "Space Mono,monospace", fontSize: 11,
    width: "100%", boxSizing: "border-box", outline: "none",
  },
  btn: {
    padding: "9px 18px", fontFamily: "Space Mono,monospace",
    fontSize: 9, letterSpacing: 2, textTransform: "uppercase",
    cursor: "pointer", border: "1px solid var(--accent)",
    background: "rgba(200,255,0,0.08)", color: "var(--accent)",
  },
  danger: {
    padding: "6px 12px", fontFamily: "Space Mono,monospace",
    fontSize: 8, letterSpacing: 1, textTransform: "uppercase",
    cursor: "pointer", border: "1px solid rgba(255,80,80,0.4)",
    background: "rgba(255,50,50,0.06)", color: "#ff5555",
  },
}

export default function Admin({ user }) {
  const [users, setUsers]       = useState([])
  const [status, setStatus]     = useState(null)
  const [newName, setNewName]   = useState("")
  const [newPass, setNewPass]   = useState("")
  const [newRole, setNewRole]   = useState("user")
  const [msg, setMsg]           = useState("")
  const [msgType, setMsgType]   = useState("ok")  // "ok" | "err"

  const flash = (text, type = "ok") => { setMsg(text); setMsgType(type); setTimeout(() => setMsg(""), 3000) }

  const loadUsers = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/auth/users")
      setUsers(res.data)
    } catch { flash("Failed to load users", "err") }
  }

  const loadStatus = async () => {
    try {
      const res = await axios.get("http://localhost:8000/api/status")
      setStatus(res.data)
    } catch {}
  }

  useEffect(() => { loadUsers(); loadStatus() }, [])

  const createUser = async () => {
    if (!newName.trim() || !newPass.trim()) { flash("Name and password required", "err"); return }
    try {
      const res = await axios.post("http://localhost:8000/api/auth/register", {
        name: newName.trim(), password: newPass.trim(), role: newRole
      })
      if (res.data.ok) {
        flash(`User "${newName}" created`)
        setNewName(""); setNewPass(""); setNewRole("user")
        loadUsers()
      } else {
        flash(res.data.error, "err")
      }
    } catch { flash("Create failed", "err") }
  }

  const deleteUser = async (uid, uname) => {
    if (!window.confirm(`Delete user "${uname}"?`)) return
    try {
      const res = await axios.delete(`http://localhost:8000/api/auth/users/${uid}`)
      if (res.data.ok) { flash(`"${uname}" deleted`); loadUsers() }
      else flash(res.data.error, "err")
    } catch { flash("Delete failed", "err") }
  }

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 24 }}>
        <div className="section-label" style={{ margin: 0 }}>Admin Panel</div>
        <span style={{
          fontFamily: "Space Mono,monospace", fontSize: 8, letterSpacing: 2,
          padding: "3px 8px", background: "rgba(200,255,0,0.1)",
          border: "1px solid var(--accent)", color: "var(--accent)",
        }}>ADMIN</span>
        <span style={{ fontFamily: "Space Mono,monospace", fontSize: 9, color: "var(--dim)", marginLeft: "auto" }}>
          Logged in as {user?.name}
        </span>
      </div>

      {/* Flash message */}
      {msg && (
        <div style={{
          marginBottom: 16, padding: "10px 14px",
          background: msgType === "ok" ? "rgba(200,255,0,0.08)" : "rgba(255,50,50,0.08)",
          border: `1px solid ${msgType === "ok" ? "rgba(200,255,0,0.3)" : "rgba(255,50,50,0.3)"}`,
          color: msgType === "ok" ? "var(--accent)" : "#ff5555",
          fontFamily: "Space Mono,monospace", fontSize: 10,
        }}>
          {msg}
        </div>
      )}

      {/* ── System Stats ── */}
      <div className="section-label">System Stats</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 28 }}>
        {[
          ["Users", users.length],
          ["Status", status?.online ? "ONLINE" : "OFFLINE"],
          ["Model", status?.model || "—"],
          ["Execution", status?.execution_enabled ? "ENABLED" : "DISABLED"],
        ].map(([k, v]) => (
          <div key={k} style={{
            border: "1px solid var(--border)", padding: "14px 16px",
            background: "rgba(255,255,255,0.02)",
          }}>
            <div style={{ fontFamily: "Space Mono,monospace", fontSize: 7, letterSpacing: 2, color: "var(--dim)", marginBottom: 6 }}>
              {k}
            </div>
            <div style={{ fontFamily: "Space Mono,monospace", fontSize: 13, color: "var(--accent)", letterSpacing: 1 }}>
              {v}
            </div>
          </div>
        ))}
      </div>

      {/* ── Create User ── */}
      <div className="section-label">Create User</div>
      <div style={{
        border: "1px solid var(--border)", padding: 20,
        background: "rgba(255,255,255,0.02)", marginBottom: 28,
      }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto auto", gap: 10, alignItems: "end" }}>
          <div>
            <span style={S.label}>Username</span>
            <input id="admin-new-username" style={S.input} value={newName}
              onChange={e => setNewName(e.target.value)} placeholder="username" />
          </div>
          <div>
            <span style={S.label}>Password</span>
            <input id="admin-new-password" style={S.input} type="password" value={newPass}
              onChange={e => setNewPass(e.target.value)} placeholder="password" />
          </div>
          <div>
            <span style={S.label}>Role</span>
            <select id="admin-role-select"
              value={newRole} onChange={e => setNewRole(e.target.value)}
              style={{ ...S.input, width: "auto", padding: "10px 12px" }}
            >
              <option value="user">user</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <button id="admin-create-btn" style={{ ...S.btn, marginTop: 0 }} onClick={createUser}>
            Create
          </button>
        </div>
      </div>

      {/* ── User Table ── */}
      <div className="section-label">Users ({users.length})</div>
      <div style={{ border: "1px solid var(--border)" }}>
        {/* Header */}
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 80px 160px 100px 60px",
          borderBottom: "1px solid var(--border)",
          padding: "8px 16px",
          background: "rgba(255,255,255,0.03)",
        }}>
          {["Name", "Role", "Created", "Sandbox", ""].map(h => (
            <span key={h} style={{
              fontFamily: "Space Mono,monospace", fontSize: 7,
              letterSpacing: 2, color: "var(--dim)", textTransform: "uppercase"
            }}>{h}</span>
          ))}
        </div>
        {/* Rows */}
        {users.length === 0
          ? <div style={{ padding: "20px 16px", fontFamily: "Space Mono,monospace", fontSize: 10, color: "var(--dim)" }}>
              No users found
            </div>
          : users.map(u => (
            <div key={u.id} style={{
              display: "grid", gridTemplateColumns: "1fr 80px 160px 100px 60px",
              padding: "10px 16px", borderBottom: "1px solid var(--border)",
              alignItems: "center",
            }}>
              <span style={{ fontFamily: "Space Mono,monospace", fontSize: 10, color: "#ddd" }}>
                {u.name}
                {u.id === user?.id && (
                  <span style={{ marginLeft: 8, fontSize: 8, color: "var(--accent)" }}>(you)</span>
                )}
              </span>
              <span style={{
                fontFamily: "Space Mono,monospace", fontSize: 8,
                color: u.role === "admin" ? "var(--accent)" : "var(--dim)", letterSpacing: 1
              }}>{u.role}</span>
              <span style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim)" }}>
                {u.created_at ? u.created_at.split("T")[0] : "—"}
              </span>
              <span style={{ fontFamily: "Space Mono,monospace", fontSize: 8, color: "var(--dim2)" }}>
                {u.sandbox_path || "/documents"}
              </span>
              <div>
                {u.role !== "admin" && (
                  <button style={S.danger} onClick={() => deleteUser(u.id, u.name)}>Del</button>
                )}
              </div>
            </div>
          ))
        }
      </div>
    </div>
  )
}
