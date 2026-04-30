# ============================================================
# AD INTEL v3.2 — Meta Ad Library Intelligence Board
# ============================================================
import sys, asyncio, subprocess, time, uuid, io, json, requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from urllib.parse import quote, urlparse
from playwright.sync_api import sync_playwright

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

@st.cache_resource
def ensure_browser():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    return True

def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return ""

API_KEY = get_api_key()

st.set_page_config(page_title="AD INTEL", page_icon="◼", layout="wide")

for k, v in {
    "assets": [], "hidden": set(), "history": [],
    "log": [], "ai_on": False, "dark": False,
    "selected": set(), "summary": None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# CSS
# ============================================================
D = st.session_state.dark

LIGHT = """
:root {
    --bg:#fff; --bg2:#f7f8fa; --bg3:#f0f2f5;
    --bd:#e2e5ea; --bd2:#cdd1d8;
    --ac:#1a6dff; --ac2:rgba(26,109,255,0.10);
    --tx:#111318; --tx2:#3a3f4a; --mu:#8a909e;
    --ok:#00a86b; --er:#e8284a; --wn:#e07b00;
    --sh:0 1px 3px rgba(0,0,0,.05);
    --sh2:0 4px 20px rgba(26,109,255,.12);
}"""

DARK = """
:root {
    --bg:#0d0f12; --bg2:#13161b; --bg3:#1a1e26;
    --bd:#252a34; --bd2:#2f3542;
    --ac:#4f8aff; --ac2:rgba(79,138,255,0.12);
    --tx:#e8eaf0; --tx2:#b0b8cc; --mu:#6b7280;
    --ok:#3dffa0; --er:#ff4f6b; --wn:#ffb84f;
    --sh:0 1px 4px rgba(0,0,0,.4);
    --sh2:0 4px 20px rgba(79,138,255,.18);
}"""

st.markdown(f"""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

{DARK if D else LIGHT}

html,body,[class*="css"]{{font-family:'Pretendard',sans-serif;background:var(--bg)!important;color:var(--tx)!important;}}
.stApp{{background:var(--bg)!important;}}
[data-testid="stHeader"]{{background:var(--bg)!important;border-bottom:1px solid var(--bd);}}
[data-testid="stSidebar"]{{background:var(--bg2)!important;border-right:1px solid var(--bd)!important;}}
[data-testid="stSidebar"] *{{color:var(--tx)!important;}}
.block-container{{padding-top:4.5rem;padding-bottom:3rem;max-width:1600px;}}

.hdr{{margin-bottom:2rem;padding-bottom:1.2rem;border-bottom:2px solid var(--bd);}}
.hdr-row{{display:flex;align-items:center;gap:10px;}}
.logo{{font-family:'Pretendard',sans-serif;font-size:22px;font-weight:800;letter-spacing:-.5px;color:var(--tx);}}
.logo b{{color:var(--ac);}}
.ver{{font-size:10px;color:var(--mu);border:1px solid var(--bd2);padding:2px 8px;border-radius:4px;background:var(--bg3);}}
.sub{{font-size:10px;color:var(--mu);letter-spacing:2px;margin-top:8px;}}

.slbl{{font-size:9px;color:var(--mu);letter-spacing:1.5px;text-transform:uppercase;margin:8px 0 6px;}}

.srch{{background:var(--bg2);border:1.5px solid var(--bd);border-radius:14px;padding:16px 20px;margin-bottom:1.2rem;}}
.srch-lbl{{font-size:9px;color:var(--mu);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;}}

.sc{{background:var(--bg);border:1.5px solid var(--bd);border-radius:12px;padding:20px 20px 18px;position:relative;overflow:hidden;box-shadow:var(--sh);transition:.2s;}}
.sc:hover{{border-color:var(--ac);box-shadow:var(--sh2);}}
.sc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--ac),#5b9dff);opacity:0;transition:.2s;}}
.sc:hover::before{{opacity:1;}}
.sc-lbl{{font-size:9px;color:var(--mu);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}}
.sc-val{{font-family:'Pretendard',sans-serif;font-size:32px;font-weight:800;color:var(--tx);line-height:1;}}
.sc-sub{{font-size:11px;color:var(--mu);margin-top:8px;}}

.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1.2rem;}}
.tag{{font-size:11px;background:var(--ac2);border:1px solid var(--ac2);color:var(--ac);padding:4px 10px;border-radius:20px;display:inline-flex;align-items:center;gap:6px;}}
.tag-dot{{width:5px;height:5px;border-radius:50%;background:var(--ok);}}

.sec{{display:flex;align-items:center;justify-content:space-between;margin-bottom:.8rem;padding-bottom:10px;border-bottom:1.5px solid var(--bd);}}
.sec-t{{font-family:'Pretendard',sans-serif;font-size:13px;font-weight:800;color:var(--tx);letter-spacing:.5px;text-transform:uppercase;}}
.sec-n{{font-size:11px;color:var(--mu);}}

.card{{border:1.5px solid var(--bd);border-radius:12px;overflow:hidden;margin-bottom:10px;background:var(--bg);box-shadow:var(--sh);transition:.2s;}}
.card:hover{{border-color:var(--ac);box-shadow:var(--sh2);}}
.card-body{{padding:10px 12px;border-top:1px solid var(--bd);background:var(--bg2);}}
.card-kw{{font-size:10px;color:var(--ac);letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px;}}
.card-meta{{font-size:11px;color:var(--mu);margin-top:4px;}}
.card-cap{{font-size:11px;color:var(--tx2);margin:4px 0;opacity:.8;font-style:italic;line-height:1.4;}}
.bdg{{display:inline-block;font-size:9px;padding:2px 7px;border-radius:20px;margin:0 2px 4px 0;font-weight:600;}}
.b-img{{background:var(--ac2);color:var(--ac);border:1px solid var(--ac2);}}
.b-vid{{background:rgba(124,92,255,.12);color:#7c5cff;border:1px solid rgba(124,92,255,.2);}}
.b-sav{{background:rgba(255,184,79,.12);color:var(--wn);border:1px solid rgba(255,184,79,.2);}}
.b-ai {{background:rgba(61,255,160,.10);color:var(--ok);border:1px solid rgba(61,255,160,.2);}}

.ai-wrap{{padding:0 12px 12px;background:var(--bg2);}}
.ai-box{{background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:10px 12px;}}
.ai-head{{font-size:9px;color:var(--ac);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;font-weight:700;}}
.ai-body{{font-size:12px;color:var(--tx2);line-height:1.75;}}
.ai-tag{{display:inline-block;font-size:10px;background:var(--ac2);color:var(--ac);border-radius:4px;padding:1px 6px;margin:2px 2px 0 0;font-weight:600;}}

.summary-box{{background:var(--bg2);border:2px solid var(--ac);border-radius:16px;padding:24px 28px;margin-bottom:1.5rem;}}
.summary-head{{font-family:'Pretendard',sans-serif;font-size:16px;font-weight:800;color:var(--ac);margin-bottom:16px;}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}}
.summary-item{{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;}}
.summary-item-lbl{{font-size:9px;color:var(--mu);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;font-weight:700;}}
.summary-item-val{{font-size:13px;color:var(--tx);line-height:1.5;}}
.summary-strategy{{background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:14px 16px;margin-bottom:12px;}}
.summary-strategy-lbl{{font-size:9px;color:var(--ac);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;font-weight:700;}}
.summary-strategy-val{{font-size:13px;color:var(--tx2);line-height:1.65;}}
.summary-tags{{display:flex;flex-wrap:wrap;gap:6px;}}
.summary-tag{{font-size:10px;background:var(--ac2);color:var(--ac);border:1px solid var(--ac2);border-radius:4px;padding:3px 9px;font-weight:600;}}

.sel-bar{{display:flex;align-items:center;background:var(--bg2);border:1.5px solid var(--bd);border-radius:10px;padding:10px 16px;margin-bottom:1rem;}}
.sel-count{{font-family:'Pretendard',sans-serif;font-size:14px;font-weight:800;color:var(--ac);margin-right:6px;}}
.sel-bar-txt{{font-size:11px;color:var(--tx2);}}

.banner{{display:flex;align-items:center;gap:10px;background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:10px 16px;margin-bottom:1rem;}}
.banner-w{{background:rgba(224,123,0,.06);border-color:rgba(224,123,0,.2);}}
.dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
.dot-on{{background:var(--ok);box-shadow:0 0 6px var(--ok);}}
.banner-txt{{font-size:11px;color:var(--tx2);}}

.empty{{text-align:center;padding:80px 20px;}}
.empty-t{{font-family:'Pretendard',sans-serif;font-size:16px;font-weight:700;color:var(--mu);margin-bottom:8px;}}
.empty-d{{font-size:13px;color:var(--mu);line-height:1.6;}}

.log{{font-size:11px;color:var(--mu);padding:4px 0;border-bottom:1px solid var(--bd);}}
.log .ts{{color:var(--ac);margin-right:8px;}}
.log .ok{{color:var(--ok);}}
.log .er{{color:var(--er);}}

/* 버튼 — white-space:nowrap 으로 줄바꿈 방지 */
.stButton>button{{
    font-family:'Pretendard',sans-serif!important;
    font-size:13px!important;
    font-weight:600!important;
    border-radius:8px!important;
    border:1.5px solid var(--bd2)!important;
    background:var(--bg)!important;
    color:var(--tx2)!important;
    height:34px!important;
    transition:.15s!important;
    white-space:nowrap!important;
    overflow:hidden!important;
    padding:0 8px!important;
    line-height:34px!important;
}}
.stButton>button:hover{{border-color:var(--ac)!important;color:var(--ac)!important;background:var(--ac2)!important;}}
.stDownloadButton>button{{
    font-family:'Pretendard',sans-serif!important;
    font-size:12px!important;
    border-radius:8px!important;
    border:1.5px solid var(--bd2)!important;
    background:var(--bg)!important;
    color:var(--tx2)!important;
    white-space:nowrap!important;
}}

.stTextInput input{{background:var(--bg)!important;border:1.5px solid var(--bd2)!important;border-radius:10px!important;color:var(--tx)!important;font-family:'Pretendard',sans-serif!important;}}
.stTextInput input:focus{{border-color:var(--ac)!important;box-shadow:0 0 0 3px var(--ac2)!important;}}
div[data-baseweb="select"]>div{{background:var(--bg)!important;border-color:var(--bd2)!important;border-radius:8px!important;color:var(--tx)!important;}}

.stSuccess{{background:rgba(0,168,107,.08)!important;border:1px solid rgba(0,168,107,.25)!important;border-radius:10px!important;}}
.stWarning{{background:rgba(224,123,0,.08)!important;border:1px solid rgba(224,123,0,.25)!important;border-radius:10px!important;}}
.stInfo   {{background:var(--ac2)!important;border:1px solid var(--ac2)!important;border-radius:10px!important;}}
.stError  {{background:rgba(232,40,74,.08)!important;border:1px solid rgba(232,40,74,.25)!important;border-radius:10px!important;}}

hr{{border-color:var(--bd)!important;}}
.stCaption{{color:var(--mu)!important;font-size:11px!important;}}
a{{color:var(--ac)!important;}}
::-webkit-scrollbar{{width:4px;height:4px;}}
::-webkit-scrollbar-track{{background:var(--bg2);}}
::-webkit-scrollbar-thumb{{background:var(--bd2);border-radius:4px;}}
.stSpinner>div{{border-top-color:var(--ac)!important;}}
</style>""", unsafe_allow_html=True)


# ============================================================
# 스크래퍼 (기존 원본)
# ============================================================
def valid(w, h):
    # 크기 정보가 아예 없으면(0,0) 일단 통과 — URL 패턴으로 필터
    if w == 0 and h == 0: return True
    if w < 180 or h < 180: return False
    r = w / h if h else 0
    return 0.25 <= r <= 3.0

def make_fp(item):
    url = (item.get("image_url") or "").strip()
    p = urlparse(url)
    return (
        f"{p.netloc}{p.path}",
        (item.get("asset_type") or "").strip(),
        (item.get("caption") or "").strip().lower()[:80],
        item.get("width", 0),
        item.get("height", 0),
    )

def scrape(keyword, country, scrolls, limit):
    ensure_browser()
    search_url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country={country}&q={quote(keyword)}"
    )

    # ── GraphQL JSON 재귀 파싱 ──
    def deep_find(obj, keys):
        """JSON 안에서 특정 키를 재귀적으로 찾아 첫 번째 값 반환"""
        if isinstance(obj, dict):
            for k in keys:
                if k in obj and obj[k]:
                    return obj[k]
            for v in obj.values():
                result = deep_find(v, keys)
                if result: return result
        elif isinstance(obj, list):
            for item in obj:
                result = deep_find(item, keys)
                if result: return result
        return None

    def extract_text(val):
        if isinstance(val, dict):
            return val.get("text") or val.get("content") or ""
        elif isinstance(val, list):
            parts = []
            for v in val:
                t = extract_text(v)
                if t: parts.append(t)
            return " ".join(parts)
        return str(val) if val else ""

    def parse_ad_node(node: dict) -> list[dict]:
        """광고 노드에서 이미지+카피 추출"""
        results = []
        if not isinstance(node, dict): return results

        advertiser  = str(node.get("page_name") or node.get("advertiser_name") or "")
        start_ts    = node.get("start_date") or node.get("ad_delivery_start_time") or 0
        end_ts      = node.get("end_date")   or node.get("ad_delivery_stop_time") or 0
        platforms   = node.get("publisher_platforms") or []

        try:
            import datetime
            start_date = datetime.datetime.fromtimestamp(int(start_ts)).strftime("%Y-%m-%d") if start_ts else ""
            end_date   = datetime.datetime.fromtimestamp(int(end_ts)).strftime("%Y-%m-%d")   if end_ts   else ""
        except Exception:
            start_date = end_date = ""

        platform_str = ", ".join(platforms) if isinstance(platforms, list) else ""

        # 광고 크리에이티브 목록
        creatives = node.get("ads") or node.get("ad_creatives") or [node]

        for ad in creatives:
            if not isinstance(ad, dict): continue
            snap = ad.get("snapshot") or {}

            # 카피 본문
            body_raw = (ad.get("body") or snap.get("body") or
                        ad.get("ad_creative_bodies") or "")
            body = extract_text(body_raw)[:400]

            # 헤드라인
            hl_raw = (ad.get("title") or snap.get("title") or
                      ad.get("ad_creative_link_titles") or
                      snap.get("link_title") or "")
            headline = extract_text(hl_raw)[:120]

            # CTA
            cta = str(ad.get("cta_text") or snap.get("cta_text") or
                      ad.get("call_to_action_type") or "")[:40]

            base = dict(
                advertiser=advertiser, headline=headline,
                body=body, cta=cta,
                start_date=start_date, end_date=end_date,
                platforms=platform_str,
            )

            # 이미지
            imgs = (ad.get("images") or snap.get("images") or
                    ad.get("ad_creative_images") or [])
            for img in imgs:
                if not isinstance(img, dict): continue
                url = (img.get("original_image_url") or img.get("url") or
                       img.get("resized_image_url") or "")
                if url:
                    results.append({**base, "type": "image", "src": url})

            # 비디오 썸네일
            vids = (ad.get("videos") or snap.get("videos") or
                    ad.get("ad_creative_videos") or [])
            for vid in vids:
                if not isinstance(vid, dict): continue
                url = (vid.get("video_preview_image_url") or
                       vid.get("thumbnail") or "")
                if url:
                    results.append({**base, "type": "video_poster", "src": url})

        return results

    def parse_graphql_body(raw_bytes: bytes) -> list[dict]:
        results = []
        try:
            text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return results

        for line in text.splitlines():
            line = line.strip()
            if not line or not line.startswith("{"): continue
            try:
                data = json.loads(line)
                # edges 탐색
                def walk(obj):
                    if isinstance(obj, dict):
                        if "edges" in obj:
                            for edge in obj.get("edges", []):
                                node = edge.get("node", {})
                                if "page_name" in node or "ads" in node:
                                    results.extend(parse_ad_node(node))
                        for v in obj.values():
                            walk(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            walk(item)
                walk(data)
            except Exception:
                pass
        return results

    # ── Playwright 실행 ──
    gql_results = []
    captured_bodies = []  # route에서 캡처한 응답 바이트 목록

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions",
            "--disable-plugins", "--no-first-run", "--disable-default-apps",
        ])
        ctx = browser.new_context(viewport={"width": 1440, "height": 2000})
        ctx.route("**/*.{woff,woff2,ttf,otf,eot}", lambda r: r.abort())

        # GraphQL 요청을 route로 가로채서 응답 바이트 저장
        def handle_graphql(route):
            try:
                resp = route.fetch()
                body = resp.body()
                captured_bodies.append(body)
                route.fulfill(response=resp)
            except Exception:
                try:
                    route.continue_()
                except Exception:
                    pass

        ctx.route("**/api/graphql*", handle_graphql)
        ctx.route("**/graphql*",     handle_graphql)

        page = ctx.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4000)

        def card_count():
            return page.evaluate(
                "() => document.querySelectorAll('img[src*=\"fbcdn\"]').length"
            )

        prev, stalls = 0, 0
        for _ in range(scrolls):
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

        # DOM에서 이미지 + 카피 동시 수집 (카드 단위)
        dom_data = page.evaluate("""() => {
            const out = [];

            // 전체 텍스트 블록 수집
            function getText(el) {
                try { return (el.innerText || el.textContent || '').trim(); }
                catch(e) { return ''; }
            }

            // 이미지 전체
            const imgMap = {};
            for (const img of document.querySelectorAll('img[src*="fbcdn"]')) {
                const src = img.currentSrc || img.src || '';
                if (!src) continue;
                // 가장 가까운 텍스트 블록 찾기
                let parent = img.parentElement;
                let body = '', headline = '', advertiser = '', cta = '';
                for (let i = 0; i < 8 && parent; i++) {
                    const divs = parent.querySelectorAll('div[dir="auto"]');
                    const texts = [];
                    for (const d of divs) {
                        const t = getText(d);
                        if (t && t.length > 3) texts.push(t);
                    }
                    if (texts.length > 0) {
                        body = texts.slice(0, 3).join(' | ').substring(0, 400);
                        break;
                    }
                    parent = parent.parentElement;
                }
                out.push({
                    type: 'image', src,
                    w: img.naturalWidth  || img.width  || 0,
                    h: img.naturalHeight || img.height || 0,
                    body, headline, advertiser, cta
                });
            }

            // 비디오 썸네일
            for (const v of document.querySelectorAll('video')) {
                if (!v.poster) continue;
                out.push({
                    type: 'video_poster', src: v.poster,
                    w: v.videoWidth || v.clientWidth || 0,
                    h: v.videoHeight || v.clientHeight || 0,
                    body: '', headline: '', advertiser: '', cta: ''
                });
            }
            return out;
        }""")

        ctx.close(); browser.close()

    # ── GraphQL 파싱 ──
    for body_bytes in captured_bodies:
        gql_results.extend(parse_graphql_body(body_bytes))

    # GraphQL 이미지 URL → 카피 매핑
    gql_map = {}  # src → 카피 정보
    for g in gql_results:
        src = g.get("src", "")
        if src:
            gql_map[src] = g

    # ── 최종 수집 ──
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    seen, collected = set(), []

    for d in dom_data:
        if len(collected) >= limit: break
        src = (d.get("src") or "").strip()
        if not src: continue
        w, h = int(d.get("w") or 0), int(d.get("h") or 0)
        if not valid(w, h): continue

        # GraphQL 카피 우선, 없으면 DOM 카피 사용
        gql = gql_map.get(src, {})
        advertiser = gql.get("advertiser") or d.get("advertiser") or ""
        headline   = gql.get("headline")   or d.get("headline")   or ""
        body       = gql.get("body")       or d.get("body")       or ""
        cta        = gql.get("cta")        or d.get("cta")        or ""
        start_date = gql.get("start_date") or ""
        end_date   = gql.get("end_date")   or ""
        platforms  = gql.get("platforms")  or ""

        asset = {
            "id":         str(uuid.uuid4()),
            "keyword":    keyword,
            "country":    country,
            "asset_type": d.get("type", "image"),
            "image_url":  src,
            "source_url": search_url,
            "caption":    "",
            "advertiser": advertiser,
            "headline":   headline,
            "body":       body,
            "cta":        cta,
            "start_date": start_date,
            "end_date":   end_date,
            "platforms":  platforms,
            "width":      w,
            "height":     h,
            "created_at": now,
            "starred":    False,
            "ai":         None,
        }
        fp_key = make_fp(asset)
        if fp_key in seen: continue
        seen.add(fp_key)
        collected.append(asset)

    return collected



