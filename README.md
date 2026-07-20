# 樹德市場觀察室 · LINE Bot

給樹德企業（SHUTER）經營層的市場方向諮詢 LINE Bot。服務對象：公司經營層（總經理、董事長）。

主管在 LINE 上用口語直接問，例如「最近台股怎麼看？」「美股這波修正原因？」「半導體趨勢？」「新台幣升值對出口的影響？」，由 Claude AI 結合當日六大指數快照與財經新聞標題，給沉穩、精簡、決策者導向的市場方向解讀。另保留「大盤／分析代號／報告」等快速指令。

> ⚖️ 定位：提供**市場資訊與趨勢參考**，非投資建議。系統 prompt 內建合規護欄（不喊買賣特定商品、不承諾報酬）。

---

## 功能一覽

| 使用者輸入 | 回覆 |
|---|---|
| 自然語言（任何市場問題） | Claude AI 市場方向諮詢（含當日指數＋新聞脈絡） |
| `大盤` | 六大指數即時行情（台股、S&P 500、NASDAQ、費半、日經、美元/台幣） |
| `分析 2330` | 個股七指標多空判讀（均線、KD、RSI、MACD、布林、突破、排列） |
| `2330`／`NVDA` | 個股即時報價 |
| `報告` | 最新財經研報／晨訊（鉅亨標題＋原文連結） |
| `我的ID` | 顯示自己的 LINE userId（用來加白名單） |
| `幫助` | 使用說明 |

**存取控制**：預設開放（`ALLOWED_USER_IDS` 留空）——由官方帳號分享給誰來控制使用對象。若日後想在程式層鎖定特定 LINE userId，可在 `ALLOWED_USER_IDS` 填入名單，名單外的人會收到婉拒訊息（選用，非必要）。

---

## 技術架構

- **語言／框架**：Python 3.13 + Flask（沿用 wealthbot 熟悉的技術棧）
- **AI**：Anthropic Claude Messages API（預設模型 `claude-sonnet-4-6`，可用環境變數覆寫）
- **行情資料**：yfinance（指數／報價／技術分析）
- **新聞**：鉅亨公開新聞 API（只取標題＋連結）
- **部署**：Render.com（免費方案即可，自動 HTTPS，webhook 開箱即用）
- 無資料庫、無登入系統 —— 刻意做輕，方便長期零維運。

```
shuter-market-bot/
├── app.py              Flask webhook（驗簽 → 分流 → reply）+ /health
├── bot.py              訊息路由、白名單、指令、AI 分流
├── ai.py              Claude 封裝 + 市場諮詢 system prompt + 即時市場脈絡注入
├── config.py          環境變數
├── market/            行情/技術分析/新聞（自 wealthbot 抽出，無資料庫相依）
│   ├── data.py        指數、報價
│   ├── analysis.py    七指標技術分析
│   └── research.py    鉅亨新聞聚合
├── brand/             品牌視覺
│   ├── oa_avatar_640.png          LINE 官方帳號頭像
│   ├── richmenu_2500x843.png      Rich Menu 底圖
│   └── gen_brand.py               重新產生視覺的腳本
├── rich_menu_setup.py  一鍵上架 Rich Menu
├── render.yaml         Render 部署設定
└── requirements.txt
```

詳細上線步驟見 **SETUP.md**。

---

## 環境變數

| 變數 | 必填 | 說明 |
|---|---|---|
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | LINE Messaging API channel 的長期 token |
| `LINE_CHANNEL_SECRET` | ✅ | 同 channel 的 secret（webhook 驗簽） |
| `ANTHROPIC_API_KEY` | ✅ | Claude API 金鑰 |
| `ANTHROPIC_MODEL` | — | 預設 `claude-sonnet-4-6` |
| `ALLOWED_USER_IDS` | — | 逗號分隔的 LINE userId 白名單；留空＝setup 模式 |
| `ORG_NAME` | — | 預設「樹德企業」 |
| `BOT_NAME` | — | 預設「樹德市場觀察室」 |

## 本機測試

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env      # 填入金鑰
venv/bin/python app.py    # http://localhost:5000/health
```
