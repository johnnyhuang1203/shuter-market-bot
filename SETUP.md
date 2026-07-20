# 樹德市場觀察室 · 上線指南（從零到能用）

這份照著做，就能把 bot 上線給樹德企業經營層使用。
全部大約 40–60 分鐘。分成五步：

```
A. 開 LINE 官方帳號 + Messaging API   → 拿到 2 組金鑰
B. 申請 Claude API 金鑰               → 拿到 1 組金鑰
C. 部署到 Render                      → 拿到 bot 網址
D. 把網址設回 LINE（webhook）          → bot 開始會回話
E. 換頭像、上選單、鎖定兩位主管         → 正式上線
```

準備一個記事本，把過程中拿到的 3 組金鑰和 1 個網址記下來。

---

## A. 開 LINE 官方帳號 + Messaging API

### A-1 建立官方帳號
1. 到 **LINE Developers**：https://developers.line.biz/console/
2. 用你的 LINE 帳號登入。
3. 建立一個 **Provider**（提供者，例如填「樹德企業」）。
4. 在該 Provider 底下，點 **Create a new channel** → 選 **Messaging API**。
5. 填寫：
   - Channel name：`樹德市場觀察室`
   - Channel description：市場方向諮詢
   - Category / Subcategory：隨意（例如 金融）
   - 其餘照預設，勾同意條款 → 建立。

### A-2 拿到兩組金鑰
進入剛建好的 channel：
- **Basic settings** 分頁 → 找到 **Channel secret** → 複製（這是第 1 組）。
- **Messaging API** 分頁 → 最下面 **Channel access token (long-lived)** → 按 **Issue** 產生 → 複製（這是第 2 組）。

> 記事本記下：
> `LINE_CHANNEL_SECRET = ...`
> `LINE_CHANNEL_ACCESS_TOKEN = ...`

### A-3 關掉自動回覆（重要）
還在 **Messaging API** 分頁：
- 找到 **Auto-reply messages** → 關閉（Disabled）。
- **Greeting messages** 可留著或關掉皆可（我們程式自己有歡迎詞）。
- 這樣主管的訊息才會交給我們的 bot，而不是被 LINE 官方的罐頭訊息攔走。

---

## B. 申請 Claude API 金鑰

1. 到 **Anthropic Console**：https://console.anthropic.com/
2. 註冊 / 登入 → 左側 **API Keys** → **Create Key** → 複製（這是第 3 組）。
3. 到 **Billing** 儲值一點額度（例如 US$5 起，足夠這個只有兩人用的 bot 跑很久）。

> 記事本記下：`ANTHROPIC_API_KEY = ...`

### B-2 （選用）語音聽打金鑰 —— 讓主管能直接傳 LINE 語音訊息

主管用**手機鍵盤上的麥克風口述**（把說的話變文字送出）本來就能用，不需要這一步。
只有想讓他們**直接錄一段 LINE 語音訊息**丟給 bot、由 bot 自動聽打時，才需要：

1. 到 **Groq Console**：https://console.groq.com/keys （免費，不需綁信用卡）
2. 登入 → **Create API Key** → 複製（這是選用的第 4 組）。
3. Whisper 聽打在 Groq 免費額度內，兩人使用綽綽有餘。

> 記事本記下（選用）：`GROQ_API_KEY = ...`
> 沒填也沒關係：主管傳語音時，bot 會友善提示改用打字或手機口述。

---

## C. 部署到 Render（最省事，免費方案即可）

### C-1 先把程式放上你的 GitHub
把本資料夾（shuter-market-bot）推到一個 GitHub repo。可以：
- 新開一個 repo（例如 `shuter-market-bot`），把這些檔案上傳；或
- 放進你現有帳號皆可。私有 repo 也行。

### C-2 在 Render 建立服務
1. 到 **Render**：https://render.com/ → 用 GitHub 登入。
2. **New +** → **Web Service** → 連到剛剛那個 repo。
3. Render 會自動讀到 `render.yaml`，大部分欄位會自動帶好。確認：
   - Runtime：Python
   - Build command：`pip install -r requirements.txt`
   - Start command：`gunicorn app:app --workers 2 --timeout 60 --bind 0.0.0.0:$PORT`
   - Plan：**Free**
4. 在 **Environment**（環境變數）區塊，填入 A、B 拿到的金鑰：
   | Key | Value |
   |---|---|
   | `LINE_CHANNEL_ACCESS_TOKEN` | （第 2 組） |
   | `LINE_CHANNEL_SECRET` | （第 1 組） |
   | `ANTHROPIC_API_KEY` | （第 3 組） |
   | `GROQ_API_KEY` | （選用，第 4 組；不填則語音聽打停用） |
   | `ALLOWED_USER_IDS` | **先留空**（第 E 步再填） |
