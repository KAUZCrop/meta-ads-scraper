# ============================================================
# 올리브영 리뷰 수집기 — 별도 페이지 (원본 oliveyoung_scrap 기반)
# ============================================================
import asyncio
import concurrent.futures
import io
import json
import os
import queue
import random
import re

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="올리브영 리뷰 — ADINTEL",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color: #f7faf8; }
.main-title { font-size:2rem; font-weight:800; color:#1a5c38; }
.sub-title  { color:#6b9e7e; font-size:0.9rem; margin-bottom:1.5rem; }
div[data-testid="metric-container"] {
    background:white; border:1px solid #d4edda; border-radius:10px; padding:12px;
}
.stButton > button {
    background-color:#1a5c38 !important; color:white !important;
    border-radius:8px !important; border:none !important; font-weight:600 !important;
}
.stDownloadButton > button {
    background-color:#f0f7f3 !important; color:#1a5c38 !important;
    border:1.5px solid #1a5c38 !important; border-radius:8px !important;
    font-weight:600 !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# 스크래퍼 (원본 reviews.py 그대로)
# ============================================================
_DETAIL_URL    = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"
_HOME_URL      = "https://www.oliveyoung.co.kr"
_CHROMIUM_PATH = "/usr/bin/chromium"

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
]

_ANTI_DETECT_JS = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3, 4, 5] });
    window.chrome = { runtime: {} };
