# Waseda Grade Checker

早稲田大学の成績を自動取得し、必修科目の平均点や偏差値、度数分布を表示するwebアプリです。

## 構成

- **Frontend**: Next.js (Port 3001)
- **Backend**: Python FastAPI + Selenium (Port 8001)

## 実行方法 (Ubuntu / macOS)

### 前提条件

- Python 3.10+
- Node.js 18+
- Google Chrome または Chromium (BackendでSeleniumを使用するため)

**UbuntuでのChromeインストール例:**
```bash
sudo apt-get update
sudo apt-get install -y chromium-browser
```

### セットアップと実行

`make` コマンドを使用して簡単に実行できます。

1. **依存関係のインストール**
   ```bash
   make install
   ```

2. **アプリケーションの起動**
   ```bash
   make run
   ```
   
   起動後、ブラウザで [http://localhost:3001](http://localhost:3001) にアクセスしてください。

## Dockerを使用する場合

Docker Composeを使用して実行することも可能です。

### 環境変数の設定（オプション）

本番環境では、セキュリティのためデータベース認証情報を変更することを推奨します。

1. `.env.example`をコピーして`.env`ファイルを作成
   ```bash
   cp .env.example .env
   ```

2. `.env`ファイルを編集し、安全なパスワードを設定
   ```bash
   MYSQL_USER=seiseki
   MYSQL_PASSWORD=your-secure-password-here
   MYSQL_DATABASE=seiseki
   MYSQL_ROOT_PASSWORD=your-root-password-here
   ```

### 起動

```bash
docker compose up -d --build
```

※ `.env`ファイルが存在しない場合は、デフォルトの開発用認証情報が使用されます。

## 機能

- 成績の自動取得（Microsoft Entra ID認証対応）
- 必修科目の重み付け平均点算出
- 偏差値・順位の表示(現状/adminのみ)
- 度数分布グラフの表示(現状/adminのみ)
- CSV形式でのデータ保存(個人情報保護の観点から廃止,スコアのみ学籍番号を2回ハッシュ化してmysqlに保存)
