# 耐久レース テレメトリー解析 Web アプリ

## ディレクトリ構成

```
webapp/
├── backend/
│   └── main.py              # FastAPI バックエンド
├── engine/                  # 解析エンジン（既存コードをここに置く）
│   ├── __init__.py
│   ├── analyzer.py          # CSV読み込み・前処理・PDF生成
│   ├── lap_detector.py      # ラップ自動検出
│   ├── plots.py             # ← main.py から plot_* 関数をコピー
│   ├── new_features.py      # ← new_features.py をコピー
│   ├── extra_functions.py   # ← extra_functions.py をコピー
│   ├── ai_engine.py         # ← ai_engine.py をコピー
│   ├── data_manager.py      # ← data_manager.py をコピー
│   └── lap_ai.py            # ← lap_ai.py をコピー（tkinter import を除去）
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx
│   │   │   └── AnalysisPage.jsx
│   │   └── components/
│   │       ├── LapSelector.jsx
│   │       ├── GraphViewer.jsx
│   │       ├── TableViewer.jsx
│   │       └── PdfPanel.jsx
│   ├── package.json
│   └── vite.config.js
├── data/                    # DB・モデル保存（Railway Volume）
├── uploads/                 # アップロードCSV（Railway Volume）
├── outputs/                 # 生成PDF（Railway Volume）
├── requirements.txt
├── railway.toml
└── README.md
```

## セットアップ手順

### 1. 既存コードをコピー

```bash
# engine/ フォルダに既存ファイルをコピー
cp main.py         webapp/engine/plots.py      # plot_* 関数を抜き出す
cp new_features.py webapp/engine/new_features.py
cp extra_functions.py webapp/engine/extra_functions.py
cp ai_engine.py    webapp/engine/ai_engine.py
cp data_manager.py webapp/engine/data_manager.py
cp lap_ai.py       webapp/engine/lap_ai.py
```

### 2. plots.py の作成

`main.py` から以下の関数を `engine/plots.py` にコピーする：
- `plot_speed_trace`
- `plot_delta_time`
- `plot_gg`
- `plot_brake_map`
- `plot_corner_analysis`
- `plot_sector_comparison`
- `plot_lap_consistency`
- `plot_racing_line`
- `plot_speed_heatmap`
- `plot_gps_track`
- `plot_all_speed`
- `plot_ideal_speed`
- `plot_ideal_line`
- `calc_ideal_pit` → `get_ideal_pit_data` に rename してJSON返すように変更
- `show_ai_advice` → `get_ai_advice_data` に rename してJSON返すように変更
- `plot_tire_degradation`（新規：tire_model から劣化曲線グラフ）
- `plot_ai_ideal_line`（新規：AI理想ライン）
- `plot_cross_session_compare`（新規：セッション間比較）

### 3. tkinter import を除去

各ファイルから以下を削除：
```python
# 削除
import tkinter as tk
from tkinter import ttk, messagebox
matplotlib.use('TkAgg')   # → 'Agg' に変更

# 変更
plt.show(block=False)     # → 削除（figを返すだけでOK）
messagebox.showinfo(...)  # → print() または例外に変更
```

### 4. engine/__init__.py 作成

```bash
touch webapp/engine/__init__.py
```

### 5. ローカル起動

```bash
# バックエンド
cd webapp
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000

# フロントエンド（別ターミナル）
cd webapp/frontend
npm install
npm run dev
# → http://localhost:5173 でアクセス
```

### 6. Railway デプロイ

```bash
# GitHubリポジトリにpush
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USER/race-analyzer.git
git push -u origin main
```

Railway（https://railway.app）で：
1. 「New Project」→「Deploy from GitHub repo」
2. リポジトリを選択
3. 環境変数は特になし（railway.toml が自動的に設定）
4. Volume は railway.toml の設定で自動作成される
5. デプロイ完了後に表示されるURLでアクセス

### 7. フロントエンドのビルドをバックエンドで配信

```bash
cd webapp/frontend
npm run build
# → backend/static/ にビルド結果が出力される
```

`backend/main.py` の末尾に追加：
```python
# 静的ファイルの配信（本番用）
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="backend/static", html=True), name="static")
```

## 無料枠の注意点

Railway の無料枠：
- 月500時間のサービス稼働時間
- 1GB RAM / 1 vCPU
- 5GB ストレージ（Volume）
- 常時稼働させる場合は有料プラン（$5/月〜）が必要

重いAI処理（全モデル学習など）はメモリを多く使うため、
最初は `ml/train` エンドポイントの処理を軽量化することを推奨。

## よくある問題

**matplotlib の日本語が文字化け**
```python
import matplotlib
matplotlib.rcParams['font.family'] = 'DejaVu Sans'
# 日本語テキストはすべて英語に変えるか、日本語フォントをDockerfileでインストール
```

**tkinter がインポートできない（サーバー上）**
各ファイルの冒頭で以下を確認：
```python
import matplotlib
matplotlib.use("Agg")  # TkAgg ではなく Agg を使う
```

**セッションがメモリ上のみで再起動で消える**
現在は `_sessions` dict でメモリ管理している。
本番では Redis や SQLite に保存するよう拡張推奨。
