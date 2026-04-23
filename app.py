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
from urllib.parse import quote, urlparse

import streamlit as st
from playwright.sync_api import sync_playwright


# =========================================================
# Streamlit page config
# =========================================================
st.set_page_config(
    page_title="Meta Ad Library Board",
    page_icon="🔎",
    layout="wide",
)


# =========================================================
# Custom UI theme
# =========================================================
CUSTOM_CSS = """
<style>
    .stApp {
        background-color: #ffffff;
        color: #000000;
    }

    html, body, [class*="css"] {
        color: #000000;
    }

    [data-testid="stHeader"] {
        background: #ffffff;
    }

    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e9eef5;
    }

    .block-container {
        padding-top: 5rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }

    .app-title {
        font-size: 28px;
        font-weight: 800;
        color: #000000;
        margin-top: 0.8rem;
        margin-bottom: 8px;
    }

    .app-subtitle {
        font-size: 14px;
        color: #3b3b3b;
        margin-bottom: 22px;
    }

    .blue-chip {
        display: inline-block;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(20, 115, 230, 0.10);
        color: #1473e6;
        font-weight: 700;
        font-size: 12px;
        border: 1px solid rgba(20, 115, 230, 0.18);
        margin-right: 8px;
        margin-bottom: 8px;
    }

    .asset-card {
        border: 1px solid #e8edf5;
        border-radius: 18px;
        padding: 14px;
        background: #ffffff;
        box-shadow: 0 8px 24px rgba(0,0,0,0.04);
        margin-bottom: 14px;
    }

    .asset-meta {
        font-size: 12px;
        color: #4a4a4a;
        margin-top: 8px;
        line-height: 1.55;
    }

    .asset-title {
        font-size: 14px;
        font-weight: 700;
        color: #000000;
        margin-top: 8px;
        margin-bottom: 6px;
    }

    .toolbar-box {
        border: 1px solid #e8edf5;
        border-radius: 18px;
        padding: 14px;
        background: #ffffff;
        box-shadow: 0 8px 24px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }

    .stat-box {
        border: 1px solid #e8edf5;
        border-radius: 14px;
        padding: 12px;
        background: #ffffff;
        box-shadow: 0 6px 16px rgba(0,0,0,0.03);
    }

    .stat-label {
        font-size: 12px;
        color: #4a4a4a;
        margin-bottom: 4px;
    }

    .stat-value {
        font-size: 22px;
        font-weight: 800;
        color: #1473e6;
    }

    a {
        color: #1473e6 !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        border-radius: 12px;
        border: 1px solid #1473e6;
        color: #1473e6;
        background: #ffffff;
        font-weight: 700;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: rgba(20, 115, 230, 0.06);
        border-color: #1473e6;
        color: #1473e6;
    }

    .stTextInput input,
    .stSelectbox div[data-baseweb="select"] > div,
    .stNumberInput input {
        border-radius: 12px !important;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# =========================================================
# Session state
# =========================================================
if "assets" not in st.session_state:
    st.session_state.assets = []

if "hidden_asset_ids" not in st.session_state:
    st.session_state.hidden_asset_ids = set()

if "search_history" not in st.session_state:
    st.session_state.search_history = []

if "last_error" not in st.session_state:
    st.session_state.last_error = ""


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

    return (
        normalized_url,
        asset_type,
        caption[:80],
        width,
        height,
    )


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


def visible_assets():
    hidden = st.session_state.hidden_asset_ids
    return [item for item in st.session_state.assets if item["id"] not in hidden]


def reset_board():
    st.session_state.assets = []
    st.session_state.hidden_asset_ids = set()
    st.session_state.search_history = []
    st.session_state.last_error = ""


# =========================================================
# Header
# =========================================================
st.markdown('<div class="app-title">🔵 Meta Ad Library Search Board</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="app-subtitle">키워드 검색 → 실시간 수집 → 카드 확인 → 개별 삭제 → 추가 검색 누적</div>',
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown("### 🔵 설정")
    country = st.selectbox("국가", ["KR", "US", "JP", "GB"], index=0)
    max_scrolls = st.slider("스크롤 횟수", min_value=3, max_value=15, value=8, step=1)
    max_assets = st.slider("검색당 최대 결과 수", min_value=10, max_value=120, value=50, step=10)
    asset_filter = st.selectbox("표시 타입", ["전체", "image", "video_poster"], index=0)
    st.divider()
    if st.button("보드 전체 초기화", use_container_width=True):
        reset_board()
        st.rerun()


# =========================================================
# Search bar and actions
# =========================================================
st.markdown('<div class="toolbar-box">', unsafe_allow_html=True)
search_col, btn_col1, btn_col2 = st.columns([5, 1.2, 1.2])

with search_col:
    keyword = st.text_input(
        "검색어",
        placeholder="예: 캐리어, 공기청정기, 여행가방",
        label_visibility="collapsed",
    )

with btn_col1:
    search_clicked = st.button("검색", use_container_width=True)

with btn_col2:
    add_clicked = st.button("추가 검색", use_container_width=True)

st.caption("검색 결과는 같은 보드에 누적됩니다. 중복 소재는 최대한 자동 제거됩니다.")
st.markdown('</div>', unsafe_allow_html=True)

if search_clicked or add_clicked:
    cleaned = (keyword or "").strip()

    if not cleaned:
        st.warning("검색어를 입력하세요.")
    else:
        try:
            if add_clicked and cleaned in st.session_state.search_history:
                st.info("이미 검색한 키워드입니다. 같은 결과가 일부 포함될 수 있습니다.")

            with st.spinner(f"'{cleaned}' 검색 중입니다. 몇 초 걸릴 수 있습니다."):
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

            if added_count == 0:
                st.info("새로 추가된 결과가 없습니다. 검색 결과가 적거나 기존 결과와 중복일 수 있습니다.")
            else:
                st.success(f"{added_count}개 소재를 추가했습니다.")

            st.rerun()

        except Exception as e:
            st.session_state.last_error = str(e)
            st.error(f"검색 중 오류가 발생했습니다: {e}")


# =========================================================
# Stats
# =========================================================
all_assets = st.session_state.assets
shown_assets = visible_assets()

if asset_filter != "전체":
    shown_assets = [item for item in shown_assets if item["asset_type"] == asset_filter]

stat1, stat2, stat3 = st.columns(3)

with stat1:
    st.markdown(
        f'<div class="stat-box"><div class="stat-label">총 누적 소재</div><div class="stat-value">{len(all_assets)}</div></div>',
        unsafe_allow_html=True,
    )

with stat2:
    st.markdown(
        f'<div class="stat-box"><div class="stat-label">현재 표시 소재</div><div class="stat-value">{len(shown_assets)}</div></div>',
        unsafe_allow_html=True,
    )

with stat3:
    st.markdown(
        f'<div class="stat-box"><div class="stat-label">숨김 처리 수</div><div class="stat-value">{len(st.session_state.hidden_asset_ids)}</div></div>',
        unsafe_allow_html=True,
    )


# =========================================================
# Search history
# =========================================================
if st.session_state.search_history:
    st.markdown("### 🔵 검색 이력")
    history_html = "".join(
        [f'<span class="blue-chip">{item}</span>' for item in st.session_state.search_history[-12:]]
    )
    st.markdown(history_html, unsafe_allow_html=True)

if st.session_state.last_error:
    st.warning(f"최근 오류: {st.session_state.last_error}")


# =========================================================
# Board
# =========================================================
st.markdown("### 🔵 소재 보드")

if not shown_assets:
    st.info("표시할 소재가 없습니다. 검색어를 입력한 뒤 검색하세요.")
else:
    cols = st.columns(4)

    for idx, item in enumerate(shown_assets):
        col = cols[idx % 4]
        with col:
            st.markdown('<div class="asset-card">', unsafe_allow_html=True)
            st.image(item["image_url"], use_container_width=True)
            st.markdown(
                f'<div class="asset-title">{item["keyword"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                (
                    '<div class="asset-meta">'
                    f'타입: <b>{item["asset_type"]}</b><br>'
                    f'크기: {item["width"]} × {item["height"]}<br>'
                    f'수집 시각: {item["created_at"]}'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

            action_col1, action_col2 = st.columns(2)

            with action_col1:
                if st.button("삭제", key=f"delete_{item['id']}", use_container_width=True):
                    st.session_state.hidden_asset_ids.add(item["id"])
                    st.rerun()

            with action_col2:
                st.link_button("원본", item["source_url"], use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# Footer notes
# =========================================================
st.divider()
st.caption(
    "이 앱은 검색 시점에 Meta Ad Library 공개 페이지를 불러와 소재 이미지를 추출해 보드에 표시합니다. "
    "이미지 파일을 로컬에 저장하지 않고, 현재 세션 메모리 기준으로만 결과를 유지합니다."
)
