"""Playwright automation script to record real BreatheWise browser interactions
at 1920x1080 into demo-video/raw-recordings/.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw-recordings"
RAW_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "http://localhost:3000"
VIEWPORT = {"width": 1920, "height": 1080}

CURSOR_INIT_SCRIPT = """
(() => {
  const initCursor = () => {
    if (document.getElementById('bw-demo-cursor')) return;
    const style = document.createElement('style');
    style.textContent = `
      #bw-demo-cursor {
        position: fixed;
        width: 22px;
        height: 22px;
        margin-left: -11px;
        margin-top: -11px;
        border-radius: 9999px;
        border: 2px solid rgba(183, 243, 107, 0.95);
        background: rgba(183, 243, 107, 0.16);
        box-shadow: 0 0 18px rgba(183, 243, 107, 0.35);
        pointer-events: none;
        z-index: 2147483647;
        transform: translate3d(-100px, -100px, 0) scale(1);
        transition: transform 110ms ease-out, background 120ms ease;
      }
      #bw-demo-cursor.clicking {
        transform: translate3d(var(--cx, -100px), var(--cy, -100px), 0) scale(0.72);
        background: rgba(88, 214, 160, 0.45);
      }
    `;
    document.head.appendChild(style);
    const el = document.createElement('div');
    el.id = 'bw-demo-cursor';
    document.body.appendChild(el);

    window.addEventListener('mousemove', (e) => {
      el.style.setProperty('--cx', e.clientX + 'px');
      el.style.setProperty('--cy', e.clientY + 'px');
      el.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0) scale(1)`;
    }, { passive: true });
    window.addEventListener('mousedown', () => el.classList.add('clicking'), { passive: true });
    window.addEventListener('mouseup', () => el.classList.remove('clicking'), { passive: true });
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCursor);
  } else {
    initCursor();
  }
})();
"""


def smooth_move(page: Page, x: float, y: float, steps: int = 24) -> None:
    page.mouse.move(x, y, steps=steps)


def smooth_click_locator(page: Page, locator, steps: int = 22) -> None:
    box = locator.bounding_box()
    if box:
        cx = box["x"] + box["width"] / 2.0
        cy = box["y"] + box["height"] / 2.0
        smooth_move(page, cx, cy, steps=steps)
        time.sleep(0.18)
        page.mouse.down()
        time.sleep(0.08)
        page.mouse.up()
    else:
        locator.click()


def smooth_scroll(page: Page, delta_y: int, steps: int = 28, step_delay: float = 0.03) -> None:
    per_step = delta_y / steps
    for _ in range(steps):
        page.mouse.wheel(0, per_step)
        time.sleep(step_delay)


def record_clip(browser, name: str, fn) -> Path:
    temp_dir = RAW_DIR / f"_tmp_{name}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    context = browser.new_context(
        viewport=VIEWPORT,
        record_video_dir=str(temp_dir),
        record_video_size=VIEWPORT,
        device_scale_factor=1,
    )
    context.add_init_script(CURSOR_INIT_SCRIPT)
    page = context.new_page()
    video_path = None
    try:
        fn(page)
        page.screenshot(path=str(RAW_DIR / f"{name}_end.png"))
        # Brief gentle pointer nudge ensures WebM encoder flushes final frame cleanly
        page.mouse.move(960, 540, steps=6)
        time.sleep(0.6)
    finally:
        video = page.video
        context.close()
        if video is not None:
            video_path = Path(video.path())

    out_path = RAW_DIR / f"{name}.webm"
    if video_path and video_path.exists():
        shutil.move(str(video_path), str(out_path))
    shutil.rmtree(temp_dir, ignore_errors=True)
    print(f"Saved raw recording: {out_path}")
    return out_path


def run_all_recordings(only: set[str] | None = None) -> None:
    def should(name: str) -> bool:
        return not only or name in only

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Scene 2: Landing Page (with live Pune Open-Meteo preview)
        def rec_landing(page: Page):
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            page.wait_for_selector("text=Verified Live Reading", timeout=15000)
            # Wait until Loading... disappears
            page.wait_for_function(
                "() => !document.body.innerText.includes('Loading...')",
                timeout=15000,
            )
            smooth_move(page, 1280, 380, steps=20)
            time.sleep(1.5)
            smooth_scroll(page, 420, steps=30, step_delay=0.035)
            time.sleep(1.2)

        if should("scene2_landing"):
            record_clip(browser, "scene2_landing", rec_landing)

        # 2. Scene 3: Dashboard (AQI, Weather, Trend Chart, Daily Insight & Recommendations)
        def rec_dashboard(page: Page):
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle")
            page.wait_for_selector("text=Raw Pollutant Concentrations", timeout=20000)
            page.wait_for_selector("text=Daily Air Insight", timeout=35000)
            time.sleep(1.5)

            # Hover AQI card and weather card deliberately
            smooth_move(page, 420, 320, steps=25)
            time.sleep(1.2)
            smooth_move(page, 1420, 340, steps=25)
            time.sleep(1.0)

            # Scroll smoothly to pollution trend chart & toggle PM2.5
            smooth_scroll(page, 380, steps=26, step_delay=0.03)
            time.sleep(0.8)
            pm25_btn = page.get_by_role("button", name="PM2.5", exact=True)
            smooth_click_locator(page, pm25_btn)
            time.sleep(1.4)

            # Sweep across chart points to trigger Recharts tooltip
            smooth_move(page, 620, 560, steps=20)
            time.sleep(0.5)
            smooth_move(page, 980, 540, steps=25)
            time.sleep(1.0)

            # Scroll down to Daily Air Insight & Recommended Actions
            smooth_scroll(page, 460, steps=30, step_delay=0.032)
            time.sleep(2.0)
            smooth_move(page, 850, 650, steps=18)
            time.sleep(1.2)

        if should("scene3_dashboard"):
            record_clip(browser, "scene3_dashboard", rec_dashboard)

        # 3. Scene 4: AI Air Advisor (Real Gemini API completion)
        def rec_advisor(page: Page):
            page.goto(f"{BASE_URL}/advisor", wait_until="networkidle")
            page.wait_for_selector("text=Live Context Passed to Model", timeout=20000)
            time.sleep(1.0)

            input_box = page.get_by_placeholder(
                "Ask about outdoor exercise, windows, children, commute..."
            )
            smooth_click_locator(page, input_box)
            time.sleep(0.3)
            input_box.type("Is it safe to go for a morning run today?", delay=42)
            time.sleep(0.4)

            ask_btn = page.get_by_role("button", name="Ask", exact=True)
            smooth_click_locator(page, ask_btn)

            # Wait for REAL Gemini API response to finish rendering
            page.wait_for_selector("text=Advisor Assessment", timeout=45000)
            time.sleep(1.2)
            smooth_move(page, 1180, 380, steps=28)
            time.sleep(1.6)
            smooth_scroll(page, 220, steps=24, step_delay=0.03)
            time.sleep(1.8)
            smooth_move(page, 1020, 540, steps=24)
            time.sleep(2.4)
            smooth_move(page, 1040, 550, steps=10)
            time.sleep(0.8)

        if should("scene4_advisor"):
            record_clip(browser, "scene4_advisor", rec_advisor)

        # 4. Scene 5: Smart Daily Routine
        def rec_routine(page: Page):
            page.goto(f"{BASE_URL}/routine", wait_until="networkidle")
            page.wait_for_selector("text=Optimal Outdoor Window", timeout=45000)
            time.sleep(1.8)
            smooth_move(page, 1280, 300, steps=22)
            time.sleep(1.0)
            smooth_scroll(page, 420, steps=35, step_delay=0.035)
            time.sleep(2.4)
            smooth_scroll(page, 260, steps=22, step_delay=0.035)
            smooth_move(page, 900, 520, steps=15)
            time.sleep(1.6)

        if should("scene5_routine"):
            record_clip(browser, "scene5_routine", rec_routine)

        # 5. Scene 6a: Indoor Air Guide
        def rec_indoor(page: Page):
            page.goto(f"{BASE_URL}/indoor", wait_until="networkidle")
            page.wait_for_selector("text=Daily Indoor Protection Checklist", timeout=40000)
            time.sleep(1.5)
            smooth_scroll(page, 420, steps=28, step_delay=0.03)
            time.sleep(0.8)
            # Click first two checklist items
            c1 = page.get_by_text("Run kitchen exhaust chimney or fan during all high-heat cooking")
            smooth_click_locator(page, c1)
            time.sleep(0.5)
            c2 = page.get_by_text("Replace dry sweeping with damp microfiber mopping for floor dust")
            smooth_click_locator(page, c2)
            time.sleep(1.2)

        if should("scene6_indoor"):
            record_clip(browser, "scene6_indoor", rec_indoor)

        # 6. Scene 6b: Sustainable Alternatives
        def rec_sustainable(page: Page):
            page.goto(f"{BASE_URL}/sustainable", wait_until="networkidle")
            page.wait_for_selector("text=All Categories", timeout=40000)
            page.wait_for_selector("text=Current habit", timeout=40000)
            time.sleep(1.5)
            smooth_scroll(page, 320, steps=25, step_delay=0.03)
            time.sleep(1.5)

        if should("scene6_sustainable"):
            record_clip(browser, "scene6_sustainable", rec_sustainable)

        # 7. Scene 6c: Personal Impact Tracker (real registered session + logged actions)
        def rec_impact(page: Page):
            # Register a real account through /auth so Impact Tracker persists & displays real charts
            page.goto(f"{BASE_URL}/auth", wait_until="networkidle")
            create_tab = page.get_by_role("button", name="Create Account")
            smooth_click_locator(page, create_tab)
            time.sleep(0.25)

            unique_email = f"demo.{int(time.time())}@example.com"
            page.get_by_placeholder("Ananya Deshmukh").fill("Ananya Deshmukh")
            page.get_by_placeholder("you@example.com").fill(unique_email)
            page.get_by_placeholder("At least 8 characters").fill("BreatheWiseDemo123!")
            submit_btn = page.get_by_role("button", name="Create BreatheWise Account")
            smooth_click_locator(page, submit_btn)

            page.wait_for_url("**/dashboard", timeout=15000)
            page.goto(f"{BASE_URL}/impact", wait_until="networkidle")
            page.wait_for_selector("text=Log Sustainable Action", timeout=15000)

            # Log a real cycling action
            qty_input = page.locator("input[type='number']")
            qty_input.fill("6")
            log_btn = page.get_by_role("button", name="Log Action")
            smooth_click_locator(page, log_btn)
            page.wait_for_selector("text=Recent Logged Actions", timeout=10000)
            time.sleep(0.8)

            # Log a metro trip too
            page.locator("select").select_option("public_transport_km")
            qty_input.fill("14")
            smooth_click_locator(page, log_btn)
            time.sleep(1.8)
            smooth_move(page, 1180, 460, steps=20)
            time.sleep(2.2)

        if should("scene6_impact"):
            record_clip(browser, "scene6_impact", rec_impact)

        browser.close()


if __name__ == "__main__":
    targets = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    run_all_recordings(targets)
    print("All Playwright recordings completed.")
