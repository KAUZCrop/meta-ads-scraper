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

import streamlit as st
from playwright.sync_api import sync_playwright

# =========================================================
# Streamlit page config
# =========================================================
st.set_page_config(
    page_title="AD INTEL — Meta Ad Library",
    page_icon="◼",
    layout="wide",
)

# =========================================================
# Custom UI — 대행사 내부 툴 스타일
# =========================================================
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

    :root {
        --bg:       #0d0f12;
        --bg2:      #13161b;
        --bg3:      #1a1e26;
        --border:   #252a34;
        --border2:  #2f3542;
        --accent:   #4f7cff;
        --accent2:  #7c5cff;
        --danger:   #ff4f6b;
        --success:  #3dffa0;
        --text:     #e8eaf0;
        --muted:    #6b7280;
        --tag:      #1e2330;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: var(--bg) !important;
        color: var(--text) !important;
    }

    .stApp {
        background-color: var(--bg) !important;
    }

    [data-testid="stHeader"] {
        background: var(--bg) !important;
        border-bottom: 1px solid var(--border);
    }

    [data-testid="stSidebar"] {
        background: var(--bg2) !important;
        border-right: 1px solid var(--border) !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--text) !important;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1600px;
    }

    /* 헤더 */
    .ad-header {
        display: flex;
        align-items: flex-end;
        gap: 16px;
        margin-bottom: 2rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
    }

    .ad-logo {
        font-family: 'Syne', sans-serif;
        font-size: 22px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text);
    }

    .ad-logo span {
        color: var(--accent);
    }

    .ad-version {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--muted);
        margin-bottom: 3px;
        border: 1px solid var(--border2);
        padding: 2px 8px;
        border-radius: 4px;
    }

    .ad-subtitle {
        font-size: 13px;
        color: var(--muted);
        margin-left: auto;
        font-family: 'DM Mono', monospace;
    }

    /* 검색바 */
    .search-wrapper {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 1.5rem;
        transition: border-color 0.2s;
    }

    .search-wrapper:focus-within {
        border-color: var(--accent);
    }

    .search-label {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--muted);
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    /* 스탯 카드 */
    .stat-row {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 1.5rem;
    }

    .stat-card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 16px 18px;
        position: relative;
        overflow: hidden;
    }

    .stat-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, var(--accent), var(--accent2));
        opacity: 0;
        transition: opacity 0.2s;
    }

    .stat-card:hover::before { opacity: 1; }

    .stat-label {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--muted);
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 8px;
    }

    .stat-value {
        font-family: 'Syne', sans-serif;
        font-size: 28px;
        font-weight: 700;
        color: var(--text);
        line-height: 1;
    }

    .stat-sub {
        font-size: 11px;
        color: var(--muted);
        margin-top: 4px;
    }

    /* 키워드 태그 */
    .tag-wrap { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 1.5rem; }

    .kw-tag {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        background: var(--tag);
        border: 1px solid var(--border2);
        color: var(--accent);
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }

    .kw-tag .dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        background: var(--success);
        display: inline-block;
    }

    /* 섹션 헤더 */
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 10px;
        border-bottom: 1px solid var(--border);
    }

    .section-title {
        font-family: 'Syne', sans-serif;
        font-size: 13px;
        font-weight: 700;
        color: var(--text);
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }

    .section-count {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--muted);
    }

    /* 소재 카드 */
    .asset-card {
        background: var(--bg2);
        border: 1px solid var(--border);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 12px;
        transition: border-color 0.15s, transform 0.15s;
    }

    .asset-card:hover {
        border-color: var(--border2);
        transform: translateY(-1px);
    }

    .asset-img-wrap {
        position: relative;
        background: var(--bg3);
    }

    .asset-body {
        padding: 12px 14px;
        border-top: 1px solid var(--border);
    }

    .asset-kw {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--accent);
        letter-spacing: 0.8px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .asset-type-badge {
        display: inline-block;
        font-family: 'DM Mono', monospace;
        font-size: 9px;
        padding: 2px 7px;
        border-radius: 4px;
        margin-bottom: 8px;
        letter-spacing: 0.5px;
    }

    .badge-image {
        background: rgba(79, 124, 255, 0.12);
        color: var(--accent);
        border: 1px solid rgba(79, 124, 255, 0.25);
    }

    .badge-video {
        background: rgba(124, 92, 255, 0.12);
        color: var(--accent2);
        border: 1px solid rgba(124, 92, 255, 0.25);
    }

    .asset-meta {
        font-size: 11px;
        color: var(--muted);
        line-height: 1.6;
    }

    .asset-caption {
        font-size: 12px;
        color: var(--text);
        margin-top: 6px;
        margin-bottom: 8px;
        line-height: 1.4;
        opacity: 0.8;
        font-style: italic;
    }

    /* 버튼 */
    .stButton > button {
        font-family: 'DM Mono', monospace !important;
        font-size: 11px !important;
        letter-spacing: 0.5px !important;
        border-radius: 8px !important;
        border: 1px solid var(--border2) !important;
        background: var(--bg3) !important;
        color: var(--muted) !important;
        transition: all 0.15s !important;
        height: 34px !important;
    }

    .stButton > button:hover {
        border-color: var(--accent) !important;
        color: var(--accent) !important;
        background: rgba(79, 124, 255, 0.08) !important;
    }

    .stDownloadButton > button {
        font-family: 'DM Mono', monospace !important;
        font-size: 11px !important;
        border-radius: 8px !important;
        border: 1px solid var(--border2) !important;
        background: var(--bg3) !important;
        color: var(--muted) !important;
    }

    /* 입력 필드 */
    .stTextInput input {
        background: var(--bg3) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-family: 'DM Sans', sans-serif !important;
    }

    .stTextInput input:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(79, 124, 255, 0.12) !important;
    }

    .stSelectbox > div > div {
        background: var(--bg3) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
    }

    .stSlider > div { padding: 4px 0; }

    /* 알림 */
    .stSuccess {
        background: rgba(61, 255, 160, 0.08) !important;
        border: 1px solid rgba(61, 255, 160, 0.2) !important;
        border-radius: 8px !important;
        color: var(--success) !important;
    }

    .stWarning {
        background: rgba(255, 160, 50, 0.08) !important;
        border: 1px solid rgba(255, 160, 50, 0.2) !important;
        border-radius: 8px !important;
    }

    .stInfo {
        background: rgba(79, 124, 255, 0.08) !important;
        border: 1px solid rgba(79, 124, 255, 0.2) !important;
        border-radius: 8px !important;
    }

    /* 구분선 */
    hr { border-color: var(--border) !important; }

    /* 탭 */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent !important;
        border-bottom: 1px solid var(--border) !important;
        gap: 0 !important;
    }

    .stTabs [data-baseweb="tab"] {
        font-family: 'DM Mono', monospace !important;
        font-size: 11px !important;
        color: var(--muted) !important;
        background: transparent !important;
        padding: 8px 16px !important;
        letter-spacing: 0.5px !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
    }

    /* 사이드바 */
    .sidebar-section {
        margin-bottom: 1.5rem;
        padding-bottom: 1.5rem;
        border-bottom: 1px solid var(--border);
    }

    .sidebar-label {
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--muted);
        letter-spacing: 1.2px;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    /* 필터 칩 */
    .filter-chip {
        display: inline-block;
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        padding: 3px 9px;
        border-radius: 5px;
        border: 1px solid var(--border2);
        color: var(--muted);
        margin-right: 6px;
        margin-bottom: 6px;
    }

    /* 툴팁/캡션 */
    .stCaption { color: var(--muted) !important; font-size: 11px !important; }

    /* 링크 */
    a { color: var(--accent) !important; }

    /* 스피너 */
    .stSpinner > div { border-top-color: var(--accent) !important; }

    /* 스크롤바 */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: var(--bg); }
    ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

    /* 빈 상태 */
    .empty-state {
        text-align: center;
        padding: 80px 20px;
        color: var(--muted);
    }

    .empty-icon {
        font-size: 40px;
        margin-bottom: 16px;
        opacity: 0.3;
    }

    .empty-title {
        font-family: 'Syne', sans-serif;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 8px;
        color: var(--text);
        opacity: 0.5;
    }

    .empty-desc {
        font-size: 13px;
        line-height: 1.6;
    }

    /* 로그 라인 */
    .log-line {
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--muted);
        padding: 3px 0;
        border-bottom: 1px solid var(--border);
    }

    .log-line .ts { color: var(--accent); margin-right: 10px; }
    .log-line .ok { color: var(--success); }
    .log-line .err { color: var(--danger); }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================================================
