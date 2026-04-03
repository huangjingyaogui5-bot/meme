// frontend/src/pages/UploadPage.jsx
import { useState, useRef } from "react"

const API = import.meta.env.VITE_API_URL || ""

export default function UploadPage({ onSessionReady }) {
  const [dragging, setDragging] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState("")
  const fileRef = useRef()

  const upload = async (file) => {
    if (!file || !file.name.endsWith(".csv")) {
      setError("CSVファイルを選択してください"); return
    }
    setLoading(true); setError("")
    const form = new FormData()
    form.append("file", file)
    try {
      const res  = await fetch(`${API}/api/upload`, { method: "POST", body: form })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "アップロードエラー")
      onSessionReady(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) upload(file)
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", alignItems:"center",
                  justifyContent:"center", minHeight:"100vh", padding:"2rem" }}>
      <h1 style={{ color:"#00E5FF", fontSize:"1.6rem", marginBottom:"0.5rem" }}>
        🏁 耐久レース テレメトリー解析
      </h1>
      <p style={{ color:"#5A6A8A", marginBottom:"2rem", fontSize:"0.85rem" }}>
        AI Lap Detection  |  Machine Learning  |  PDF Report
      </p>

      {/* ドロップゾーン */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current.click()}
        style={{
          width: "480px", maxWidth: "90vw", height: "200px",
          border: `2px dashed ${dragging ? "#00E5FF" : "#1E2840"}`,
          borderRadius: "12px", background: "#0F1421",
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          cursor: "pointer", transition: "border-color 0.2s",
        }}
      >
        <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>📂</div>
        <div style={{ color: "#8B9EC0", fontSize: "0.9rem" }}>
          CSVファイルをドロップ
        </div>
        <div style={{ color: "#5A6A8A", fontSize: "0.75rem", marginTop:"0.3rem" }}>
          または クリックして選択
        </div>
        <input
          ref={fileRef} type="file" accept=".csv"
          style={{ display: "none" }}
          onChange={(e) => upload(e.target.files[0])}
        />
      </div>

      {/* ローディング */}
      {loading && (
        <div style={{ marginTop: "1.5rem", color: "#00E5FF", fontSize: "0.9rem" }}>
          ⏳ CSV解析中・ラップ検出中...
        </div>
      )}

      {/* エラー */}
      {error && (
        <div style={{ marginTop: "1rem", color: "#FF4E4E",
                      background: "#1A0A0A", padding: "0.6rem 1rem",
                      borderRadius: "8px", fontSize: "0.85rem" }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  )
}