# ============================================================
# AI 분석
# ============================================================
def fetch_image_b64(url: str):
    """이미지 URL → (base64, media_type). 실패 시 None"""
    try:
        import base64
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.facebook.com/",
        })
        if resp.status_code != 200 or len(resp.content) < 500:
            return None
        ct = resp.headers.get("content-type", "image/jpeg")
        if "png"  in ct: mt = "image/png"
        elif "gif"  in ct: mt = "image/gif"
        elif "webp" in ct: mt = "image/webp"
        else:               mt = "image/jpeg"
        return base64.standard_b64encode(resp.content).decode("utf-8"), mt
    except Exception:
        return None


def analyze(item):
    """
    Claude Vision으로 광고 소재 분석
    1. 이미지 내 카피 추출
    2. 톤앤매너 분석
    3. 소구포인트 인사이트
    """
    if not API_KEY: return None
    try:
        # ── 프롬프트 구성 ──
        meta_ctx = ""
        parts = []
        if item.get("advertiser"): parts.append(f"광고주: {item['advertiser']}")
        if item.get("start_date"): parts.append(f"집행 시작: {item['start_date']}")
        if item.get("platforms"):  parts.append(f"플랫폼: {item['platforms']}")
        if parts:
            meta_ctx = "\n[메타 정보]\n" + "\n".join(parts)

        prompt_text = (
            "당신은 광고 전략 전문가이자 크리에이티브 디렉터입니다.\n"
            "아래 Meta 광고 소재 이미지를 보고 세 가지를 분석해주세요.\n\n"
            f"[검색 키워드] {item['keyword']}"
            + meta_ctx +
            "\n\n"
            "반드시 아래 JSON 형식으로만 답하세요 (마크다운·백틱 없이 순수 JSON):\n"
            "{\n"
            '  "copy_analysis": {\n'
            '    "visible_text": "이미지에서 실제로 보이는 텍스트/카피 전체 (그대로 옮겨쓰기)",\n'
            '    "hook": "첫 시선을 잡는 핵심 문구 또는 비주얼 요소",\n'
            '    "headline": "메인 헤드라인 (있다면)",\n'
            '    "cta": "CTA 버튼 또는 행동 유도 문구 (있다면)",\n'
            '    "appeal": "소구포인트 유형 — 감성/이성/사회적증거/희소성/혜택/공포 중 선택 + 근거"\n'
            '  },\n'
            '  "tone_manner": {\n'
            '    "mood": "전체적인 분위기 (예: 고급스러운, 친근한, 역동적인, 미니멀한 등)",\n'
            '    "color_tone": "주요 색상과 색감이 주는 인상",\n'
            '    "visual_style": "비주얼 스타일 (예: 제품 중심, 라이프스타일, UGC, 인포그래픽 등)",\n'
            '    "typography": "폰트/텍스트 스타일의 특징 (있다면)",\n'
            '    "target_feel": "이 광고가 타겟에게 주려는 감정이나 느낌"\n'
            '  },\n'
            '  "insight": {\n'
            '    "target": "추정 타겟 고객 (연령·성별·관심사·상황 구체적으로)",\n'
            '    "message": "이 광고가 전달하려는 핵심 메시지 한 줄",\n'
            '    "strategy": "이 소재의 광고 전략적 의도 (왜 이렇게 만들었는가)",\n'
            '    "strength": "이 소재의 강점",\n'
            '    "weakness": "이 소재의 약점 또는 개선 제안",\n'
            '    "tags": ["태그1","태그2","태그3","태그4"]\n'
            '  }\n'
            "}"
        )

        # ── 이미지 base64 시도 ──
        img_result = fetch_image_b64(item["image_url"])

        if img_result:
            b64, mt = img_result
            content = [
                {
                    "type": "image",
                    "source": {
                        "type":       "base64",
                        "media_type": mt,
                        "data":       b64,
                    }
                },
                {"type": "text", "text": prompt_text}
            ]
        else:
            # 이미지 로드 실패 시 텍스트만으로 분석
            content = [{"type": "text", "text": prompt_text}]

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",  # vision 지원
                "max_tokens": 900,
                "messages":   [{"role": "user", "content": content}],
            },
            timeout=30,
        )
        if resp.status_code != 200: return None
        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{"), txt.rfind("}") + 1
        return json.loads(txt[s:e]) if s != -1 and e > 0 else None
    except Exception:
        return None


