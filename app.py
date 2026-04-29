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

# ── Playwright 설치 (최초 1회) ──
@st.cache_resource
def ensure_browser():
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    return True

# ── API Key (Streamlit Secrets) ──
# Streamlit Cloud: Settings > Secrets > ANTHROPIC_API_KEY = "sk-ant-..."
# 로컬: .streamlit/secrets.toml 에 동일하게 등록
def get_api_key():
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return ""

API_KEY = get_api_key()

# ── Page config ──
st.set_page_config(page_title="AD INTEL", page_icon="◼", layout="wide")

# ── Session state 초기화 ──
for k, v in {
    "assets": [], "hidden": set(), "history": [],
    "log": [], "ai_on": False, "dark": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# CSS — 라이트/다크 테마 전환
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
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700;800&family=DM+Sans:wght@400;500&display=swap');

{DARK if D else LIGHT}

html,body,[class*="css"]{{font-family:'DM Sans',sans-serif;background:var(--bg)!important;color:var(--tx)!important;}}
.stApp{{background:var(--bg)!important;}}
[data-testid="stHeader"]{{background:var(--bg)!important;border-bottom:1px solid var(--bd);}}
[data-testid="stSidebar"]{{background:var(--bg2)!important;border-right:1px solid var(--bd)!important;}}
[data-testid="stSidebar"] *{{color:var(--tx)!important;}}
.block-container{{padding-top:4.5rem;padding-bottom:3rem;max-width:1600px;}}

/* 헤더 */
.hdr{{margin-bottom:2rem;padding-bottom:1.2rem;border-bottom:2px solid var(--bd);}}
.hdr-row{{display:flex;align-items:center;gap:10px;}}
.logo{{font-family:'Syne',sans-serif;font-size:22px;font-weight:800;letter-spacing:-.5px;color:var(--tx);}}
.logo b{{color:var(--ac);}}
.ver{{font-family:'DM Mono',monospace;font-size:10px;color:var(--mu);border:1px solid var(--bd2);padding:2px 8px;border-radius:4px;background:var(--bg3);}}
.sub{{font-family:'DM Mono',monospace;font-size:10px;color:var(--mu);letter-spacing:2px;margin-top:8px;}}

/* 사이드바 라벨 */
.slbl{{font-family:'DM Mono',monospace;font-size:9px;color:var(--mu);letter-spacing:1.5px;text-transform:uppercase;margin:8px 0 6px;}}

/* 검색창 */
.srch{{background:var(--bg2);border:1.5px solid var(--bd);border-radius:14px;padding:16px 20px;margin-bottom:1.2rem;}}
.srch-lbl{{font-family:'DM Mono',monospace;font-size:9px;color:var(--mu);letter-spacing:2px;text-transform:uppercase;margin-bottom:8px;}}

/* 스탯 카드 */
.sc{{background:var(--bg);border:1.5px solid var(--bd);border-radius:12px;padding:20px 20px 18px;position:relative;overflow:hidden;box-shadow:var(--sh);transition:.2s;}}
.sc:hover{{border-color:var(--ac);box-shadow:var(--sh2);}}
.sc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--ac),#5b9dff);opacity:0;transition:.2s;}}
.sc:hover::before{{opacity:1;}}
.sc-lbl{{font-family:'DM Mono',monospace;font-size:9px;color:var(--mu);letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;}}
.sc-val{{font-family:'Syne',sans-serif;font-size:32px;font-weight:800;color:var(--tx);line-height:1;}}
.sc-sub{{font-size:11px;color:var(--mu);margin-top:8px;}}

/* 키워드 태그 */
.tags{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:1.2rem;}}
.tag{{font-family:'DM Mono',monospace;font-size:11px;background:var(--ac2);border:1px solid var(--ac2);color:var(--ac);padding:4px 10px;border-radius:20px;display:inline-flex;align-items:center;gap:6px;}}
.tag-dot{{width:5px;height:5px;border-radius:50%;background:var(--ok);}}

/* 섹션 헤더 */
.sec{{display:flex;align-items:center;justify-content:space-between;margin-bottom:.8rem;padding-bottom:10px;border-bottom:1.5px solid var(--bd);}}
.sec-t{{font-family:'Syne',sans-serif;font-size:13px;font-weight:800;color:var(--tx);letter-spacing:.5px;text-transform:uppercase;}}
.sec-n{{font-family:'DM Mono',monospace;font-size:11px;color:var(--mu);}}

