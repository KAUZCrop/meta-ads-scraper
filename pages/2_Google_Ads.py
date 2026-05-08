# ============================================================
# Google 광고 투명성 센터 — 별도 페이지
# ============================================================
import sys, os, time, json, sqlite3, uuid
import streamlit as st

# CSS 공유
_css_path = os.path.join(os.path.dirname(__file__), "..", "static", "style.css")
try:
    with open(_css_path) as _f:
        st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "adintel.db")

# ============================================================
# DB — Google 광고 저장 테이블
# ============================================================
def _db_init():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("""
        CREATE TABLE IF NOT EXISTS google_ads (
            id TEXT PRIMARY KEY,
            advertiser_id TEXT DEFAULT '',
            advertiser_name TEXT DEFAULT '',
            creative_id TEXT DEFAULT '',
            ad_format TEXT DEFAULT '',
            first_shown TEXT DEFAULT '',
            last_shown TEXT DEFAULT '',
            destination_url TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            video_url TEXT DEFAULT '',
            ad_title TEXT DEFAULT '',
            ad_body TEXT DEFAULT '',
            keyword TEXT DEFAULT '',
            country TEXT DEFAULT 'KR',
            created_at TEXT NOT NULL,
            starred INTEGER DEFAULT 0,
            memo TEXT DEFAULT ''
        )
    """)
    con.commit()
    con.close()

_db_init()


