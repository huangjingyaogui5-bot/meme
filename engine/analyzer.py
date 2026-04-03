"""
engine/analyzer.py  ─  解析コア（tkinter依存を除去したもの）
main.py から純粋な関数だけ抜き出し、ウェブ用に調整。
"""

import sys, os, io
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

BRAKE_THR    = -0.2
RESAMPLE_PTS = 2000

PLT_STYLE = {
    "figure.facecolor": "#0A0E1A",
    "axes.facecolor":   "#0F1421",
    "axes.edgecolor":   "#1E2840",
    "axes.labelcolor":  "#8B9EC0",
    "axes.titlecolor":  "#E8EEF8",
    "xtick.color":      "#5A6A8A",
    "ytick.color":      "#5A6A8A",
    "grid.color":       "#1A2035",
    "legend.facecolor": "#0F1421",
    "legend.edgecolor": "#1E2840",
    "legend.labelcolor":"#8B9EC0",
    "text.color":       "#E8EEF8",
    "savefig.facecolor":"#0A0E1A",
    "font.family":      "monospace",
}
plt.rcParams.update(PLT_STYLE)


def fmt_time(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{sec:.3f}s"


def load_csv(path: str) -> pd.DataFrame:
    for enc in ["shift_jis", "cp932", "utf-8", "utf-8-sig", "latin1"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            print(f"[OK] {enc}  {len(df)}行 x {len(df.columns)}列")
            return df
        except Exception:
            continue
    raise ValueError("CSVの文字コードを判定できませんでした")


def auto_rename(df: pd.DataFrame) -> pd.DataFrame:
    col_map = {
        "秒": "time_sec", "時間": "time_str", "緯度": "lat", "経度": "lon",
        "距離(km)": "distance_km", "標高(m)": "altitude_m", "速度(km/h)": "speed_kmh",
        "旋回半径(m)": "turn_radius_m", "コーナリングG": "cornering_g",
        "加減速G": "accel_g_raw", "合算G": "total_g",
    }
    return df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    num_cols = ["time_sec", "lat", "lon", "distance_km", "altitude_m", "speed_kmh",
                "turn_radius_m", "cornering_g", "accel_g_raw", "total_g"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.sort_values("time_sec").dropna(
        subset=["time_sec", "lat", "lon"]).reset_index(drop=True)

    for col in ["lat", "lon"]:
        df[col] = df[col].rolling(5, min_periods=1).mean()
    if len(df) > 25:
        w = min(11, len(df) - 2)
        w = w if w % 2 == 1 else w - 1
        w = max(w, 5)
        df["lat"] = savgol_filter(df["lat"].fillna(0), w, 3)
        df["lon"] = savgol_filter(df["lon"].fillna(0), w, 3)

    if "speed_kmh" in df.columns:
        jump = df["speed_kmh"].diff().abs()
        df.loc[jump > 80, "speed_kmh"] = np.nan
        df["speed_kmh"] = df["speed_kmh"].interpolate()

    dt = df["time_sec"].diff().fillna(0.05).clip(lower=0.001)
    df["dt"] = dt
    if "speed_kmh" in df.columns:
        spd_ms = df["speed_kmh"] / 3.6
        df["accel"]  = spd_ms.diff() / dt
        df["long_g"] = df["accel"] / 9.81
        df["long_g"] = df["long_g"].clip(-5, 5)

    lat_diff = df["lat"].diff().fillna(0)
    lon_diff = df["lon"].diff().fillna(0)
    heading  = np.arctan2(lon_diff, lat_diff)
    h_unwrap = np.unwrap(heading.values)
    h_diff   = np.diff(h_unwrap, prepend=h_unwrap[0])
    if "speed_kmh" in df.columns:
        spd_ms2  = df["speed_kmh"].fillna(0) / 3.6
        df["lat_g"] = (spd_ms2 * h_diff / dt) / 9.81
        df["lat_g"] = df["lat_g"].clip(-5, 5).rolling(3).mean().fillna(0)

    if "cornering_g" in df.columns:
        df["lat_g"] = df["cornering_g"]

    lat1 = df["lat"].values[:-1]; lat2 = df["lat"].values[1:]
    lon1 = df["lon"].values[:-1]; lon2 = df["lon"].values[1:]
    d = np.sqrt((lat2 - lat1) ** 2 + (lon2 - lon1) ** 2) * 111000
    df["dist_m"] = np.insert(np.cumsum(d), 0, 0)

    if "long_g" in df.columns:
        df["brake"] = (df["long_g"] < BRAKE_THR) & (df.get("speed_kmh", 0) > 30)

    print(f"[前処理] {len(df)}行 完了")
    return df


def resample_lap(lap_df: pd.DataFrame, points: int = RESAMPLE_PTS) -> pd.DataFrame:
    d = lap_df["dist_m"] - lap_df["dist_m"].min()
    t = lap_df["time_sec"] - lap_df["time_sec"].min()
    length = d.max()
    if length == 0:
        return pd.DataFrame({"dist": [], "speed": [], "time": []})
    nd = np.linspace(0, length, points)
    return pd.DataFrame({
        "dist":  nd,
        "speed": np.interp(nd, d, lap_df["speed_kmh"].fillna(0)) if "speed_kmh" in lap_df else np.zeros(points),
        "time":  np.interp(nd, d, t),
    })


def theoretical_best(df: pd.DataFrame, lap_data: dict, lap_times: dict, n: int = 10) -> float:
    total = 0
    for i in range(n):
        times = []
        for lap in lap_times:
            ld = lap_data[lap].copy()
            ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
            length = ld["ld"].max()
            if length == 0:
                continue
            sl  = length / n
            sec = ld[(ld["ld"] >= i * sl) & (ld["ld"] < (i + 1) * sl)]
            if len(sec) > 3:
                t = sec["time_sec"].max() - sec["time_sec"].min()
                if t > 0:
                    times.append(t)
        if times:
            total += min(times)
    return total


def make_sectors(lap_data: dict, best_lap: int) -> dict:
    ld = lap_data[best_lap].copy()
    ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
    L = ld["ld"].max()
    return {f"S{i+1}": (round(L * i / 3), round(L * (i + 1) / 3)) for i in range(3)}


def generate_ai_comment(data: dict) -> dict:
    """AIコメント生成（tkinter不要版）"""
    comments = {}
    best  = data["best_lap_time"]
    tb    = data["theoretical_best"]
    gain  = best - tb
    std   = data["lap_std"]
    total = data["total_laps"]

    cons = "高い" if std < 1.0 else ("普通" if std < 2.0 else "低い")
    comments["summary"] = (
        f"総走行ラップ数 {total} Lap。ベストラップ {fmt_time(best)}、"
        f"理論ベスト {fmt_time(tb)}、ポテンシャルゲイン {gain:.3f}秒。"
        f"ラップタイムSTD {std:.3f}秒（安定性：{cons}）。"
    )

    ms  = data.get("max_speed", 0)
    ms2 = data.get("min_speed", 0)
    avs = data.get("avg_speed", 0)
    comments["speed"] = (
        f"最高速度 {ms:.1f} km/h、最低速度 {ms2:.1f} km/h、平均速度 {avs:.1f} km/h。"
    )

    mlg = data.get("max_lat_g", 0)
    mbg = data.get("max_brake_g", 0)
    mag = data.get("max_lon_g", 0)
    comments["gg"] = (
        f"横G最大 {mlg:.2f}g、加速G最大 {mag:.2f}g、制動G最大 {abs(mbg):.2f}g。"
    )

    comments["delta"]  = "デルタタイムが上昇している区間がタイムロスポイントです。"
    comments["brake"]  = "制動Gのピーク値と持続時間を確認し、リリースタイミングを最適化してください。"
    comments["corner"] = "コーナーエントリー速度が高くてもミニマムが低い場合はブレーキが早すぎます。"
    comments["line"]   = "全ラップの走行ラインを重ね合わせました。ばらつきが大きい区間が課題です。"

    suggestions = []
    if gain > 3.0:
        suggestions.append(f"[タイム] 理論ベストとの差が {gain:.3f}秒。セクター別にタイムロスを特定してください。")
    elif gain > 1.0:
        suggestions.append(f"[タイム] あと {gain:.3f}秒の改善余地。各セクターのベストを同一ラップで再現が目標です。")
    if std > 2.0:
        suggestions.append(f"[安定性] STD {std:.3f}秒は大きいです。制動点の一貫性を優先してください。")
    if mlg < 1.2:
        suggestions.append(f"[コーナリング] 横G最大 {mlg:.2f}g。コーナリング速度を3〜5 km/h上げてください。")
    if abs(mbg) < 0.8:
        suggestions.append(f"[ブレーキング] 制動G最大 {abs(mbg):.2f}g。制動点を5〜10m遅らせてください。")
    if not suggestions:
        suggestions.append("[総合] 非常に安定した走りです。制動点を1m単位で詰めることを推奨します。")
    comments["suggestions"] = suggestions[:5]
    return comments


def generate_pdf(selected, lap_data, lap_times, best_lap, df,
                 lat_col, lon_col,
                 course_name="—", driver_name="—", car_name="—", weather="—",
                 output_path="telemetry_report.pdf"):
    """PDF生成（ウェブ用・output_pathを引数で受け取る）"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import mm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Image, Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import ParagraphStyle
        import datetime
    except ImportError:
        raise RuntimeError("reportlab が必要です: pip install reportlab")

    from engine.plots import (plot_speed_trace, plot_delta_time, plot_gg,
                               plot_racing_line, plot_brake_map,
                               plot_corner_analysis, plot_lap_consistency,
                               plot_sector_comparison)

    import tempfile, os
    tmp_dir = tempfile.mkdtemp()

    def save_fig(fig, name):
        path = os.path.join(tmp_dir, name)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return path

    sectors = make_sectors(lap_data, best_lap)
    imgs = {}
    imgs["speed"]   = save_fig(plot_speed_trace(selected, lap_data, lap_times, best_lap, sectors), "speed.png")
    imgs["delta"]   = save_fig(plot_delta_time(selected, lap_data, lap_times, best_lap, sectors), "delta.png")
    imgs["gg"]      = save_fig(plot_gg(selected, lap_data, lap_times, best_lap), "gg.png")
    imgs["line"]    = save_fig(plot_racing_line(selected, lap_data, df, lat_col, lon_col, best_lap, lap_times), "line.png")
    imgs["brake"]   = save_fig(plot_brake_map(selected, lap_data, df, lat_col, lon_col, best_lap), "brake.png")
    imgs["corner"]  = save_fig(plot_corner_analysis(best_lap, lap_data, lap_times), "corner.png")
    imgs["consist"] = save_fig(plot_lap_consistency(selected, lap_times, best_lap), "consist.png")
    imgs["sector"]  = save_fig(plot_sector_comparison(selected, lap_data, lap_times, best_lap), "sector.png")

    tb   = theoretical_best(df, lap_data, lap_times)
    gain = lap_times[best_lap] - tb
    std  = float(pd.Series([lap_times[l] for l in selected]).std())
    ai_data = {
        "best_lap_time": lap_times[best_lap], "total_laps": len(selected),
        "theoretical_best": tb, "lap_std": std,
        "max_speed":  float(lap_data[best_lap]["speed_kmh"].max()) if "speed_kmh" in lap_data[best_lap] else 0,
        "min_speed":  float(lap_data[best_lap]["speed_kmh"].min()) if "speed_kmh" in lap_data[best_lap] else 0,
        "avg_speed":  float(lap_data[best_lap]["speed_kmh"].mean()) if "speed_kmh" in lap_data[best_lap] else 0,
        "max_lat_g":  float(lap_data[best_lap]["lat_g"].abs().max()) if "lat_g" in lap_data[best_lap] else 0,
        "max_lon_g":  float(lap_data[best_lap]["long_g"].max()) if "long_g" in lap_data[best_lap] else 0,
        "max_brake_g":float(lap_data[best_lap]["long_g"].min()) if "long_g" in lap_data[best_lap] else 0,
    }
    comments = generate_ai_comment(ai_data)

    PW, PH = A4
    LM = RM = 18 * mm
    W   = PW - LM - RM
    fn  = "Helvetica"

    C_ACCENT = rl_colors.HexColor("#00E5FF")
    C_GOLD   = rl_colors.HexColor("#FFD700")
    C_WARN   = rl_colors.HexColor("#FF6B35")
    C_GOOD   = rl_colors.HexColor("#39FF8A")
    C_TEXT   = rl_colors.HexColor("#E8EEF8")
    C_SUB    = rl_colors.HexColor("#8B9EC0")
    C_PANEL  = rl_colors.HexColor("#0F1421")
    C_BORDER = rl_colors.HexColor("#1E2840")
    C_BG     = rl_colors.HexColor("#0A0E1A")

    def S(name, **kw):
        return ParagraphStyle(name, fontName=fn, **kw)

    def mkp(txt, c=None):
        return Paragraph(str(txt), S(f"p{id(txt)}", fontSize=9, textColor=c or C_SUB))

    def sec_hdr(text):
        tbl = Table([["", Paragraph(f"◆  {text}", S("sh", fontSize=10, textColor=C_TEXT, leading=18, leftIndent=4))]], colWidths=[3, W - 3])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), rl_colors.HexColor("#141720")),
            ("BACKGROUND", (0, 0), (0, -1), C_ACCENT),
            ("LINEBELOW",  (0, 0), (-1, -1), 1.5, C_ACCENT),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return tbl

    def ai_block(text):
        tbl = Table([[Paragraph(text, S("ai", fontSize=9, textColor=rl_colors.HexColor("#B0C8E8"), leading=15, leftIndent=10))]], colWidths=[W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), rl_colors.HexColor("#0C1830")),
            ("LINERIGHT",    (0, 0), (0, -1), 3, C_ACCENT),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        return tbl

    E   = []
    now = datetime.datetime.now().strftime("%Y.%m.%d  %H:%M")
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=LM, rightMargin=RM,
                            topMargin=28 * mm, bottomMargin=20 * mm)

    kpi = [
        ("BEST LAP",    fmt_time(lap_times[best_lap]), C_ACCENT),
        ("THEORY BEST", fmt_time(tb),                  C_GOLD),
        ("GAIN",        f"{gain:.3f}s",                C_WARN if gain > 2 else C_GOOD),
        ("LAP STD",     f"{std:.3f}s",                 C_GOOD if std < 1.5 else C_WARN),
        ("TOTAL LAPS",  str(len(selected)),             C_SUB),
    ]
    n  = len(kpi); cw = W / n
    kpi_cells = [[Table([[Paragraph(str(v), S(f"kv{i}", fontSize=14, textColor=c, leading=18))],
                          [Paragraph(lb, S(f"kl{i}", fontSize=6, textColor=C_SUB))]],
                         colWidths=[cw - 6]) for i, (lb, v, c) in enumerate(kpi)]]
    kpi_tbl = Table(kpi_cells, colWidths=[cw] * n, rowHeights=[44])
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_PANEL),
        ("GRID",       (0, 0), (-1, -1), 0.5, C_BORDER),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))

    E.append(Paragraph("TELEMETRY ANALYSIS REPORT", S("tt", fontSize=18, textColor=C_ACCENT, spaceAfter=4)))
    E.append(Paragraph(f"{course_name}  |  {driver_name}  |  {car_name}  |  {weather}  |  {now}",
                       S("sub", fontSize=8, textColor=C_SUB, spaceAfter=8)))
    E.append(kpi_tbl); E.append(Spacer(1, 8))
    E.append(ai_block(comments["summary"])); E.append(Spacer(1, 10))

    laps_s  = sorted(selected, key=lambda l: lap_times[l])
    hdr     = [mkp(h, C_TEXT) for h in ["Lap", "Time", "Gap to Best", "Rank"]]
    rows_l  = [hdr]
    for rank, lap in enumerate(laps_s, 1):
        t  = lap_times[lap]; gb = t - lap_times[best_lap]
        c  = C_ACCENT if lap == best_lap else C_SUB
        rows_l.append([mkp(f"Lap {lap}", c), mkp(fmt_time(t), c),
                        mkp("—" if gb < 0.001 else f"+{gb:.3f}", c),
                        mkp("★ BEST" if lap == best_lap else f"P{rank}", c)])
    lt = Table(rows_l, colWidths=[40 * mm, 50 * mm, 50 * mm, 34 * mm])
    lt.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), rl_colors.HexColor("#0C1830")),
        ("LINEBELOW",     (0, 0), (-1, 0), 1.5, C_ACCENT),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_PANEL, rl_colors.HexColor("#0C1020")]),
        ("GRID",          (0, 0), (-1, -1), 0.3, C_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    E.append(sec_hdr("LAP TIME RESULTS")); E.append(Spacer(1, 4))
    E.append(lt); E.append(Spacer(1, 10))

    for title, img_key, comment_key, h_ratio in [
        ("SPEED TRACE",           "speed",   "speed",  9/16),
        ("DELTA TIME",            "delta",   "delta",  5/16),
        ("LAP CONSISTENCY",       "consist", "",       5/16),
        ("RACING LINE & HEATMAP", "line",    "line",   6/16),
        ("BRAKING ANALYSIS",      "brake",   "brake",  6/16),
        ("CORNER SPEED",          "corner",  "corner", 5/16),
        ("SECTOR COMPARISON",     "sector",  "",       5/16),
    ]:
        E.append(sec_hdr(title)); E.append(Spacer(1, 4))
        if img_key in imgs and os.path.exists(imgs[img_key]):
            E.append(Image(imgs[img_key], width=W, height=W * h_ratio))
        if comment_key and comments.get(comment_key):
            E.append(Spacer(1, 3)); E.append(ai_block(comments[comment_key]))
        E.append(Spacer(1, 10))

    if "gg" in imgs and os.path.exists(imgs["gg"]):
        E.append(sec_hdr("G-G DIAGRAM")); E.append(Spacer(1, 4))
        E.append(Image(imgs["gg"], width=W * 0.5, height=W * 0.5))
        E.append(Spacer(1, 10))

    E.append(sec_hdr("AI IMPROVEMENT SUGGESTIONS")); E.append(Spacer(1, 6))
    for s in comments.get("suggestions", []):
        tbl = Table([[Paragraph(s, S("sg", fontSize=9, textColor=rl_colors.HexColor("#FFB8A0"), leading=15, leftIndent=10))]], colWidths=[W])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), rl_colors.HexColor("#1A0E0A")),
            ("LINERIGHT",  (0, 0), (0, -1), 3, C_WARN),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        E.append(tbl); E.append(Spacer(1, 3))

    doc.build(E)
    print(f"[OK] PDF生成完了: {output_path}")
    return output_path
