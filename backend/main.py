"""
backend/main.py  ─  FastAPI バックエンド
=========================================
全解析機能をREST APIとして提供する。
既存の解析ロジックをほぼそのまま流用し、
tkinterのGUI部分だけAPIエンドポイントに置き換える。
"""

import os, sys, io, uuid, json, pickle, asyncio
from pathlib import Path
from typing import Optional, List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # GUIなし（サーバー用）
import matplotlib.pyplot as plt

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# ── パス設定 ────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
DATA_DIR    = BASE_DIR / "data"
UPLOAD_DIR  = BASE_DIR / "uploads"
OUTPUT_DIR  = BASE_DIR / "outputs"
for d in [DATA_DIR, UPLOAD_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# 既存モジュールをパスに追加
sys.path.insert(0, str(BASE_DIR / "engine"))

app = FastAPI(title="耐久レース テレメトリー解析 Web API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── セッション管理（メモリ内キャッシュ）────────────────────────
# session_id → {df, lap_data, lap_times, best_lap, ...}
_sessions: dict = {}


def get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="セッションが見つかりません。CSVを再アップロードしてください。")
    return _sessions[session_id]


def fig_to_png(fig) -> bytes:
    """matplotlibのfigureをPNGバイト列に変換"""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def png_response(fig) -> StreamingResponse:
    return StreamingResponse(io.BytesIO(fig_to_png(fig)), media_type="image/png")


# ============================================================
# 1. CSV アップロード & 前処理
# ============================================================

@app.post("/api/upload")
async def upload_csv(file: UploadFile = File(...)):
    """
    CSVをアップロードして前処理・ラップ検出を実行。
    session_id を返す。以後の全APIはこのsession_idを使う。
    """
    from engine.analyzer import load_csv, auto_rename, preprocess
    from engine.lap_detector import detect_laps

    # 保存
    session_id = str(uuid.uuid4())[:8]
    save_path  = UPLOAD_DIR / f"{session_id}_{file.filename}"
    content    = await file.read()
    save_path.write_bytes(content)

    try:
        # 読み込み・前処理
        df = load_csv(str(save_path))
        df = auto_rename(df)
        df = preprocess(df)

        # ラップ検出
        df, lap_times = detect_laps(df)
        if not lap_times:
            raise HTTPException(status_code=422, detail="ラップを検出できませんでした。CSVを確認してください。")

        best_lap  = min(lap_times, key=lap_times.get)
        lap_data  = {l: df[df["lap"] == l].reset_index(drop=True) for l in lap_times}

        # セッション保存
        _sessions[session_id] = {
            "df":        df,
            "lap_data":  lap_data,
            "lap_times": lap_times,
            "best_lap":  best_lap,
            "lat_col":   "lat",
            "lon_col":   "lon",
            "csv_path":  str(save_path),
            "filename":  file.filename,
        }

        # ラップ一覧を返す
        laps_info = [
            {
                "lap":      l,
                "time_sec": round(lap_times[l], 3),
                "time_fmt": _fmt_time(lap_times[l]),
                "is_best":  l == best_lap,
            }
            for l in sorted(lap_times.keys())
        ]

        return {
            "session_id": session_id,
            "filename":   file.filename,
            "total_laps": len(lap_times),
            "best_lap":   best_lap,
            "best_time":  _fmt_time(lap_times[best_lap]),
            "laps":       laps_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"処理エラー: {str(e)}")


def _fmt_time(sec: float) -> str:
    m = int(sec // 60)
    s = sec - m * 60
    return f"{m}:{s:06.3f}" if m > 0 else f"{sec:.3f}s"


# ============================================================
# 2. 基本解析グラフ API
# ============================================================

@app.get("/api/{session_id}/speed_trace")
async def speed_trace(session_id: str, laps: str = ""):
    """速度トレース（速度 / 縦G / 横G 3段グラフ）"""
    from engine.plots import plot_speed_trace
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_speed_trace(selected, sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/delta_time")
async def delta_time(session_id: str, laps: str = ""):
    from engine.plots import plot_delta_time
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    if len(selected) < 2:
        raise HTTPException(status_code=400, detail="2ラップ以上選択してください")
    fig = plot_delta_time(selected, sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/gg_diagram")
async def gg_diagram(session_id: str, laps: str = ""):
    from engine.plots import plot_gg
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_gg(selected, sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/brake_map")
async def brake_map(session_id: str, laps: str = ""):
    from engine.plots import plot_brake_map
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_brake_map(selected, sess["lap_data"], sess["df"],
                         sess["lat_col"], sess["lon_col"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/corner_analysis")
async def corner_analysis(session_id: str):
    from engine.plots import plot_corner_analysis
    sess = get_session(session_id)
    fig = plot_corner_analysis(sess["best_lap"], sess["lap_data"], sess["lap_times"])
    return png_response(fig)


@app.get("/api/{session_id}/sector_comparison")
async def sector_comparison(session_id: str, laps: str = ""):
    from engine.plots import plot_sector_comparison
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_sector_comparison(selected, sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/lap_consistency")
async def lap_consistency(session_id: str, laps: str = ""):
    from engine.plots import plot_lap_consistency
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_lap_consistency(selected, sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/racing_line")
async def racing_line(session_id: str, laps: str = ""):
    from engine.plots import plot_racing_line
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_racing_line(selected, sess["lap_data"], sess["df"],
                           sess["lat_col"], sess["lon_col"],
                           sess["best_lap"], sess["lap_times"])
    return png_response(fig)


@app.get("/api/{session_id}/speed_heatmap")
async def speed_heatmap(session_id: str):
    from engine.plots import plot_speed_heatmap
    sess = get_session(session_id)
    fig = plot_speed_heatmap(sess["df"], sess["best_lap"], sess["lap_data"],
                             sess["lat_col"], sess["lon_col"])
    return png_response(fig)


@app.get("/api/{session_id}/gps_track")
async def gps_track(session_id: str):
    from engine.plots import plot_gps_track
    sess = get_session(session_id)
    fig = plot_gps_track(sess["df"], sess["lat_col"], sess["lon_col"],
                         sess["lap_data"], sess["lap_times"])
    return png_response(fig)


@app.get("/api/{session_id}/all_speed")
async def all_speed(session_id: str):
    from engine.plots import plot_all_speed
    sess = get_session(session_id)
    fig = plot_all_speed(sess["lap_data"], sess["lap_times"],
                         sess["df"], sess["lat_col"], sess["lon_col"])
    return png_response(fig)


# ============================================================
# 3. テーブルデータ API（JSON）
# ============================================================

@app.get("/api/{session_id}/lap_table")
async def lap_table(session_id: str):
    sess = get_session(session_id)
    lap_times = sess["lap_times"]
    best_lap  = sess["best_lap"]
    rows = []
    for l in sorted(lap_times.keys()):
        t    = lap_times[l]
        gap  = t - lap_times[best_lap]
        rows.append({
            "lap":      l,
            "time_fmt": _fmt_time(t),
            "time_sec": round(t, 3),
            "gap":      f"+{gap:.3f}" if gap > 0.001 else "BEST",
            "is_best":  l == best_lap,
        })
    return {"laps": rows}


@app.get("/api/{session_id}/corner_g_table")
async def corner_g_table(session_id: str):
    sess = get_session(session_id)
    rows = []
    for l in sorted(sess["lap_times"].keys()):
        ld = sess["lap_data"][l]
        if "lat_g" in ld.columns:
            rows.append({"lap": l, "max_lat_g": round(float(ld["lat_g"].abs().max()), 3)})
    return {"rows": sorted(rows, key=lambda x: -x["max_lat_g"])}


@app.get("/api/{session_id}/brake_g_table")
async def brake_g_table(session_id: str):
    sess = get_session(session_id)
    rows = []
    for l in sorted(sess["lap_times"].keys()):
        ld = sess["lap_data"][l]
        if "long_g" in ld.columns:
            rows.append({"lap": l, "max_brake_g": round(abs(float(ld["long_g"].min())), 3)})
    return {"rows": sorted(rows, key=lambda x: -x["max_brake_g"])}


@app.get("/api/{session_id}/min_speed_table")
async def min_speed_table(session_id: str):
    sess = get_session(session_id)
    rows = []
    for l in sorted(sess["lap_times"].keys()):
        ld = sess["lap_data"][l]
        if "speed_kmh" in ld.columns:
            rows.append({"lap": l, "min_speed": round(float(ld["speed_kmh"].min()), 1)})
    return {"rows": sorted(rows, key=lambda x: -x["min_speed"])}


@app.get("/api/{session_id}/theoretical_best")
async def theoretical_best_api(session_id: str):
    from engine.analyzer import theoretical_best
    sess = get_session(session_id)
    tb   = theoretical_best(sess["df"], sess["lap_data"], sess["lap_times"])
    bl   = sess["lap_times"][sess["best_lap"]]
    return {
        "theoretical_best":     round(tb, 3),
        "theoretical_best_fmt": _fmt_time(tb),
        "best_lap_time":        round(bl, 3),
        "best_lap_time_fmt":    _fmt_time(bl),
        "potential_gain":       round(bl - tb, 3),
    }


# ============================================================
# 4. 新解析機能 API
# ============================================================

@app.get("/api/{session_id}/brake_distance")
async def brake_distance(session_id: str, laps: str = ""):
    from engine.new_features import plot_brake_distance_analysis
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_brake_distance_analysis(
        selected, sess["lap_data"], sess["lap_times"],
        sess["best_lap"], sess["lat_col"], sess["lon_col"], sess["df"])
    return png_response(fig)


@app.get("/api/{session_id}/throttle_on")
async def throttle_on(session_id: str, laps: str = ""):
    from engine.new_features import plot_throttle_on_analysis
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig = plot_throttle_on_analysis(
        selected, sess["lap_data"], sess["lap_times"],
        sess["best_lap"], sess["lat_col"], sess["lon_col"], sess["df"])
    return png_response(fig)


@app.get("/api/{session_id}/corner_ranking")
async def corner_ranking(session_id: str):
    from engine.new_features import get_corner_ranking_data
    sess = get_session(session_id)
    data = get_corner_ranking_data(sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return data


@app.get("/api/{session_id}/os_us")
async def os_us(session_id: str, laps: str = ""):
    from engine.new_features import plot_oversteer_understeer
    sess = get_session(session_id)
    selected = _parse_laps(laps, sess)
    fig, result = plot_oversteer_understeer(
        selected, sess["lap_data"], sess["lap_times"],
        sess["best_lap"], sess["lat_col"], sess["lon_col"], sess["df"])
    return png_response(fig)


@app.get("/api/{session_id}/fatigue")
async def fatigue(session_id: str):
    from engine.new_features import plot_driver_fatigue
    sess = get_session(session_id)
    fig = plot_driver_fatigue(
        sess["lap_data"], sess["lap_times"], sess["best_lap"],
        sess["lat_col"], sess["lon_col"])
    return png_response(fig)


@app.get("/api/{session_id}/quality_score")
async def quality_score(session_id: str):
    from engine.new_features import get_quality_score_data
    sess = get_session(session_id)
    fig, data = get_quality_score_data(
        sess["lap_data"], sess["lap_times"], sess["best_lap"],
        sess["df"], sess["lat_col"], sess["lon_col"])
    return png_response(fig)


# ============================================================
# 5. AI理想分析 API
# ============================================================

@app.get("/api/{session_id}/ideal_speed")
async def ideal_speed(session_id: str):
    from engine.plots import plot_ideal_speed
    sess = get_session(session_id)
    fig = plot_ideal_speed(sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return png_response(fig)


@app.get("/api/{session_id}/ideal_line")
async def ideal_line(session_id: str):
    from engine.plots import plot_ideal_line
    sess = get_session(session_id)
    fig = plot_ideal_line(sess["lap_data"], sess["lap_times"], sess["best_lap"],
                          sess["lat_col"], sess["lon_col"], sess["df"])
    return png_response(fig)


@app.get("/api/{session_id}/ai_advice")
async def ai_advice(session_id: str):
    from engine.plots import get_ai_advice_data
    sess = get_session(session_id)
    data = get_ai_advice_data(sess["lap_data"], sess["lap_times"],
                              sess["best_lap"], sess["df"])
    return data


@app.get("/api/{session_id}/ideal_pit")
async def ideal_pit(session_id: str):
    from engine.plots import get_ideal_pit_data
    sess = get_session(session_id)
    data = get_ideal_pit_data(sess["lap_data"], sess["lap_times"], sess["best_lap"])
    return data


# ============================================================
# 6. 機械学習 AI API
# ============================================================

@app.post("/api/{session_id}/ml/train")
async def ml_train(session_id: str, background_tasks: BackgroundTasks):
    """全AIモデルを学習（バックグラウンドで実行）"""
    from engine.ai_engine import RaceAIEngine
    sess = get_session(session_id)

    def _train():
        engine = RaceAIEngine()
        engine.train_all(sess["lap_data"], sess["lap_times"],
                         sess["best_lap"], sess["lat_col"], sess["lon_col"])
        sess["engine"] = engine

    background_tasks.add_task(_train)
    return {"status": "学習開始しました。完了まで数秒かかります。"}


@app.get("/api/{session_id}/ml/lap_predict")
async def ml_lap_predict(session_id: str):
    sess = get_session(session_id)
    if "engine" not in sess:
        raise HTTPException(status_code=400, detail="先にAIモデルを学習してください（/ml/train）")
    pred, conf = sess["engine"].predict_next_lap(sess["lap_data"], sess["lap_times"])
    if pred is None:
        raise HTTPException(status_code=400, detail="予測に必要なデータが不足しています")
    return {"predicted_time": round(pred, 3), "predicted_fmt": _fmt_time(pred),
            "confidence_mae": round(conf, 3) if conf else None}


@app.get("/api/{session_id}/ml/tire")
async def ml_tire(session_id: str):
    sess = get_session(session_id)
    if "engine" not in sess:
        raise HTTPException(status_code=400, detail="先にAIモデルを学習してください")
    from engine.plots import plot_tire_degradation
    fig = plot_tire_degradation(sess["engine"].tire_model, sess["lap_times"])
    return png_response(fig)


@app.get("/api/{session_id}/ml/corner_priority")
async def ml_corner_priority(session_id: str):
    sess = get_session(session_id)
    if "engine" not in sess:
        raise HTTPException(status_code=400, detail="先にAIモデルを学習してください")
    priority = sess["engine"].corner_priority()
    return {"priority": priority}


@app.get("/api/{session_id}/ml/ideal_line_ai")
async def ml_ideal_line_ai(session_id: str):
    sess = get_session(session_id)
    if "engine" not in sess:
        raise HTTPException(status_code=400, detail="先にAIモデルを学習してください")
    from engine.plots import plot_ai_ideal_line
    fig = plot_ai_ideal_line(sess["engine"], sess["lap_data"],
                             sess["lap_times"], sess["lat_col"], sess["lon_col"])
    return png_response(fig)


# ============================================================
# 7. データ管理 API
# ============================================================

@app.post("/api/{session_id}/db/register")
async def db_register(session_id: str):
    """現在のセッションをDBに登録"""
    from engine.data_manager import register_session
    sess = get_session(session_id)
    register_session(sess["csv_path"], sess["lap_data"], sess["lap_times"])
    return {"status": "登録完了"}


@app.get("/api/db/sessions")
async def db_sessions():
    """登録済みセッション一覧"""
    from engine.data_manager import load_db
    db = load_db()
    return {"sessions": db.get("sessions", []), "total": len(db.get("sessions", []))}


@app.post("/api/db/train")
async def db_train(background_tasks: BackgroundTasks):
    """蓄積データで再学習"""
    from engine.data_manager import train_cross_model
    def _train():
        train_cross_model()
    background_tasks.add_task(_train)
    return {"status": "蓄積学習を開始しました"}


@app.get("/api/db/cross_compare")
async def db_cross_compare():
    """蓄積セッション比較グラフ"""
    from engine.data_manager import load_db
    from engine.plots import plot_cross_session_compare
    db  = load_db()
    fig = plot_cross_session_compare(db)
    return png_response(fig)


# ============================================================
# 8. 詳細解析（extra_functions）API
# ============================================================

@app.get("/api/{session_id}/extra/{func_name}")
async def extra_func(session_id: str, func_name: str, laps: str = ""):
    """
    extra_functions.py の各関数を呼ぶ汎用エンドポイント。
    func_name: compare_speed, delta_map, min_speed_map, など
    """
    import engine.extra_functions as ef
    sess     = get_session(session_id)
    selected = _parse_laps(laps, sess)

    # コンテキストをセット
    from engine.analyzer import theoretical_best
    tb_val  = theoretical_best(sess["df"], sess["lap_data"], sess["lap_times"])
    ld_best = sess["lap_data"][sess["best_lap"]].copy()
    ld_best["ld"] = ld_best["dist_m"] - ld_best["dist_m"].min()
    cl = float(ld_best["ld"].max())

    ef.set_context(
        df=sess["df"], lap_data=sess["lap_data"],
        lap_times=pd.Series(sess["lap_times"]),
        best_lap=sess["best_lap"],
        lat_col=sess["lat_col"], lon_col=sess["lon_col"],
        speed_col="speed_kmh", time_col="time_sec",
        sectors={f"S{i+1}": (round(cl*i/3), round(cl*(i+1)/3)) for i in range(3)},
        corners={},
        lap_vars={l: type("V", (), {"get": lambda self: 1 if l in selected else 0})()
                  for l in sess["lap_times"]},
        theoretical_best_val=tb_val, course_length=cl,
    )

    fn = getattr(ef, func_name, None)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"関数 {func_name} が見つかりません")

    # 既存のplt.show()をキャプチャして返す
    plt.close("all")
    try:
        fn()
        figs = [plt.figure(n) for n in plt.get_fignums()]
        if not figs:
            return JSONResponse({"status": "完了（グラフなし）"})
        fig = figs[-1]
        return png_response(fig)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 9. PDF生成 API
# ============================================================

@app.post("/api/{session_id}/pdf")
async def generate_pdf(
    session_id: str,
    laps: str = "",
    course_name: str = "—",
    driver_name: str = "—",
    car_name: str = "—",
    weather: str = "—",
):
    from engine.analyzer import generate_pdf as _gen_pdf
    sess     = get_session(session_id)
    selected = _parse_laps(laps, sess)
    if not selected:
        raise HTTPException(status_code=400, detail="ラップを選択してください")

    pdf_path = str(OUTPUT_DIR / f"{session_id}_report.pdf")
    _gen_pdf(selected, sess["lap_data"], sess["lap_times"], sess["best_lap"],
             sess["df"], sess["lat_col"], sess["lon_col"],
             course_name=course_name, driver_name=driver_name,
             car_name=car_name, weather=weather,
             output_path=pdf_path)

    return FileResponse(pdf_path, media_type="application/pdf",
                        filename=f"telemetry_{session_id}.pdf")


# ============================================================
# ヘルパー
# ============================================================

def _parse_laps(laps_str: str, sess: dict) -> list:
    """クエリパラメータ "1,2,3" → [1,2,3]、空なら全ラップ"""
    if not laps_str:
        return sorted(sess["lap_times"].keys())
    try:
        return [int(x) for x in laps_str.split(",") if x.strip()]
    except ValueError:
        return sorted(sess["lap_times"].keys())


# ============================================================
# ヘルスチェック
# ============================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "sessions": len(_sessions)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
