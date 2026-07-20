"""個股七指標技術分析 (移植自 tw-stock-line-bot 邏輯,唯讀判讀)。
僅供參考,不構成投資建議。"""
import time
from datetime import datetime, timedelta

import yfinance as yf

_CACHE: dict = {}
_TTL = timedelta(minutes=15)

def _history(symbol: str):
    hit = _CACHE.get(symbol)
    if hit and datetime.now() - hit["ts"] < _TTL:
        return hit["df"]
    for attempt in range(2):
        try:
            df = yf.Ticker(symbol).history(period="6mo", auto_adjust=False)
            if df is None or len(df) < 60:
                raise ValueError("insufficient data")
            _CACHE[symbol] = {"df": df, "ts": datetime.now()}
            return df
        except Exception:
            time.sleep(1 * (attempt + 1))
    return None

def _sig(name, signal, note):
    return {"name": name, "signal": signal, "note": note}  # bull / bear / neutral

def analyze(symbol: str):
    """回傳 {symbol, price, indicators[7], summary} 或 None"""
    candidates = [f"{symbol}.TW", f"{symbol}.TWO"] if symbol.isdigit() else [symbol]
    df = None
    for sym in candidates:
        df = _history(sym)
        if df is not None:
            symbol = sym
            break
    if df is None:
        return None

    c = df["Close"]; h = df["High"]; l = df["Low"]
    price = float(c.iloc[-1])
    out = []

    # 1. 均線交叉 MA5 vs MA20
    ma5, ma20 = c.rolling(5).mean(), c.rolling(20).mean()
    if ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]:
        out.append(_sig("均線交叉", "bull", "MA5 黃金交叉 MA20"))
    elif ma5.iloc[-2] >= ma20.iloc[-2] and ma5.iloc[-1] < ma20.iloc[-1]:
        out.append(_sig("均線交叉", "bear", "MA5 死亡交叉 MA20"))
    else:
        above = ma5.iloc[-1] > ma20.iloc[-1]
        out.append(_sig("均線交叉", "neutral", f"MA5 位於 MA20 {'上方' if above else '下方'},無交叉"))

    # 2. KD (9,3,3)
    low9 = l.rolling(9).min(); high9 = h.rolling(9).max()
    rsv = (c - low9) / (high9 - low9).replace(0, float("nan")) * 100
    k = rsv.ewm(alpha=1/3, adjust=False).mean()
    d = k.ewm(alpha=1/3, adjust=False).mean()
    kv, dv = float(k.iloc[-1]), float(d.iloc[-1])
    if kv < 20 and kv > dv and float(k.iloc[-2]) <= float(d.iloc[-2]):
        out.append(_sig("KD", "bull", f"低檔黃金交叉 (K={kv:.0f})"))
    elif kv < 20:
        out.append(_sig("KD", "bull", f"超賣區 (K={kv:.0f})"))
    elif kv > 80:
        out.append(_sig("KD", "bear", f"超買區 (K={kv:.0f})"))
    else:
        out.append(_sig("KD", "neutral", f"K={kv:.0f} D={dv:.0f}"))

    # 3. RSI (14, Wilder)
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = float((100 - 100 / (1 + rs)).iloc[-1])
    if rsi < 30:
        out.append(_sig("RSI", "bull", f"超賣 (RSI={rsi:.0f})"))
    elif rsi > 70:
        out.append(_sig("RSI", "bear", f"超買 (RSI={rsi:.0f})"))
    else:
        out.append(_sig("RSI", "neutral", f"RSI={rsi:.0f}"))

    # 4. MACD (12,26,9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    if float(dif.iloc[-2]) <= float(dea.iloc[-2]) and float(dif.iloc[-1]) > float(dea.iloc[-1]):
        out.append(_sig("MACD", "bull", "DIF 上穿 DEA (柱翻紅)"))
    elif float(dif.iloc[-2]) >= float(dea.iloc[-2]) and float(dif.iloc[-1]) < float(dea.iloc[-1]):
        out.append(_sig("MACD", "bear", "DIF 下穿 DEA"))
    else:
        pos = float(dif.iloc[-1]) > float(dea.iloc[-1])
        out.append(_sig("MACD", "neutral", f"DIF {'高於' if pos else '低於'} DEA,無交叉"))

    # 5. 布林通道 (20, 2σ)
    mid = c.rolling(20).mean(); sd = c.rolling(20).std()
    upper = float((mid + 2 * sd).iloc[-1]); lower = float((mid - 2 * sd).iloc[-1])
    if price > upper:
        out.append(_sig("布林通道", "bull", "突破上軌 (強勢)"))
    elif price < lower:
        out.append(_sig("布林通道", "bear", "跌破下軌 (弱勢)"))
    else:
        pct = (price - lower) / (upper - lower) * 100 if upper != lower else 50
        out.append(_sig("布林通道", "neutral", f"通道內 {pct:.0f}% 位置"))

    # 6. 20 日突破
    high20 = float(h.iloc[-21:-1].max())
    if price >= high20:
        out.append(_sig("突破", "bull", "突破 20 日新高"))
    else:
        out.append(_sig("突破", "neutral", f"距 20 日高點 {(high20 - price) / high20 * 100:.1f}%"))

    # 7. 均線多頭排列 5>10>20>60
    m10, m60 = c.rolling(10).mean(), c.rolling(60).mean()
    if float(ma5.iloc[-1]) > float(m10.iloc[-1]) > float(ma20.iloc[-1]) > float(m60.iloc[-1]):
        out.append(_sig("均線排列", "bull", "多頭排列 5>10>20>60"))
    elif float(ma5.iloc[-1]) < float(m10.iloc[-1]) < float(ma20.iloc[-1]) < float(m60.iloc[-1]):
        out.append(_sig("均線排列", "bear", "空頭排列 5<10<20<60"))
    else:
        out.append(_sig("均線排列", "neutral", "均線糾結"))

    bulls = sum(1 for s in out if s["signal"] == "bull")
    bears = sum(1 for s in out if s["signal"] == "bear")
    score = bulls - bears
    verdict = "偏多" if score >= 3 else ("偏空" if score <= -3 else "觀望")
    return {"symbol": symbol, "price": round(price, 2),
            "indicators": out,
            "summary": {"bulls": bulls, "bears": bears, "verdict": verdict}}
