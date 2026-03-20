/* hermes-ui/src/pages/Files.jsx */
import { useState, useEffect } from "react"
import axios from "axios"

export default function Files() {
  const [files, setFiles] = useState([])
  const [readModal, setReadModal] = useState(null)
  const [approveModal, setApproveModal] = useState(null)
  const [newFileName, setNewFileName] = useState("")
  const [newFileContent, setNewFileContent] = useState("")

  const load = () =>
    axios.get("http://localhost:8000/api/files").then(r => setFiles(r.data)).catch(() => {})

  useEffect(() => { load() }, [])

  const readFile = async (name) => {
    const res = await axios.get("http://localhost:8000/api/files/read", { params: { path: `/documents/${name}` } })
    setReadModal({ name, content: res.data.content })
  }

  const deleteFile = (name) => {
    setApproveModal({ action: "DELETE", path: `/documents/${name}`, name })
  }

  const confirmDelete = async () => {
    await axios.delete("http://localhost:8000/api/files/delete", { params: { path: approveModal.path } })
    setApproveModal(null)
    load()
  }

  const writeFile = async () => {
    if (!newFileName.trim()) return
    const path = `/documents/${newFileName.trim()}`
    setApproveModal({ action: "WRITE", path, content: newFileContent, isWrite: true })
  }

  const confirmWrite = async () => {
    await axios.post("http://localhost:8000/api/files/write", { path: approveModal.path, content: approveModal.content || "" })
    setApproveModal(null)
    setNewFileName("")
    setNewFileContent("")
    load()
  }

  const fmtSize = (bytes) => bytes < 1024 ? `${bytes}B` : `${(bytes/1024).toFixed(1)}KB`

  return (
    <div>
      <div className="section-label">Sandbox — user_1</div>

      <div className="file-browser">
        <div className="file-path">
          SANDBOX — <span className="file-path-accent">user_1</span> / <span className="file-path-accent">documents</span>
        </div>
        <div>
          {files.length === 0 ? (
            <div className="file-empty">No files in sandbox.</div>
          ) : (
            files.map(f => (
              <div className="file-row" key={f.name}>
                <div className="file-icon">{f.is_dir ? "d" : "f"}</div>
                <div className="file-name">{f.name}</div>
                <div className="file-size">{fmtSize(f.size)}</div>
                <div className="file-date">{f.modified.substring(0, 10)}</div>
                <div className="file-actions">
                  {!f.is_dir && <button className="file-btn" onClick={() => readFile(f.name)}>Read</button>}
                  {!f.is_dir && <button className="file-btn del" onClick={() => deleteFile(f.name)}>Delete</button>}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div style={{marginTop: 24}}>
        <div className="section-label">New File</div>
        <div style={{display:"flex", gap:1, background:"var(--border)", marginBottom:8}}>
          <input
            className="new-file-input"
            placeholder="filename.txt"
            value={newFileName}
            onChange={e => setNewFileName(e.target.value)}
            style={{flex:"0 0 200px"}}
          />
          <input
            className="new-file-input"
            placeholder="file content..."
            value={newFileContent}
            onChange={e => setNewFileContent(e.target.value)}
            onKeyDown={e => e.key === "Enter" && writeFile()}
            style={{flex:1, borderLeft:"1px solid var(--border)"}}
          />
          <button className="new-file-btn" onClick={writeFile}>Write</button>
        </div>
      </div>

      {/* READ MODAL */}
      {readModal && (
        <div className="modal-bg" onClick={() => setReadModal(null)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div className="modal-title">{readModal.name}</div>
            <div className="modal-content">{readModal.content || "(empty file)"}</div>
            <button className="modal-close" onClick={() => setReadModal(null)}>Close</button>
          </div>
        </div>
      )}

      {/* APPROVE MODAL */}
      {approveModal && (
        <div className="approve-bg">
          <div className="approve-box">
            <div className="approve-title">Approval Required</div>
            <div className="approve-sub">Filesystem Write Operation</div>
            <div className="approve-field">
              <div className="approve-label">Action</div>
              <div className="approve-val">{approveModal.action}</div>
            </div>
            <div className="approve-field">
              <div className="approve-label">Path</div>
              <div className="approve-val">{approveModal.path}</div>
            </div>
            {approveModal.content && (
              <div className="approve-field">
                <div className="approve-label">Content Preview</div>
                <div className="approve-val">{approveModal.content.substring(0, 120)}{approveModal.content.length > 120 ? "..." : ""}</div>
              </div>
            )}
            <div className="approve-actions">
              <button className="btn-approve" onClick={approveModal.isWrite ? confirmWrite : confirmDelete}>Approve</button>
              <button className="btn-reject" onClick={() => setApproveModal(null)}>Reject</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
