// frontend/src/pages/AnalysisPage.jsx
import { useState } from "react"
import LapSelector from "../components/LapSelector"
import GraphViewer from "../components/GraphViewer"
import TableViewer from "../components/TableViewer"
import PdfPanel   from "../components/PdfPanel"

const API = import.meta.env.VITE_API_URL || ""

export default function AnalysisPage({ session, onReset }) {
  const [selectedLaps, setSelectedLaps] = useState(
    session.laps.filter(l => l.is_best).map(l => l.lap)
  )
  const [currentGraph, setCurrentGraph] = useState(null)
  const [currentTable, setCurrentTable] = useState(null)
  const [mlStatus,     setMlStatus]     = useState("")

  const sid    = session.session_id
  const lapsQS = selectedLaps.join(",")

  // ── グラフ表示 ──────────────────────────────────────────────
  const showGraph = (endpoint) => {
    setCurrentTable(null)
    setCurrentGraph(`${API}/api/${sid}/${endpoint}?laps=${lapsQS}&t=${Date.now()}`)
  }

  // ── テーブル表示 ────────────────────────────────────────────
  const showTable = async (endpoint) => {
    setCurrentGraph(null)
    const res  = await fetch(`${API}/api/${sid}/${endpoint}`)
    const data = await res.json()
    setCurrentTable(data)
  }

  // ── ML学習 ──────────────────────────────────────────────────
  const trainML = async () => {
    setMlStatus("学習中...")
    await fetch(`${API}/api/${sid}/ml/train`, { method: "POST" })
    setMlStatus("✅ 学習完了")
    setTimeout(() => setMlStatus(""), 3000)
  }

  // ── Extra関数呼び出し ────────────────────────────────────────
  const showExtra = (funcName) => {
    setCurrentTable(null)
    setCurrentGraph(`${API}/api/${sid}/extra/${funcName}?laps=${lapsQS}&t=${Date.now()}`)
  }

  // ── ボタン定義 ──────────────────────────────────────────────
  const sections = [
    {
      label: "── 解析機能 ──", color: "#00E5FF",
      buttons: [
        ["速度トレース",       () => showGraph("speed_trace")],
        ["デルタタイム",       () => showGraph("delta_time")],
        ["G-Gダイアグラム",    () => showGraph("gg_diagram")],
        ["ブレーキマップ",     () => showGraph("brake_map")],
        ["コーナー速度解析",   () => showGraph("corner_analysis")],
        ["セクター比較",       () => showGraph("sector_comparison")],
        ["ラップ安定性",       () => showGraph("lap_consistency")],
        ["GPSライン比較",      () => showGraph("racing_line")],
        ["速度ヒートマップ",   () => showGraph("speed_heatmap")],
        ["全Lap速度一覧",      () => showGraph("all_speed")],
        ["GPSトラックMAP",     () => showGraph("gps_track")],
        ["理論ベストLap",      () => showTable("theoretical_best")],
        ["ラップタイム一覧",   () => showTable("lap_table")],
        ["コーナーG最大値",    () => showTable("corner_g_table")],
        ["ブレーキG最大値",    () => showTable("brake_g_table")],
        ["最低速度ランキング", () => showTable("min_speed_table")],
      ],
      bg: "#0F1421", fg: "#8B9EC0",
    },
    {
      label: "── 新解析機能 ──", color: "#00E5FF",
      buttons: [
        ["🛑 制動点距離解析",       () => showGraph("brake_distance")],
        ["🚀 スロットルON解析",     () => showGraph("throttle_on")],
        ["🏆 コーナー別ランキング", () => showTable("corner_ranking")],
        ["🔄 OS/US自動判定",        () => showGraph("os_us")],
        ["😴 疲労度スコア",          () => showGraph("fatigue")],
        ["⭐ 走行品質スコア",        () => showGraph("quality_score")],
      ],
      bg: "#0A1A2A", fg: "#00E5FF",
    },
    {
      label: "── AI 理想分析 ──", color: "#C97FFF",
      buttons: [
        ["🎯 理想速度プロファイル", () => showGraph("ideal_speed")],
        ["🗺️ 理想ライン（GPS）",    () => showGraph("ideal_line")],
        ["🤖 AIアドバイス",          () => showTable("ai_advice")],
        ["⛽ 理想ピット戦略",        () => showTable("ideal_pit")],
      ],
      bg: "#1A0E28", fg: "#C97FFF",
    },
    {
      label: "── 機械学習 AI ──", color: "#39FF8A",
      buttons: [
        ["📈 次Lapタイム予測",  () => showTable(`ml/lap_predict`)],
        ["🔬 タイヤ劣化AI",     () => showGraph("ml/tire")],
        ["🏁 コーナー優先度AI", () => showTable("ml/corner_priority")],
        ["✨ AI理想ライン合成",  () => showGraph("ml/ideal_line_ai")],
        ["🔁 AIモデル学習",     trainML],
      ],
      bg: "#0A1A0E", fg: "#39FF8A",
    },
    {
      label: "── データ管理 ──", color: "#FFB84E",
      buttons: [
        ["📂 DBに登録",         async () => {
          await fetch(`${API}/api/${sid}/db/register`, { method: "POST" })
          alert("登録完了")
        }],
        ["📊 全セッション一覧", () => showTable("db/sessions").catch(() =>
          fetch(`${API}/api/db/sessions`).then(r=>r.json()).then(setCurrentTable))],
        ["🧠 蓄積データ学習",   async () => {
          await fetch(`${API}/api/db/train`, { method: "POST" })
          alert("学習開始しました")
        }],
        ["📈 セッション間比較", () => showGraph("extra/gps_overlay")],
      ],
      bg: "#1A1000", fg: "#FFB84E",
    },
    {
      label: "── 詳細解析（全機能）──", color: "#5A6A8A",
      buttons: [
        ["速度比較(詳細)",      () => showExtra("compare_speed")],
        ["ライン比較(詳細)",    () => showExtra("compare_line")],
        ["全Lap速度(詳細)",     () => showExtra("show_all_speed")],
        ["ブレーキMAP(詳細)",   () => showExtra("brake_map_ex")],
        ["デルタタイム(詳細)",  () => showExtra("delta_time_ex")],
        ["タイムロスMAP",       () => showExtra("delta_map")],
        ["最低速度マップ",      () => showExtra("min_speed_map")],
        ["ブレーキ強度MAP",     () => showExtra("brake_intensity_map")],
        ["セクター解析(詳細)",  () => showExtra("auto_sector")],
        ["コーナーセクター",    () => showExtra("corner_sector_analysis")],
        ["速度ヒートMAP",       () => showExtra("speed_heatmap_ex")],
        ["理論ベスト(詳細)",    () => showExtra("theoretical_lap_ex")],
        ["Lap安定性(詳細)",     () => showExtra("lap_consistency_ex")],
        ["加速性能",            () => showExtra("accel_performance")],
        ["トラクション解析",    () => showExtra("traction_analysis")],
        ["コーナー解析(詳細)",  () => showExtra("corner_analysis_ex")],
        ["コーナータイム差",    () => showExtra("corner_time_delta_ex")],
        ["理想速度(詳細)",      () => showExtra("ideal_speed_ex")],
        ["G-G(詳細)",           () => showExtra("gg_diagram_ex")],
        ["最低速度ランキング",  () => showExtra("corner_speed_rank")],
        ["ブレーキG",           () => showExtra("brake_g_ex")],
        ["スロットルMAP",       () => showExtra("throttle_map_ex")],
        ["立ち上がり加速",      () => showExtra("exit_accel")],
        ["LapヒートMAP",        () => showExtra("lap_time_heatmap")],
        ["GPSライン重ね",       () => showExtra("gps_overlay")],
        ["コーナー時間合計",    () => showExtra("corner_total_loss")],
        ["ライン差解析",        () => showExtra("racing_line_delta")],
        ["スロットルON位置",    () => showExtra("throttle_on_map")],
        ["コーナーG限界",       () => showExtra("corner_g_limit")],
        ["ブレーキ距離解析",    () => showExtra("brake_distance_analysis")],
        ["コーナータイムロス",  () => showExtra("corner_time_loss_ex")],
        ["Ideal Lap解析",       () => showExtra("ideal_lap_analysis")],
      ],
      bg: "#111118", fg: "#5A6A8A",
    },
  ]

  // ── スタイル定数 ────────────────────────────────────────────
  const S = {
    sidebar: {
      width: "220px", flexShrink: 0,
      background: "#0A0E1A",
      borderRight: "1px solid #1E2840",
      overflowY: "auto", height: "100vh",
      position: "sticky", top: 0,
    },
    main: {
      flex: 1, padding: "1rem", overflowY: "auto",
    },
    btn: (bg, fg) => ({
      background: bg, color: fg,
      border: "none", borderRadius: "6px",
      padding: "5px 6px", fontSize: "11px",
      fontFamily: "monospace", cursor: "pointer",
      width: "100%", textAlign: "left",
      marginBottom: "2px",
    }),
    sectionLabel: (color) => ({
      color, fontSize: "11px", fontWeight: "bold",
      padding: "10px 8px 4px", display: "block",
    }),
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>

      {/* ── 左：ラップ選択 ──────────────────────────────── */}
      <div style={{ width: "180px", flexShrink: 0, background: "#0A0E1A",
                    borderRight: "1px solid #1E2840", overflowY: "auto",
                    height: "100vh", position: "sticky", top: 0 }}>
        <div style={{ padding: "8px 8px 4px", color: "#00E5FF",
                      fontSize: "11px", fontWeight: "bold" }}>── Lap 選択 ──</div>
        <LapSelector
          laps={session.laps}
          selected={selectedLaps}
          onChange={setSelectedLaps}
        />
        <div style={{ padding: "4px 6px" }}>
          <button style={S.btn("#0F1421","#8B9EC0")}
            onClick={() => setSelectedLaps(session.laps.map(l=>l.lap))}>
            全選択
          </button>
          <button style={S.btn("#0F1421","#8B9EC0")}
            onClick={() => setSelectedLaps([])}>
            全解除
          </button>
          <button style={{ ...S.btn("#0A1A2A","#00E5FF"), marginTop:"6px" }}
            onClick={onReset}>
            ↩ CSV再アップロード
          </button>
        </div>
        <div style={{ padding: "4px 6px 8px", fontSize:"10px", color:"#5A6A8A" }}>
          {session.total_laps}ラップ  Best: Lap {session.best_lap}<br/>
          {session.best_time}
        </div>
      </div>

      {/* ── 中：解析ボタン ─────────────────────────────── */}
      <div style={S.sidebar}>
        <div style={{ padding: "8px 8px 4px", color: "#00E5FF",
                      fontSize: "11px", fontWeight: "bold" }}>── 解析機能 ──</div>

        {mlStatus && (
          <div style={{ padding:"4px 8px", color:"#39FF8A", fontSize:"10px" }}>
            {mlStatus}
          </div>
        )}

        {sections.map(({ label, color, buttons, bg, fg }) => (
          <div key={label}>
            <span style={S.sectionLabel(color)}>{label}</span>
            <div style={{ padding: "0 6px" }}>
              {buttons.map(([text, handler]) => (
                <button key={text} style={S.btn(bg, fg)} onClick={handler}>
                  {text}
                </button>
              ))}
            </div>
          </div>
        ))}

        {/* PDF */}
        <div style={{ padding: "8px 6px" }}>
          <PdfPanel sessionId={sid} laps={lapsQS} apiBase={API} />
        </div>
      </div>

      {/* ── 右：グラフ・テーブル表示エリア ──────────────── */}
      <div style={S.main}>
        <div style={{ marginBottom: "0.5rem", color: "#5A6A8A", fontSize: "11px" }}>
          {session.filename}  |  選択ラップ: {selectedLaps.join(", ") || "（なし）"}
        </div>

        {currentGraph && <GraphViewer src={currentGraph} />}
        {currentTable && <TableViewer data={currentTable} />}

        {!currentGraph && !currentTable && (
          <div style={{ textAlign: "center", color: "#2A3A5A",
                        paddingTop: "6rem", fontSize: "0.9rem" }}>
            左のボタンから解析を選択してください
          </div>
        )}
      </div>
    </div>
  )
}
