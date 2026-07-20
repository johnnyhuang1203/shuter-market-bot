"""報告/晨訊聚合:鉅亨公開新聞 API(只取標題+連結,15 分鐘快取,不存內文)。
版權說明:僅聚合標題與原文連結,內容一律導回原站。"""
import time
import requests

_CACHE: dict = {}   # cat -> (ts, rows)
_TTL = 900

# 鉅亨公開分類 → 顯示名
CATEGORIES = {
    "stock_report": "專家觀點",
    "tw_macro":     "總經",
    "fund":         "基金",
    "tw_stock":     "台股新聞",
}

def fetch_cnyes(cat: str, limit: int = 15):
    if cat not in CATEGORIES:
        return []
    now = time.time()
    hit = _CACHE.get(cat)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    try:
        r = requests.get(
            f"https://api.cnyes.com/media/api/v1/newslist/category/{cat}",
            params={"limit": limit},
            headers={"User-Agent": "Mozilla/5.0 (WealthBot link aggregator)"},
            timeout=10)
        data = (r.json().get("items") or {}).get("data") or []
        rows = [{
            "title": d.get("title"),
            "url": f"https://news.cnyes.com/news/id/{d.get('newsId')}",
            "published_at": d.get("publishAt"),
            "source": "鉅亨網",
            "category": CATEGORIES[cat],
        } for d in data if d.get("newsId")]
        _CACHE[cat] = (now, rows)
        return rows
    except Exception as e:
        print(f"[research] cnyes {cat} failed: {e}", flush=True)
        return hit[1] if hit else []

# 固定連結牆(公開頁,點出去原站)
LINK_WALL = [
    {"group": "官方資料", "links": [
        {"name": "公開資訊觀測站・法說會", "url": "https://mops.twse.com.tw/mops/#/web/t100sb02_1"},
        {"name": "證交所研究報告", "url": "https://www.twse.com.tw/zh/products/report"},
    ]},
    {"group": "總經 / 研究", "links": [
        {"name": "財經M平方(快報)", "url": "https://www.macromicro.me/blog"},
        {"name": "MM 全球財經日曆", "url": "https://www.macromicro.me/calendar"},
        {"name": "鉅亨研究報告區", "url": "https://www.cnyes.com/report/"},
    ]},
    {"group": "投顧公開晨訊", "links": [
        {"name": "群益投顧", "url": "https://www.capitalim.com.tw/newsite/research-report"},
        {"name": "元大投顧", "url": "https://www.yuanta-consulting.com.tw/"},
        {"name": "國泰證期顧問", "url": "https://consultant.cathayfut.com.tw/CT_research.aspx"},
        {"name": "中國信託投顧", "url": "https://www.ctbcsis.com.tw/"},
        {"name": "凱基投顧(市場洞察)", "url": "https://www.kgisia.com.tw/zh-tw/report"},
    ]},
    {"group": "房市行情(各區域房價指數)", "links": [
        {"name": "國泰房地產指數(政大)", "url": "https://rer.nccu.edu.tw/"},
        {"name": "信義房價指數季報", "url": "https://www.sinyinews.com.tw/quarterly"},
        {"name": "永慶房價網", "url": "https://price.yungching.com.tw/"},
        {"name": "內政部不動產資訊平台", "url": "https://pip.moi.gov.tw/"},
        {"name": "MM 各縣市信義房價指數", "url": "https://www.macromicro.me/collections/15/tw-housing-relative"},
    ]},
]