"""

_EXTRACT_JS = """
() => {
    function findInShadow(root, tagName) {
        const found = Array.from(root.querySelectorAll(tagName));
        for (const el of root.querySelectorAll('*')) {
            if (el.shadowRoot) {
                const nested = findInShadow(el.shadowRoot, tagName);
                for (const n of nested) found.push(n);
            }
        }
        return found;
    }

    const container = document.querySelector('oy-review-review-in-product');
    if (!container?.shadowRoot) return { error: 'no_container', reviews: [] };

    const items = findInShadow(container.shadowRoot, 'oy-review-review-item');
    if (!items.length) return { error: 'no_items', reviews: [] };

    const reviews = [];
    for (const item of items) {
        if (!item.shadowRoot) continue;
        const sr = item.shadowRoot;

        const userComp = sr.querySelector('oy-review-review-user');
        const name     = userComp?.shadowRoot?.querySelector('.name')?.textContent?.trim() || '';
        const skinType = userComp?.shadowRoot?.querySelector('.skin-type')?.textContent?.trim() || '';

        let stars = 0;
        for (const icon of sr.querySelectorAll('oy-review-star-icon')) {
            if ((icon.getAttribute('fill') || '').toLowerCase().includes('ff5753')) stars++;
        }

        const date    = sr.querySelector('.date')?.textContent?.trim() || '';
        const option  = sr.querySelector('.goods-option')?.textContent?.trim() || '';

        const contentComp = sr.querySelector('oy-review-review-content');
        const content = contentComp?.shadowRoot?.querySelector('p')?.textContent?.trim() || '';
        const helpful = sr.querySelector('.helpful-count')?.textContent?.trim() || '0';

        if (name || content) {
            reviews.push({ name, stars, date, option, content, skinType, helpful });
        }
    }
    return { reviews, count: reviews.length };
}
"""

_WAIT_READY_JS = "() => { const el = document.querySelector('oy-review-review-in-product'); return !!(el && el.shadowRoot); }"

_WAIT_ITEMS_JS = """
() => {
    const el = document.querySelector('oy-review-review-in-product');
    if (!el?.shadowRoot) return false;
    for (const node of el.shadowRoot.querySelectorAll('*')) {
        if (node.tagName?.toLowerCase() === 'oy-review-review-item') return true;
        if (node.shadowRoot) {
            if (node.shadowRoot.querySelector('oy-review-review-item')) return true;
        }
    }
    return false;
}
"""


def _to_review(r: dict) -> dict:
    return {
        "reviewer":      r.get("name", "익명"),
        "rating":        str(r.get("stars", "")),
        "date":          r.get("date", ""),
        "title":         "",
        "content":       r.get("content", ""),
        "skin_type":     r.get("skinType", ""),
        "helpful":       r.get("helpful", "0"),
        "purchase_type": r.get("option", ""),
    }


async def _run(goods_no: str, max_pages: int, on_progress, log: list) -> list:
    from playwright.async_api import async_playwright, TimeoutError as PWTimeout

    executable = _CHROMIUM_PATH if os.path.exists(_CHROMIUM_PATH) else None
    log.append(f"[시작] goodsNo={goods_no}, 최대 {max_pages}페이지")
    log.append(f"[브라우저] {executable or '내장 (Playwright 기본)'}")

    async with async_playwright() as pw:
        launch_kwargs = dict(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        if executable:
            launch_kwargs["executable_path"] = executable

        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice(_USER_AGENTS),
            locale="ko-KR",
        )
        await context.add_init_script(_ANTI_DETECT_JS)
        page = await context.new_page()
        all_reviews = []
        seen = set()

        try:
            log.append("[1단계] 홈 접속...")
            await page.goto(_HOME_URL, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(random.uniform(1.5, 2.5))

            log.append("[2단계] 상품 페이지 접속...")
            await page.goto(
                f"{_DETAIL_URL}?goodsNo={goods_no}&tab=review",
                wait_until="load",
                timeout=60_000,
            )
            log.append(f"[2단계] 완료 — {page.url}")

            try:
                await page.wait_for_load_state("networkidle", timeout=12_000)
            except Exception:
                pass

            log.append("[3단계] 리뷰 컴포넌트로 스크롤...")
            scrolled = await page.evaluate("""
                () => {
                    const el = document.querySelector('oy-review-review-in-product');
                    if (!el) return false;
                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                    return true;
                }
            """)
            log.append(f"[3단계] 스크롤: {'성공' if scrolled else '컴포넌트 없음'}")
            if not scrolled:
                log.append("[오류] oy-review-review-in-product 없음")
                return []

            log.append("[4단계] shadow root 초기화 대기...")
            try:
                await page.wait_for_function(_WAIT_READY_JS, timeout=15_000)
                log.append("[4단계] shadow root 확인됨")
            except PWTimeout:
                log.append("[4단계] 타임아웃 — 계속 진행")

            log.append("[5단계] 리뷰 아이템 렌더링 대기...")
            try:
                await page.wait_for_function(_WAIT_ITEMS_JS, timeout=20_000)
                log.append("[5단계] 리뷰 아이템 감지됨")
            except PWTimeout:
                log.append("[5단계] 타임아웃")

            await asyncio.sleep(1.0)

            target = max_pages * 10
            no_new_streak = 0
            scroll_num = 0

            log.append(f"[6단계] 추출→저장→스크롤 반복 시작 (목표 {target}개)")

            while len(all_reviews) < target:
                result = await page.evaluate(_EXTRACT_JS)
                raw = result.get("reviews", [])
                new_batch = [_to_review(r) for r in raw
                             if r.get("content") not in seen]

                if new_batch:
                    all_reviews.extend(new_batch)
                    seen.update(r["content"] for r in new_batch if r.get("content"))
                    no_new_streak = 0
                    log.append(f"[스크롤{scroll_num}] +{len(new_batch)}개 (누적 {len(all_reviews)}개)")
                else:
                    no_new_streak += 1
                    if no_new_streak >= 4:
                        log.append(f"[스크롤{scroll_num}] 4회 연속 신규 없음 → 종료")
                        break

                if on_progress:
                    on_progress(
                        min(len(all_reviews) // 10 + 1, max_pages),
                        max_pages,
                        len(all_reviews),
                    )

                scroll_num += 1
                await page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(0.6)

        except Exception as e:
            log.append(f"[오류] {type(e).__name__}: {e}")
        finally:
            await browser.close()

    log.append(f"[완료] 최종 수집: {len(all_reviews)}개")
    return all_reviews


def _run_in_thread(goods_no, max_pages, on_progress, log):
    return asyncio.run(_run(goods_no, max_pages, on_progress, log))


def scrape_reviews(goods_no, max_pages=10, on_progress=None):
    log = []
    progress_q = queue.Queue() if on_progress else None

    def thread_progress(cur, total, collected):
        progress_q.put((cur, total, collected))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _run_in_thread, goods_no, max_pages,
            thread_progress if on_progress else None,
            log,
        )
        if on_progress:
            while not future.done():
                try:
                    on_progress(*progress_q.get(timeout=0.1))
                except queue.Empty:
                    pass
            while True:
                try:
                    on_progress(*progress_q.get_nowait())
                except queue.Empty:
                    break
        return future.result(), log


# ============================================================
# 유틸
# ============================================================
def _extract_goods_no(text: str) -> str:
    text = text.strip()
    if re.match(r'^A\d{9,}$', text):
        return text
    match = re.search(r'goodsNo=([A-Za-z0-9]+)', text)
    return match.group(1) if match else ""


def _stars(rating) -> str:
    try:
        r = max(0, min(5, int(float(rating))))
    except Exception:
        return "☆☆☆☆☆"
    return "★" * r + "☆" * (5 - r)


def _to_csv(df):
    buf = io.BytesIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue()


def _to_excel(df):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="리뷰")
        ws = w.sheets["리뷰"]
        for col, width in zip("ABCDEFGH", [14, 8, 14, 24, 60, 12, 10, 14]):
            ws.column_dimensions[col].width = width
        from openpyxl.styles import PatternFill, Font, Alignment
        fill = PatternFill(start_color="1A5C38", end_color="1A5C38", fill_type="solid")
        for cell in ws[1]:
            cell.fill = fill
            cell.font = Font(color="FFFFFF", bold=True)
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for row in ws.iter_rows(min_row=2):
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    return buf.getvalue()


def _ko_df(df):
    return df.rename(columns={
        "reviewer": "작성자", "rating": "별점", "date": "작성일",
        "title": "제목", "content": "내용", "skin_type": "피부타입",
        "helpful": "도움돼요", "purchase_type": "구매유형",
    })


# ============================================================
# 세션 상태
# ============================================================
for _k, _v in {"oy_product": None, "oy_reviews": []}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ============================================================
# 사이드바
# ============================================================
with st.sidebar:
    st.markdown("## 🌿 올리브영 리뷰 수집기")
    st.caption("상품 URL 붙여넣기 → 수집 → 다운로드")
    st.divider()

    with st.form(key="oy_form"):
        url_input = st.text_area(
            "상품 URL 또는 goodsNo 입력",
            placeholder=(
                "https://www.oliveyoung.co.kr/store/goods/"
                "getGoodsDetail.do?goodsNo=A000000200106\n\n"
                "또는 goodsNo만: A000000200106"
            ),
            height=130,
            label_visibility="collapsed",
        )
        pname_input = st.text_input("상품명 (파일명용)", placeholder="예: 투에이엔 선크림")
        max_pages   = st.slider("수집 페이지 수", 1, 50, 10, help="1페이지 ≈ 리뷰 10개")
        submit_btn  = st.form_submit_button("🚀 리뷰 수집 시작", use_container_width=True)

    st.divider()
    if st.button("🔄 초기화", use_container_width=True):
        for _k in list(st.session_state.keys()):
            del st.session_state[_k]
        st.rerun()
    st.caption("⚠️ 개인·연구 목적으로만 사용하세요.")

# ============================================================
# 메인
# ============================================================
st.markdown('<p class="main-title">🌿 올리브영 리뷰 수집기</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">상품 URL을 붙여넣으면 리뷰를 한 번에 수집해요</p>', unsafe_allow_html=True)

if not st.session_state.oy_reviews and not st.session_state.oy_product:
    st.markdown("""
    <div style="background:white;border:1.5px solid #d4edda;border-radius:12px;
                padding:22px 26px;margin-bottom:20px;">
        <div style="font-weight:700;color:#1a5c38;font-size:1.05rem;margin-bottom:14px;">
            📋 사용 방법
        </div>
        <div style="color:#444;font-size:0.9rem;line-height:2.2;">
            1. 올리브영에서 원하는 <b>상품 페이지</b>를 열어요<br>
            2. 브라우저 <b>주소창 URL 전체</b>를 복사해요<br>
            3. 왼쪽 입력창에 붙여넣고 버튼 클릭<br>
            4. 수집 완료 후 <b>CSV / Excel / JSON</b>으로 다운로드
        </div>
    </div>
    """, unsafe_allow_html=True)

if submit_btn:
    goods_no = _extract_goods_no(url_input or "")
    if not goods_no:
        st.error("URL 또는 goodsNo를 올바르게 입력해주세요.")
    else:
        pname = pname_input.strip() or goods_no
        st.session_state.oy_product = {"name": pname, "goods_no": goods_no}
        st.session_state.oy_reviews = []

        pbar   = st.progress(0, text="수집 준비 중...")
        status = st.empty()

        def _on_progress(cur, total, collected):
            pbar.progress(int(cur / total * 100), text=f"페이지 {cur} / {total} 수집 중...")
            status.caption(f"📦 현재까지 {collected}개 리뷰 수집됨")

        with st.spinner("리뷰 수집 중... Playwright 브라우저로 우회 중입니다 ☕"):
            reviews, diag_log = scrape_reviews(goods_no, max_pages=max_pages, on_progress=_on_progress)

        pbar.progress(100, text="✅ 완료!")
        status.empty()

        if not reviews:
            st.error("리뷰를 가져오지 못했습니다.")
            with st.expander("🔍 진단 로그", expanded=True):
                for line in diag_log:
                    st.text(line)
            st.session_state.oy_product = None
        else:
            st.session_state.oy_reviews = reviews
            st.rerun()

if st.session_state.oy_reviews:
    reviews = st.session_state.oy_reviews
    pname   = (st.session_state.oy_product or {}).get("name", "상품")[:30]
    df      = _ko_df(pd.DataFrame(reviews))

    try:
        ratings  = [float(r["rating"]) for r in reviews if r.get("rating")]
        avg      = sum(ratings) / len(ratings) if ratings else 0.0
        five_pct = sum(1 for r in ratings if r == 5) / len(ratings) * 100 if ratings else 0.0
    except Exception:
        avg = five_pct = 0.0

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 리뷰 수",  f"{len(reviews):,}개")
    c2.metric("평균 별점",   f"{avg:.2f} / 5.0")
    c3.metric("5점 비율",    f"{five_pct:.1f}%")
    c4.metric("수집 페이지", f"{(len(reviews) - 1) // 10 + 1}페이지")

    st.markdown("---")
    st.markdown("#### ⬇️ 다운로드")
    d1, d2, d3, _ = st.columns([1, 1, 1, 2])
    with d1:
        st.download_button("📄 CSV", data=_to_csv(df),
            file_name=f"{pname}_리뷰.csv", mime="text/csv", use_container_width=True)
    with d2:
        st.download_button("📊 Excel", data=_to_excel(df),
            file_name=f"{pname}_리뷰.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True)
    with d3:
        st.download_button("🗂 JSON",
            data=json.dumps(reviews, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"{pname}_리뷰.json", mime="application/json",
            use_container_width=True)

    st.markdown("---")
    tab1, tab2 = st.tabs(["💬 리뷰 목록", "📋 데이터 테이블"])

    with tab1:
        filt = st.select_slider("별점 필터", ["전체", "5점", "4점", "3점", "2점", "1점"], "전체")
        shown = (reviews if filt == "전체"
                 else [r for r in reviews if str(r.get("rating", "")) == filt[0]])
        st.caption(f"{len(shown)}개 표시 중 (전체 {len(reviews)}개)")

        for r in shown[:50]:
            skin    = f" · {r['skin_type']}" if r.get("skin_type") else ""
            helpful = f" · 도움돼요 {r['helpful']}" if r.get("helpful") else ""
            content = str(r.get("content", "")).replace("\n", "<br>")
            st.markdown(f"""
            <div style="background:white;border-radius:10px;border:1px solid #e8f0eb;
                        padding:16px 20px;margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-weight:600;color:#1a1a1a;">{r.get("reviewer","익명")}</span>
                    <span style="color:#f5a623;letter-spacing:2px;">{_stars(r.get("rating",0))}</span>
                </div>
                <div style="color:#bbb;font-size:0.78rem;margin:4px 0 10px;">
                    {r.get("date","")}{skin}{helpful}
                </div>
                <div style="color:#333;line-height:1.65;font-size:0.9rem;">{content}</div>
            </div>
            """, unsafe_allow_html=True)

        if len(shown) > 50:
            st.info(f"화면에는 50개까지 표시됩니다. 전체 {len(shown)}개는 다운로드로 확인하세요.")

    with tab2:
        st.dataframe(df, use_container_width=True, height=520)
