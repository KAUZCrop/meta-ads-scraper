import sys
import asyncio
import subprocess
import streamlit as st

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@st.cache_resource
def ensure_playwright_browser():
    subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        check=True,
    )
    return True


import time
import uuid
import io
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

st.set_page_config(
    page_title="AD INTEL — Meta Ad Library",
    page_icon="◼",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
:root {
    --bg:#0d0f12; --bg2:#13161b; --bg3:#1a1e26;
    --border:#252a34; --border2:#2f3542;
    --accent:#4f7cff; --accent2:#7c5cff;
    --danger:#ff4f6b; --success:#3dffa0; --warn:#ffb84f;
    --text:#e8eaf0; --muted:#6b7280; --tag:#1e2330;
}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;background-color:var(--bg)!important;color:var(--text)!important;}
.stApp{background-color:var(--bg)!important;}
[data-testid="stHeader"]{background:var(--bg)!important;border-bottom:1px solid var(--border);}
[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--border)!important;}
[data-testid="stSidebar"] *{color:var(--text)!important;}
.block-container{padding-top:4.5rem;padding-bottom:3rem;max-width:1600px;}
.ad-header{margin-bottom:2rem;padding-bottom:1.2rem;border-bottom:1px solid var(--border);}
.ad-header-inner{display:flex;align-items:center;gap:10px;}
.ad-logo{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;letter-spacing:-.5px;color:var(--text);line-height:1;}
.ad-logo span{color:var(--accent);}
.ad-version{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);border:1px solid var(--border2);padding:2px 8px;border-radius:4px;line-height:1.4;}
.ad-subtitle{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);letter-spacing:1.5px;margin-top:8px;}
.sidebar-label{font-family:'DM Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:1.2px;text-transform:uppercase;margin-bottom:10px;margin-top:4px;}
.search-wrapper{background:var(--bg2);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:1.2rem;}
.search-label{font-family:'DM Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:14px 16px;position:relative;overflow:hidden;}
.stat-card::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),var(--accent2));opacity:0;transition:opacity .2s;}
.stat-card:hover::before{opacity:1;}
.stat-label{font-family:'DM Mono',monospace;font-size:9px;color:var(--muted);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}
.stat-value{font-family:'Syne',sans-serif;font-size:26px;font-weight:700;color:var(--text);line-height:1;}
.stat-sub{font-size:11px;color:var(--muted);margin-top:4px;}
.tag-wrap{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1.2rem;}
.kw-tag{font-family:'DM Mono',monospace;font-size:11px;background:var(--tag);border:1px solid var(--border2);color:var(--accent);padding:4px 10px;border-radius:6px;display:inline-flex;align-items:center;gap:6px;}
.kw-tag .dot{width:5px;height:5px;border-radius:50%;background:var(--success);}
.section-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:.8rem;padding-bottom:8px;border-bottom:1px solid var(--border);}
.section-title{font-family:'Syne',sans-serif;font-size:12px;font-weight:700;color:var(--text);letter-spacing:.5px;text-transform:uppercase;}
.section-count{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);}
.asset-body{padding:10px 12px;border-top:1px solid var(--border);background:var(--bg2);border-radius:0 0 10px 10px;}
.asset-kw{font-family:'DM Mono',monospace;font-size:10px;color:var(--accent);letter-spacing:.8px;text-transform:uppercase;margin-bottom:3px;}
.asset-type-badge{display:inline-block;font-family:'DM Mono',monospace;font-size:9px;padding:2px 7px;border-radius:4px;margin-bottom:6px;letter-spacing:.5px;}
.badge-image{background:rgba(79,124,255,.12);color:var(--accent);border:1px solid rgba(79,124,255,.25);}
.badge-video{background:rgba(124,92,255,.12);color:var(--accent2);border:1px solid rgba(124,92,255,.25);}
.badge-star{background:rgba(255,184,79,.12);color:var(--warn);border:1px solid rgba(255,184,79,.25);}
.asset-meta{font-size:11px;color:var(--muted);line-height:1.6;}
.asset-caption{font-size:11px;color:var(--text);margin:4px 0 6px;line-height:1.4;opacity:.7;font-style:italic;}
.stButton>button{font-family:'DM Mono',monospace!important;font-size:11px!important;letter-spacing:.5px!important;border-radius:8px!important;border:1px solid var(--border2)!important;background:var(--bg3)!important;color:var(--muted)!important;transition:all .15s!important;height:34px!important;}
.stButton>button:hover{border-color:var(--accent)!important;color:var(--accent)!important;background:rgba(79,124,255,.08)!important;}
.stDownloadButton>button{font-family:'DM Mono',monospace!important;font-size:11px!important;border-radius:8px!important;border:1px solid var(--border2)!important;background:var(--bg3)!important;color:var(--muted)!important;}
.stTextInput input{background:var(--bg3)!important;border:1px solid var(--border)!important;border-radius:8px!important;color:var(--text)!important;font-family:'DM Sans',sans-serif!important;}
.stTextInput input:focus{border-color:var(--accent)!important;box-shadow:0 0 0 2px rgba(79,124,255,.12)!important;}
div[data-baseweb="select"]>div{background:var(--bg3)!important;border-color:var(--border)!important;}
.stTabs [data-baseweb="tab-list"]{background:transparent!important;border-bottom:1px solid var(--border)!important;gap:0!important;}
.stTabs [data-baseweb="tab"]{font-family:'DM Mono',monospace!important;font-size:11px!important;color:var(--muted)!important;background:transparent!important;padding:8px 16px!important;letter-spacing:.5px!important;}
.stTabs [aria-selected="true"]{color:var(--accent)!important;border-bottom:2px solid var(--accent)!important;}
.stSuccess{background:rgba(61,255,160,.08)!important;border:1px solid rgba(61,255,160,.2)!important;border-radius:8px!important;}
.stWarning{background:rgba(255,184,79,.08)!important;border:1px solid rgba(255,184,79,.2)!important;border-radius:8px!important;}
.stInfo{background:rgba(79,124,255,.08)!important;border:1px solid rgba(79,124,255,.2)!important;border-radius:8px!important;}
.stError{background:rgba(255,79,107,.08)!important;border:1px solid rgba(255,79,107,.2)!important;border-radius:8px!important;}
.empty-state{text-align:center;padding:80px 20px;color:var(--muted);}
.empty-icon{font-size:40px;margin-bottom:16px;opacity:.3;}
.empty-title{font-family:'Syne',sans-serif;font-size:16px;font-weight:600;margin-bottom:8px;color:var(--text);opacity:.5;}
.empty-desc{font-size:13px;line-height:1.6;}
.log-line{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);padding:3px 0;border-bottom:1px solid var(--border);}
.log-line .ts{color:var(--accent);margin-right:8px;}
.log-line .ok{color:var(--success);}
.log-line .err{color:var(--danger);}
hr{border-color:var(--border)!important;}
.stCaption{color:var(--muted)!important;font-size:11px!important;}
a{color:var(--accent)!important;}
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px;}
</style>
""", unsafe_allow_html=True)

# ── Session state ──
DEFAULTS = {
    "assets": [],
    "hidden_asset_ids": set(),
    "search_history": [],
    "search_log": [],
    "last_error": "",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Scraper helpers ──
def valid_asset(w, h):
    if w < 180 or h < 180:
        return False
    r = w / h if h else 0
    return 0.25 <= r <= 3.0

def make_fp(item):
    url = (item.get("image_url") or "").strip()
    p = urlparse(url)
    return (
        f"{p.netloc}{p.path}",
        (item.get("asset_type") or "").strip(),
        (item.get("caption") or "").strip().lower()[:80],
        item.get("width") or 0,
        item.get("height") or 0,
    )

def scrape(keyword, country, max_scrolls, max_assets):
    ensure_playwright_browser()
    search_url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country={country}&q={quote(keyword)}"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage","--disable-extensions",
                  "--disable-plugins","--disable-background-networking",
                  "--no-first-run","--disable-default-apps"],
        )
        ctx = browser.new_context(viewport={"width": 1440, "height": 2000})
        ctx.route("**/*.{woff,woff2,ttf,otf,eot}", lambda r: r.abort())
        page = ctx.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)

        def card_count():
            return page.evaluate("""() => {
                const sels = ['div[class*="x8gbvx8"]','div[data-visualcompletion="ignore-dynamic"]','div._7jyr','div[class*="xh8yej3"]'];
                for (const s of sels) { const n = document.querySelectorAll(s).length; if (n>0) return n; }
                return document.querySelectorAll('img[src*="fbcdn"]').length;
            }""")

        prev, stalls = 0, 0
        for _ in range(max_scrolls):
            page.mouse.wheel(0, 3200)
            waited = 0
            while waited < 3500:
                page.wait_for_timeout(400)
                waited += 400
                cur = card_count()
                if cur > prev:
                    prev = cur; stalls = 0; break
            else:
                stalls += 1
                if stalls >= 2: break

        raw = page.evaluate("""() => {
            const out = [];
            for (const img of document.querySelectorAll('img')) {
                const src = img.currentSrc || img.src || '';
                if (!src || src.startsWith('data:')) continue;
                out.push({type:'image', src, w:img.naturalWidth||img.width||0, h:img.naturalHeight||img.height||0, alt:img.alt||''});
            }
            for (const v of document.querySelectorAll('video')) {
                const poster = v.poster || '';
                if (!poster) continue;
                out.push({type:'video_poster', src:poster, w:v.videoWidth||v.clientWidth||0, h:v.videoHeight||v.clientHeight||0, alt:''});
            }
            return out;
        }""")
        ctx.close(); browser.close()

    seen, collected, now = set(), [], time.strftime("%Y-%m-%d %H:%M:%S")
    for r in raw:
        if len(collected) >= max_assets: break
        src = (r.get("src") or "").strip()
        w, h = int(r.get("w") or 0), int(r.get("h") or 0)
        if not src or not valid_asset(w, h): continue
        asset = {"id":str(uuid.uuid4()),"keyword":keyword,"country":country,
                 "asset_type":r.get("type","image"),"image_url":src,
                 "source_url":search_url,"caption":(r.get("alt") or "").strip(),
                 "width":w,"height":h,"created_at":now,"starred":False}
        fp = make_fp(asset)
        if fp in seen: continue
        seen.add(fp); collected.append(asset)
    return collected

def merge(existing, new_items, hidden_ids):
    known = {make_fp(a) for a in existing}
    known |= {make_fp(a) for a in existing if a["id"] in hidden_ids}
    out, added = list(existing), 0
    for item in new_items:
        fp = make_fp(item)
        if fp in known: continue
        known.add(fp); out.append(item); added += 1
    return out, added

def get_visible(filter_type, filter_kw, filter_star):
    hidden = st.session_state.hidden_asset_ids
    items = [a for a in st.session_state.assets if a["id"] not in hidden]
    if filter_type != "전체":
        items = [a for a in items if a["asset_type"] == filter_type]
    if filter_kw and filter_kw != "전체":
        items = [a for a in items if a["keyword"] == filter_kw]
    if filter_star:
        items = [a for a in items if a.get("starred")]
    return items

def reset():
    st.session_state.assets = []
    st.session_state.hidden_asset_ids = set()
    st.session_state.search_history = []
    st.session_state.search_log = []
    st.session_state.last_error = ""

def star_toggle(asset_id):
    for a in st.session_state.assets:
        if a["id"] == asset_id:
            a["starred"] = not a.get("starred", False)
            break

def get_csv(assets):
    import csv
    fields = ["keyword","country","asset_type","image_url","source_url","caption","width","height","created_at","starred"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for a in assets:
        w.writerow({f: a.get(f, "") for f in fields})
    return buf.getvalue().encode("utf-8-sig")

# ── Header ──
st.markdown("""
<div class="ad-header">
  <div class="ad-header-inner">
    <div class="ad-logo">AD<span>INTEL</span></div>
    <div class="ad-version">v2.1</div>
  </div>
  <div class="ad-subtitle">META AD LIBRARY INTELLIGENCE BOARD</div>
