# BreatheWise Demo Video Production

Production pipeline for **BreatheWise — Breathe Smarter. Live Better.** (`breathewise-demo.mp4`, 1920×1080, 30 FPS, H.264 MP4).

## Directory Layout

```text
demo-video/
├── breathewise-demo.mp4       # Final rendered 60–75s product demonstration video
├── raw-recordings/            # Unedited 1920×1080 Playwright browser captures (.webm)
├── assets/                    # Generated title sequences, lower-third badges, soundtrack.wav
├── scripts/
│   ├── generate_assets.py     # Renders Scene 1/2/7 title sequences, badges & soundtrack
│   ├── record_scenes.py       # Playwright automation recording real frontend interactions
│   └── assemble_video.py      # FFmpeg timeline assembly, transitions, zooms & audio mix
└── README.md
```

## Scene Breakdown

| Time | Scene | Source |
| :--- | :--- | :--- |
| `0:00 – 0:07` | **Scene 1 — Opening:** Dark eco-tech urban skyline, `"THE AIR WE BREATHE MATTERS."`, transition to BreatheWise logo | `assets/scene1_opening.mp4` |
| `0:07 – 0:13` | **Scene 2 — Product Introduction:** `BREATHEWISE — "Breathe Smarter. Live Better."` into live landing page | `assets/scene2_intro.mp4` + `raw-recordings/scene2_landing.webm` |
| `0:13 – 0:25` | **Scene 3 — Dashboard:** Real AQI (Indian NAQI & US EPA AQI), location, weather, pollutant metrics, interactive forecast chart & Daily Air Insight | `raw-recordings/scene3_dashboard.webm` |
| `0:25 – 0:40` | **Scene 4 — AI Air Advisor:** Submitting `"Is it safe to go for a morning run today?"` and capturing the live Google Gemini response & recommendations | `raw-recordings/scene4_advisor.webm` |
| `0:40 – 0:49` | **Scene 5 — Daily Routine:** Forecast-driven hourly schedule & Optimal Outdoor Window | `raw-recordings/scene5_routine.webm` |
| `0:49 – 0:59` | **Scene 6 — Indoor Air & Sustainability:** Ventilation guide & checklist, Sustainable Alternatives, and Personal Impact Tracker | `raw-recordings/scene6_indoor.webm`, `scene6_sustainable.webm`, `scene6_impact.webm` |
| `0:59 – 1:09` | **Scene 7 — Final Reveal:** Real-screen montage resolving to `BREATHEWISE — "Breathe Smarter. Live Better." — "Because every breath matters."` | `assets/scene7_end.mp4` |

## Reproducing the Render

1. Ensure the BreatheWise backend (`http://localhost:8000`) and frontend (`http://localhost:3000`) are running.
2. Activate `demo-video/.venv` and run:
   ```powershell
   demo-video\.venv\Scripts\python.exe demo-video\scripts\generate_assets.py
   demo-video\.venv\Scripts\python.exe demo-video\scripts\record_scenes.py
   demo-video\.venv\Scripts\python.exe demo-video\scripts\assemble_video.py
   ```
