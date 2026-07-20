"""市場資料層 (yfinance)。移植自 MyFCN data_source.py 精簡版:
15 分鐘記憶體快取 + 重試 2 次。回傳 (price, prev_close) 供算漲跌。"""
import time
from datetime import datetime, timedelta

import yfinance as yf

_CACHE: dict = {}
_TTL = timedelta(minutes=15)

# 主要指數/匯率 (Yahoo 代號 → 顯示名)
INDICES = [
    ("^TWII",  "台股加權"),
    ("^GSPC",  "S&P 500"),
    ("^IXIC",  "NASDAQ"),
    ("^SOX",   "費城半導體"),
    ("^N225",  "日經 225"),
    ("TWD=X",  "美元/台幣"),
]

def _fetch(symbol: str):
    """回傳 dict(price, prev, ts) 或 None"""
    hit = _CACHE.get(symbol)
    if hit and datetime.now() - hit["ts"] < _TTL:
        return hit
    last_err = None
    for attempt in range(2):
        try:
            h = yf.Ticker(symbol).history(period="5d", auto_adjust=False)
            closes = [float(c) for c in h["Close"].dropna().tolist()]
            if not closes:
                raise ValueError("no data")
            out = {"price": closes[-1],
                   "prev": closes[-2] if len(closes) > 1 else closes[-1],
                   "ts": datetime.now()}
            _CACHE[symbol] = out
            return out
        except Exception as e:
            last_err = e
            time.sleep(1 * (attempt + 1))
    print(f"[market] fetch {symbol} failed: {last_err}", flush=True)
    return None

def quote(symbol: str):
    """台股免加後綴:純數字自動試 .TW (上市),失敗再試 .TWO (上櫃)"""
    candidates = [f"{symbol}.TW", f"{symbol}.TWO"] if symbol.isdigit() else [symbol]
    for sym in candidates:
        d = _fetch(sym)
        if d:
            chg = (d["price"] - d["prev"]) / d["prev"] * 100 if d["prev"] else 0.0
            return {"symbol": sym, "price": round(d["price"], 2),
                    "change_pct": round(chg, 2)}
    return None

def history(symbol: str, days: int = 30):
    """回傳近 N 日收盤序列 [{d, c}],台股純數字自動 .TW/.TWO"""
    candidates = [f"{symbol}.TW", f"{symbol}.TWO"] if symbol.isdigit() else [symbol]
    for sym in candidates:
        key = f"hist:{sym}:{days}"
        hit = _CACHE.get(key)
        if hit and datetime.now() - hit["ts"] < _TTL:
            return hit["out"]
        try:
            df = yf.Ticker(sym).history(period=f"{max(days + 10, 40)}d", auto_adjust=False)
            closes = df["Close"].dropna()
            if len(closes) < 5:
                continue
            out = {"symbol": sym,
                   "points": [{"d": idx.strftime("%m/%d"), "c": round(float(v), 2)}
                              for idx, v in closes.tail(days).items()]}
            _CACHE[key] = {"out": out, "ts": datetime.now()}
            return out
        except Exception:
            continue
    return None

def indices():
    out = []
    for sym, name in INDICES:
        q = quote(sym)
        if q:
            q["name"] = name
            out.append(q)
    return out
