#!/usr/bin/env python3
"""
Microsoft Entra ID Device Code Flow認証を使用してMoodleページのHTMLを取得するスクリプト

Device Code Flowは以下の手順で動作します：
1. スクリプトがデバイスコードを生成
2. ユーザーがブラウザで https://microsoft.com/devicelogin にアクセス
3. コードを入力して認証
4. スクリプトがトークンを取得

注意: 早稲田MoodleがMicrosoft Entra IDと直接連携していない場合、
取得したトークンではMoodleに直接アクセスできない可能性があります。
"""

import os
import sys
from pathlib import Path
import msal
import requests

# Microsoft Entra ID設定
# Azureポータルでアプリを登録して取得
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "organizations")

# スコープ
SCOPES = ["User.Read"]  # Microsoft Graphの基本スコープ

def load_target_url():
    """kenkyushitu/.envからターゲットURLを読み込む"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            url = f.read().strip()
            if url and url.startswith("http"):
                return url
    raise ValueError(".envファイルにURLが設定されていません")

def get_msal_app():
    """MSALアプリケーションを作成"""
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    )

def authenticate_device_code():
    """Device Code Flow認証を実行"""
    app = get_msal_app()
    
    # キャッシュからトークンを取得
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print("キャッシュからトークンを取得しました")
            return result
    
    # Device Code Flow開始
    flow = app.initiate_device_flow(scopes=SCOPES)
    
    if "user_code" not in flow:
        raise Exception(f"Device Code Flowの開始に失敗: {flow.get('error_description', 'Unknown error')}")
    
    print("\n" + "=" * 60)
    print("認証手順:")
    print(f"1. ブラウザで次のURLにアクセス: {flow['verification_uri']}")
    print(f"2. 以下のコードを入力: {flow['user_code']}")
    print("3. Microsoftアカウントでログイン")
    print("=" * 60)
    print(flow.get("message", ""))
    print("=" * 60 + "\n")
    
    # トークン取得を待機
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("認証成功!")
        return result
    else:
        error = result.get("error_description", result.get("error", "不明なエラー"))
        raise Exception(f"認証失敗: {error}")

def fetch_url_with_session(url, access_token):
    """認証情報を使用してURLからHTMLを取得"""
    session = requests.Session()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    print(f"\nURLにアクセス中: {url}")
    
    # まずトークンなしでアクセス（リダイレクト先を確認）
    response = session.get(url, allow_redirects=True)
    print(f"ステータスコード: {response.status_code}")
    print(f"最終URL: {response.url}")
    
    return response

def main():
    """メイン処理"""
    if not CLIENT_ID:
        print("=" * 60)
        print("AZURE_CLIENT_ID が設定されていません。")
        print()
        print("オプション1: Azure ADアプリを登録して使用")
        print("  1. Azure Portal > Azure Active Directory > アプリの登録")
        print("  2. 新規登録 (パブリッククライアント)")
        print("  3. 「モバイル/デスクトップ」プラットフォームを追加")
        print("  4. 環境変数を設定:")
        print("     export AZURE_CLIENT_ID='your-client-id'")
        print()
        print("オプション2: Seleniumスクリプトを使用")
        print("  python3 fetch_moodle_selenium.py")
        print("=" * 60)
        return
    
    try:
        target_url = load_target_url()
        print(f"ターゲットURL: {target_url}")
        
        # 認証
        auth_result = authenticate_device_code()
        
        # ユーザー情報を表示
        if "id_token_claims" in auth_result:
            claims = auth_result["id_token_claims"]
            print(f"\n認証ユーザー:")
            print(f"  名前: {claims.get('name', 'N/A')}")
            print(f"  メール: {claims.get('preferred_username', 'N/A')}")
        
        # URLにアクセス
        response = fetch_url_with_session(target_url, auth_result.get("access_token", ""))
        
        print("\n" + "=" * 60)
        print("HTML内容:")
        print("=" * 60)
        print(response.text)
        
    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