# Session state
# =========================================================
defaults = {
    "assets": [],
    "hidden_asset_ids": set(),
    "search_history": [],
    "last_error": "",
    "search_log": [],
    "view_mode": "grid",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# =========================================================
# Scraper helpers
# =========================================================
def valid_asset(width: int, height: int) -> bool:
    if width < 180 or height < 180:
        return False
    ratio = width / height if height else 0
    if ratio > 3.0 or ratio < 0.25:
        return False
    return True


def make_asset_fingerprint(item):
    image_url = (item.get("image_url") or "").strip()
    caption = (item.get("caption") or "").strip().lower()
    width = item.get("width") or 0
    height = item.get("height") or 0
    asset_type = (item.get("asset_type") or "").strip()
    parsed = urlparse(image_url)
    normalized_url = f"{parsed.netloc}{parsed.path}"
    return (normalized_url, asset_type, caption[:80], width, height)


def extract_assets_from_meta(keyword: str, country: str = "KR", max_scrolls: int = 8, max_assets: int = 80):
    ensure_playwright_browser()

    url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country={country}&q={quote(keyword)}"
    )

    collected = []
    seen_keys = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 2000})
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(7000)

        for _ in range(max_scrolls):
            page.mouse.wheel(0, 3200)
            page.wait_for_timeout(1800)

        js = """
        () => {
            const results = [];

            const imgs = Array.from(document.querySelectorAll('img'));
            for (const img of imgs) {
                const src = img.currentSrc || img.src || '';
                results.push({
                    asset_type: 'image',
                    src: src,
                    width: img.naturalWidth || 0,
                    height: img.naturalHeight || 0,
                    alt: img.alt || ''
                });
            }

            const videos = Array.from(document.querySelectorAll('video'));
            for (const video of videos) {
                const poster = video.poster || '';
                results.push({
                    asset_type: 'video_poster',
                    src: poster,
                    width: video.videoWidth || video.clientWidth || 0,
                    height: video.videoHeight || video.clientHeight || 0,
                    alt: ''
                });
            }

            return results;
        }
        """

        candidates = page.evaluate(js)
        browser.close()

    for item in candidates:
        if len(collected) >= max_assets:
            break

        src = (item.get("src") or "").strip()
        width = int(item.get("width") or 0)
        height = int(item.get("height") or 0)
        alt = (item.get("alt") or "").strip()
        asset_type = (item.get("asset_type") or "image").strip()

        if not src or src.startswith("data:"):
            continue
        if not valid_asset(width, height):
            continue

        asset = {
            "id": str(uuid.uuid4()),
            "keyword": keyword,
            "country": country,
            "asset_type": asset_type,
            "image_url": src,
            "source_url": url,
            "caption": alt,
            "width": width,
            "height": height,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "starred": False,
        }

        fp = make_asset_fingerprint(asset)
        if fp in seen_keys:
            continue

        seen_keys.add(fp)
        collected.append(asset)

    return collected