def analyze_parallel(items, max_workers=3):
    """
    병렬 분석 - 이미지 다운로드와 API 호출 동시 진행
    실패 시 재시도 1회 + 텍스트 fallback 보장
    """
    if not API_KEY: return items
    id_map = {item["id"]: item for item in items}

    def task(item):
        # 1차 시도 (이미지 포함)
        result = analyze(item)
        if result:
            return item["id"], result
        # 2차 시도 - 잠깐 대기 후 재시도
        time.sleep(1.5)
        result = analyze(item)
        if result:
            return item["id"], result
        # 3차 - 이미지 없이 키워드+메타정보만으로 강제 분석
        result = analyze_text_only(item)
        return item["id"], result

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(task, item): item["id"]
            for item in items if not item.get("ai")
        }
        for future in as_completed(futures):
            try:
                aid, result = future.result(timeout=60)
                if result and aid in id_map:
                    id_map[aid]["ai"] = result
            except Exception:
                pass
    return items


def analyze_text_only(item):
    """이미지 없이 키워드·메타정보만으로 분석 (최후 fallback)"""
    if not API_KEY: return None
    try:
        parts = [f"검색 키워드: {item['keyword']}"]
        if item.get("advertiser"): parts.append(f"광고주: {item['advertiser']}")
        if item.get("headline"):   parts.append(f"헤드라인: {item['headline']}")
        if item.get("body"):       parts.append(f"본문: {item['body']}")
        if item.get("cta"):        parts.append(f"CTA: {item['cta']}")
        if item.get("platforms"):  parts.append(f"플랫폼: {item['platforms']}")

        prompt = (
            "광고 전략 전문가입니다. 아래 정보로 광고 소재를 분석해주세요.\n\n"
            + "\n".join(parts) +
            "\n\n이미지를 직접 볼 수 없으니 수집된 텍스트 정보 기반으로 최대한 분석해주세요.\n"
            "아래 JSON만 반환 (마크다운·백틱 없이):\n"
            '{"copy_analysis":{"visible_text":"수집된 카피 요약","hook":"추정 후크",'
            '"headline":"헤드라인","cta":"CTA","appeal":"소구포인트 유형+근거"},'
            '"tone_manner":{"mood":"추정 분위기","color_tone":"알 수 없음",'
            '"visual_style":"알 수 없음","typography":"알 수 없음","target_feel":"추정 감정"},'
            '"insight":{"target":"타겟 추정","message":"핵심 메시지",'
            '"strategy":"전략 추정","strength":"강점","weakness":"약점",'
            '"tags":["태그1","태그2","태그3"]}}'
        )
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 700,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=20,
        )
        if resp.status_code != 200: return None
        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{"), txt.rfind("}") + 1
        return json.loads(txt[s:e]) if s != -1 and e > 0 else None
    except Exception:
        return None

