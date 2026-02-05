# Waseda Grade Checker

早稲田大学の成績を自動取得し、必修科目の平均点や偏差値、度数分布を表示するwebアプリです。  
研究室志望情報（Moodle Quiz）の取得・保存にも対応しています。

## 構成

- **Frontend**: Next.js (Port 3001)
- **Backend**: Python FastAPI + Selenium (Port 8001)
- **Database**: MySQL (user: `seiseki`, password: `seiseki-mitai`)

## クイックスタート (Ubuntu 22.04)

```bash
# 1. 全ての依存関係をインストール（初回のみ）
make install

# 2. アプリケーションを起動
make run
```

起動後、ブラウザで [http://localhost:3001](http://localhost:3001) にアクセスしてください。

`make run` 実行時のターミナル出力は `logs/run-YYYYmmdd-HHMMSS.log` に自動保存されます。

## Makeコマンド一覧

### セットアップ

| コマンド | 説明 |
|----------|------|
| `make install` | 全ての依存関係をインストール（初回セットアップ） |
| `make system-deps` | システムパッケージをインストール（Python, Node.js, Chrome, MySQL） |
| `make backend-deps` | Python仮想環境に依存関係をインストール |
| `make frontend-deps` | Node.js依存関係をインストール |
| `make setup-db` | MySQLデータベースをセットアップ |
| `make build-frontend` | フロントエンドをビルド |

### 実行

| コマンド | 説明 |
|----------|------|
| `make run` | バックエンドとフロントエンドを両方起動 |
| `make run-backend` | バックエンドのみ起動 |
| `make run-frontend` | フロントエンドのみ起動 |
| `make stop` | 全てのプロセスを停止 |

### データベース管理

| コマンド | 説明 |
|----------|------|
| `make show-schema` | gpadataテーブルの構造を表示 |
| `make show-database` | データベースの中身を表示（GPA・研究室志望） |

### その他

| コマンド | 説明 |
|----------|------|
| `make clean` | ビルド成果物と依存関係を削除 |
| `make help` | 利用可能なコマンド一覧を表示 |

## Dockerを使用する場合

Docker Composeを使用して実行することも可能です。

```bash
docker compose up -d --build
```

## 機能

- 成績の自動取得（Microsoft Entra ID認証対応）
- 必修科目の重み付け平均点算出
- 偏差値・順位の表示 (adminページ)
- 度数分布グラフの表示 (adminページ)
- 研究室志望情報の取得・保存（Moodle Quiz連携）

## データベース構造

`gpadata` テーブル:

| カラム | 型 | 説明 |
|--------|------|------|
| student_id | VARCHAR(64) | 適当につけた番号 |
| avg_gpa | FLOAT | 必修科目平均GPA |
| timestamp | DATETIME | GPA更新日時 |