def _db_upsert(ads: list):
    if not ads:
        return
    con = sqlite3.connect(DB_PATH, timeout=15)
    for a in ads:
        con.execute("""
            INSERT OR REPLACE INTO google_ads
            (id,advertiser_id,advertiser_name,creative_id,ad_format,
             first_shown,last_shown,destination_url,image_url,video_url,
             ad_title,ad_body,keyword,country,created_at,starred,memo)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            a.get("id", str(uuid.uuid4())),
            a.get("advertiser_id",""), a.get("advertiser_name",""),
            a.get("creative_id",""),  a.get("ad_format",""),
            a.get("first_shown",""),  a.get("last_shown",""),
            a.get("destination_url",""), a.get("image_url",""),
            a.get("video_url",""),    a.get("ad_title",""),
            a.get("ad_body",""),      a.get("keyword",""),
            a.get("country","KR"),    a.get("created_at", time.strftime("%Y-%m-%d %H:%M:%S")),
            1 if a.get("starred") else 0,
            a.get("memo",""),
        ))
    con.commit()
    con.close()


def _db_load(keyword: str = "", limit: int = 200) -> list:
    con = sqlite3.connect(DB_PATH, timeout=15)
    if keyword:
        rows = con.execute(
            "SELECT * FROM google_ads WHERE keyword=? ORDER BY created_at DESC LIMIT ?",
            (keyword, limit),
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT * FROM google_ads ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    cols = [d[0] for d in con.execute("PRAGMA table_info(google_ads)").fetchall()]
    con.close()
    return [dict(zip(cols, r)) for r in rows]


def _db_reset_keyword(keyword: str):
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.execute("DELETE FROM google_ads WHERE keyword=?", (keyword,))
    con.commit()
    con.close()


# ============================================================
# 스크래퍼 — Google Ads Transparency Scraper 라이브러리 사용
# ============================================================
def _check_library() -> bool:
    try:
        import importlib
        importlib.import_module("google_ads_transparency_scraper")
        return True
    except ImportError:
        return False


def scrape_google_ads(keyword: str, country: str = "KR", limit: int = 50) -> tuple[list, str | None]:
    """
    Google 광고 투명성 센터에서 키워드로 광고 수집.
    반환: (ads_list, error_message)
    """
    try:
        from google_ads_transparency_scraper import GoogleAdTransparencyScraper
    except ImportError:
        return [], "google_ads_transparency_scraper 패키지가 설치되지 않았습니다.\n`pip install Google-Ads-Transparency-Scraper` 로 설치하세요."

    try:
        scraper = GoogleAdTransparencyScraper()
        raw_ads = scraper.search_by_keyword(keyword, region=country)
    except Exception as ex:
        return [], f"스크래핑 오류: {str(ex)[:300]}"

    ads = []
    for r in (raw_ads or [])[:limit]:
        ad_id = str(r.get("creativeId") or r.get("creative_id") or uuid.uuid4())
        image_url = ""
        video_url = ""
        fmt = str(r.get("format") or r.get("adFormat") or "").lower()
        if "video" in fmt:
            video_url = r.get("link") or r.get("videoUrl") or ""
        else:
            image_url = r.get("link") or r.get("imageUrl") or r.get("previewUrl") or ""

        ads.append({
            "id":               str(uuid.uuid4()),
            "advertiser_id":    str(r.get("advertiserId") or ""),
            "advertiser_name":  str(r.get("advertiserName") or ""),
            "creative_id":      ad_id,
            "ad_format":        fmt or "unknown",
            "first_shown":      str(r.get("firstShown") or ""),
            "last_shown":       str(r.get("lastShown") or ""),
            "destination_url":  str(r.get("destinationUrl") or r.get("destination") or ""),
            "image_url":        image_url,
            "video_url":        video_url,
            "ad_title":         str(r.get("title") or ""),
            "ad_body":          str(r.get("body") or r.get("text") or ""),
            "keyword":          keyword,
            "country":          country,
            "created_at":       time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    return ads, None


# ============================================================
# 페이지 UI
# ============================================================
st.set_page_config(
    page_title="Google Ads — ADINTEL",
    page_icon="🔍",
    layout="wide",
)

# 헤더
st.markdown(
    '<div class="hdr">'
    '<div class="hdr-row">'
    '<div class="logo">AD<b>INTEL</b></div>'
    '<span class="ver">Google Ads</span>'
    '</div>'
    '<div class="sub">GOOGLE ADS TRANSPARENCY CENTER · 광고 투명성 센터 스크래퍼</div>'
    '</div>',
    unsafe_allow_html=True,
)

# 라이브러리 설치 안내
if not _check_library():
    st.warning(
        "**google_ads_transparency_scraper** 패키지가 설치되지 않았습니다.\n\n"
        "터미널에서 다음 명령을 실행하세요:\n"
        "```\npip install Google-Ads-Transparency-Scraper\n```\n\n"
        "설치 후 페이지를 새로고침하면 자동으로 활성화됩니다."
    )

# ── 사이드바 ────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="slbl">SEARCH</div>', unsafe_allow_html=True)
    g_keyword = st.text_input("키워드", placeholder="예: 에어컨, 다이어트, 보험")
    g_country = st.selectbox("국가", ["KR","US","JP","GB","AU","CA","SG"], index=0)
    g_limit   = st.select_slider("최대 수집 수", options=[20, 50, 100, 200], value=50)
    do_search = st.button("🔍 Google 광고 수집", use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="slbl">FILTER</div>', unsafe_allow_html=True)
    all_kws   = sorted(set(a["keyword"] for a in _db_load()))
    sel_kw    = st.selectbox("저장된 키워드", ["전체"] + all_kws)
    ftype     = st.selectbox("광고 형식", ["전체", "image", "video", "text"])
    fstar     = st.toggle("즐겨찾기만")

    st.markdown("---")
    if all_kws and st.button("현재 키워드 데이터 삭제", use_container_width=True):
        if sel_kw != "전체":
            _db_reset_keyword(sel_kw)
            st.rerun()

# ── 수집 실행 ───────────────────────────────────────────────
if do_search and g_keyword.strip():
    kws = [k.strip() for k in g_keyword.split(",") if k.strip()]
    for kw in kws:
        with st.spinner(f"'{kw}' 수집 중..."):
            ads, err = scrape_google_ads(kw, g_country, g_limit)
        if err:
            st.error(f"**{kw}** — {err}")
        elif ads:
            _db_upsert(ads)
            st.success(f"**{kw}** — {len(ads)}개 광고 수집 완료")
        else:
            st.warning(f"**{kw}** — 결과 없음")
    st.rerun()

# ── 데이터 로드 ─────────────────────────────────────────────
items = _db_load(keyword=sel_kw if sel_kw != "전체" else "")
if ftype != "전체":
    items = [a for a in items if ftype in a.get("ad_format","").lower()]
if fstar:
    items = [a for a in items if a.get("starred")]

# ── 헤더 KPI ────────────────────────────────────────────────
if items:
    advertisers = set(a["advertiser_name"] for a in items if a["advertiser_name"])
    vid_cnt = sum(1 for a in items if a.get("video_url"))
    img_cnt = sum(1 for a in items if a.get("image_url") and not a.get("video_url"))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 광고 수", len(items))
    k2.metric("광고주 수", len(advertisers))
    k3.metric("이미지 광고", img_cnt)
    k4.metric("영상 광고", vid_cnt)
    st.markdown("---")

# ── 광고 그리드 ─────────────────────────────────────────────
if not items:
    st.markdown(
        '<div class="empty"><div class="empty-t">수집된 Google 광고가 없습니다</div>'
        '<div class="empty-d">키워드를 입력하고 수집 버튼을 누르세요.</div></div>',
        unsafe_allow_html=True,
    )
else:
    g_cols = st.select_slider("열 수", options=[2, 3, 4, 5], value=4, key="g_grid_cols")
    grid   = st.columns(g_cols)
    for i, ad in enumerate(items):
        with grid[i % g_cols]:
            # 이미지 또는 영상
            if ad.get("video_url"):
                st.markdown(
                    f'<div class="g-card"><div class="card-img-wrap" style="padding-top:56.25%;">'
                    f'<video src="{ad["video_url"]}" controls preload="none" playsinline '
                    f'class="card-vid"></video></div></div>',
                    unsafe_allow_html=True,
                )
            elif ad.get("image_url"):
                st.markdown(f'<div class="g-card">', unsafe_allow_html=True)
                st.image(ad["image_url"], use_container_width=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div class="g-card"><div style="padding:20px;background:var(--bg3);'
                    'text-align:center;color:var(--mu);font-size:11px;">텍스트 광고</div></div>',
                    unsafe_allow_html=True,
                )

            # 본문
            fmt_badge = f'<span class="g-badge">{ad.get("ad_format","").upper() or "ADS"}</span>'
            st.markdown(
                f'{fmt_badge}'
                f'<div style="font-size:11px;font-weight:700;color:#4285f4;margin:4px 0 2px;">'
                f'{ad.get("advertiser_name","—")}</div>'
                + (f'<div style="font-size:11px;color:var(--tx2);margin-bottom:2px;">{ad["ad_title"]}</div>' if ad.get("ad_title") else "")
                + (f'<div style="font-size:10px;color:var(--mu);font-style:italic;">{ad["ad_body"][:60]}...</div>' if ad.get("ad_body") else "")
                + f'<div style="font-size:10px;color:var(--mu);margin-top:4px;">'
                f'{ad.get("first_shown","")[:10]} ~ {ad.get("last_shown","")[:10]}</div>',
                unsafe_allow_html=True,
            )

            b1, b2 = st.columns(2)
            with b1:
                if ad.get("destination_url"):
                    st.link_button("원본 ↗", ad["destination_url"], use_container_width=True)
            with b2:
                star_key = f"g_star_{ad['id']}"
                if st.button("★" if ad.get("starred") else "☆", key=star_key, use_container_width=True):
                    con = sqlite3.connect(DB_PATH, timeout=15)
                    new_val = 0 if ad.get("starred") else 1
                    con.execute("UPDATE google_ads SET starred=? WHERE id=?", (new_val, ad["id"]))
                    con.commit()
                    con.close()
                    st.rerun()

# ── CSV 내보내기 ─────────────────────────────────────────────
if items:
    st.markdown("---")
    import io, csv as _csv
    buf = io.StringIO()
    fields = ["advertiser_name","advertiser_id","ad_format","ad_title","ad_body",
              "first_shown","last_shown","destination_url","image_url","video_url","keyword","country"]
    w = _csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(items)
    st.download_button(
        "CSV 내보내기",
        data=buf.getvalue().encode("utf-8-sig"),
        file_name=f"google_ads_{time.strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=False,
    )
