# ============================================================
# AD INTEL v3.2 — Meta Ad Library Intelligence Board
# ============================================================
import sys, asyncio, subprocess, time, uuid, io, json, requests, base64
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
# 스크래퍼 — 모달/요소 스크린샷 기반 이미지 payload 확보
# ============================================================
def valid(w, h):
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
        item.get("width", 0),
        item.get("height", 0),
    )

def _bytes_to_b64(img_bytes: bytes | None) -> str:
    if not img_bytes:
        return ""
    return base64.b64encode(img_bytes).decode("utf-8")

def _close_modal(page):
    """Meta 모달을 닫기 위한 안전 처리"""
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
    except Exception:
        pass

def _capture_modal_or_element_b64(page, img_index: int, asset_type: str = "image") -> tuple[str, str]:
    """
    1순위: 소재 클릭 후 열린 모달(dialog) 화면을 메모리 screenshot → base64
    2순위: 모달 실패 시 현재 이미지/비디오 요소 자체를 screenshot → base64
    파일 저장 없음. 메모리에서 바로 처리.
    """
    try:
        locator = page.locator("img").nth(img_index) if asset_type == "image" else page.locator("video").nth(img_index)
        locator.scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(500)

        # 1) 모달 열기 시도
        try:
            locator.click(timeout=4000, force=True)
            page.wait_for_timeout(1200)

            dialog = page.locator('div[role="dialog"]').last
            if dialog.count() > 0 and dialog.is_visible():
                shot = dialog.screenshot(type="jpeg", quality=60, timeout=12000)
                _close_modal(page)
                b64 = _bytes_to_b64(shot)
                if b64:
                    return b64, "modal_screenshot"
        except Exception:
            _close_modal(page)

        # 2) fallback: 화면에 렌더링된 이미지 요소 자체 캡처
        try:
            locator.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(300)
            shot = locator.screenshot(type="jpeg", quality=70, timeout=10000)
            b64 = _bytes_to_b64(shot)
            if b64:
                return b64, "element_screenshot"
        except Exception:
            pass

    except Exception:
        pass

    return "", "capture_failed"

