# Waseda Grade API

早稲田大学の成績照会画面のHTMLを解析してJSONデータを返すAPIです。

## 必要要件

- Python 3.x
- 以下のライブラリ（`requirements.txt`に含まれています）
    - fastapi
    - uvicorn
    - beautifulsoup4
    - requests
    - python-multipart

## セットアップ

1. 仮想環境の作成と有効化（推奨）
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Mac/Linux
    # .venv\Scripts\activate  # Windows
    ```

2. 依存ライブラリのインストール
    ```bash
    pip install -r requirements.txt
    ```

## 実行方法

以下のコマンドでサーバーを起動します。

```bash
python main.py
```

サーバーが起動したら、ブラウザで以下のURLにアクセスしてください。

http://localhost:8001

## 使い方

1. `http://localhost:8001` にアクセスするとログインフォームが表示されます。
2. 学籍番号（またはWaseda ID）とパスワードを入力して「Get Grades」ボタンをクリックします。
3. （現在はデモモードのため）サンプルデータの解析結果がJSON形式で表示されます。

## 注意事項

- 実際の早稲田大学のログインシステム（Shibboleth）との連携は実装されていません。現在は提供されたHTML構造に基づいた解析ロジックのデモとして動作します。
- `main.py` 内の `login_url` や `payload` を実際の環境に合わせて修正する必要があります。
