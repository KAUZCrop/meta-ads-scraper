from pathlib import Path
from datetime import datetime
from urllib.parse import quote, urlparse
import csv
import requests

from playwright.sync_api import sync_playwright

KEYWORD = "air purifier"
COUNTRY = "KR"
MAX_IMAGES = 30
MIN_WIDTH = 300
MIN_HEIGHT = 300

BASE_DIR = Path(__file__).parent
IMAGES_DIR = BASE_DIR / "images"
CSV_PATH = BASE_DIR / "ads.csv"

IMAGES_DIR.mkdir(exist_ok=True)

def init_csv():
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["image", "brand", "keyword", "ad_text", "source_url", "collected_at"])

def append_csv(row):
    with open(CSV_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def download_image(url, save_path):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    save_path.write_bytes(r.content)

def run():
    init_csv()

    url = (
        "https://www.facebook.com/ads/library/"
        f"?active_status=all&ad_type=all&country={COUNTRY}&q={quote(KEYWORD)}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 1800})
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(8000)

        # 스크롤
        for i in range(8):
            page.mouse.wheel(0, 3500)
            page.wait_for_timeout(2000)
            print(f"scroll {i+1} 완료")

        # 디버그용 전체 페이지
        page.screenshot(path=str(IMAGES_DIR / "debug_full_page.png"), full_page=True)

        # img 정보 한 번에 가져오기
        img_data = page.evaluate("""
        () => {
            const imgs = Array.from(document.querySelectorAll("img"));
            return imgs.map(img => ({
                src: img.currentSrc || img.src || "",
                width: img.naturalWidth || 0,
                height: img.naturalHeight || 0,
                alt: img.alt || ""
            }));
        }
        """)

        print("img 개수:", len(img_data))

        collected_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        saved = 0
        seen_src = set()

        for item in img_data:
            if saved >= MAX_IMAGES:
                break

            src = item.get("src", "")
            width = item.get("width", 0)
            height = item.get("height", 0)
            alt = item.get("alt", "")

            if not src:
                continue

            if src in seen_src:
                continue
            seen_src.add(src)

            # 너무 작은 이미지 제외
            if width < MIN_WIDTH or height < MIN_HEIGHT:
                continue

            # data:image 같은 건 제외
            if src.startswith("data:"):
                continue

            # 비율 필터
            ratio = width / height if height else 0
            if ratio > 2.5 or ratio < 0.3:
                continue

            ext = ".jpg"
            parsed = urlparse(src)
            path = parsed.path.lower()
            if ".png" in path:
                ext = ".png"
            elif ".webp" in path:
                ext = ".webp"
            elif ".jpeg" in path:
                ext = ".jpeg"

            image_name = f"ad_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{saved+1}{ext}"
            image_path = IMAGES_DIR / image_name

            try:
                download_image(src, image_path)

                append_csv([
                    image_name,
                    "unknown",
                    KEYWORD,
                    alt[:300],
                    src,
                    collected_at
                ])

                saved += 1
                print(f"저장 완료: {image_name} / {width}x{height}")

            except Exception as e:
                print(f"다운로드 실패: {src[:80]} / {e}")

        print("총 저장 수:", saved)
        browser.close()

if __name__ == "__main__":
    run()