def scrape(keyword, country, scrolls, limit):
    ensure_browser()
    search_url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country={country}&q={quote(keyword)}"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions",
            "--disable-plugins", "--disable-background-networking",
            "--no-first-run", "--disable-default-apps",
        ])
        ctx = browser.new_context(viewport={"width": 1440, "height": 2000})
        ctx.route("**/*.{woff,woff2,ttf,otf,eot}", lambda r: r.abort())
        page = ctx.new_page()
        page.goto(search_url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(4500)

        def card_count():
            return page.evaluate("""() => {
                const sels = [
                    'div[class*="x8gbvx8"]',
                    'div[data-visualcompletion="ignore-dynamic"]',
                    'div._7jyr',
                    'div[class*="xh8yej3"]'
                ];
                for (const s of sels) {
                    const n = document.querySelectorAll(s).length;
                    if (n > 0) return n;
                }
                return document.querySelectorAll('img[src*="fbcdn"]').length;
            }""")

        prev, stalls = 0, 0
        for _ in range(scrolls):
            page.mouse.wheel(0, 3200)
            waited = 0
            while waited < 3500:
                page.wait_for_timeout(400)
                waited += 400
                cur = card_count()
                if cur > prev:
                    prev = cur
                    stalls = 0
                    break
            else:
                stalls += 1
                if stalls >= 2:
                    break

        raw = page.evaluate("""() => {
            const out = [];
            const imgs = Array.from(document.querySelectorAll('img'));
            imgs.forEach((img, idx) => {
                const src = img.currentSrc || img.src || '';
                if (!src || src.startsWith('data:')) return;
                out.push({
                    type: 'image', src, idx,
                    w: img.naturalWidth  || img.width  || 0,
                    h: img.naturalHeight || img.height || 0,
                    alt: img.alt || ''
                });
            });
            const vids = Array.from(document.querySelectorAll('video'));
            vids.forEach((v, idx) => {
                const poster = v.poster || '';
                if (!poster) return;
                out.push({
                    type: 'video_poster', src: poster, idx,
                    w: v.videoWidth  || v.clientWidth  || 0,
                    h: v.videoHeight || v.clientHeight || 0,
                    alt: ''
                });
            });
            return out;
        }""")

        seen, collected, now = set(), [], time.strftime("%Y-%m-%d %H:%M:%S")
        for r in raw:
            if len(collected) >= limit:
                break
            src = (r.get("src") or "").strip()
            w, h = int(r.get("w") or 0), int(r.get("h") or 0)
            if not src or not valid(w, h):
                continue

            asset_type = r.get("type", "image")
            img_b64, capture_source = _capture_modal_or_element_b64(
                page,
                int(r.get("idx") or 0),
                "image" if asset_type == "image" else "video_poster",
            )

            asset = {
                "id":             str(uuid.uuid4()),
                "keyword":        keyword,
                "country":        country,
                "asset_type":     asset_type,
                "image_url":      src,
                "source_url":     search_url,
                "caption":        (r.get("alt") or "").strip(),
                "width":          w,
                "height":         h,
                "created_at":     now,
                "starred":        False,
                "ai":             None,
                "img_b64":        img_b64,
                "capture_source": capture_source,
            }
            fp = make_fp(asset)
            if fp in seen:
                continue
            seen.add(fp)
            collected.append(asset)

        ctx.close()
        browser.close()

    return collected


# ============================================================
# AI 분석
# ============================================================
def _anthropic_model() -> str:
    try:
        return st.secrets.get("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
    except Exception:
        return "claude-haiku-4-5-20251001"

def analyze(item):
    """모달/요소 스크린샷 base64가 있을 때만 Claude Vision 분석. 추정 fallback 없음."""
    if not API_KEY:
        return {"_error": "API Key 없음"}

    b64 = item.get("img_b64", "")
    if not b64:
        return {"_error": "모달/요소 스크린샷 확보 실패: 실제 이미지 payload가 없어 분석하지 않았습니다."}

    try:
        prompt = f"""
당신은 광고 소재 분석가입니다. 첨부된 이미지는 Meta 광고 라이브러리에서 캡처한 실제 소재 화면입니다.
반드시 첨부 이미지에서 확인 가능한 내용만 분석하세요. 보이지 않는 정보는 추정하지 말고 '확인 불가'라고 쓰세요.

검색 키워드: {item['keyword']}
캡처 방식: {item.get('capture_source', 'unknown')}

아래 JSON만 반환하세요. 마크다운/백틱 금지:
{{"hook":"이미지에서 첫 시선을 잡는 핵심 요소",
"copy":"이미지 안에 보이는 텍스트/카피를 그대로 옮겨쓰기. 없으면 확인 불가",
"main_visual":"이미지에서 확인되는 주요 비주얼 요소",
"appeal":"소구포인트 유형 + 이미지 근거. 감성/이성/사회적증거/희소성/혜택 중 선택",
"tone":"색감·분위기·비주얼 스타일",
"target":"이미지 근거로 추정 가능한 타겟. 근거 부족 시 확인 불가",
"message":"이미지 내 텍스트와 비주얼 기준 핵심 메시지 한 줄",
"evidence":"위 분석의 근거가 되는 이미지 내 요소",
"tags":["태그1","태그2","태그3"]}}
"""
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": prompt},
        ]

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model": _anthropic_model(),
                "max_tokens": 700,
                "temperature": 0,
                "messages": [{"role": "user", "content": content}],
            },
            timeout=40,
        )
        if resp.status_code != 200:
            return {"_error": f"API {resp.status_code}: {resp.text[:300]}"}

        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{"), txt.rfind("}") + 1
        if s == -1 or e == 0:
            return {"_error": f"JSON 파싱 실패: {txt[:150]}"}
        return json.loads(txt[s:e])
    except Exception as ex:
        return {"_error": str(ex)[:300]}


