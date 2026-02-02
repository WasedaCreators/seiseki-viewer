#!/usr/bin/env python3
"""
Microsoft Entra ID認証を使用してMoodleページのHTMLを取得するスクリプト
"""

import os
import webbrowser
import http.server
import urllib.parse
from pathlib import Path
import msal
import requests

# Microsoft Entra ID設定
# 公開クライアント（デスクトップアプリ）として登録が必要
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
TENANT_ID = os.environ.get("AZURE_TENANT_ID", "organizations")  # マルチテナントの場合は"organizations"
REDIRECT_URI = "http://localhost:8400"

# スコープ（早稲田のMoodleがEntra IDと連携している場合）
SCOPES = ["openid", "profile", "email"]

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

def authenticate_interactive():
    """対話式認証を実行"""
    app = get_msal_app()
    
    # キャッシュからトークンを取得
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            print("キャッシュからトークンを取得しました")
            return result
    
    # 対話式認証
    print("ブラウザで認証を行ってください...")
    result = app.acquire_token_interactive(
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    
    if "access_token" in result:
        print("認証成功!")
        return result
    else:
        error = result.get("error_description", result.get("error", "不明なエラー"))
        raise Exception(f"認証失敗: {error}")

def fetch_with_session(url, auth_result):
    """
    認証情報を使用してURLからHTMLを取得
    
    注意: 早稲田MoodleがMicrosoft Entra IDでSSOしている場合、
    実際の認証フローは以下のようになる可能性があります：
    1. Moodleにアクセス
    2. Moodleがidp（早稲田のSSO）にリダイレクト
    3. idpがMicrosoft Entra IDにリダイレクト
    4. 認証後、SAMLやOIDCでMoodleに戻る
    """
    session = requests.Session()
    
    # アクセストークンをAuthorizationヘッダーに設定
    headers = {
        "Authorization": f"Bearer {auth_result.get('access_token', '')}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    
    print(f"\nアクセス中: {url}")
    
    # 直接アクセス（Bearer認証）
    response = session.get(url, headers=headers, allow_redirects=True)
    
    return response

def main():
    """メイン処理"""
    # CLIENT_IDが設定されているか確認
    if not CLIENT_ID:
        print("=" * 60)
        print("エラー: AZURE_CLIENT_ID 環境変数が設定されていません")
        print()
        print("以下の手順で設定してください：")
        print("1. Azure Portal でアプリを登録")
        print("   - Azure Portal > Azure Active Directory > アプリの登録")
        print("   - 新規登録でパブリッククライアント（デスクトップアプリ）を作成")
        print("   - リダイレクトURI: http://localhost:8400")
        print()
        print("2. 環境変数を設定:")
        print("   export AZURE_CLIENT_ID='your-client-id'")
        print("   export AZURE_TENANT_ID='your-tenant-id'  # または 'organizations'")
        print("=" * 60)
        return
    
    try:
        # ターゲットURLを読み込み
        target_url = load_target_url()
        print(f"ターゲットURL: {target_url}")
        
        # Microsoft Entra ID認証
        auth_result = authenticate_interactive()
        
        # 認証情報を表示
        print("\n--- 認証情報 ---")
        if "id_token_claims" in auth_result:
            claims = auth_result["id_token_claims"]
            print(f"ユーザー: {claims.get('preferred_username', 'N/A')}")
            print(f"名前: {claims.get('name', 'N/A')}")
        
        # HTMLを取得
        response = fetch_with_session(target_url, auth_result)
        
        print(f"\n--- レスポンス ---")
        print(f"ステータスコード: {response.status_code}")
        print(f"最終URL: {response.url}")
        print(f"\n--- HTML内容 ---")
        print(response.text)
        
    except Exception as e:
        print(f"エラー: {e}")
        raise

if __name__ == "__main__":
    main()