/* 소재 카드 */
.card{{border:1.5px solid var(--bd);border-radius:12px;overflow:hidden;margin-bottom:10px;background:var(--bg);box-shadow:var(--sh);transition:.2s;}}
.card:hover{{border-color:var(--ac);box-shadow:var(--sh2);}}
.card-body{{padding:10px 12px;border-top:1px solid var(--bd);background:var(--bg2);}}
.card-kw{{font-family:'DM Mono',monospace;font-size:10px;color:var(--ac);letter-spacing:.8px;text-transform:uppercase;margin-bottom:4px;}}
.card-meta{{font-size:11px;color:var(--mu);margin-top:4px;}}
.card-cap{{font-size:11px;color:var(--tx2);margin:4px 0;opacity:.8;font-style:italic;line-height:1.4;}}
.bdg{{display:inline-block;font-family:'DM Mono',monospace;font-size:9px;padding:2px 7px;border-radius:20px;margin:0 2px 4px 0;font-weight:500;}}
.b-img{{background:var(--ac2);color:var(--ac);border:1px solid var(--ac2);}}
.b-vid{{background:rgba(124,92,255,.12);color:#7c5cff;border:1px solid rgba(124,92,255,.2);}}
.b-sav{{background:rgba(255,184,79,.12);color:var(--wn);border:1px solid rgba(255,184,79,.2);}}
.b-ai {{background:rgba(61,255,160,.10);color:var(--ok);border:1px solid rgba(61,255,160,.2);}}

/* AI 분석 박스 */
.ai-wrap{{padding:0 12px 12px;background:var(--bg2);}}
.ai-box{{background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:10px 12px;}}
.ai-head{{font-family:'DM Mono',monospace;font-size:9px;color:var(--ac);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;}}
.ai-body{{font-size:12px;color:var(--tx2);line-height:1.75;}}
.ai-tag{{display:inline-block;font-size:10px;background:var(--ac2);color:var(--ac);border-radius:4px;padding:1px 6px;margin:2px 2px 0 0;}}

/* AI 배너 */
.banner{{display:flex;align-items:center;gap:10px;background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:10px 16px;margin-bottom:1rem;}}
.banner-w{{background:rgba(224,123,0,.06);border-color:rgba(224,123,0,.2);}}
.dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
.dot-on{{background:var(--ok);box-shadow:0 0 6px var(--ok);}}
.dot-off{{background:var(--mu);}}
.banner-txt{{font-family:'DM Mono',monospace;font-size:11px;color:var(--tx2);}}

/* 총합 인사이트 */
.summary-box{{background:var(--bg2);border:2px solid var(--ac);border-radius:16px;padding:24px 28px;margin-bottom:1.5rem;}}
.summary-head{{font-family:'Syne',sans-serif;font-size:16px;font-weight:800;color:var(--ac);margin-bottom:16px;letter-spacing:.5px;}}
.summary-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;}}
.summary-item{{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;}}
.summary-item-lbl{{font-family:'DM Mono',monospace;font-size:9px;color:var(--mu);letter-spacing:1px;text-transform:uppercase;margin-bottom:6px;}}
.summary-item-val{{font-size:13px;color:var(--tx);line-height:1.5;}}
.summary-strategy{{background:var(--ac2);border:1px solid var(--ac2);border-radius:10px;padding:14px 16px;margin-bottom:12px;}}
.summary-strategy-lbl{{font-family:'DM Mono',monospace;font-size:9px;color:var(--ac);letter-spacing:1px;text-transform:uppercase;margin-bottom:8px;}}
.summary-strategy-val{{font-size:13px;color:var(--tx2);line-height:1.65;}}
.summary-tags{{display:flex;flex-wrap:wrap;gap:6px;}}
.summary-tag{{font-family:'DM Mono',monospace;font-size:10px;background:var(--ac2);color:var(--ac);border:1px solid var(--ac2);border-radius:4px;padding:3px 9px;}}
.sel-bar{{display:flex;align-items:center;background:var(--bg2);border:1.5px solid var(--bd);border-radius:10px;padding:10px 16px;margin-bottom:1rem;}}
.sel-count{{font-family:'Syne',sans-serif;font-size:14px;font-weight:800;color:var(--ac);margin-right:6px;}}
.sel-bar-txt{{font-family:'DM Mono',monospace;font-size:11px;color:var(--tx2);}}

