"""
engine/plots.py  ─  全プロット関数（ウェブ用）
================================================
main.py から plot_* 関数を抜き出し、
  ・plt.show() を削除
  ・messagebox を例外/print に変更
  ・matplotlib.use("Agg") 使用
  ・全関数が fig を return する
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from engine.analyzer import resample_lap, fmt_time, theoretical_best, make_sectors

RESAMPLE_PTS = 2000
BRAKE_THR    = -0.2

COLORS_LAP = [
    '#FF4E4E','#4E9FFF','#4EFF9F','#FFD24E','#FF4EE0',
    '#4EFFF0','#FF884E','#A44EFF','#B8FF4E','#FF4E88',
    '#4EC8FF','#FFEE4E','#FF6B4E','#4EFFB8','#884EFF',
    '#FF4EC0','#4EFFD4','#FFB84E','#4E7FFF','#D4FF4E',
]
COLOR_BEST    = '#00E5FF'
COLOR_WARN    = '#FF6B35'
COLOR_GOOD    = '#39FF8A'
COLOR_NEUTRAL = '#8B9EC0'

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


# ============================================================
# 基本解析グラフ
# ============================================================

def plot_speed_trace(selected, lap_data, lap_times, best_lap, sectors=None):
    if sectors is None:
        sectors = make_sectors(lap_data, best_lap)
    fig, axes = plt.subplots(3, 1, figsize=(14, 10),
                             gridspec_kw={"height_ratios": [3, 1, 1], "hspace": 0.04})
    ax_s, ax_lg, ax_latg = axes
    for idx, lap in enumerate(sorted(selected, key=lambda l: lap_times[l])):
        ld = lap_data[lap].copy()
        ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
        ld = ld.sort_values("ld")
        c  = COLOR_BEST if lap == best_lap else COLORS_LAP[idx % len(COLORS_LAP)]
        lw = 2.5 if lap == best_lap else 1.0
        al = 1.0 if lap == best_lap else 0.6
        lb = f"Lap {lap}  {fmt_time(lap_times[lap])}" + (" ★" if lap == best_lap else "")
        if "speed_kmh" in ld.columns:
            ax_s.plot(ld["ld"], ld["speed_kmh"], color=c, lw=lw, alpha=al, label=lb,
                      zorder=5 + (lap == best_lap))
        if "long_g" in ld.columns:
            ax_lg.plot(ld["ld"], ld["long_g"], color=c, lw=lw * 0.7, alpha=al)
        if "lat_g" in ld.columns:
            ax_latg.plot(ld["ld"], ld["lat_g"], color=c, lw=lw * 0.7, alpha=al)
    for ax in axes:
        ax.grid(True, color="#1A2035", lw=0.5)
        ax.spines[:].set_color("#1E2840")
    for sec_name, (ss, _) in sectors.items():
        for ax in axes:
            ax.axvline(ss, color="#FFD700", lw=1, ls="--", alpha=0.6)
        ylim = ax_s.get_ylim()
        ax_s.text(ss + 5, ylim[1] * 0.97, sec_name, color="#FFD700", fontsize=8,
                  fontweight="bold", bbox=dict(fc="#0A0E1A", ec="#FFD700", lw=0.6, pad=2))
    ax_s.set_ylabel("Speed (km/h)")
    ax_s.legend(fontsize=7, ncol=min(4, len(selected)), loc="upper right")
    ax_s.set_title("SPEED TRACE", fontweight="bold")
    ax_s.tick_params(labelbottom=False)
    ax_lg.set_ylabel("Long G"); ax_lg.axhline(0, color="#2A3A5A", lw=0.8)
    ax_lg.tick_params(labelbottom=False)
    ax_latg.set_ylabel("Lat G"); ax_latg.axhline(0, color="#2A3A5A", lw=0.8)
    ax_latg.set_xlabel("Distance (m)")
    plt.tight_layout()
    return fig


def plot_delta_time(selected, lap_data, lap_times, best_lap, sectors=None):
    if len(selected) < 2:
        raise ValueError("2ラップ以上選択してください")
    if sectors is None:
        sectors = make_sectors(lap_data, best_lap)
    base_res = resample_lap(lap_data[best_lap])
    fig, ax  = plt.subplots(figsize=(14, 5))
    for idx, lap in enumerate([l for l in selected if l != best_lap]):
        c   = COLORS_LAP[idx % len(COLORS_LAP)]
        res = resample_lap(lap_data[lap])
        ml  = min(len(base_res), len(res))
        delta = res["time"].values[:ml] - base_res["time"].values[:ml]
        diff  = lap_times[lap] - lap_times[best_lap]
        ax.plot(res["dist"].values[:ml], delta, color=c, lw=1.5,
                label=f"Lap {lap}  ({'+' if diff >= 0 else ''}{diff:.3f}s)")
        ax.fill_between(res["dist"].values[:ml], delta, 0,
                        where=delta > 0, color="#FF4E4E", alpha=0.08)
        ax.fill_between(res["dist"].values[:ml], delta, 0,
                        where=delta < 0, color="#4EFF9F", alpha=0.08)
    ax.axhline(0, color=COLOR_BEST, lw=1.5, ls="--")
    for sn, (ss, _) in sectors.items():
        ax.axvline(ss, color="#FFD700", lw=0.8, ls=":", alpha=0.5)
    ax.set_title(f"DELTA TIME  Base: Lap {best_lap} ★  {fmt_time(lap_times[best_lap])}", fontweight="bold")
    ax.set_xlabel("Distance (m)"); ax.set_ylabel("Delta (s)\n(+slow / -fast)")
    ax.legend(fontsize=8); ax.grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


def plot_gg(selected, lap_data, lap_times, best_lap):
    fig, ax = plt.subplots(figsize=(7, 7))
    for idx, lap in enumerate(selected):
        ld = lap_data[lap]
        if "lat_g" not in ld.columns or "long_g" not in ld.columns:
            continue
        c  = COLOR_BEST if lap == best_lap else COLORS_LAP[idx % len(COLORS_LAP)]
        s  = 12 if lap == best_lap else 4
        al = 0.9 if lap == best_lap else 0.25
        ax.scatter(ld["lat_g"], ld["long_g"], s=s, color=c, alpha=al,
                   label=f"Lap {lap}{'★' if lap == best_lap else ''}", linewidths=0)
    for r in [0.5, 1.0, 1.5, 2.0, 2.5]:
        th = np.linspace(0, 2 * np.pi, 300)
        ax.plot(r * np.cos(th), r * np.sin(th), color="#1E2840", lw=0.8, ls="--")
        ax.text(r * 0.707 + 0.02, r * 0.707 + 0.02, f"{r}g", color="#3A4A6A", fontsize=7)
    ax.axhline(0, color="#2A3A5A", lw=0.8); ax.axvline(0, color="#2A3A5A", lw=0.8)
    ax.set_xlim(-3.5, 3.5); ax.set_ylim(-3, 2)
    ax.set_xlabel("Lateral G"); ax.set_ylabel("Longitudinal G")
    ax.set_title("G-G DIAGRAM", fontweight="bold")
    ax.legend(fontsize=8)
    plt.tight_layout()
    return fig


def plot_brake_map(selected, lap_data, df, lat_col, lon_col, best_lap):
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax in axes:
        ax.set_facecolor("#080C14"); ax.axis("off")
    ax1, ax2 = axes
    df_base  = lap_data[best_lap]
    ax1.plot(df[lon_col], df[lat_col], color="#0D1520", lw=8, alpha=0.4)
    for idx, lap in enumerate(selected):
        ld  = lap_data[lap]
        brk = ld[ld["brake"] == True] if "brake" in ld.columns else ld.head(0)
        c   = COLOR_BEST if lap == best_lap else COLORS_LAP[idx % len(COLORS_LAP)]
        ax1.scatter(brk[lon_col], brk[lat_col],
                    s=20 if lap == best_lap else 12,
                    color=c, alpha=0.85 if lap == best_lap else 0.6,
                    label=f"Lap {lap}{'★' if lap == best_lap else ''}", linewidths=0)
    ax1.set_aspect("equal"); ax1.set_title("BRAKE POINTS", color="white", fontweight="bold")
    ax1.legend(fontsize=7, facecolor="#0F1421", labelcolor="white")
    ax2.plot(df[lon_col], df[lat_col], color="#0D1520", lw=8, alpha=0.4)
    if "long_g" in df_base.columns:
        bd = df_base[df_base["long_g"] < -0.05]
        if len(bd):
            sc = ax2.scatter(bd[lon_col], bd[lat_col], c=-bd["long_g"],
                             cmap="RdYlBu_r", s=10, alpha=0.9, vmin=0, vmax=2.5, linewidths=0)
            cb = plt.colorbar(sc, ax=ax2, pad=0.02, fraction=0.03)
            cb.set_label("Brake G", color=COLOR_NEUTRAL)
    ax2.set_aspect("equal")
    ax2.set_title(f"BRAKE INTENSITY  Lap {best_lap}★", color="white", fontweight="bold")
    plt.tight_layout()
    return fig


def plot_corner_analysis(best_lap, lap_data, lap_times):
    ld   = lap_data[best_lap]
    latg = ld["lat_g"].abs().rolling(5).mean() if "lat_g" in ld.columns else pd.Series(0, index=ld.index)
    in_c = False; data = []; c_num = 0
    for i in range(len(latg)):
        if latg.iloc[i] > 0.25 and not in_c:
            cs = i; in_c = True
        elif latg.iloc[i] < 0.2 and in_c:
            in_c = False
            sec = ld.iloc[cs:i]
            if len(sec) > 5:
                c_num += 1
                data.append({
                    "num":   c_num,
                    "entry": float(sec["speed_kmh"].iloc[0]) if "speed_kmh" in sec.columns else 0,
                    "min":   float(sec["speed_kmh"].min())   if "speed_kmh" in sec.columns else 0,
                    "exit":  float(sec["speed_kmh"].iloc[-1]) if "speed_kmh" in sec.columns else 0,
                })
    if not data:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.text(0.5, 0.5, "コーナーを検出できませんでした", ha="center", va="center",
                transform=ax.transAxes, color=COLOR_NEUTRAL)
        return fig
    fig, ax = plt.subplots(figsize=(max(10, len(data) * 1.5), 5))
    x = np.arange(len(data)); w = 0.25
    ax.bar(x - w, [d["entry"] for d in data], w, label="Entry",   color="#4E9FFF", alpha=0.85)
    ax.bar(x,     [d["min"]   for d in data], w, label="Minimum", color="#FF4E4E", alpha=0.85)
    ax.bar(x + w, [d["exit"]  for d in data], w, label="Exit",    color="#4EFF9F", alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels([f"C{d['num']}" for d in data])
    ax.set_ylabel("Speed (km/h)")
    ax.set_title(f"CORNER SPEED  Lap {best_lap}★", fontweight="bold")
    ax.legend(); ax.grid(True, color="#1A2035", axis="y", lw=0.5)
    plt.tight_layout()
    return fig


def plot_sector_comparison(selected, lap_data, lap_times, best_lap, n=6):
    fig, ax  = plt.subplots(figsize=(14, 5))
    laps_s   = sorted(selected, key=lambda l: lap_times[l])
    x        = np.arange(n)
    for li, lap in enumerate(laps_s):
        ld = lap_data[lap].copy()
        ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
        length = ld["ld"].max()
        if length == 0: continue
        c  = COLOR_BEST if lap == best_lap else COLORS_LAP[li % len(COLORS_LAP)]
        ts = []
        for si in range(n):
            sec = ld[(ld["ld"] >= si * length / n) & (ld["ld"] < (si + 1) * length / n)]
            t   = (sec["time_sec"].max() - sec["time_sec"].min()) if len(sec) > 3 else 0
            ts.append(t)
        offset = (li - len(laps_s) / 2 + 0.5) * (0.7 / len(laps_s))
        ax.bar(x + offset, ts, 0.65 / len(laps_s), color=c, alpha=0.85,
               label=f"Lap {lap}{'★' if lap == best_lap else ''}")
    ax.set_xticks(x); ax.set_xticklabels([f"S{i+1}" for i in range(n)])
    ax.set_ylabel("Sector Time (s)"); ax.set_title("SECTOR COMPARISON", fontweight="bold")
    ax.legend(fontsize=8); ax.grid(True, color="#1A2035", axis="y", lw=0.5)
    plt.tight_layout()
    return fig


def plot_lap_consistency(selected, lap_times, best_lap):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    laps_s    = sorted(selected, key=lambda l: lap_times[l])
    times_s   = [lap_times[l] for l in laps_s]
    best_t    = min(times_s)
    colors_b  = [COLOR_BEST if t == best_t else (COLOR_WARN if t - best_t > 2 else COLOR_NEUTRAL)
                 for t in times_s]
    axes[0].bar(range(len(laps_s)), times_s, color=colors_b, alpha=0.85)
    axes[0].axhline(best_t, color="#FFD700", lw=1.5, ls="--", label=f"Best {fmt_time(best_t)}")
    axes[0].set_xticks(range(len(laps_s)))
    axes[0].set_xticklabels([f"L{l}" for l in laps_s])
    axes[0].set_ylabel("Lap Time (s)"); axes[0].set_title("LAP TIME BREAKDOWN", fontweight="bold")
    axes[0].legend(fontsize=8); axes[0].grid(True, color="#1A2035", axis="y", lw=0.5)
    for i, (l, t) in enumerate(zip(laps_s, times_s)):
        diff = t - best_t
        axes[0].text(i, t + 0.1, "BEST" if diff == 0 else f"+{diff:.2f}",
                     ha="center", fontsize=7,
                     color="#FFD700" if diff == 0 else COLOR_NEUTRAL)
    laps_all  = sorted(lap_times.keys())
    times_all = [lap_times[l] for l in laps_all]
    axes[1].plot(range(len(laps_all)), times_all, "o-", color=COLOR_NEUTRAL, lw=1.5, ms=6)
    axes[1].scatter([times_all.index(min(times_all))], [min(times_all)],
                    s=80, color=COLOR_BEST, zorder=10)
    if len(times_all) >= 3:
        roll = pd.Series(times_all).rolling(3, center=True).mean()
        axes[1].plot(range(len(laps_all)), roll, color="#FFD700", lw=1.5,
                     ls="--", label="Rolling avg(3)")
    axes[1].set_xticks(range(len(laps_all)))
    axes[1].set_xticklabels([f"L{l}" for l in laps_all])
    axes[1].set_ylabel("Lap Time (s)"); axes[1].set_title("LAP TIME TREND", fontweight="bold")
    axes[1].legend(fontsize=8); axes[1].grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


def plot_racing_line(selected, lap_data, df, lat_col, lon_col, best_lap, lap_times):
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax in axes:
        ax.set_facecolor("#080C14"); ax.axis("off")
    ax1, ax2 = axes
    ax1.plot(df[lon_col], df[lat_col], color="#0D1520", lw=10, alpha=0.4)
    for idx, lap in enumerate(sorted(selected, key=lambda l: lap_times[l])):
        ld = lap_data[lap]
        c  = COLOR_BEST if lap == best_lap else COLORS_LAP[idx % len(COLORS_LAP)]
        lw = 2.5 if lap == best_lap else 1.0
        ax1.plot(ld[lon_col], ld[lat_col], color=c, lw=lw,
                 alpha=0.8 if lap == best_lap else 0.5,
                 label=f"Lap {lap}{'★' if lap == best_lap else ''}  {fmt_time(lap_times[lap])}")
    ax1.set_aspect("equal"); ax1.set_title("RACING LINE OVERLAY", color="white", fontweight="bold")
    ax1.legend(fontsize=7, facecolor="#0F1421", labelcolor="white", ncol=2)
    ax2.plot(df[lon_col], df[lat_col], color="#0D1520", lw=10, alpha=0.4)
    ld_b = lap_data[best_lap]
    if "speed_kmh" in ld_b.columns:
        sc = ax2.scatter(ld_b[lon_col], ld_b[lat_col], c=ld_b["speed_kmh"],
                         cmap="turbo", s=8, alpha=0.9, linewidths=0)
        cb = plt.colorbar(sc, ax=ax2, pad=0.02, fraction=0.03)
        cb.set_label("Speed (km/h)", color=COLOR_NEUTRAL)
    ax2.set_aspect("equal")
    ax2.set_title(f"SPEED HEATMAP  Lap {best_lap}★", color="white", fontweight="bold")
    plt.tight_layout()
    return fig


def plot_speed_heatmap(df, best_lap, lap_data, lat_col, lon_col):
    ld  = lap_data[best_lap]
    fig, ax = plt.subplots(figsize=(8, 7))
    ax.set_facecolor("#080C14"); ax.axis("off")
    if "speed_kmh" in ld.columns:
        sc = ax.scatter(ld[lon_col], ld[lat_col], c=ld["speed_kmh"],
                        cmap="turbo", s=10, alpha=0.9, linewidths=0)
        plt.colorbar(sc, ax=ax, label="Speed (km/h)")
    ax.set_aspect("equal")
    ax.set_title(f"SPEED HEATMAP  Lap {best_lap}★", color="white", fontweight="bold")
    plt.tight_layout()
    return fig


def plot_gps_track(df, lat_col, lon_col, lap_data, lap_times):
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.set_facecolor("#080C14"); ax.axis("off")
    spd = df["speed_kmh"].fillna(0) if "speed_kmh" in df.columns else pd.Series(0, index=df.index)
    sc  = ax.scatter(df[lon_col], df[lat_col], c=spd, cmap="RdYlGn", s=1.5, alpha=0.7)
    plt.colorbar(sc, ax=ax, label="Speed (km/h)")
    ax.set_aspect("equal")
    ax.set_title("GPS TRACK MAP (全データ)", color="white", fontweight="bold")
    plt.tight_layout()
    return fig


def plot_all_speed(lap_data, lap_times, df_all, lat_col, lon_col):
    fig, ax = plt.subplots(figsize=(12, 6))
    for lap in sorted(lap_times.keys()):
        ld = lap_data[lap].copy()
        ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
        if "speed_kmh" in ld.columns:
            ax.plot(ld["ld"], ld["speed_kmh"], alpha=0.3, lw=0.8)
    ax.set_xlabel("Distance (m)"); ax.set_ylabel("Speed (km/h)")
    ax.set_title("ALL LAP SPEED OVERVIEW", fontweight="bold")
    ax.grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


# ============================================================
# AI 理想分析
# ============================================================

def plot_ideal_speed(lap_data, lap_times, best_lap):
    POINTS   = 2000
    profiles = []
    for lap in lap_times:
        res = resample_lap(lap_data[lap], POINTS)
        if len(res) == POINTS:
            profiles.append(res["speed"].values)
    if not profiles:
        raise ValueError("データ不足")
    profiles = np.array(profiles)
    ideal    = profiles.max(axis=0)
    best_spd = resample_lap(lap_data[best_lap], POINTS)["speed"].values
    dist_arr = resample_lap(lap_data[best_lap], POINTS)["dist"].values

    fig, axes = plt.subplots(2, 1, figsize=(14, 8),
                             gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05})
    ax_s, ax_d = axes
    for p in profiles:
        ax_s.plot(dist_arr, p, color="#334455", lw=0.5, alpha=0.4)
    ax_s.plot(dist_arr, best_spd, color=COLOR_BEST, lw=2,
              label=f"Best Lap {best_lap}  {fmt_time(lap_times[best_lap])}", zorder=5)
    ax_s.plot(dist_arr, ideal, color="#FFD700", lw=2.5, ls="--",
              label="理想速度プロファイル（区間ベスト合成）", zorder=6)
    ax_s.fill_between(dist_arr, best_spd, ideal,
                      where=ideal > best_spd, color="#FFD700", alpha=0.12, label="改善余地")
    ax_s.set_ylabel("Speed (km/h)"); ax_s.set_title("理想速度プロファイル  IDEAL SPEED PROFILE", fontweight="bold")
    ax_s.legend(fontsize=8); ax_s.grid(True, color="#1A2035", lw=0.5)
    ax_s.tick_params(labelbottom=False)
    diff = ideal - best_spd
    ax_d.fill_between(dist_arr, diff, 0, where=diff > 0, color="#FFD700", alpha=0.6, label="速度改善余地")
    ax_d.fill_between(dist_arr, diff, 0, where=diff <= 0, color=COLOR_GOOD, alpha=0.4, label="ベスト超え区間")
    ax_d.axhline(0, color="#aaaaaa", lw=0.8)
    ax_d.set_ylabel("Speed Diff (km/h)"); ax_d.set_xlabel("Distance (m)")
    ax_d.legend(fontsize=7); ax_d.grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


def plot_ideal_line(lap_data, lap_times, best_lap, lat_col, lon_col, df):
    POINTS = 2000
    fig, axes = plt.subplots(1, 2, figsize=(15, 7))
    for ax in axes:
        ax.set_facecolor("#080C14"); ax.axis("off")
    ax1, ax2 = axes
    ax1.plot(df[lon_col], df[lat_col], color="#0D1520", lw=10, alpha=0.5)
    ax2.plot(df[lon_col], df[lat_col], color="#0D1520", lw=10, alpha=0.5)
    for i, lap in enumerate(sorted(lap_times.keys())):
        ld = lap_data[lap]
        ax1.plot(ld[lon_col], ld[lat_col], color=COLORS_LAP[i % len(COLORS_LAP)], lw=0.8, alpha=0.3)
    bl = lap_data[best_lap]
    ax1.plot(bl[lon_col], bl[lat_col], color=COLOR_BEST, lw=2.5, label=f"Best Lap {best_lap}", zorder=10)
    all_res = {}
    for lap in lap_times:
        ld = lap_data[lap].copy()
        ld["ld"] = ld["dist_m"] - ld["dist_m"].min()
        length = ld["ld"].max()
        if length == 0: continue
        nd    = np.linspace(0, length, POINTS)
        lat_i = np.interp(nd, ld["ld"], ld[lat_col])
        lon_i = np.interp(nd, ld["ld"], ld[lon_col])
        g_i   = np.interp(nd, ld["ld"],
                           ld["lat_g"].abs() if "lat_g" in ld.columns else np.zeros(len(ld)))
        all_res[lap] = {"lat": lat_i, "lon": lon_i, "g": g_i}
    if all_res:
        i_lat  = np.zeros(POINTS); i_lon = np.zeros(POINTS)
        best_g = np.full(POINTS, -999.0)
        for lap, res in all_res.items():
            mask = res["g"] > best_g
            i_lat[mask] = res["lat"][mask]
            i_lon[mask] = res["lon"][mask]
            best_g[mask] = res["g"][mask]
        ax1.plot(i_lon, i_lat, color="#FFD700", lw=1.5, ls="--",
                 label="理想ライン（区間Gベスト合成）", zorder=11, alpha=0.85)
    ax1.set_aspect("equal")
    ax1.set_title("理想ライン  IDEAL RACING LINE", color="white", fontweight="bold")
    ax1.legend(fontsize=8, facecolor="#0F1421", labelcolor="white")
    if "speed_kmh" in bl.columns:
        sc = ax2.scatter(bl[lon_col], bl[lat_col], c=bl["speed_kmh"],
                         cmap="turbo", s=8, alpha=0.9, linewidths=0)
        cb = plt.colorbar(sc, ax=ax2, pad=0.02, fraction=0.03)
        cb.set_label("Speed (km/h)", color=COLOR_NEUTRAL)
    ax2.set_aspect("equal")
    ax2.set_title(f"Speed Heatmap  Lap {best_lap}★", color="white", fontweight="bold")
    plt.tight_layout()
    return fig


def get_ideal_pit_data(lap_data, lap_times, best_lap):
    """理想ピット戦略をJSONで返す（+グラフも生成）"""
    laps  = sorted(lap_times.keys())
    times = [lap_times[l] for l in laps]
    n     = len(laps)
    if n < 3:
        return {"error": "ラップ数が少なすぎます（3ラップ以上必要）"}

    x      = np.arange(n)
    thresh = np.percentile(times, 90)
    mask   = np.array(times) < thresh
    if mask.sum() < 3:
        mask = np.ones(n, dtype=bool)
    coef   = np.polyfit(x[mask], np.array(times)[mask], deg=2)
    fitted = np.polyval(coef, x)
    base   = fitted[0]
    deg_threshold  = 1.5
    optimal_stint  = next((i for i in range(1, n) if fitted[i] - base > deg_threshold), n)
    total_laps     = n
    pit_laps       = [optimal_stint * (i + 1) for i in range(total_laps // max(optimal_stint, 1))
                      if optimal_stint * (i + 1) < total_laps]

    return {
        "optimal_stint":   optimal_stint,
        "pit_laps":        pit_laps,
        "degradation_rate": round(float(coef[1]), 4),
        "base_time":       round(float(base), 3),
        "base_time_fmt":   fmt_time(float(base)),
        "total_laps":      total_laps,
        "message": (f"最適スティント長: {optimal_stint}ラップ  "
                    f"推奨ピット: {', '.join(f'Lap {l}' for l in pit_laps) or 'なし'}")
    }


def get_ai_advice_data(lap_data, lap_times, best_lap, df):
    """AIアドバイスをJSONで返す"""
    from engine.analyzer import theoretical_best, generate_ai_comment
    laps  = sorted(lap_times.keys())
    times = [lap_times[l] for l in laps]
    tb    = theoretical_best(df, lap_data, lap_times)
    std   = float(pd.Series(times).std()) if len(times) > 1 else 0
    ld    = lap_data[best_lap]

    ai_data = {
        "best_lap_time":    lap_times[best_lap],
        "total_laps":       len(laps),
        "theoretical_best": tb,
        "lap_std":          std,
        "max_speed":  float(ld["speed_kmh"].max()) if "speed_kmh" in ld.columns else 0,
        "min_speed":  float(ld["speed_kmh"].min()) if "speed_kmh" in ld.columns else 0,
        "avg_speed":  float(ld["speed_kmh"].mean()) if "speed_kmh" in ld.columns else 0,
        "max_lat_g":  float(ld["lat_g"].abs().max()) if "lat_g" in ld.columns else 0,
        "max_lon_g":  float(ld["long_g"].max()) if "long_g" in ld.columns else 0,
        "max_brake_g":float(ld["long_g"].min()) if "long_g" in ld.columns else 0,
    }
    comments = generate_ai_comment(ai_data)

    # アドバイスリストに整形
    advices = []
    if comments.get("summary"):
        advices.append(["📊 総評", comments["summary"]])
    for s in comments.get("suggestions", []):
        advices.append(["💡 改善提案", s])

    return {"advices": advices, "raw": comments}


# ============================================================
# 機械学習 AI グラフ
# ============================================================

def plot_tire_degradation(tire_model, lap_times):
    """タイヤ劣化曲線グラフ"""
    laps  = sorted(lap_times.keys())
    times = [lap_times[l] for l in laps]
    n     = len(laps)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.scatter(range(1, n + 1), times, color=COLOR_NEUTRAL, s=40, zorder=5, label="実測ラップタイム")

    if tire_model.trained and tire_model.coef is not None:
        x_fit  = np.linspace(0, n - 1, 100)
        y_fit  = np.polyval(tire_model.coef, x_fit)
        ax.plot(x_fit + 1, y_fit, color=COLOR_WARN, lw=2, ls="--", label="劣化トレンド")
        if tire_model.base_time:
            ax.axhline(tire_model.base_time + 1.5, color="#FF4444", lw=1.5, ls=":",
                       label="交換推奨ライン (+1.5s)")
        if tire_model.optimal_stint:
            ax.axvline(tire_model.optimal_stint, color="#FFD700", lw=2,
                       label=f"最適スティント: {tire_model.optimal_stint}ラップ")
        for al in tire_model.anomaly_laps:
            if al in laps:
                idx = laps.index(al)
                ax.scatter([idx + 1], [times[idx]], color="#FF4444", s=100, zorder=10,
                           marker="X", label=f"異常ラップ: {al}")

    ax.set_xlabel("Lap"); ax.set_ylabel("Lap Time (s)")
    ax.set_title("タイヤ劣化 AI  TIRE DEGRADATION MODEL", fontweight="bold")
    ax.legend(fontsize=8); ax.grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


def plot_ai_ideal_line(engine, lap_data, lap_times, lat_col, lon_col):
    """AI理想ライン合成グラフ"""
    try:
        result = engine.build_ideal_line(lap_data, lap_times, lat_col, lon_col)
        if result is None:
            raise ValueError("理想ライン生成に失敗しました")
        ideal_lat, ideal_lon, score_map, dist_out = result
    except Exception as e:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, f"AI理想ライン生成エラー:\n{str(e)}", ha="center", va="center",
                transform=ax.transAxes, color=COLOR_NEUTRAL, fontsize=10)
        return fig

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    for ax in axes:
        ax.set_facecolor("#080C14"); ax.axis("off")
    ax1, ax2 = axes

    # 全ラップ背景
    for i, lap in enumerate(sorted(lap_times.keys())):
        ld = lap_data[lap]
        ax1.plot(ld[lon_col], ld[lat_col], color=COLORS_LAP[i % len(COLORS_LAP)], lw=0.5, alpha=0.25)

    # AI理想ライン
    sc = ax1.scatter(ideal_lon, ideal_lat, c=score_map, cmap="plasma",
                     s=3, alpha=0.9, linewidths=0)
    plt.colorbar(sc, ax=ax1, label="Speed Score", fraction=0.03)
    ax1.set_aspect("equal")
    ax1.set_title("AI 理想ライン合成  AI IDEAL LINE", color="white", fontweight="bold")

    # スコアマップ
    ax2.plot(dist_out, score_map, color=COLOR_BEST, lw=1.5)
    ax2.fill_between(dist_out, score_map, alpha=0.3, color=COLOR_BEST)
    ax2.set_xlabel("Distance (m)"); ax2.set_ylabel("Speed Score")
    ax2.set_title("コーナー区間スコア", color="white", fontweight="bold")
    ax2.set_facecolor("#0F1421")
    ax2.grid(True, color="#1A2035", lw=0.5)
    plt.tight_layout()
    return fig


def plot_cross_session_compare(db):
    """セッション間比較グラフ"""
    sessions = db.get("sessions", [])
    if not sessions:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "登録済みセッションがありません", ha="center", va="center",
                transform=ax.transAxes, color=COLOR_NEUTRAL, fontsize=12)
        return fig

    df_s = pd.DataFrame(sessions)
    df_s = df_s[df_s["best_lap"] > 0].sort_values("best_lap")

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for ax in axes:
        ax.set_facecolor("#0F1421")

    # ベストラップ棒グラフ
    n  = len(df_s)
    x  = np.arange(n)
    colors_b = [COLORS_LAP[i % len(COLORS_LAP)] for i in range(n)]
    axes[0].bar(x, df_s["best_lap"].values, color=colors_b, alpha=0.85)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(
        [f"{r.get('driver','?')[:6]}\n{r.get('date','?')[:5]}"
         for _, r in df_s.iterrows()], fontsize=7)
    axes[0].set_ylabel("Best Lap (s)")
    axes[0].set_title("セッション別ベストラップ比較", fontweight="bold")
    axes[0].grid(True, color="#1A2035", axis="y", lw=0.5)

    # ドライバー別ベスト
    if "driver" in df_s.columns:
        drv = df_s.groupby("driver")["best_lap"].min().sort_values()
        colors_d = [COLORS_LAP[i % len(COLORS_LAP)] for i in range(len(drv))]
        axes[1].barh(range(len(drv)), drv.values, color=colors_d, alpha=0.85)
        axes[1].set_yticks(range(len(drv)))
        axes[1].set_yticklabels(drv.index, fontsize=9)
        axes[1].set_xlabel("Best Lap (s)")
        axes[1].set_title("ドライバー別ベストラップ", fontweight="bold")
        axes[1].grid(True, color="#1A2035", axis="x", lw=0.5)

    plt.suptitle("セッション間クロス比較  CROSS SESSION COMPARISON",
                 color="white", fontsize=11, fontweight="bold")
    plt.tight_layout()
    return fig