def summarize_insights(analyzed_items):
    if not API_KEY or not analyzed_items: return None
    snippets = []
    for a in analyzed_items[:20]:
        ai = a.get("ai") or {}
        if not ai: continue
        snippets.append(
            "- 소구:" + ai.get("appeal", "") +
            " / 타겟:" + ai.get("target", "") +
            " / 메시지:" + ai.get("message", "")
        )
    if not snippets: return None
    json_schema = (
        '{"dominant_appeal":"가장 많이 쓰인 소구 유형 + 비율 설명",'
        '"common_target":"공통 타겟 고객 요약",'
        '"key_message":"반복되는 핵심 메시지 패턴",'
        '"strategy":"이 광고들이 공유하는 전략적 방향 (2~3문장)",'
        '"recommendations":"경쟁 우위를 위한 차별화 제안 (2~3문장)",'
        '"tags":["태그1","태그2","태그3","태그4","태그5"]}'
    )
    prompt = (
        "광고 전략 전문가입니다. 아래는 Meta 광고 소재 분석 결과들입니다.\n\n" +
        "\n".join(snippets) +
        "\n\n이 소재들을 종합해 아래 JSON만 반환 (마크다운/백틱 없이 순수 JSON):\n" +
        json_schema
    )
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model":      "claude-haiku-4-5-20251001",
                "max_tokens": 700,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        if resp.status_code != 200: return None
        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{"), txt.rfind("}") + 1
        return json.loads(txt[s:e]) if s != -1 and e > 0 else None
    except Exception:
        return None


# ============================================================
# 유틸
# ============================================================
def merge(existing, new_items):
    known = {make_fp(a) for a in existing}
    known |= {make_fp(a) for a in existing if a["id"] in st.session_state.hidden}
    out, n = list(existing), 0
    for item in new_items:
        k = make_fp(item)
        if k in known: continue
        known.add(k); out.append(item); n += 1
    return out, n