/* 빈 상태 */
.empty{{text-align:center;padding:80px 20px;}}
.empty-t{{font-family:'Syne',sans-serif;font-size:16px;font-weight:700;color:var(--mu);margin-bottom:8px;}}
.empty-d{{font-size:13px;color:var(--mu);line-height:1.6;}}

/* 로그 */
.log{{font-family:'DM Mono',monospace;font-size:11px;color:var(--mu);padding:4px 0;border-bottom:1px solid var(--bd);}}
.log .ts{{color:var(--ac);margin-right:8px;}}
.log .ok{{color:var(--ok);}}
.log .er{{color:var(--er);}}

/* 버튼 */
.stButton>button{{font-family:'DM Mono',monospace!important;font-size:11px!important;border-radius:8px!important;border:1.5px solid var(--bd2)!important;background:var(--bg)!important;color:var(--tx2)!important;height:34px!important;transition:.15s!important;letter-spacing:.3px!important;}}
.stButton>button:hover{{border-color:var(--ac)!important;color:var(--ac)!important;background:var(--ac2)!important;}}
.stDownloadButton>button{{font-family:'DM Mono',monospace!important;font-size:11px!important;border-radius:8px!important;border:1.5px solid var(--bd2)!important;background:var(--bg)!important;color:var(--tx2)!important;}}

/* 입력 */
.stTextInput input{{background:var(--bg)!important;border:1.5px solid var(--bd2)!important;border-radius:10px!important;color:var(--tx)!important;font-family:'DM Sans',sans-serif!important;}}
.stTextInput input:focus{{border-color:var(--ac)!important;box-shadow:0 0 0 3px var(--ac2)!important;}}
div[data-baseweb="select"]>div{{background:var(--bg)!important;border-color:var(--bd2)!important;border-radius:8px!important;color:var(--tx)!important;}}

/* 알림 */
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
# 스크래퍼
# ============================================================
def valid(w, h):
    if w < 180 or h < 180: return False
    r = w / h if h else 0
    return 0.25 <= r <= 3.0

def fp(item):
    p = urlparse((item.get("image_url") or "").strip())
    return (f"{p.netloc}{p.path}", item.get("asset_type",""),
            (item.get("caption") or "").lower()[:80],
            item.get("width",0), item.get("height",0))

def scrape(keyword, country, scrolls, limit):
    ensure_browser()
    url = f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country={country}&q={quote(keyword)}"
    with sync_playwright() as p:
        br  = p.chromium.launch(headless=True, args=[
            "--no-sandbox","--disable-dev-shm-usage","--disable-extensions",
            "--disable-plugins","--disable-background-networking","--no-first-run"])
        ctx = br.new_context(viewport={"width":1440,"height":2000})
        ctx.route("**/*.{woff,woff2,ttf,otf,eot}", lambda r: r.abort())
        pg  = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(4000)

        def cnt():
            return pg.evaluate("""() => {
                for (const s of ['div[class*="x8gbvx8"]','div._7jyr','div[class*="xh8yej3"]']) {
                    const n = document.querySelectorAll(s).length; if (n>0) return n;
                }
                return document.querySelectorAll('img[src*="fbcdn"]').length;
            }""")

        prev = stalls = 0
        for _ in range(scrolls):
            pg.mouse.wheel(0, 3200)
            waited = 0
            while waited < 3500:
                pg.wait_for_timeout(400); waited += 400
                cur = cnt()
                if cur > prev: prev=cur; stalls=0; break
            else:
                stalls += 1
                if stalls >= 2: break

        raw = pg.evaluate("""() => {
            const o=[];
            for (const i of document.querySelectorAll('img')) {
                const s=i.currentSrc||i.src||'';
                if(!s||s.startsWith('data:')) continue;
                o.push({t:'image',s,w:i.naturalWidth||i.width||0,h:i.naturalHeight||i.height||0,a:i.alt||''});
            }
            for (const v of document.querySelectorAll('video')) {
                if(!v.poster) continue;
                o.push({t:'video_poster',s:v.poster,w:v.videoWidth||v.clientWidth||0,h:v.videoHeight||v.clientHeight||0,a:''});
            }
            return o;
        }""")
        ctx.close(); br.close()

    seen, out, now = set(), [], time.strftime("%Y-%m-%d %H:%M:%S")
    for r in raw:
        if len(out) >= limit: break
        s = (r.get("s") or "").strip()
        w, h = int(r.get("w",0)), int(r.get("h",0))
        if not s or not valid(w, h): continue
        a = {"id":str(uuid.uuid4()),"keyword":keyword,"country":country,
             "asset_type":r.get("t","image"),"image_url":s,"source_url":url,
             "caption":(r.get("a") or "").strip(),"width":w,"height":h,
             "created_at":now,"starred":False,"ai":None}
        k = fp(a)
        if k in seen: continue
        seen.add(k); out.append(a)
    return out