5. 按 **Create Web Service**，等它跑完（約 2–3 分鐘），狀態變 **Live**。
6. 上方會有你的網址，例如：`https://shuter-market-bot.onrender.com`
   - 打開 `你的網址/health`，看到 `{"ok": true, ...}` 就成功了。

> 記事本記下：`bot 網址 = https://xxxx.onrender.com`

> 💡 Render 免費方案閒置一段時間會休眠，第一則訊息可能慢 20–30 秒喚醒，之後就順了。兩位主管若覺得偶爾第一句慢，屬正常；要完全避免可升級 Render 付費方案（約 US$7/月）或改用 Google Cloud Run。

---

## D. 把網址設回 LINE（webhook）

1. 回到 **LINE Developers** → 你的 channel → **Messaging API** 分頁。
2. **Webhook URL** 填：`你的網址/webhook`
   例：`https://shuter-market-bot.onrender.com/webhook`
3. 按 **Update** → 再按 **Verify**，看到 Success 即可。
4. 把 **Use webhook** 打開（Enabled）。

現在用你自己的手機加這個官方帳號為好友，隨便打一句話，應該就會收到回覆了 🎉

---

## E. 換頭像、上選單、鎖定兩位主管

### E-1 換頭像
LINE Developers → channel → **Basic settings**（或到 LINE Official Account Manager）→ 上傳頭像，用 `brand/oa_avatar_640.png`。

### E-2 上 Rich Menu（底部選單）
在你電腦上（已設好金鑰的環境）執行一次：
```bash
export LINE_CHANNEL_ACCESS_TOKEN="第2組token"
python rich_menu_setup.py
```
完成後，聊天室底部會出現「即時大盤／最新研報／使用說明」三格選單。
（也可以之後在 LINE Official Account Manager 用網頁介面手動上傳同一張圖。）

### E-3 收集兩位主管的 LINE ID
1. 請要使用的主管各自加這個官方帳號為好友。
2. 請她們在聊天室各打一句 **`我的ID`**，bot 會回一串 `U` 開頭的英數字。
3. 把兩串 ID 收集起來。
   （你也可以到 Render 的 **Logs** 看，每則訊息都會印出寄件者的 userId。）

### E-4 啟用白名單（鎖定只有兩人能用）
1. 回 Render → **Environment** → 編輯 `ALLOWED_USER_IDS`，填入兩串 ID，用逗號隔開：
   ```
   ALLOWED_USER_IDS = U主管1的id,U主管2的id
   ```
2. 儲存，Render 會自動重啟。之後名單外的人再傳訊息，只會收到「本服務為樹德企業指定主管專用」的婉拒。

完成 ✅ 正式上線。

---

## 上線後測試清單

- [ ] `你的網址/health` 回 `{"ok": true, "ai": true, "stt": true/false, ...}`
- [ ] 傳「現在適合布局哪個市場、哪個商品？」→ 收到**建議圖卡**（市場／商品／方向／風險）
- [ ] 接著追問「那風險呢？」→ bot **記得前文**，接續同一標的回答
- [ ] 傳「大盤」→ 收到六大指數圖卡
- [ ] 傳「分析 2330」→ 收到七指標判讀
- [ ] （若有設 GROQ）錄一段語音問問題 → bot 先回「🎙️ 我聽到…」再給圖卡
- [ ] 傳「重新開始」→ 清掉對話記憶
- [ ] 用名單外的帳號傳話 → 收到婉拒訊息（需先在第 E 步啟用白名單）

---

## 費用估算（兩人使用）

| 項目 | 費用 |
|---|---|
| LINE 官方帳號 | 免費方案即可（每月有免費訊息額度；本 bot 用 reply 回覆不佔推播額度） |
| Render | 免費方案 US$0（或付費 ~US$7/月免休眠） |
| Claude API | 用多少算多少，兩人問答一個月通常 US$1–5 之譜 |

## 之後想調整

- **換模型**：改環境變數 `ANTHROPIC_MODEL`。
- **改 bot 語氣／諮詢範圍**：改 `ai.py` 最上面的 `SYSTEM` 文字。
- **改選單樣式**：改 `brand/gen_brand.py` 重新產生，再跑一次 `rich_menu_setup.py`。
- **換官方 logo**：把樹德官方 logo 檔給我，我可精準替換頭像與選單的視覺。
- **加即時新聞理解 / 網路搜尋**：目前 AI 會參考當日指數與鉅亨標題；若要讓它能即時查更多，可再加 Claude 的 web search 工具（需另議）。