def analyze_parallel(items, max_workers=6):
    if not API_KEY: return items
    id_map = {item["id"]: item for item in items}
    def task(item):
        return item["id"], analyze(item)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(task, item): item["id"] for item in items if not item.get("ai")}
        for future in as_completed(futures):
            try:
                aid, result = future.result(timeout=40)
                if result and aid in id_map:
                    id_map[aid]["ai"] = result
            except Exception as ex:
                pass
    return items


def test_api():
    """API 연결 테스트 — 실제 에러 메시지 반환"""
    if not API_KEY:
        return False, "API Key가 없습니다. Streamlit Secrets를 확인하세요."
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 10, "messages": [{"role": "user", "content": "hi"}]},
            timeout=10,
        )
        if resp.status_code == 200:
            return True, "API 정상 연결됨"
        return False, f"API 오류 {resp.status_code}: {resp.text[:300]}"
    except Exception as ex:
        return False, f"연결 실패: {ex}"

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
    fields = ["keyword","country","asset_type","image_url","source_url",
              "caption","width","height","created_at","starred"]
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
            if st.button("API 연결 테스트", use_container_width=True):
                ok, msg = test_api()
                if ok: st.success(msg)
                else:  st.error(msg)
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
                pb = st.progress(0, text="분석 중...")
                # analyze_parallel이 items 딕셔너리를 직접 수정하므로
                # st.session_state.assets의 동일 객체가 업데이트됨
                analyze_parallel(sel_unanalyzed, max_workers=6)
                done = sum(1 for it in sel_unanalyzed if it.get("ai"))
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
            cap   = item.get("caption", "")
            cap_h = f'<div class="card-cap">"{cap[:55]}{"..." if len(cap) > 55 else ""}"</div>' if cap else ""

            st.markdown(
                '<div class="card-body">'
                f'<div class="card-kw">{item["keyword"]} · {item["country"]}</div>'
                + sel_b + sv_b + ai_b +
                f'<span class="bdg {bc}">{bl}</span>'
                + cap_h +
                f'<div class="card-meta">{item["width"]}x{item["height"]}px · {item["created_at"][11:16]} · {item.get("capture_source","-")}</div>'
                '</div>',
                unsafe_allow_html=True)

            ai_data = item.get("ai")
            if ai_data:
                if ai_data.get("_error"):
                    # 에러 메시지 표시
                    st.markdown(
                        '<div class="ai-wrap"><div class="ai-box" style="border-color:var(--er)">'
                        f'<div class="ai-head" style="color:var(--er)">분석 오류</div>'
                        f'<div class="ai-body" style="font-size:11px">{ai_data["_error"]}</div>'
                        '</div></div>',
                        unsafe_allow_html=True)
                else:
                    has_img = bool(item.get("img_b64"))
                    tags_str = "".join(f'<span class="ai-tag">{t}</span>' for t in ai_data.get("tags", []))
                    copy_line = f'<b>카피</b>&nbsp;&nbsp;&nbsp;{ai_data["copy"]}<br>' if ai_data.get("copy") else ""
                    tone_line = f'<b>톤&매너</b>&nbsp;{ai_data["tone"]}<br>' if ai_data.get("tone") else ""
                    img_badge = '<span class="bdg b-ai" style="font-size:8px">IMG분석</span> ' if has_img else '<span class="bdg" style="background:var(--bg3);color:var(--mu);font-size:8px">텍스트추정</span> '
                    st.markdown(
                        '<div class="ai-wrap"><div class="ai-box">'
                        f'<div class="ai-head">APPEAL ANALYSIS {img_badge}</div>'
                        '<div class="ai-body">'
                        f'<b>후크</b>&nbsp;&nbsp;&nbsp;{ai_data.get("hook","—")}<br>'
                        + copy_line
                        + f'<b>소구</b>&nbsp;&nbsp;&nbsp;{ai_data.get("appeal","—")}<br>'
                        + tone_line
                        + f'<b>타겟</b>&nbsp;&nbsp;&nbsp;{ai_data.get("target","—")}<br>'
                        f'<b>메시지</b>&nbsp;{ai_data.get("message","—")}<br>'
                        f'<div style="margin-top:6px">{tags_str}</div>'
                        '</div></div></div>',
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