# ============================================================
# AI 분석
# ============================================================
def analyze(image_url, keyword):
    if not API_KEY: return None
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key":API_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"},
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 350,
                "messages": [{"role":"user","content":f"""광고 전략 전문가로서 Meta 광고 소재를 분석해주세요.

검색 키워드: {keyword}
이미지 URL: {image_url}

이미지를 직접 볼 수 없어도 키워드와 URL 패턴으로 분석해주세요.
아래 JSON만 반환 (마크다운·백틱 없이):
{{"hook":"첫 시선을 잡는 요소 (1문장)","appeal":"소구포인트 유형 + 설명 (감성/이성/사회적증거/희소성/혜택 분류)","target":"추정 타겟 (연령·성별·관심사)","message":"핵심 메시지 (1문장)","tags":["태그1","태그2","태그3"]}}"""}]
            },
            timeout=25,
        )
        if resp.status_code != 200: return None
        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{"), txt.rfind("}")+1
        return json.loads(txt[s:e]) if s != -1 and e > 0 else None
    except Exception:
        return None

def analyze_parallel(items, max_workers=6):
    """병렬 처리로 빠른 AI 분석 (순차 대비 4~6배 빠름)"""
    if not API_KEY: return items
    id_map = {item["id"]: item for item in items}

    def task(item):
        return item["id"], analyze(item["image_url"], item["keyword"])

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(task, item): item["id"] for item in items if not item.get("ai")}
        for future in as_completed(futures):
            aid, result = future.result()
            if result and aid in id_map:
                id_map[aid]["ai"] = result
    return items


def summarize_insights(analyzed_items) -> dict | None:
    """분석된 소재들을 종합해 총합 인사이트 생성"""
    if not API_KEY or not analyzed_items: return None
    snippets = []
    for a in analyzed_items[:20]:  # 최대 20개
        ai = a.get("ai", {})
        if not ai: continue
        snippets.append(
            f"- 소구:{ai.get('appeal','')} / 타겟:{ai.get('target','')} / 메시지:{ai.get('message','')}"
        )
    if not snippets: return None
    try:
        prompt = f"""광고 전략 전문가입니다. 아래는 Meta 광고 소재 분석 결과들입니다.

{chr(10).join(snippets)}

이 소재들을 종합해 아래 JSON만 반환 (마크다운·백틱 없이):
{{"dominant_appeal":"가장 많이 쓰인 소구 유형 + 비율 설명","common_target":"공통 타겟 고객 요약","key_message":"반복되는 핵심 메시지 패턴","strategy":"이 광고들이 공유하는 전략적 방향 (2~3문장)","recommendations":"경쟁 우위를 위한 차별화 제안 (2~3문장)","tags":["태그1","태그2","태그3","태그4","태그5"]}}"""

        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={{"x-api-key":API_KEY,"anthropic-version":"2023-06-01","content-type":"application/json"}},
            json={{"model":"claude-haiku-4-5-20251001","max_tokens":600,
                  "messages":[{{"role":"user","content":prompt}}]}},
            timeout=30,
        )
        if resp.status_code != 200: return None
        txt = resp.json()["content"][0]["text"].strip()
        s, e = txt.find("{{"), txt.rfind("}}")+1
        return json.loads(txt[s:e]) if s != -1 and e > 0 else None
    except Exception:
        return None


# ============================================================
# 유틸
# ============================================================
def merge(existing, new_items):
    known = {fp(a) for a in existing}
    known |= {fp(a) for a in existing if a["id"] in st.session_state.hidden}
    out, n = list(existing), 0
    for item in new_items:
        k = fp(item)
        if k in known: continue
        known.add(k); out.append(item); n += 1
    return out, n

