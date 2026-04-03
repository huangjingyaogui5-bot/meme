// frontend/src/components/GraphViewer.jsx
import { useState } from "react"

export default function GraphViewer({ src }) {
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(false)
  return (
    <div style={{ background: "#0F1421", borderRadius: "8px",
                  border: "1px solid #1E2840", overflow: "hidden" }}>
      {loading && !error && (
        <div style={{ padding: "2rem", color: "#5A6A8A",
                      textAlign: "center", fontSize: "0.85rem" }}>
          ⏳ グラフ生成中...
        </div>
      )}
      {error && (
        <div style={{ padding: "2rem", color: "#FF4E4E",
                      textAlign: "center", fontSize: "0.85rem" }}>
          ⚠️ グラフの生成に失敗しました
        </div>
      )}
      <img
        src={src}
        alt="analysis graph"
        style={{ width: "100%", display: loading || error ? "none" : "block" }}
        onLoad={() => { setLoading(false); setError(false) }}
        onError={() => { setLoading(false); setError(true) }}
      />
    </div>
  )
}