# =========================================================
# App helpers
# =========================================================
def merge_assets(existing_assets, new_assets):
    existing_keys = {make_asset_fingerprint(item) for item in existing_assets}
    merged = list(existing_assets)
    added_count = 0
    for item in new_assets:
        fp = make_asset_fingerprint(item)
        if fp in existing_keys:
            continue
        merged.append(item)
        existing_keys.add(fp)
        added_count += 1
    return merged, added_count


def visible_assets(asset_filter="전체", kw_filter=None):
    hidden = st.session_state.hidden_asset_ids
    items = [a for a in st.session_state.assets if a["id"] not in hidden]
    if asset_filter != "전체":
        items = [a for a in items if a["asset_type"] == asset_filter]
    if kw_filter and kw_filter != "전체":
        items = [a for a in items if a["keyword"] == kw_filter]
    return items


def reset_board():
    st.session_state.assets = []
    st.session_state.hidden_asset_ids = set()
    st.session_state.search_history = []
    st.session_state.last_error = ""
    st.session_state.search_log = []


def toggle_star(asset_id):
    for a in st.session_state.assets:
        if a["id"] == asset_id:
            a["starred"] = not a.get("starred", False)
            break


def get_csv_data(assets):
    import csv
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["keyword", "country", "asset_type", "image_url", "source_url", "caption", "width", "height", "created_at"])
    writer.writeheader()
    for a in assets:
        writer.writerow({k: a.get(k, "") for k in writer.fieldnames})
    return output.getvalue().encode("utf-8-sig")


