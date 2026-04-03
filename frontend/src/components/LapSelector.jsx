// frontend/src/components/LapSelector.jsx
export default function LapSelector({ laps, selected, onChange }) {
  const toggle = (lap) => {
    if (selected.includes(lap)) onChange(selected.filter(l => l !== lap))
    else onChange([...selected, lap])
  }
  return (
    <div style={{ padding: "0 6px" }}>
      {laps.map(l => (
        <label key={l.lap} style={{
          display: "flex", alignItems: "center", gap: "6px",
          padding: "2px 0", cursor: "pointer",
          color: l.is_best ? "#00E5FF" : "#8B9EC0", fontSize: "11px",
        }}>
          <input type="checkbox"
            checked={selected.includes(l.lap)}
            onChange={() => toggle(l.lap)}
            style={{ accentColor: "#00E5FF" }}
          />
          Lap {l.lap}　{l.time_fmt}{l.is_best ? " ★" : ""}
        </label>
      ))}
    </div>
  )
}
