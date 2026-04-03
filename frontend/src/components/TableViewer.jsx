// frontend/src/components/TableViewer.jsx
export default function TableViewer({ data }) {
  if (!data) return null

  // lap_table
  if (data.laps) {
    return (
      <div style={{ background:"#0F1421", borderRadius:"8px",
                    border:"1px solid #1E2840", overflow:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse",
                        fontFamily:"monospace", fontSize:"12px" }}>
          <thead>
            <tr style={{ background:"#141720", color:"#E8EEF8" }}>
              {["Lap","タイム","Gap","ベスト"].map(h => (
                <th key={h} style={{ padding:"8px 16px", textAlign:"center",
                                     borderBottom:"1px solid #00E5FF" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.laps.map((l, i) => (
              <tr key={l.lap} style={{ background: i%2===0?"#0F1421":"#0C1020" }}>
                <td style={{ padding:"6px 16px", textAlign:"center",
                             color: l.is_best ? "#00E5FF" : "#8B9EC0" }}>
                  Lap {l.lap}
                </td>
                <td style={{ padding:"6px 16px", textAlign:"center",
                             color: l.is_best ? "#00E5FF" : "#8B9EC0" }}>
                  {l.time_fmt}
                </td>
                <td style={{ padding:"6px 16px", textAlign:"center",
                             color: l.gap === "BEST" ? "#FFD700" : "#FF6B35" }}>
                  {l.gap}
                </td>
                <td style={{ padding:"6px 16px", textAlign:"center",
                             color: l.is_best ? "#FFD700" : "#5A6A8A" }}>
                  {l.is_best ? "★ BEST" : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // theoretical_best
  if (data.theoretical_best !== undefined) {
    const rows = [
      ["理論ベスト",     data.theoretical_best_fmt],
      ["ベストラップ",   data.best_lap_time_fmt],
      ["ポテンシャルゲイン", `${data.potential_gain.toFixed(3)}秒`],
    ]
    return <SimpleTable rows={rows} />
  }

  // ai_advice
  if (data.advices) {
    return (
      <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
        {data.advices.map(([title, body]) => (
          <div key={title} style={{ background:"#0F1421", borderRadius:"8px",
                                    border:"1px solid #1E2840", overflow:"hidden" }}>
            <div style={{ background:"#141720", padding:"8px 12px",
                          color:"#00E5FF", fontSize:"12px", fontWeight:"bold" }}>
              {title}
            </div>
            <div style={{ padding:"10px 12px", color:"#C0CCDE", fontSize:"11px",
                          lineHeight:"1.6" }}>
              {body}
            </div>
          </div>
        ))}
      </div>
    )
  }

  // rows 形式（corner_g, brake_g など）
  if (data.rows) {
    const keys = Object.keys(data.rows[0] || {})
    return (
      <div style={{ background:"#0F1421", borderRadius:"8px",
                    border:"1px solid #1E2840", overflow:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse",
                        fontFamily:"monospace", fontSize:"12px" }}>
          <thead>
            <tr style={{ background:"#141720" }}>
              {keys.map(k => (
                <th key={k} style={{ padding:"8px 16px", textAlign:"center",
                                     color:"#E8EEF8",
                                     borderBottom:"1px solid #1E2840" }}>{k}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} style={{ background: i%2===0?"#0F1421":"#0C1020" }}>
                {keys.map(k => (
                  <td key={k} style={{ padding:"6px 16px", textAlign:"center",
                                       color:"#8B9EC0" }}>
                    {typeof row[k] === "number" ? row[k].toFixed(3) : String(row[k])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  // priority形式（コーナー優先度）
  if (data.priority) {
    return (
      <div style={{ display:"flex", flexDirection:"column", gap:"6px" }}>
        {data.priority.map((p, i) => (
          <div key={i} style={{ background:"#0F1421", borderRadius:"8px",
                                border:"1px solid #1E2840", padding:"8px 12px" }}>
            <div style={{ color:"#39FF8A", fontSize:"12px", fontWeight:"bold" }}>
              #{i+1} コーナー {p.corner}
            </div>
            <div style={{ color:"#8B9EC0", fontSize:"11px", marginTop:"4px" }}>
              {p.reason}　速度ロス: {p.speed_loss?.toFixed(1)} km/h
            </div>
          </div>
        ))}
      </div>
    )
  }

  // フォールバック：JSON表示
  return (
    <pre style={{ background:"#0F1421", borderRadius:"8px",
                  border:"1px solid #1E2840", padding:"1rem",
                  color:"#8B9EC0", fontSize:"11px", overflow:"auto" }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

function SimpleTable({ rows }) {
  return (
    <div style={{ background:"#0F1421", borderRadius:"8px",
                  border:"1px solid #1E2840", overflow:"hidden" }}>
      <table style={{ width:"100%", borderCollapse:"collapse",
                      fontFamily:"monospace", fontSize:"13px" }}>
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label} style={{ borderBottom:"1px solid #1E2840" }}>
              <td style={{ padding:"10px 16px", color:"#8B9EC0" }}>{label}</td>
              <td style={{ padding:"10px 16px", color:"#00E5FF",
                           fontWeight:"bold", textAlign:"right" }}>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