# =========================================================
# Header
# =========================================================
st.markdown("""
<div class="ad-header">
    <div class="ad-logo">AD<span>INTEL</span></div>
    <div class="ad-version">v2.0</div>
    <div class="ad-subtitle">META AD LIBRARY INTELLIGENCE BOARD</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown('<div class="sidebar-label">수집 설정</div>', unsafe_allow_html=True)

    country = st.selectbox(
        "국가",
        ["KR", "US", "JP", "GB", "SG", "AU"],
        index=0,
        label_visibility="collapsed",
    )
    st.caption(f"대상 국가: **{country}**")

    max_scrolls = st.slider("스크롤 깊이", 3, 15, 8, 1)
    max_assets = st.slider("최대 수집량", 10, 120, 50, 10)

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">뷰 설정</div>', unsafe_allow_html=True)

    asset_filter = st.selectbox("소재 타입", ["전체", "image", "video_poster"])

    all_keywords = ["전체"] + list(dict.fromkeys(
        [a["keyword"] for a in st.session_state.assets]
    ))
    kw_filter = st.selectbox("키워드 필터", all_keywords)

    col_count = st.select_slider("열 수", options=[2, 3, 4, 5], value=4)

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-label">데이터 관리</div>', unsafe_allow_html=True)

    shown = visible_assets(asset_filter, kw_filter if kw_filter != "전체" else None)

    if shown:
        csv_data = get_csv_data(shown)
        st.download_button(
            "CSV 내보내기",
            data=csv_data,
            file_name=f"ad_intel_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    if st.button("보드 초기화", use_container_width=True):
        reset_board()
        st.rerun()

    # 검색 로그
    if st.session_state.search_log:
        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">검색 로그</div>', unsafe_allow_html=True)
        for log in reversed(st.session_state.search_log[-6:]):
            status = "ok" if log["success"] else "err"
            symbol = "+" if log["success"] else "!"
            st.markdown(
                f'<div class="log-line">'
                f'<span class="ts">{log["time"]}</span>'
                f'<span class="{status}">[{symbol}] {log["keyword"]} — {log["count"]}건</span>'
                f'</div>',
                unsafe_allow_html=True
            )


# =========================================================
# Search bar
# =========================================================
st.markdown('<div class="search-wrapper">', unsafe_allow_html=True)
st.markdown('<div class="search-label">⌕ 키워드 검색</div>', unsafe_allow_html=True)

search_col, btn_col1, btn_col2 = st.columns([5, 1, 1])

with search_col:
    keyword = st.text_input(
        "keyword",
        placeholder="예: 캐리어, 공기청정기, 스킨케어, 다이어트",
        label_visibility="collapsed",
    )

with btn_col1:
    search_clicked = st.button("검색", use_container_width=True)

with btn_col2:
    add_clicked = st.button("누적 검색", use_container_width=True)

st.caption("누적 검색: 기존 보드에 결과 추가 / 검색: 새 검색으로 교체")
st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# Search logic
# =========================================================
if search_clicked or add_clicked:
    cleaned = (keyword or "").strip()
    if not cleaned:
        st.warning("검색어를 입력하세요.")
    else:
        try:
            if search_clicked:
                st.session_state.assets = []
                st.session_state.hidden_asset_ids = set()

            with st.spinner(f"'{cleaned}' 수집 중 — Meta Ad Library 실시간 접근 중..."):
                new_results = extract_assets_from_meta(
                    keyword=cleaned,
                    country=country,
                    max_scrolls=max_scrolls,
                    max_assets=max_assets,
                )

            merged, added_count = merge_assets(st.session_state.assets, new_results)
            st.session_state.assets = merged
            st.session_state.last_error = ""

            if cleaned not in st.session_state.search_history:
                st.session_state.search_history.append(cleaned)

            st.session_state.search_log.append({
                "time": time.strftime("%H:%M"),
                "keyword": cleaned,
                "count": added_count,
                "success": True,
            })

            if added_count == 0:
                st.info("새로 추가된 소재가 없습니다. 중복이거나 검색 결과가 적을 수 있어요.")
            else:
                st.success(f"✓  {added_count}개 소재 수집 완료")

            st.rerun()

        except Exception as e:
            st.session_state.last_error = str(e)
            st.session_state.search_log.append({
                "time": time.strftime("%H:%M"),
                "keyword": cleaned,
                "count": 0,
                "success": False,
            })
            st.error(f"오류: {e}")


# =========================================================
# Stats row
# =========================================================
all_assets = st.session_state.assets
shown_assets = visible_assets(asset_filter, kw_filter if kw_filter != "전체" else None)

img_count = sum(1 for a in shown_assets if a["asset_type"] == "image")
vid_count = sum(1 for a in shown_assets if a["asset_type"] == "video_poster")
hidden_count = len(st.session_state.hidden_asset_ids)
kw_count = len(set(a["keyword"] for a in all_assets))

s1, s2, s3, s4 = st.columns(4)

with s1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">TOTAL ASSETS</div>
        <div class="stat-value">{len(all_assets)}</div>
        <div class="stat-sub">누적 수집 소재</div>
    </div>""", unsafe_allow_html=True)