def get_visible(ftype, fkw, fstar, fai):
    hidden = st.session_state.hidden
    items = [a for a in st.session_state.assets if a["id"] not in hidden]
    if ftype != "전체":        items = [a for a in items if a["asset_type"] == ftype]
    if fkw and fkw != "전체": items = [a for a in items if a["keyword"] == fkw]
    if fstar:                  items = [a for a in items if a.get("starred")]
    if fai:                    items = [a for a in items if a.get("ai")]
    return items

def do_reset():
    st.session_state.assets   = []
    st.session_state.hidden   = set()
    st.session_state.history  = []
    st.session_state.log      = []
    st.session_state.selected = set()
    st.session_state.summary  = None

def toggle_star(aid):
    for a in st.session_state.assets:
        if a["id"] == aid:
            a["starred"] = not a.get("starred", False); break

def to_csv(items):
    import csv
    fields = ["keyword","country","asset_type","advertiser","headline","body","cta",
              "image_url","source_url","caption","width","height","created_at","starred"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for a in items:
        w.writerow({f: a.get(f, "") for f in fields})
    return buf.getvalue().encode("utf-8-sig")


def fetch_image_bytes(url: str) -> bytes | None:
    """이미지 URL → bytes. 직접 다운로드 실패 시 Playwright 스크린샷으로 fallback"""
    # 1차: requests 직접 다운로드
    try:
        resp = requests.get(url, timeout=8, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.facebook.com/",
        })
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.content
    except Exception:
        pass

    # 2차: Playwright 스크린샷 fallback
    try:
        ensure_browser()
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 800, "height": 800})
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(1500)
            img_bytes = page.screenshot(type="jpeg", quality=80)
            browser.close()
            return img_bytes
    except Exception:
        return None


def to_pptx(items: list, summary: dict | None = None) -> bytes:
    """
    선택된 소재 → PPT
    슬라이드 구성:
      1. 표지
      2. 소재별 슬라이드 (이미지 + AI 분석)
      3. 총합 인사이트 (summary 있을 때)
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    import tempfile

    # 색상 팔레트
    C_BG    = RGBColor(0xFF, 0xFF, 0xFF)
    C_DARK  = RGBColor(0x11, 0x13, 0x18)
    C_BLUE  = RGBColor(0x1A, 0x6D, 0xFF)
    C_GRAY  = RGBColor(0x3A, 0x3F, 0x4A)
    C_MUTED = RGBColor(0x8A, 0x90, 0x9E)
    C_BG2   = RGBColor(0xF7, 0xF8, 0xFA)
    C_GREEN = RGBColor(0x00, 0xA8, 0x6B)
    C_BDBLUE= RGBColor(0xCC, 0xDD, 0xFF)

    def add_text(slide, text, x, y, w, h, size=12, bold=False,
                 color=None, align=PP_ALIGN.LEFT, wrap=True):
        txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = txBox.text_frame
        tf.word_wrap = wrap
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color or C_DARK
        return txBox

    def add_rect(slide, x, y, w, h, fill_color, line_color=None):
        from pptx.util import Inches
        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE_TYPE.RECTANGLE
            Inches(x), Inches(y), Inches(w), Inches(h)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill_color
        if line_color:
            shape.line.color.rgb = line_color
            shape.line.width = Pt(0.5)
        else:
            shape.line.fill.background()
        return shape

    prs = Presentation()
    prs.slide_width  = Inches(13.33)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]  # 완전 빈 레이아웃

    # ── 1. 표지 슬라이드 ──────────────────────────────
    slide = prs.slides.add_slide(blank)

    # 배경
    add_rect(slide, 0, 0, 13.33, 7.5, C_DARK)
    # 파란 포인트 바
    add_rect(slide, 0, 0, 0.08, 7.5, C_BLUE)

    add_text(slide, "AD INTEL",        0.4, 1.8, 12, 1.2, size=44, bold=True,  color=C_BG)
    add_text(slide, "META AD LIBRARY INTELLIGENCE REPORT",
                                       0.4, 3.0, 12, 0.6, size=13, bold=False, color=C_BLUE)

    kw_list = list(dict.fromkeys(a["keyword"] for a in items))
    add_text(slide, "키워드: " + " · ".join(kw_list),
                                       0.4, 3.8, 12, 0.5, size=12, color=C_MUTED)
    add_text(slide, f"소재 {len(items)}개  ·  {time.strftime('%Y.%m.%d')}",
                                       0.4, 4.3, 12, 0.5, size=12, color=C_MUTED)

    # ── 2. 소재별 슬라이드 ────────────────────────────
    for item in items:
        slide = prs.slides.add_slide(blank)

        # 배경
        add_rect(slide, 0,    0, 13.33, 7.5, C_BG)
        add_rect(slide, 0,    0, 13.33, 0.06, C_BLUE)   # 상단 파란 선
        add_rect(slide, 4.8,  0, 0.01,  7.5, C_BDBLUE)  # 세로 구분선

        # ── 왼쪽: 이미지 영역 ──
        img_bytes = fetch_image_bytes(item["image_url"])
        if img_bytes:
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(img_bytes)
                tmp_path = tmp.name
            try:
                pic = slide.shapes.add_picture(tmp_path, Inches(0.3), Inches(0.4),
                                               width=Inches(4.2))
                # 이미지 높이 최대 6.5인치 제한
                if pic.height > Inches(6.5):
                    pic.height = Inches(6.5)
                    pic.width  = Inches(4.2)
            except Exception:
                add_text(slide, "이미지 로드 실패", 0.3, 2.5, 4.2, 1, color=C_MUTED)
            import os; os.unlink(tmp_path)
        else:
            add_rect(slide, 0.3, 0.4, 4.2, 6.5, C_BG2)
            add_text(slide, "이미지 없음", 0.3, 3.2, 4.2, 0.8, align=PP_ALIGN.CENTER, color=C_MUTED)

        # ── 오른쪽: 메타 + AI 분석 ──
        rx = 5.1  # 오른쪽 시작 x
        rw = 7.8  # 오른쪽 너비

        # 키워드 배지
        add_text(slide, item["keyword"].upper() + "  ·  " + item["country"],
                 rx, 0.25, rw, 0.35, size=9, bold=True, color=C_BLUE)

        # 타입 + 사이즈
        badge = "IMAGE" if item["asset_type"] == "image" else "VIDEO"
        add_text(slide, f"{badge}  {item['width']}×{item['height']}px  ·  {item['created_at'][11:16]}",
                 rx, 0.6, rw, 0.35, size=9, color=C_MUTED)

        ai = item.get("ai")
        if ai:
            # AI 분석 박스 배경
            add_rect(slide, rx - 0.1, 1.05, rw + 0.2, 5.9, C_BG2)

            add_text(slide, "APPEAL ANALYSIS",
                     rx, 1.15, rw, 0.35, size=9, bold=True, color=C_BLUE)

            fields_ai = [
                ("후크",   ai.get("hook",    "—")),
                ("소구",   ai.get("appeal",  "—")),
                ("타겟",   ai.get("target",  "—")),
                ("메시지", ai.get("message", "—")),
            ]
            y_pos = 1.6
            for label, val in fields_ai:
                add_text(slide, label, rx, y_pos, 0.9, 0.4, size=10, bold=True, color=C_GRAY)
                add_text(slide, val,   rx + 0.9, y_pos, rw - 1.0, 0.5,
                         size=10, color=C_DARK, wrap=True)
                y_pos += 0.65

            # 태그
            tags = ai.get("tags", [])
            if tags:
                add_text(slide, "  ".join(f"#{t}" for t in tags),
                         rx, y_pos + 0.15, rw, 0.45, size=10, color=C_BLUE)
        else:
            add_text(slide, "AI 분석 없음\n(소재 선택 후 [선택 분석] 실행)",
                     rx, 2.5, rw, 1.0, size=11, color=C_MUTED)

    # ── 3. 총합 인사이트 슬라이드 ─────────────────────
    if summary:
        slide = prs.slides.add_slide(blank)
        add_rect(slide, 0, 0, 13.33, 7.5, C_DARK)
        add_rect(slide, 0, 0, 0.08,  7.5, C_BLUE)

        add_text(slide, "TOTAL INSIGHT",
                 0.4, 0.3, 12, 0.6, size=22, bold=True, color=C_BG)
        add_text(slide, "선택 소재 종합 분석",
                 0.4, 0.9, 12, 0.4, size=12, color=C_BLUE)

        # 2열 그리드
        grid = [
            ("DOMINANT APPEAL",    summary.get("dominant_appeal", "—")),
            ("COMMON TARGET",      summary.get("common_target",   "—")),
            ("KEY MESSAGE PATTERN",summary.get("key_message",     "—")),
        ]
        for i, (lbl, val) in enumerate(grid):
            col = i % 2
            row = i // 2
            gx = 0.4 + col * 6.4
            gy = 1.5 + row * 1.6
            add_rect(slide, gx, gy, 6.0, 1.4,
                     RGBColor(0x1A, 0x20, 0x30))
            add_text(slide, lbl, gx + 0.15, gy + 0.1,  5.7, 0.3,
                     size=8, bold=True, color=C_BLUE)
            add_text(slide, val, gx + 0.15, gy + 0.45, 5.7, 0.85,
                     size=10, color=C_BG, wrap=True)

        # 전략 + 제안
        sy = 4.6
        for lbl, key in [("STRATEGY", "strategy"), ("RECOMMENDATIONS", "recommendations")]:
            add_text(slide, lbl, 0.4, sy, 12, 0.3,
                     size=8, bold=True, color=C_BLUE)
            add_text(slide, summary.get(key, "—"), 0.4, sy + 0.3, 12.5, 0.7,
                     size=10, color=C_BG, wrap=True)
            sy += 1.2

        # 태그
        tags = summary.get("tags", [])
        if tags:
            add_text(slide, "  ".join(f"#{t}" for t in tags),
                     0.4, 7.0, 12, 0.35, size=10, color=C_BLUE)

    # 버퍼로 저장
    buf = io.BytesIO()
    prs.save(buf)
    buf.seek(0)
    return buf.read()


# ============================================================
# 헤더
# ============================================================
st.markdown("""
<div class="hdr">
  <div class="hdr-row"><div class="logo">AD<b>INTEL</b></div><div class="ver">v3.2</div></div>
  <div class="sub">META AD LIBRARY INTELLIGENCE BOARD</div>
