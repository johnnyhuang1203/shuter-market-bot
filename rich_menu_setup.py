"""建立 / 更新 Rich Menu 並設為預設。
用法(先 export 或 .env 設好 LINE_CHANNEL_ACCESS_TOKEN):
    python rich_menu_setup.py
會:①建立一個 2500x843、三格的 Rich Menu ②上傳 brand/richmenu_2500x843.png
   ③設為所有使用者的預設選單。三格點下去分別送出「大盤 / 報告 / 幫助」文字。
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brand", "richmenu_2500x843.png")

if not TOKEN:
    sys.exit("請先設定 LINE_CHANNEL_ACCESS_TOKEN(環境變數或 .env)")

H = {"Authorization": f"Bearer {TOKEN}"}

# 三格版面(2500x843,每格約 833 寬)
W, HH = 2500, 843
third = W // 3
menu = {
    "size": {"width": W, "height": HH},
    "selected": True,
    "name": "shuter-market-menu",
    "chatBarText": "市場選單",
    "areas": [
        {"bounds": {"x": 0, "y": 0, "width": third, "height": HH},
         "action": {"type": "message", "text": "大盤"}},
        {"bounds": {"x": third, "y": 0, "width": third, "height": HH},
         "action": {"type": "message", "text": "報告"}},
        {"bounds": {"x": third * 2, "y": 0, "width": W - third * 2, "height": HH},
         "action": {"type": "message", "text": "幫助"}},
    ],
}


def main():
    # 0) 先刪除同名舊選單(避免累積)
    r = requests.get("https://api.line.me/v2/bot/richmenu/list", headers=H, timeout=10)
    for m in (r.json().get("richmenus") or []):
        if m.get("name") == menu["name"]:
            requests.delete(f"https://api.line.me/v2/bot/richmenu/{m['richMenuId']}", headers=H, timeout=10)
            print("刪除舊選單", m["richMenuId"])

    # 1) 建立選單
    r = requests.post("https://api.line.me/v2/bot/richmenu",
                      headers={**H, "Content-Type": "application/json"},
                      json=menu, timeout=15)
    if r.status_code != 200:
        sys.exit(f"建立失敗 {r.status_code}: {r.text}")
    rid = r.json()["richMenuId"]
    print("建立選單:", rid)

    # 2) 上傳圖片
    with open(IMG, "rb") as f:
        r = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rid}/content",
            headers={**H, "Content-Type": "image/png"}, data=f.read(), timeout=30)
    if r.status_code != 200:
        sys.exit(f"上傳圖片失敗 {r.status_code}: {r.text}")
    print("圖片已上傳")

    # 3) 設為預設
    r = requests.post(f"https://api.line.me/v2/bot/user/all/richmenu/{rid}", headers=H, timeout=10)
    if r.status_code != 200:
        sys.exit(f"設為預設失敗 {r.status_code}: {r.text}")
    print("已設為預設選單。完成 ✓")


if __name__ == "__main__":
    main()
