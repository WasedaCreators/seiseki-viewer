#!/usr/bin/env python3
"""
Microsoft Entra ID認証（Seleniumブラウザ自動化版）を使用してMoodleページのHTMLを取得するスクリプト

早稲田のMoodleは通常、以下のフローで認証されます：
1. Moodleにアクセス
2. 早稲田SSO（MyWaseda）にリダイレクト
3. MyWasedaがMicrosoft Entra IDにリダイレクト（教職員/学生の場合）
4. 認証後、SAMLでMoodleに戻る

このスクリプトはSeleniumを使用してこのフローを自動化します。
"""

import os
import time
from pathlib import Path

def load_target_url():
    """kenkyushitu/.envからターゲットURLを読み込む"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            url = f.read().strip()
            if url and url.startswith("http"):
                return url
    raise ValueError(".envファイルにURLが設定されていません")

def main():
    """メイン処理"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        print("=" * 60)
        print("Seleniumがインストールされていません。")
        print("以下のコマンドでインストールしてください：")
        print("  pip3 install selenium webdriver-manager")
        print("=" * 60)
        return
    
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        print("webdriver-managerがインストールされていません。")
        print("  pip3 install webdriver-manager")
        return
    
    target_url = load_target_url()
    print(f"ターゲットURL: {target_url}")
    
    # Chromeオプション設定
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # ヘッドレスモード（認証時はコメントアウト推奨）
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    print("\nブラウザを起動しています...")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"ChromeDriverの初期化に失敗: {e}")
        print("\nChromeがインストールされているか確認してください。")
        return
    
    try:
        print(f"URLにアクセス中: {target_url}")
        driver.get(target_url)
        
        print("\n" + "=" * 60)
        print("ブラウザで認証を完了してください。")
        print("Microsoft Entra ID（またはMyWaseda）でログインしてください。")
        print("認証完了後、Enterキーを押してください...")
        print("=" * 60)
        
        input()
        
        # ページ読み込み完了を待つ
        time.sleep(2)
        
        # 現在のURLを表示
        print(f"\n現在のURL: {driver.current_url}")
        
        # HTMLを取得
        html_content = driver.page_source
        
        print("\n" + "=" * 60)
        print("HTML内容:")
        print("=" * 60)
        print(html_content)
        
        # クッキー情報も表示（デバッグ用）
        print("\n" + "=" * 60)
        print("Cookies:")
        print("=" * 60)
        for cookie in driver.get_cookies():
            print(f"  {cookie['name']}: {cookie['value'][:50]}...")
            
    except Exception as e:
        print(f"エラー: {e}")
        raise
    finally:
        print("\nブラウザを閉じます...")
        driver.quit()

if __name__ == "__main__":
    main()