</div>
""", unsafe_allow_html=True)

# ── Sidebar ──
with st.sidebar:
    st.markdown('<div class="sidebar-label">수집 설정</div>', unsafe_allow_html=True)
    country = st.selectbox("국가", ["KR","US","JP","GB","SG","AU"], index=0, label_visibility="collapsed")
    st.caption(f"대상 국가: **{country}**")
    max_scrolls = st.slider("스크롤 깊이", 3, 15, 8, 1)
    max_assets  = st.slider("최대 수집량", 10, 150, 60, 10)
    st.markdown("---")

    st.markdown('<div class="sidebar-label">뷰 설정</div>', unsafe_allow_html=True)
    filter_type = st.selectbox("소재 타입", ["전체","image","video_poster"], label_visibility="collapsed")
    all_kws     = ["전체"] + list(dict.fromkeys(a["keyword"] for a in st.session_state.assets))
    filter_kw   = st.selectbox("키워드 필터", all_kws, label_visibility="collapsed")
    filter_star = st.toggle("⭐ 즐겨찾기만 보기", value=False)
    col_count   = st.select_slider("열 수", options=[2,3,4,5], value=4)
    st.markdown("---")

    st.markdown('<div class="sidebar-label">정렬</div>', unsafe_allow_html=True)
    sort_by = st.selectbox("정렬 기준", ["최신순","오래된순","키워드순","즐겨찾기순"], label_visibility="collapsed")
    st.markdown("---")

    st.markdown('<div class="sidebar-label">데이터 관리</div>', unsafe_allow_html=True)
    shown_for_export = get_visible(filter_type, filter_kw if filter_kw != "전체" else None, filter_star)
    starred_assets   = [a for a in st.session_state.assets if a.get("starred")]

    if shown_for_export:
        st.download_button("📥 현재 보드 CSV", data=get_csv(shown_for_export),
            file_name=f"adintel_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    if starred_assets:
        st.download_button("⭐ 즐겨찾기 CSV", data=get_csv(starred_assets),
            file_name=f"adintel_starred_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)

    st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)
    if st.button("🗑 보드 초기화", use_container_width=True):
        reset(); st.rerun()

    if st.session_state.search_log:
        st.markdown("---")
        st.markdown('<div class="sidebar-label">검색 로그</div>', unsafe_allow_html=True)
        for log in reversed(st.session_state.search_log[-8:]):
            cls = "ok" if log["success"] else "err"
            sym = "+" if log["success"] else "!"
            st.markdown(
                f'<div class="log-line"><span class="ts">{log["time"]}</span>'
                f'<span class="{cls}">[{sym}] {log["keyword"]} — {log["count"]}건</span></div>',
                unsafe_allow_html=True)

# ── Search bar ──
st.markdown('<div class="search-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="search-label">⌕ 키워드 검색</div>', unsafe_allow_html=True)
sc, b1, b2 = st.columns([5, 1, 1])
with sc:
    keyword = st.text_input("keyword",
        placeholder="예: 캐리어, 공기청정기, 스킨케어, 다이어트",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({"_enter": True}))
with b1:
    btn_search = st.button("검색", use_container_width=True)
with b2:
    btn_add = st.button("누적 검색", use_container_width=True)

enter_fired = st.session_state.pop("_enter", False)
if enter_fired:
    btn_search = True

st.caption("↵ 엔터 = 새 검색  ·  누적 검색 = 기존 보드에 추가 (중복·제외 자동 제외)")
st.markdown('</div>', unsafe_allow_html=True)

# ── Search logic ──
if btn_search or btn_add:
    kw = (keyword or "").strip()
    if not kw:
        st.warning("검색어를 입력하세요.")
    else:
        try:
            if btn_search:
                st.session_state.assets = []
                st.session_state.hidden_asset_ids = set()
                st.session_state.search_history = []

            with st.spinner(f"'{kw}' 수집 중 — Meta Ad Library 실시간 접근..."):
                new_items = scrape(kw, country, max_scrolls, max_assets)

            merged, added = merge(st.session_state.assets, new_items, st.session_state.hidden_asset_ids)
            st.session_state.assets = merged

            if kw not in st.session_state.search_history:
                st.session_state.search_history.append(kw)

            st.session_state.search_log.append({"time": time.strftime("%H:%M"), "keyword": kw, "count": added, "success": True})

            if added == 0:
                st.info("새로 추가된 소재가 없습니다.")
            else:
                st.success(f"✓ {added}개 소재 수집 완료")
            st.rerun()

        except Exception as e:
            st.session_state.search_log.append({"time": time.strftime("%H:%M"), "keyword": kw, "count": 0, "success": False})
            st.error(f"오류: {e}")

# ── Stats ──
all_assets   = st.session_state.assets
shown_assets = get_visible(filter_type, filter_kw if filter_kw != "전체" else None, filter_star)

if sort_by == "최신순":
    shown_assets = sorted(shown_assets, key=lambda a: a["created_at"], reverse=True)
elif sort_by == "오래된순":
    shown_assets = sorted(shown_assets, key=lambda a: a["created_at"])
elif sort_by == "키워드순":
    shown_assets = sorted(shown_assets, key=lambda a: a["keyword"])
elif sort_by == "즐겨찾기순":
    shown_assets = sorted(shown_assets, key=lambda a: (not a.get("starred"), a["created_at"]))

img_cnt  = sum(1 for a in shown_assets if a["asset_type"] == "image")
vid_cnt  = sum(1 for a in shown_assets if a["asset_type"] == "video_poster")
star_cnt = sum(1 for a in all_assets if a.get("starred"))
hid_cnt  = len(st.session_state.hidden_asset_ids)
kw_cnt   = len(set(a["keyword"] for a in all_assets))

c1,c2,c3,c4,c5 = st.columns(5)
for col, label, val, sub in [
    (c1,"TOTAL",    len(all_assets),   "누적 수집"),
    (c2,"DISPLAYED",len(shown_assets), f"IMG {img_cnt} · VID {vid_cnt}"),
    (c3,"KEYWORDS", kw_cnt,            "검색 키워드"),
    (c4,"STARRED",  star_cnt,          "즐겨찾기"),
    (c5,"HIDDEN",   hid_cnt,           "제외 소재"),
]:
    col.markdown(f"""<div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{val}</div>
        <div class="stat-sub">{sub}</div>
    </div>""", unsafe_allow_html=True)

# ── Keyword tags ──
if st.session_state.search_history:
    html = '<div class="tag-wrap">'
    for kw in st.session_state.search_history[-20:]:
        cnt = sum(1 for a in all_assets if a["keyword"] == kw)
        html += f'<span class="kw-tag"><span class="dot"></span>{kw} <span style="opacity:.5">({cnt})</span></span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ── Board ──
st.markdown(f"""<div class="section-header">
  <div class="section-title">소재 보드</div>
  <div class="section-count">{len(shown_assets)} assets · {sort_by}</div>