with s2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">DISPLAYED</div>
        <div class="stat-value">{len(shown_assets)}</div>
        <div class="stat-sub">이미지 {img_count} · 영상 {vid_count}</div>
    </div>""", unsafe_allow_html=True)

with s3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">KEYWORDS</div>
        <div class="stat-value">{kw_count}</div>
        <div class="stat-sub">검색 키워드 수</div>
    </div>""", unsafe_allow_html=True)

with s4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">HIDDEN</div>
        <div class="stat-value">{hidden_count}</div>
        <div class="stat-sub">제외 처리 소재</div>
    </div>""", unsafe_allow_html=True)


# =========================================================
# Keyword tags
# =========================================================
if st.session_state.search_history:
    tags_html = '<div class="tag-wrap">'
    for kw in st.session_state.search_history[-15:]:
        count = sum(1 for a in all_assets if a["keyword"] == kw)
        tags_html += f'<span class="kw-tag"><span class="dot"></span>{kw} <span style="opacity:0.5">({count})</span></span>'
    tags_html += '</div>'
    st.markdown(tags_html, unsafe_allow_html=True)


# =========================================================
# Board
# =========================================================
st.markdown(f"""
<div class="section-header">
    <div class="section-title">소재 보드</div>
    <div class="section-count">{len(shown_assets)} assets</div>
</div>
""", unsafe_allow_html=True)

if not shown_assets:
    st.markdown("""
    <div class="empty-state">
        <div class="empty-icon">◻</div>
        <div class="empty-title">수집된 소재가 없습니다</div>
        <div class="empty-desc">키워드를 입력하고 검색하면<br>Meta Ad Library에서 광고 소재를 실시간으로 수집합니다.</div>
    </div>
    """, unsafe_allow_html=True)
else:
    cols = st.columns(col_count)

    for idx, item in enumerate(shown_assets):
        col = cols[idx % col_count]
        with col:
            badge_class = "badge-image" if item["asset_type"] == "image" else "badge-video"
            badge_label = "IMG" if item["asset_type"] == "image" else "VID"
            caption_html = f'<div class="asset-caption">"{item["caption"][:60]}..."</div>' if item.get("caption") else ""

            st.markdown(f'<div class="asset-card">', unsafe_allow_html=True)
            st.image(item["image_url"], use_container_width=True)
            st.markdown(f"""
            <div class="asset-body">
                <div class="asset-kw">{item["keyword"]}</div>
                <span class="asset-type-badge {badge_class}">{badge_label}</span>
                {caption_html}
                <div class="asset-meta">
                    {item["width"]} × {item["height"]}px · {item["created_at"][11:16]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            a1, a2 = st.columns(2)
            with a1:
                if st.button("제외", key=f"del_{item['id']}", use_container_width=True):
                    st.session_state.hidden_asset_ids.add(item["id"])
                    st.rerun()
            with a2:
                st.link_button("원본 →", item["source_url"], use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# Footer
# =========================================================
st.markdown('<div style="height:40px"></div>', unsafe_allow_html=True)
st.markdown(f"""
<div style="border-top:1px solid var(--border);padding-top:16px;display:flex;justify-content:space-between;align-items:center;">
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)">
        AD INTEL · META AD LIBRARY INTELLIGENCE
    </span>
    <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--muted)">
        세션 메모리 기반 · 로컬 저장 없음 · {time.strftime("%Y-%m-%d")}
    </span>
</div>
""", unsafe_allow_html=True)
