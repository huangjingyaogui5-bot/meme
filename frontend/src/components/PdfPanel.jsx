// frontend/src/components/PdfPanel.jsx
import { useState } from "react"

export default function PdfPanel({ sessionId, laps, apiBase }) {
  const [open,    setOpen]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [fields,  setFields]  = useState({
    course_name: "", driver_name: "", car_name: "", weather: ""
  })

  const generate = async () => {
    setLoading(true)
    const params = new URLSearchParams({ laps, ...fields })
    const res = await fetch(
      `${apiBase}/api/${sessionId}/pdf?${params}`,
      { method: "POST" }
    )
    if (res.ok) {
      const blob = await res.blob()
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement("a")
      a.href     = url
      a.download = `telemetry_${sessionId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      alert("PDF生成に失敗しました")
    }
    setLoading(false)
    setOpen(false)
  }

  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        style={{
          width: "100%", padding: "8px",
          background: "#0A1A2A", color: "#00E5FF",
          border: "1px solid #00E5FF", borderRadius: "6px",
          fontFamily: "monospace", fontSize: "12px",
          fontWeight: "bold", cursor: "pointer",
        }}
      >
        📄 PDFレポート生成
      </button>

      {open && (
        <div style={{ marginTop: "8px", background: "#0F1421",
                      border: "1px solid #1E2840", borderRadius: "8px",
                      padding: "10px" }}>
          {[
            ["コース名", "course_name"],
            ["ドライバー", "driver_name"],
            ["車種", "car_name"],
            ["天気", "weather"],
          ].map(([label, key]) => (
            <div key={key} style={{ marginBottom: "6px" }}>
              <div style={{ color: "#5A6A8A", fontSize: "10px",
                            marginBottom: "2px" }}>{label}</div>
              <input
                value={fields[key]}
                onChange={e => setFields({ ...fields, [key]: e.target.value })}
                style={{
                  width: "100%", background: "#0A0E1A",
                  border: "1px solid #1E2840", borderRadius: "4px",
                  color: "#E8EEF8", fontFamily: "monospace",
                  fontSize: "11px", padding: "4px 6px",
                  boxSizing: "border-box",
                }}
                placeholder={`${label}を入力`}
              />
            </div>
          ))}
          <button
            onClick={generate}
            disabled={loading}
            style={{
              width: "100%", padding: "6px",
              background: loading ? "#1A2035" : "#0A1A2A",
              color: "#00E5FF", border: "none",
              borderRadius: "6px", fontFamily: "monospace",
              fontSize: "11px", cursor: loading ? "wait" : "pointer",
            }}
          >
            {loading ? "⏳ 生成中..." : "📥 ダウンロード"}
          </button>
        </div>
      )}
    </div>
  )
}