</div>""", unsafe_allow_html=True)

if not shown_assets:
    st.markdown("""<div class="empty-state">
        <div class="empty-icon">◻</div>
        <div class="empty-title">수집된 소재가 없습니다</div>
        <div class="empty-desc">키워드를 입력하고 검색하면<br>Meta Ad Library에서 광고 소재를 실시간으로 수집합니다.</div>
    </div>""", unsafe_allow_html=True)
else:
    cols = st.columns(col_count)
    for idx, item in enumerate(shown_assets):
        with cols[idx % col_count]:
            try:
                st.image(item["image_url"], use_container_width=True)
            except Exception:
                st.markdown('<div style="height:120px;background:var(--bg3);border-radius:8px;display:flex;align-items:center;justify-content:center;color:var(--muted);font-size:11px">이미지 로드 실패</div>', unsafe_allow_html=True)

            badge_cls = "badge-image" if item["asset_type"] == "image" else "badge-video"
            badge_lbl = "IMG" if item["asset_type"] == "image" else "VID"
            star_badge = '<span class="asset-type-badge badge-star">★</span> ' if item.get("starred") else ""
            cap = item.get("caption", "")
            cap_html = f'<div class="asset-caption">"{cap[:55]}{"..." if len(cap)>55 else ""}"</div>' if cap else ""

            st.markdown(f"""<div class="asset-body">
                <div class="asset-kw">{item["keyword"]} · {item["country"]}</div>
                {star_badge}<span class="asset-type-badge {badge_cls}">{badge_lbl}</span>
                {cap_html}
                <div class="asset-meta">{item["width"]}×{item["height"]}px · {item["created_at"][11:16]}</div>
            </div>""", unsafe_allow_html=True)

            ba, bb, bc = st.columns(3)
            with ba:
                star_lbl = "★ 해제" if item.get("starred") else "☆ 저장"
                if st.button(star_lbl, key=f"star_{item['id']}", use_container_width=True):
                    star_toggle(item["id"]); st.rerun()
            with bb:
                if st.button("제외", key=f"hide_{item['id']}", use_container_width=True):
                    st.session_state.hidden_asset_ids.add(item["id"]); st.rerun()
            with bc:
                st.link_button("원본 →", item["source_url"], use_container_width=True)

# ── Footer ──
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
st.markdown(f"""<div style="border-top:1px solid var(--border);padding-top:14px;display:flex;justify-content:space-between;align-items:center;">
  <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)">ADINTEL v2.1 · META AD LIBRARY INTELLIGENCE</span>
  <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)">세션 메모리 기반 · {time.strftime("%Y-%m-%d")}</span>
</div>""", unsafe_allow_html=True)