def visible(ftype, fkw, fstar, fai):
    items = [a for a in st.session_state.assets if a["id"] not in st.session_state.hidden]
    if ftype != "전체": items = [a for a in items if a["asset_type"]==ftype]
    if fkw and fkw != "전체": items = [a for a in items if a["keyword"]==fkw]
    if fstar: items = [a for a in items if a.get("starred")]
    if fai:   items = [a for a in items if a.get("ai")]
    return items

def do_reset():
    st.session_state.assets  = []
    st.session_state.hidden  = set()
    st.session_state.history = []
    st.session_state.log     = []

def toggle_star(aid):
    for a in st.session_state.assets:
        if a["id"] == aid: a["starred"] = not a.get("starred",False); break

def to_csv(items):
    import csv
    fields = ["keyword","country","asset_type","image_url","source_url","caption","width","height","created_at","starred"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for a in items: w.writerow({f:a.get(f,"") for f in fields})
    return buf.getvalue().encode("utf-8-sig")


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

    # 테마
    st.markdown('<div class="slbl">DISPLAY</div>', unsafe_allow_html=True)
    new_dark = st.toggle("Dark Mode", value=st.session_state.dark)
    if new_dark != st.session_state.dark:
        st.session_state.dark = new_dark; st.rerun()

    st.markdown("---")

    # AI
    st.markdown('<div class="slbl">AI ANALYSIS</div>', unsafe_allow_html=True)
    ai_on = st.toggle("소구포인트 자동 분석", value=st.session_state.ai_on)
    st.session_state.ai_on = ai_on
    if ai_on:
        if API_KEY:
            st.success("API Key 연결됨")
            st.caption("검색 후 자동 분석 · Haiku · 소재당 ~1원")
        else:
            st.error("API Key 없음")
            st.caption("Streamlit Cloud > Settings > Secrets\nANTHROPIC_API_KEY = 'sk-ant-...'")
    else:
        st.caption("OFF — API 호출 없음 (무료)")

    st.markdown("---")

    # 수집
    st.markdown('<div class="slbl">SCRAPE</div>', unsafe_allow_html=True)
    country  = st.selectbox("국가", ["KR","US","JP","GB","SG","AU"], index=0, label_visibility="collapsed")
    st.caption(f"대상 국가: **{country}**")
    scrolls  = st.slider("스크롤 깊이", 3, 15, 8, 1)
    max_n    = st.slider("최대 수집량", 10, 150, 60, 10)

    st.markdown("---")

    # 필터
    st.markdown('<div class="slbl">FILTER & SORT</div>', unsafe_allow_html=True)
    ftype = st.selectbox("소재 타입", ["전체","image","video_poster"], label_visibility="collapsed")
    kws   = ["전체"] + list(dict.fromkeys(a["keyword"] for a in st.session_state.assets))
    fkw   = st.selectbox("키워드", kws, label_visibility="collapsed")
    fstar = st.toggle("즐겨찾기만", value=False)
    fai   = st.toggle("AI 분석된 것만", value=False)
    cols  = st.select_slider("열 수", options=[2,3,4,5], value=4)
    sort  = st.selectbox("정렬", ["최신순","오래된순","키워드순","즐겨찾기순"], label_visibility="collapsed")

    st.markdown("---")

    # 내보내기
    st.markdown('<div class="slbl">EXPORT</div>', unsafe_allow_html=True)
    exp   = visible(ftype, fkw if fkw!="전체" else None, fstar, fai)
    stars = [a for a in st.session_state.assets if a.get("starred")]
    if exp:
        st.download_button("CSV 내보내기", data=to_csv(exp),
            file_name=f"adintel_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    if stars:
        st.download_button("즐겨찾기 CSV", data=to_csv(stars),
            file_name=f"adintel_star_{time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv", use_container_width=True)
    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)
    if st.button("보드 초기화", use_container_width=True):
        do_reset(); st.rerun()

    # 로그
    if st.session_state.log:
        st.markdown("---")
        st.markdown('<div class="slbl">LOG</div>', unsafe_allow_html=True)
        for lg in reversed(st.session_state.log[-8:]):
            c = "ok" if lg["ok"] else "er"
            st.markdown(
                f'<div class="log"><span class="ts">{lg["t"]}</span>'
                f'<span class="{c}">{"+" if lg["ok"] else "!"} {lg["kw"]} — {lg["n"]}건</span></div>',
                unsafe_allow_html=True)


# ============================================================
# AI 상태 배너
# ============================================================
if ai_on and API_KEY:
    st.markdown("""<div class="banner">
        <div class="dot dot-on"></div>
        <span class="banner-txt">AI 분석 <b>ON</b> &nbsp;—&nbsp; 소재 선택 후 일괄 분석 (병렬 처리) &nbsp;·&nbsp; Claude Haiku</span>
    </div>""", unsafe_allow_html=True)
elif ai_on and not API_KEY:
    st.markdown("""<div class="banner banner-w">
        <div class="dot" style="background:var(--wn)"></div>
        <span class="banner-txt">AI ON — API Key 없음 &nbsp;·&nbsp; Streamlit Cloud > Settings > Secrets > <b>ANTHROPIC_API_KEY</b></span>
    </div>""", unsafe_allow_html=True)


# ============================================================
# 검색창
# ============================================================
st.markdown('<div class="srch">', unsafe_allow_html=True)
st.markdown('<div class="srch-lbl">KEYWORD SEARCH</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns([5,1,1])
with c1:
    kw = st.text_input("kw", placeholder="예: 캐리어, 스킨케어, 공기청정기",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({"_enter":True}))
with c2:
    do_new = st.button("검색", use_container_width=True)
with c3:
    do_add = st.button("누적 검색", use_container_width=True)

if st.session_state.pop("_enter", False): do_new = True
st.caption("엔터 / 검색 = 새 검색   ·   누적 검색 = 기존 보드에 추가")
st.markdown('</div>', unsafe_allow_html=True)


# ============================================================
# 검색 실행
# ============================================================
if do_new or do_add:
    q = (kw or "").strip()
    if not q:
        st.warning("검색어를 입력하세요.")
    else:
        try:
            if do_new:
                st.session_state.assets  = []
                st.session_state.hidden  = set()
                st.session_state.history = []

            # 1. 스크래핑
            with st.spinner(f"'{q}' 수집 중..."):
                items = scrape(q, country, scrolls, max_n)

            # 3. 병합
            merged, added = merge(st.session_state.assets, items)
            st.session_state.assets = merged
            if q not in st.session_state.history:
                st.session_state.history.append(q)

            ai_done = sum(1 for a in items if a.get("ai"))
            st.session_state.log.append({"t":time.strftime("%H:%M"),"kw":q,"n":added,"ok":True})

            msg = f"{added}개 수집 완료"
            if ai_on and API_KEY: msg += f" · AI 분석 {ai_done}개"
            (st.success(msg) if added > 0 else st.info("새 소재 없음"))
            st.rerun()

        except Exception as e:
            st.session_state.log.append({"t":time.strftime("%H:%M"),"kw":q,"n":0,"ok":False})
            st.error(f"오류: {e}")


# ============================================================
# 스탯
# ============================================================
all_a = st.session_state.assets
shown = visible(ftype, fkw if fkw!="전체" else None, fstar, fai)

if sort == "최신순":   shown = sorted(shown, key=lambda a:a["created_at"], reverse=True)
elif sort == "오래된순": shown = sorted(shown, key=lambda a:a["created_at"])
elif sort == "키워드순": shown = sorted(shown, key=lambda a:a["keyword"])
elif sort == "즐겨찾기순": shown = sorted(shown, key=lambda a:(not a.get("starred"),a["created_at"]))

ic = sum(1 for a in shown if a["asset_type"]=="image")
vc = sum(1 for a in shown if a["asset_type"]=="video_poster")
sc_data = [
    ("TOTAL",    len(all_a),   "누적 수집"),
    ("SHOWN",    len(shown),   f"IMG {ic} · VID {vc}"),
    ("KEYWORDS", len(set(a["keyword"] for a in all_a)), "검색어"),
    ("STARRED",  sum(1 for a in all_a if a.get("starred")), "즐겨찾기"),
    ("HIDDEN",   len(st.session_state.hidden), "제외"),
    ("AI",       sum(1 for a in all_a if a.get("ai")), "분석 완료"),
]
for col, (lbl, val, sub) in zip(st.columns(6), sc_data):
    col.markdown(f'<div class="sc"><div class="sc-lbl">{lbl}</div>'
                 f'<div class="sc-val">{val}</div><div class="sc-sub">{sub}</div></div>',
                 unsafe_allow_html=True)


# ============================================================
# 키워드 태그
# ============================================================
if st.session_state.history:
    html = '<div class="tags">'
    for h in st.session_state.history[-20:]:
        n = sum(1 for a in all_a if a["keyword"]==h)
        html += f'<span class="tag"><span class="tag-dot"></span>{h} <span style="opacity:.5">({n})</span></span>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)



# ============================================================
# 총합 인사이트 패널
# ============================================================
summary = st.session_state.get("summary")
if summary:
    tags_html = "".join(f'<span class="summary-tag">{t}</span>' for t in summary.get("tags",[]))
    st.markdown(
        '<div class="summary-box">' +
        '<div class="summary-head">TOTAL INSIGHT â 선택 소재 종합 분석</div>' +
        '<div class="summary-grid">' +
        '<div class="summary-item"><div class="summary-item-lbl">DOMINANT APPEAL</div>' +
        f'<div class="summary-item-val">{summary.get("dominant_appeal","—")}</div></div>' +
        '<div class="summary-item"><div class="summary-item-lbl">COMMON TARGET</div>' +
        f'<div class="summary-item-val">{summary.get("common_target","—")}</div></div>' +
        '<div class="summary-item"><div class="summary-item-lbl">KEY MESSAGE PATTERN</div>' +
        f'<div class="summary-item-val">{summary.get("key_message","—")}</div></div>' +
        '<div class="summary-item"><div class="summary-item-lbl">KEYWORDS</div>' +
        f'<div class="summary-item-val"><div class="summary-tags">{tags_html}</div></div></div>' +
        '</div>' +
        '<div class="summary-strategy"><div class="summary-strategy-lbl">STRATEGY</div>' +
        f'<div class="summary-strategy-val">{summary.get("strategy","—")}</div></div>' +
        '<div class="summary-strategy" style="margin-bottom:0"><div class="summary-strategy-lbl">RECOMMENDATIONS</div>' +
        f'<div class="summary-strategy-val">{summary.get("recommendations","—")}</div></div>' +
        '</div>',
        unsafe_allow_html=True)
    if st.button("인사이트 초기화", key="clear_summary"):
        st.session_state.summary = None
        st.session_state.selected = set()
        st.rerun()

# ============================================================
# 소재 보드
# ============================================================
sel = st.session_state.selected

# 섹션 헤더
st.markdown(
    f'<div class="sec"><div class="sec-t">소재 보드</div>' +
    f'<div class="sec-n">{len(shown)} assets · {sort}</div></div>',
    unsafe_allow_html=True)

# 선택 바 + 일괄 분석 버튼
if ai_on and API_KEY and shown:
    sel_items     = [a for a in st.session_state.assets if a["id"] in sel]
    sel_unanalyzed = [a for a in sel_items if not a.get("ai")]
    analyzed_sel  = [a for a in sel_items if a.get("ai")]

    bar_c, btn_c1, btn_c2 = st.columns([4, 1, 1])
    with bar_c:
        st.markdown(
            f'<div class="sel-bar"><span class="sel-count">{len(sel)}</span>' +
            '<span class="sel-bar-txt">선택됨  ·  SELECT 버튼으로 소재를 골라주세요</span></div>',
            unsafe_allow_html=True)
    with btn_c1:
        if sel_unanalyzed:
            if st.button(f"선택 분석 ({len(sel_unanalyzed)})", use_container_width=True):
                pb = st.progress(0, text="병렬 분석 중...")
                result_items = analyze_parallel(sel_unanalyzed, max_workers=6)
                id_map = {a["id"]: a for a in st.session_state.assets}
                done = 0
                for it in result_items:
                    if it.get("ai") and it["id"] in id_map:
                        id_map[it["id"]]["ai"] = it["ai"]
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

if not shown:
    st.markdown(
        '<div class="empty"><div class="empty-t">수집된 소재가 없습니다</div>' +
        '<div class="empty-d">키워드를 입력하고 검색하면<br>Meta Ad Library에서 광고 소재를 실시간으로 수집합니다.</div></div>',
        unsafe_allow_html=True)
else:
    grid = st.columns(cols)
    for i, item in enumerate(shown):
        with grid[i % cols]:
            is_sel = item["id"] in sel

            st.markdown('<div class="card">', unsafe_allow_html=True)

            # 이미지
            try:
                st.image(item["image_url"], use_container_width=True)
            except Exception:
                st.markdown(
                    '<div style="height:100px;background:var(--bg3);display:flex;' +
                    'align-items:center;justify-content:center;color:var(--mu);' +
                    'font-family:DM Mono,monospace;font-size:10px;">LOAD FAILED</div>',
                    unsafe_allow_html=True)

            # 메타 배지
            bc  = "b-img" if item["asset_type"] == "image" else "b-vid"
            bl  = "IMG"   if item["asset_type"] == "image" else "VID"
            sel_b = '<span class="bdg" style="background:var(--ac);color:#fff;border-color:var(--ac)">SELECTED</span> ' if is_sel else ""
            sv_b  = '<span class="bdg b-sav">SAVED</span> ' if item.get("starred") else ""
            ai_b  = '<span class="bdg b-ai">AI</span> '    if item.get("ai")       else ""
            cap = item.get("caption", "")
            cap_h = f'<div class="card-cap">"{cap[:55]}{"..." if len(cap) > 55 else ""}"</div>' if cap else ""

            kw_country = item["keyword"] + " / " + item["country"]
            dims = str(item["width"]) + "x" + str(item["height"]) + "px"
            created = item["created_at"][11:16]

            st.markdown(
                '<div class="card-body">' +
                f'<div class="card-kw">{kw_country}</div>' +
                sel_b + sv_b + ai_b +
                f'<span class="bdg {bc}">{bl}</span>' +
                cap_h +
                f'<div class="card-meta">{dims} · {created}</div>' +
                '</div>',
                unsafe_allow_html=True)

            # AI 분석 결과
            ai_data = item.get("ai")
            if ai_data:
                tags_str = "".join(
                    f'<span class="ai-tag">{t}</span>'
                    for t in ai_data.get("tags", [])
                )
                st.markdown(
                    '<div class="ai-wrap"><div class="ai-box">' +
                    '<div class="ai-head">APPEAL ANALYSIS</div>' +
                    '<div class="ai-body">' +
                    f'<b>후크</b>&nbsp;&nbsp;&nbsp;{ai_data.get("hook","—")}<br>' +
                    f'<b>소구</b>&nbsp;&nbsp;&nbsp;{ai_data.get("appeal","—")}<br>' +
                    f'<b>타겟</b>&nbsp;&nbsp;&nbsp;{ai_data.get("target","—")}<br>' +
                    f'<b>메시지</b>&nbsp;{ai_data.get("message","—")}<br>' +
                    f'<div style="margin-top:6px">{tags_str}</div>' +
                    '</div></div></div>',
                    unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

            # 버튼 4개
            b1, b2, b3, b4 = st.columns(4)
            with b1:
                sel_lbl = "DESELECT" if is_sel else "SELECT"
                if st.button(sel_lbl, key="sel_" + item["id"], use_container_width=True):
                    if is_sel: st.session_state.selected.discard(item["id"])
                    else:      st.session_state.selected.add(item["id"])
                    st.rerun()
            with b2:
                sv_lbl = "UNSAVE" if item.get("starred") else "SAVE"
                if st.button(sv_lbl, key="sv_" + item["id"], use_container_width=True):
                    toggle_star(item["id"]); st.rerun()
            with b3:
                if st.button("HIDE", key="hd_" + item["id"], use_container_width=True):
                    st.session_state.hidden.add(item["id"]); st.rerun()
            with b4:
                st.link_button("LINK", item["source_url"], use_container_width=True)


# ============================================================
# 푸터
# ============================================================
st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
th = "DARK" if D else "LIGHT"
ai_s = "AI ON · Haiku" if (ai_on and API_KEY) else "AI OFF"
st.markdown(f"""<div style="border-top:2px solid var(--bd);padding-top:14px;
    display:flex;justify-content:space-between;">
  <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--mu)">
    ADINTEL v3.2 · {th} · {ai_s}
  </span>
  <span style="font-family:'DM Mono',monospace;font-size:10px;color:var(--mu)">
    {time.strftime("%Y-%m-%d")}
  </span>
</div>""", unsafe_allow_html=True)
