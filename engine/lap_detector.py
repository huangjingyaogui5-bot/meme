"""
engine/lap_detector.py  ─  ウェブ用ラップ自動検出
tkinter のクリック操作なしで GPS から S/F ラインを自動推定して検出する。
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import pickle, os
from pathlib import Path
from math import radians, cos, sin, sqrt, atan2

MODEL_PATH = str(Path(__file__).parent.parent / "data" / "lap_model.pkl")
MIN_SPEED  = 5


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a    = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))


def build_features(df, lat_col, lon_col, speed_col, time_col):
    feat = pd.DataFrame(index=df.index)
    spd  = df[speed_col].fillna(0)
    feat["speed"]        = spd
    feat["speed_diff"]   = spd.diff().fillna(0)
    feat["speed_roll5"]  = spd.rolling(5,  min_periods=1).mean()
    feat["speed_roll20"] = spd.rolling(20, min_periods=1).mean()
    feat["speed_std10"]  = spd.rolling(10, min_periods=1).std().fillna(0)
    lat = df[lat_col].ffill(); lon = df[lon_col].ffill()
    feat["lat"]  = lat; feat["lon"]  = lon
    feat["dlat"] = lat.diff().fillna(0); feat["dlon"] = lon.diff().fillna(0)
    d = np.sqrt(feat["dlat"]**2 + feat["dlon"]**2) * 111000
    feat["step_dist"] = d
    feat["cum_dist"]  = d.cumsum()
    heading = np.arctan2(feat["dlon"], feat["dlat"])
    feat["heading"]       = heading
    feat["heading_diff"]  = heading.diff().fillna(0)
    feat["heading_diff"]  = feat["heading_diff"].apply(
        lambda x: x - 2*np.pi if x > np.pi else (x + 2*np.pi if x < -np.pi else x))
    feat["heading_std10"] = feat["heading_diff"].rolling(10, min_periods=1).std().fillna(0)
    dt = df[time_col].diff().fillna(0.05).clip(lower=0.001)
    feat["dt"] = dt
    return feat.fillna(0)


def _auto_detect_sf_line(df, lat_col, lon_col, speed_col):
    """
    GPS データからスタート/フィニッシュライン付近を自動推定。
    速度が一定以上で最も多くのラップが通過する地点を S/F とする。
    """
    spd  = df[speed_col].fillna(0)
    mask = spd > 30
    df2  = df[mask].copy()
    if len(df2) < 20:
        df2 = df.copy()

    # GPS をグリッド化して最頻通過エリアを探す
    lat_arr = df2[lat_col].values
    lon_arr = df2[lon_col].values

    # 全体を10×10グリッドに分割してどのセルが一番通過回数多いか
    lat_bins = np.linspace(lat_arr.min(), lat_arr.max(), 11)
    lon_bins = np.linspace(lon_arr.min(), lon_arr.max(), 11)
    counts   = np.zeros((10, 10))
    for la, lo in zip(lat_arr, lon_arr):
        i = min(int((la - lat_bins[0]) / (lat_bins[-1] - lat_bins[0] + 1e-9) * 10), 9)
        j = min(int((lo - lon_bins[0]) / (lon_bins[-1] - lon_bins[0] + 1e-9) * 10), 9)
        counts[i, j] += 1

    # 最頻セルの中心を S/F ライン候補とする
    idx  = np.unravel_index(counts.argmax(), counts.shape)
    sf_lat = (lat_bins[idx[0]] + lat_bins[idx[0]+1]) / 2
    sf_lon = (lon_bins[idx[1]] + lon_bins[idx[1]+1]) / 2
    return sf_lat, sf_lon


def detect_laps(df, lat_col="lat", lon_col="lon",
                speed_col="speed_kmh", time_col="time_sec"):
    """
    ラップを自動検出して (df_with_lap, lap_times) を返す。
    保存済みモデルがあれば使い、なければルールベースで検出。
    """
    df = df.copy()

    # ── モデルベース検出を試みる ────────────────────────────────
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, "rb") as f:
                saved = pickle.load(f)
            model  = saved["model"]
            scaler = saved["scaler"]
            sf_lat = saved["sf_lat"]
            sf_lon = saved["sf_lon"]
            feat   = build_features(df, lat_col, lon_col, speed_col, time_col)
            X      = scaler.transform(feat[model.feature_names_in_])
            proba  = model.predict_proba(X)[:, 1]
            df["sf_proba"] = proba
            df, lap_times = _assign_laps_from_proba(df, sf_lat, sf_lon, lat_col, lon_col, time_col)
            if lap_times:
                print(f"[ラップ検出] モデルベース: {len(lap_times)}ラップ")
                return df, lap_times
        except Exception as e:
            print(f"[ラップ検出] モデル読込失敗: {e} → ルールベースで検出")

    # ── ルールベース検出 ─────────────────────────────────────────
    sf_lat, sf_lon = _auto_detect_sf_line(df, lat_col, lon_col, speed_col)
    df, lap_times  = _rule_based_detect(df, sf_lat, sf_lon, lat_col, lon_col,
                                         speed_col, time_col)
    print(f"[ラップ検出] ルールベース: {len(lap_times)}ラップ  S/F: ({sf_lat:.5f}, {sf_lon:.5f})")
    return df, lap_times


def _rule_based_detect(df, sf_lat, sf_lon, lat_col, lon_col, speed_col, time_col,
                        radius_m=50, min_lap_sec=20):
    """
    S/F ライン通過をルールで検出してラップを割り当てる。
    """
    df = df.copy()
    df["lap"] = 0
    df["_dist_sf"] = df.apply(
        lambda r: haversine_m(r[lat_col], r[lon_col], sf_lat, sf_lon), axis=1)

    # S/F から radius_m 以内を「通過候補」とする
    near = df["_dist_sf"] < radius_m
    # 連続する通過区間をひとつの通過イベントにまとめる
    groups = (near != near.shift()).cumsum()
    pass_times = []
    for g, grp in df[near].groupby(groups[near]):
        # その区間の中で最も速度が高い点の時刻を通過時刻とする
        if speed_col in grp.columns:
            idx = grp[speed_col].idxmax()
        else:
            idx = grp.index[len(grp)//2]
        pass_times.append(float(df.loc[idx, time_col]))

    pass_times = sorted(set(pass_times))

    # ラップを割り当て
    lap_times = {}
    lap_num   = 0
    for i, pt in enumerate(pass_times):
        if i == 0:
            lap_start = pt
            lap_num   = 1
            continue
        lap_dur = pt - lap_start
        if lap_dur >= min_lap_sec:
            mask = (df[time_col] >= lap_start) & (df[time_col] < pt)
            df.loc[mask, "lap"] = lap_num
            lap_times[lap_num]   = round(lap_dur, 3)
            lap_num   += 1
            lap_start  = pt

    df.drop(columns=["_dist_sf"], inplace=True)
    # ラップ0を除去
    df = df[df["lap"] > 0].copy() if lap_times else df
    return df, lap_times


def _assign_laps_from_proba(df, sf_lat, sf_lon, lat_col, lon_col, time_col,
                              threshold=0.5, min_lap_sec=20):
    """確率ベースでラップを割り当て"""
    peaks = df[df["sf_proba"] > threshold].copy()
    if len(peaks) < 2:
        return df, {}
    pass_times = []
    groups = (peaks.index.to_series().diff() > 5).cumsum()
    for _, grp in peaks.groupby(groups):
        idx = grp["sf_proba"].idxmax()
        pass_times.append(float(df.loc[idx, time_col]))

    return _rule_based_detect.__wrapped__(
        df, sf_lat, sf_lon, lat_col, lon_col, "speed_kmh", time_col,
        radius_m=100, min_lap_sec=min_lap_sec
    ) if hasattr(_rule_based_detect, "__wrapped__") else _rule_based_detect(
        df, sf_lat, sf_lon, lat_col, lon_col, "speed_kmh", time_col,
        radius_m=100, min_lap_sec=min_lap_sec
    )