</div>""", unsafe_allow_html=True)


# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown('<div class="slbl">DISPLAY</div>', unsafe_allow_html=True)
    new_dark = st.toggle("Dark Mode", value=st.session_state.dark)
    if new_dark != st.session_state.dark:
        st.session_state.dark = new_dark; st.rerun()
    st.markdown("---")

    st.markdown('<div class="slbl">AI ANALYSIS</div>', unsafe_allow_html=True)
    ai_on = st.toggle("소구포인트 분석 ON/OFF", value=st.session_state.ai_on)
    st.session_state.ai_on = ai_on
    if ai_on:
        if API_KEY:
            st.success("API Key 연결됨")
            st.caption("선택 소재만 분석 · Haiku · 소재당 ~1원")
        else:
            st.error("API Key 없음")
            st.caption("Streamlit Cloud > Settings > Secrets\nANTHROPIC_API_KEY = 'sk-ant-...'")
    else:
        st.caption("OFF — API 호출 없음 (무료)")
    st.markdown("---")

    st.markdown('<div class="slbl">SCRAPE</div>', unsafe_allow_html=True)
    country = st.selectbox("국가", ["KR","US","JP","GB","SG","AU"], index=0, label_visibility="collapsed")
    st.caption(f"대상 국가: **{country}**")
    scrolls = st.slider("스크롤 깊이", 3, 15, 8, 1)
    max_n   = st.slider("최대 수집량", 10, 150, 60, 10)
    st.markdown("---")

    st.markdown('<div class="slbl">FILTER & SORT</div>', unsafe_allow_html=True)
    ftype = st.selectbox("소재 타입", ["전체","image","video_poster"], label_visibility="collapsed")
    kws   = ["전체"] + list(dict.fromkeys(a["keyword"] for a in st.session_state.assets))
    fkw   = st.selectbox("키워드", kws, label_visibility="collapsed")
    fstar = st.toggle("즐겨찾기만", value=False)
    fai   = st.toggle("AI 분석된 것만", value=False)
    cols  = st.select_slider("열 수", options=[2,3,4,5], value=4)
    sort  = st.selectbox("정렬", ["최신순","오래된순","키워드순","즐겨찾기순"], label_visibility="collapsed")
    st.markdown("---")

    st.markdown('<div class="slbl">EXPORT</div>', unsafe_allow_html=True)
    exp_items = get_visible(ftype, fkw if fkw != "전체" else None, fstar, fai)
    stars     = [a for a in st.session_state.assets if a.get("starred")]
    if exp_items:
        st.download_button("CSV 내보내기", data=to_csv(exp_items),
            file_name=f"adintel_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    if stars:
        st.download_button("즐겨찾기 CSV", data=to_csv(stars),
            file_name=f"adintel_star_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    if st.button("보드 초기화", use_container_width=True):
        do_reset(); st.rerun()

    if st.session_state.log:
        st.markdown("---")
        st.markdown('<div class="slbl">LOG</div>', unsafe_allow_html=True)
        for lg in reversed(st.session_state.log[-8:]):
            cls = "ok" if lg["ok"] else "er"
            st.markdown(
                f'<div class="log"><span class="ts">{lg["t"]}</span>'
                f'<span class="{cls}">{"+" if lg["ok"] else "!"} {lg["kw"]} — {lg["n"]}건</span></div>',
                unsafe_allow_html=True)


# ============================================================
# AI 배너
# ============================================================
if ai_on and API_KEY:
    st.markdown("""<div class="banner">
        <div class="dot dot-on"></div>
        <span class="banner-txt">AI 분석 <b>ON</b> &nbsp;—&nbsp; 소재 선택 후 일괄 분석 &nbsp;·&nbsp; Claude Haiku (병렬 처리)</span>
    </div>""", unsafe_allow_html=True)
elif ai_on and not API_KEY:
    st.markdown("""<div class="banner banner-w">
        <div class="dot" style="background:var(--wn)"></div>
        <span class="banner-txt">AI ON — API Key 없음 &nbsp;·&nbsp; Streamlit > Settings > Secrets > <b>ANTHROPIC_API_KEY</b></span>
    </div>""", unsafe_allow_html=True)


# ============================================================
# 검색창 (기존 원본 — 단일 키워드)
# ============================================================
st.markdown('<div class="srch">', unsafe_allow_html=True)
st.markdown('<div class="srch-lbl">KEYWORD SEARCH</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([5, 1, 1])
with c1:
    kw = st.text_input("kw",
        placeholder="예: 캐리어, 공기청정기, 스킨케어, 다이어트",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({"_enter": True}))
with c2:
    do_new = st.button("검색", use_container_width=True)
with c3:
    do_add = st.button("누적 검색", use_container_width=True)

if st.session_state.pop("_enter", False): do_new = True
st.caption("엔터 / 검색 = 새 검색   ·   누적 검색 = 기존 보드에 추가 (중복·제외 자동 제외)")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 검색 실행 (기존 원본)
# ============================================================
if do_new or do_add:
    q = (kw or "").strip()
    if not q:
        st.warning("검색어를 입력하세요.")
    else:
        try:
            if do_new:
                st.session_state.assets   = []
                st.session_state.hidden   = set()
                st.session_state.history  = []
                st.session_state.summary  = None
                st.session_state.selected = set()

            with st.spinner(f"'{q}' 수집 중 — Meta Ad Library 실시간 접근..."):
                items = scrape(q, country, scrolls, max_n)

            merged, added = merge(st.session_state.assets, items)
            st.session_state.assets = merged

            if q not in st.session_state.history:
                st.session_state.history.append(q)

            st.session_state.log.append({"t": time.strftime("%H:%M"), "kw": q, "n": added, "ok": True})

            st.success(f"{added}개 수집 완료") if added > 0 else st.info("새 소재 없음")
            st.rerun()

        except Exception as e:
            st.session_state.log.append({"t": time.strftime("%H:%M"), "kw": q, "n": 0, "ok": False})
            st.error(f"오류: {e}")


# ============================================================
# 스탯
# ============================================================
all_a = st.session_state.assets
shown = get_visible(ftype, fkw if fkw != "전체" else None, fstar, fai)

if sort == "최신순":     shown = sorted(shown, key=lambda a: a["created_at"], reverse=True)
elif sort == "오래된순": shown = sorted(shown, key=lambda a: a["created_at"])
elif sort == "키워드순": shown = sorted(shown, key=lambda a: a["keyword"])
elif sort == "즐겨찾기순": shown = sorted(shown, key=lambda a: (not a.get("starred"), a["created_at"]))

ic = sum(1 for a in shown if a["asset_type"] == "image")
vc = sum(1 for a in shown if a["asset_type"] == "video_poster")

for col, (lbl, val, sub) in zip(st.columns(6), [
    ("TOTAL",    len(all_a),   "누적 수집"),
    ("SHOWN",    len(shown),   f"IMG {ic} · VID {vc}"),
    ("KEYWORDS", len(set(a["keyword"] for a in all_a)), "검색어"),
    ("STARRED",  sum(1 for a in all_a if a.get("starred")), "즐겨찾기"),
    ("HIDDEN",   len(st.session_state.hidden), "제외"),
    ("AI",       sum(1 for a in all_a if a.get("ai")), "분석 완료"),
]):
    col.markdown(
        f'<div class="sc"><div class="sc-lbl">{lbl}</div>'
        f'<div class="sc-val">{val}</div><div class="sc-sub">{sub}</div></div>',
        unsafe_allow_html=True)

st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)


# ============================================================
# 키워드 태그
# ============================================================
if st.session_state.history:
    html = '<div class="tags">'
    for h in st.session_state.history[-20:]:
        n = sum(1 for a in all_a if a["keyword"] == h)
        html += f'<span class="tag"><span class="tag-dot"></span>{h} <span style="opacity:.5">({n})</span></span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ============================================================
# 총합 인사이트 패널
# ============================================================
summary = st.session_state.get("summary")
if summary:
    tags_html = "".join(f'<span class="summary-tag">{t}</span>' for t in summary.get("tags", []))
    st.markdown(
        '<div class="summary-box">'
        '<div class="summary-head">TOTAL INSIGHT — 선택 소재 종합 분석</div>'
        '<div class="summary-grid">'
        '<div class="summary-item"><div class="summary-item-lbl">DOMINANT APPEAL</div>'
        f'<div class="summary-item-val">{summary.get("dominant_appeal","—")}</div></div>'
        '<div class="summary-item"><div class="summary-item-lbl">COMMON TARGET</div>'
        f'<div class="summary-item-val">{summary.get("common_target","—")}</div></div>'
        '<div class="summary-item"><div class="summary-item-lbl">KEY MESSAGE PATTERN</div>'
        f'<div class="summary-item-val">{summary.get("key_message","—")}</div></div>'
        '<div class="summary-item"><div class="summary-item-lbl">KEYWORDS</div>'
        f'<div class="summary-item-val"><div class="summary-tags">{tags_html}</div></div></div>'
        '</div>'
        '<div class="summary-strategy"><div class="summary-strategy-lbl">STRATEGY</div>'
        f'<div class="summary-strategy-val">{summary.get("strategy","—")}</div></div>'
        '<div class="summary-strategy" style="margin-bottom:0">'
        '<div class="summary-strategy-lbl">RECOMMENDATIONS</div>'
        f'<div class="summary-strategy-val">{summary.get("recommendations","—")}</div></div>'
        '</div>',
        unsafe_allow_html=True)
    if st.button("인사이트 초기화", key="clear_summary"):
        st.session_state.summary  = None
        st.session_state.selected = set()
        st.rerun()


# ============================================================
# 소재 보드
# ============================================================
sel = st.session_state.selected

st.markdown(
    f'<div class="sec"><div class="sec-t">소재 보드</div>'
    f'<div class="sec-n">{len(shown)} assets · {sort}</div></div>',
    unsafe_allow_html=True)

if ai_on and API_KEY and shown:
    sel_items      = [a for a in st.session_state.assets if a["id"] in sel]
    sel_unanalyzed = [a for a in sel_items if not a.get("ai")]
    analyzed_sel   = [a for a in sel_items if a.get("ai")]

    bar_c, btn_c1, btn_c2, btn_c3 = st.columns([3, 1, 1, 1])
    with bar_c:
        st.markdown(
            f'<div class="sel-bar"><span class="sel-count">{len(sel)}</span>'
            '<span class="sel-bar-txt">선택됨  ·  ○ 버튼으로 소재를 선택하세요</span></div>',
            unsafe_allow_html=True)
    with btn_c1:
        if sel_unanalyzed:
            if st.button(f"선택 분석 ({len(sel_unanalyzed)})", use_container_width=True):
                pb = st.progress(0, text=f"분석 중... 0 / {len(sel_unanalyzed)}")
                id_map = {a["id"]: a for a in st.session_state.assets}
                done = 0

                def do_one(item):
                    result = analyze(item)
                    if result: return item["id"], result
                    time.sleep(1)
                    result = analyze(item)
                    if result: return item["id"], result
                    return item["id"], analyze_text_only(item)

                with ThreadPoolExecutor(max_workers=3) as ex:
                    futures = {ex.submit(do_one, item): item for item in sel_unanalyzed}
                    for future in as_completed(futures):
                        try:
                            aid, result = future.result(timeout=60)
                            if result and aid in id_map:
                                id_map[aid]["ai"] = result
                            done += 1
                            pb.progress(
                                done / len(sel_unanalyzed),
                                text=f"분석 중... {done} / {len(sel_unanalyzed)}"
                            )
                        except Exception:
                            done += 1

                pb.progress(1.0, text=f"완료! {done}개 분석")
                pb.empty()
                st.rerun()
    with btn_c2:
        if analyzed_sel:
            if st.button(f"종합 인사이트 ({len(analyzed_sel)})", use_container_width=True):
                with st.spinner("종합 인사이트 생성 중..."):
                    st.session_state.summary = summarize_insights(analyzed_sel)
                st.rerun()
    with btn_c3:
        if analyzed_sel:
            if st.button(f"PPT 내보내기 ({len(analyzed_sel)})", use_container_width=True):
                with st.spinner(f"PPT 생성 중... 이미지 {len(analyzed_sel)}개 수집 (잠시 기다려 주세요)"):
                    pptx_bytes = to_pptx(analyzed_sel, st.session_state.get("summary"))
                fname = f"adintel_{time.strftime('%Y%m%d_%H%M')}.pptx"
                st.download_button(
                    "다운로드",
                    data=pptx_bytes,
                    file_name=fname,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True,
                )

if not shown:
    st.markdown(
        '<div class="empty"><div class="empty-t">수집된 소재가 없습니다</div>'
        '<div class="empty-d">키워드를 입력하고 검색하면<br>'
        'Meta Ad Library에서 광고 소재를 실시간으로 수집합니다.</div></div>',
        unsafe_allow_html=True)
else:
    grid = st.columns(cols)
    for i, item in enumerate(shown):
        with grid[i % cols]:
            is_sel = item["id"] in sel

            st.markdown('<div class="card">', unsafe_allow_html=True)

            try:
                st.image(item["image_url"], use_container_width=True)
            except Exception:
                st.markdown(
                    '<div style="height:100px;background:var(--bg3);display:flex;'
                    'align-items:center;justify-content:center;color:var(--mu);font-size:10px;">'
                    'LOAD FAILED</div>', unsafe_allow_html=True)

            bc   = "b-img" if item["asset_type"] == "image" else "b-vid"
            bl   = "IMG"   if item["asset_type"] == "image" else "VID"
            sel_b = '<span class="bdg" style="background:var(--ac);color:#fff;border-color:var(--ac)">SEL</span> ' if is_sel else ""
            sv_b  = '<span class="bdg b-sav">★</span> ' if item.get("starred") else ""
            ai_b  = '<span class="bdg b-ai">AI</span> ' if item.get("ai")      else ""

            # 카피 정보
            adv  = item.get("advertiser", "")
            hl   = item.get("headline", "")
            body = item.get("body", "")
            cta  = item.get("cta", "")

            adv_html  = f'<div style="font-size:10px;font-weight:700;color:var(--ac);margin-bottom:2px;">{adv}</div>' if adv else ""
            hl_html   = f'<div style="font-size:12px;font-weight:600;color:var(--tx);margin-bottom:3px;line-height:1.3;">{hl[:60]}{"..." if len(hl)>60 else ""}</div>' if hl else ""
            body_html = f'<div style="font-size:11px;color:var(--tx2);line-height:1.45;margin-bottom:4px;opacity:.85;">{body[:120]}{"..." if len(body)>120 else ""}</div>' if body else ""
            cta_html  = f'<span style="display:inline-block;font-size:9px;font-weight:700;background:var(--ac2);color:var(--ac);border-radius:4px;padding:2px 7px;margin-top:2px;">{cta}</span>' if cta else ""

            st.markdown(
                '<div class="card-body">'
                f'<div class="card-kw">{item["keyword"]} · {item["country"]}</div>'
                + sel_b + sv_b + ai_b +
                f'<span class="bdg {bc}">{bl}</span>'
                + adv_html + hl_html + body_html + cta_html +
                f'<div class="card-meta" style="margin-top:6px;">{item["width"]}x{item["height"]}px · {item["created_at"][11:16]}</div>'
                '</div>',
                unsafe_allow_html=True)

            ai_data = item.get("ai")
            if ai_data:
                copy_a  = ai_data.get("copy_analysis") or {}
                tone    = ai_data.get("tone_manner")   or {}
                insight = ai_data.get("insight")       or {}
                tags    = insight.get("tags") or ai_data.get("tags") or []
                tags_html = "".join(f'<span class="ai-tag">{t}</span>' for t in tags)

                def row(label, val):
                    if not val: return ""
                    return (f'<div style="margin-bottom:5px;">'
                            f'<span style="font-size:10px;font-weight:700;'
                            f'color:var(--ac);min-width:70px;display:inline-block">'
                            f'{label}</span>'
                            f'<span style="font-size:11px;color:var(--tx2);">{val}</span>'
                            f'</div>')

                st.markdown(
                    '<div class="ai-wrap"><div class="ai-box">'

                    # ── 1. 카피 분석 ──
                    '<div class="ai-head" style="margin-bottom:8px;">📝 카피 분석</div>'
                    + row("노출 카피", copy_a.get("visible_text","")[:120])
                    + row("후크",     copy_a.get("hook",""))
                    + row("헤드라인", copy_a.get("headline",""))
                    + row("CTA",      copy_a.get("cta",""))
                    + row("소구",     copy_a.get("appeal",""))

                    # ── 2. 톤앤매너 ──
                    + '<div style="border-top:1px solid var(--ac2);margin:10px 0 8px;"></div>'
                    '<div class="ai-head" style="margin-bottom:8px;">🎨 톤앤매너</div>'
                    + row("분위기",   tone.get("mood",""))
                    + row("색감",     tone.get("color_tone",""))
                    + row("비주얼",   tone.get("visual_style",""))
                    + row("감정",     tone.get("target_feel",""))

                    # ── 3. 인사이트 ──
                    + '<div style="border-top:1px solid var(--ac2);margin:10px 0 8px;"></div>'
                    '<div class="ai-head" style="margin-bottom:8px;">💡 인사이트</div>'
                    + row("타겟",     insight.get("target",""))
                    + row("메시지",   insight.get("message",""))
                    + row("전략",     insight.get("strategy",""))
                    + (f'<div style="font-size:11px;color:var(--ok);margin-bottom:3px;">▲ {insight.get("strength","")}</div>' if insight.get("strength") else "")
                    + (f'<div style="font-size:11px;color:var(--er);margin-bottom:6px;">▼ {insight.get("weakness","")}</div>' if insight.get("weakness") else "")
                    + (f'<div style="margin-top:6px">{tags_html}</div>' if tags_html else "")

                    + '</div></div>',
                    unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # 버튼 4개 — 아이콘으로 줄바꿈 없이
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if st.button("✓" if is_sel else "○", key="sel_" + item["id"], use_container_width=True):
                    if is_sel: st.session_state.selected.discard(item["id"])
                    else:      st.session_state.selected.add(item["id"])
                    st.rerun()
            with b2:
                if st.button("★" if item.get("starred") else "☆", key="sv_" + item["id"], use_container_width=True):
                    toggle_star(item["id"]); st.rerun()
            with b3:
                if st.button("✕", key="hd_" + item["id"], use_container_width=True):
                    st.session_state.hidden.add(item["id"]); st.rerun()
            with b4:
                st.link_button("↗", item["source_url"], use_container_width=True)


# ============================================================
# 푸터
# ============================================================
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
th   = "DARK" if D else "LIGHT"
ai_s = "AI ON · Haiku" if (ai_on and API_KEY) else "AI OFF"
st.markdown(
    f'<div style="border-top:2px solid var(--bd);padding-top:14px;display:flex;justify-content:space-between;">'
    f'<span style="font-family:Pretendard,sans-serif;font-size:10px;color:var(--mu)">ADINTEL v3.2 · {th} · {ai_s}</span>'
    f'<span style="font-family:Pretendard,sans-serif;font-size:10px;color:var(--mu)">{time.strftime("%Y-%m-%d")}</span>'
    f'</div>',
    unsafe_allow_html=True)
