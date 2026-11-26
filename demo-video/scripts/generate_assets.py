"""Generate high-resolution visual assets, title sequences, lower-third badges,
and synthesized ambient soundtrack + sound effects for the BreatheWise demo video.
"""

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Tuple

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1920, 1080
FPS = 30
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# Brand palette
BG = (9, 13, 11)          # #090D0B
SEC_BG = (17, 25, 21)     # #111915
CARD_BG = (21, 30, 25)    # #151E19
ACCENT = (183, 243, 107)  # #B7F36B
TEAL = (88, 214, 160)     # #58D6A0
TEXT = (244, 247, 243)    # #F4F7F3
MUTED = (143, 155, 145)   # #8F9B91

FONT_DISPLAY = r"C:\Windows\Fonts\segoeuib.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\segoeui.ttf"
FONT_LIGHT = r"C:\Windows\Fonts\segoeuil.ttf"
FONT_MONO = r"C:\Windows\Fonts\consolab.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _draw_breathewise_logo(
    draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, alpha: int = 255
) -> None:
    """Render the exact BreatheWise geometric emblem scaled around (cx, cy)."""
    s = size / 36.0
    x0 = cx - size / 2.0
    y0 = cy - size / 2.0
    radius = int(9 * s)
    draw.rounded_rectangle(
        [x0 + 1 * s, y0 + 1 * s, x0 + 35 * s, y0 + 35 * s],
        radius=radius,
        fill=(CARD_BG[0], CARD_BG[1], CARD_BG[2], alpha),
        outline=(ACCENT[0], ACCENT[1], ACCENT[2], int(alpha * 0.45)),
        width=max(2, int(1.6 * s)),
    )
    # Minimalist stylized cloud/air contour matching BrandMark SVG
    pts = [
        (9, 19.5),
        (9.6, 16.0),
        (12.2, 13.0),
        (16.5, 12.0),
        (19.6, 12.6),
        (21.6, 13.7),
        (22.8, 15.6),
        (25.0, 15.5),
        (26.8, 17.0),
        (27.0, 18.9),
        (26.5, 21.4),
        (24.9, 22.8),
        (22.3, 23.2),
        (12.2, 23.2),
        (10.0, 22.2),
        (9.0, 19.5),
    ]
    scaled = [(x0 + px * s, y0 + py * s) for px, py in pts]
    draw.line(
        scaled,
        fill=(ACCENT[0], ACCENT[1], ACCENT[2], alpha),
        width=max(3, int(1.9 * s)),
        joint="curve",
    )
    draw.line(
        [(x0 + 12.5 * s, y0 + 26.5 * s), (x0 + 23.5 * s, y0 + 26.5 * s)],
        fill=(TEAL[0], TEAL[1], TEAL[2], alpha),
        width=max(3, int(1.9 * s)),
    )


def _create_atmospheric_backdrop(glow_strength: float = 1.0) -> Image.Image:
    """Create dark eco-tech 1920x1080 backdrop with subtle atmospheric glow and grid."""
    y_grid, x_grid = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    dx = (x_grid - WIDTH * 0.5) / (WIDTH * 0.48)
    dy = (y_grid - HEIGHT * 0.38) / (HEIGHT * 0.52)
    dist2 = dx * dx + dy * dy
    glow = np.exp(-dist2 * 2.1) * glow_strength

    arr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.float32)
    arr[:, :, 0] = BG[0] + glow * 16.0
    arr[:, :, 1] = BG[1] + glow * 38.0
    arr[:, :, 2] = BG[2] + glow * 26.0

    # Subtle architectural grid lines
    arr[::64, :, :] += 3.5
    arr[:, ::64, :] += 3.5
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _draw_urban_skyline(
    base: Image.Image, progress: float, haze_alpha: float
) -> Image.Image:
    """Overlay a sleek dark urban skyline silhouette + gentle drifting particulate specks."""
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Stylized city towers along bottom third
    buildings = [
        (0, 810, 120), (125, 760, 95), (228, 700, 110), (345, 780, 80),
        (432, 650, 130), (570, 725, 105), (682, 610, 120), (810, 740, 90),
        (908, 675, 135), (1052, 595, 115), (1174, 710, 120), (1302, 640, 128),
        (1438, 730, 95), (1540, 680, 130), (1678, 755, 108), (1792, 690, 128),
    ]
    base_y = HEIGHT
    shift_x = -int(progress * 28)
    for bx, top_y, bw in buildings:
        x1 = bx + shift_x
        x2 = x1 + bw
        draw.rectangle(
            [x1, top_y, x2, base_y],
            fill=(13, 20, 17, 235),
            outline=(88, 214, 160, 26),
            width=1,
        )
        # Subtle lit eco-window accents
        for wy in range(top_y + 24, base_y - 40, 32):
            if (bx + wy) % 5 == 0:
                draw.rectangle(
                    [x1 + 14, wy, x1 + 26, wy + 8],
                    fill=(183, 243, 107, 38),
                )

    # Soft smog/haze horizon band (precomputed blur on half-res for speed)
    haze = Image.new("RGBA", (WIDTH // 2, HEIGHT // 2), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(haze)
    h_alpha = int(max(0, min(140, haze_alpha * 110)))
    h_draw.ellipse(
        [-100, 305, WIDTH // 2 + 100, HEIGHT // 2 + 120],
        fill=(88, 214, 160, int(h_alpha * 0.45)),
    )
    haze = haze.filter(ImageFilter.GaussianBlur(radius=30)).resize(
        (WIDTH, HEIGHT), Image.Resampling.BILINEAR
    )
    overlay = Image.alpha_composite(overlay, haze)

    # Floating subtle particulates
    rng = np.random.default_rng(42)
    p_draw = ImageDraw.Draw(overlay)
    for _ in range(55):
        px = (rng.uniform(0, WIDTH) + progress * rng.uniform(35, 95)) % WIDTH
        py = (rng.uniform(140, 920) - progress * rng.uniform(15, 55)) % HEIGHT
        r = rng.uniform(1.5, 4.0)
        al = int(rng.uniform(25, 95) * haze_alpha)
        col = TEAL if rng.random() > 0.35 else ACCENT
        p_draw.ellipse([px - r, py - r, px + r, py + r], fill=(col[0], col[1], col[2], al))

    return Image.alpha_composite(base.convert("RGBA"), overlay)


def _stream_frames_to_mp4(frames_iter, out_path: Path, total_frames: int) -> None:
    cmd = [
        FFMPEG,
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "medium",
        "-crf", "16",
        str(out_path),
    ]
    log_path = out_path.with_suffix(".ffmpeg.log")
    with open(log_path, "wb") as log_f:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=log_f, stderr=log_f)
        assert proc.stdin is not None
        for frame in frames_iter:
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        ret = proc.wait()
    if ret != 0:
        err = log_path.read_text(errors="ignore")
        raise RuntimeError(f"FFmpeg failed on {out_path.name}: {err[-1000:]}")
    log_path.unlink(missing_ok=True)


def render_scene1_opening() -> Path:
    """Scene 1 (0-7s): Urban atmosphere + 'THE AIR WE BREATHE MATTERS.' -> BreatheWise logo."""
    out = ASSETS_DIR / "scene1_opening.mp4"
    duration = 7.0
    total = int(duration * FPS)
    base_bg = _create_atmospheric_backdrop(1.0)
    f_title = _font(FONT_DISPLAY, 66)
    f_sub = _font(FONT_MONO, 22)

    def frames():
        for i in range(total):
            t = i / FPS
            prog = t / duration
            haze_fade = 1.0 - max(0.0, (t - 4.4) / 2.2) * 0.45
            canvas = _draw_urban_skyline(base_bg, prog, haze_fade)
            layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)

            # 0.5s - 4.4s: 'THE AIR WE BREATHE MATTERS.'
            if 0.3 <= t <= 4.7:
                if t < 1.1:
                    alpha = int(255 * _ease_out_cubic((t - 0.3) / 0.8))
                elif t > 4.0:
                    alpha = int(255 * (1.0 - _ease_in_out((t - 4.0) / 0.7)))
                else:
                    alpha = 255
                headline = "THE AIR WE BREATHE MATTERS."
                bbox = draw.textbbox((0, 0), headline, font=f_title)
                tw = bbox[2] - bbox[0]
                y_shift = int((1.0 - _ease_out_cubic(min(1.0, (t - 0.3) / 0.9))) * 22)
                draw.text(
                    ((WIDTH - tw) // 2, 415 + y_shift),
                    headline,
                    font=f_title,
                    fill=(TEXT[0], TEXT[1], TEXT[2], alpha),
                )
                sub = "URBAN AIR QUALITY  ·  REAL-TIME ENVIRONMENTAL INTELLIGENCE"
                sb = draw.textbbox((0, 0), sub, font=f_sub)
                draw.text(
                    ((WIDTH - (sb[2] - sb[0])) // 2, 510 + y_shift),
                    sub,
                    font=f_sub,
                    fill=(TEAL[0], TEAL[1], TEAL[2], int(alpha * 0.85)),
                )

            # 4.3s - 7.0s: Transition to BreatheWise Logo
            if t >= 4.2:
                logo_a = int(255 * _ease_out_cubic(min(1.0, (t - 4.2) / 0.9)))
                scale_in = 0.88 + 0.12 * _ease_out_cubic(min(1.0, (t - 4.2) / 1.1))
                _draw_breathewise_logo(draw, WIDTH // 2, HEIGHT // 2 - 20, int(185 * scale_in), logo_a)

            composed = Image.alpha_composite(canvas, layer).convert("RGB")
            # Subtle 4% cinematic camera push-in
            zoom = 1.0 + 0.045 * prog
            cw, ch = int(WIDTH / zoom), int(HEIGHT / zoom)
            left = (WIDTH - cw) // 2
            top = (HEIGHT - ch) // 2
            cropped = composed.crop((left, top, left + cw, top + ch)).resize(
                (WIDTH, HEIGHT), Image.Resampling.BILINEAR
            )
            yield np.asarray(cropped, dtype=np.uint8)

    _stream_frames_to_mp4(frames(), out, total)
    return out


def render_scene2_intro() -> Path:
    """Scene 2 (4.2s brand reveal before crossfade into real landing page)."""
    out = ASSETS_DIR / "scene2_intro.mp4"
    duration = 4.2
    total = int(duration * FPS)
    base_bg = _create_atmospheric_backdrop(1.15)
    f_brand = _font(FONT_DISPLAY, 92)
    f_tag = _font(FONT_LIGHT, 38)
    f_pill = _font(FONT_MONO, 20)

    def frames():
        for i in range(total):
            t = i / FPS
            prog = t / duration
            layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)

            a1 = int(255 * _ease_out_cubic(min(1.0, t / 0.7)))
            a2 = int(255 * _ease_out_cubic(max(0.0, min(1.0, (t - 0.45) / 0.75))))

            _draw_breathewise_logo(draw, WIDTH // 2, 330, 128, a1)

            brand = "BREATHEWISE"
            bb = draw.textbbox((0, 0), brand, font=f_brand)
            draw.text(
                ((WIDTH - (bb[2] - bb[0])) // 2, 430),
                brand,
                font=f_brand,
                fill=(TEXT[0], TEXT[1], TEXT[2], a1),
            )

            tag = "Breathe Smarter. Live Better."
            tb = draw.textbbox((0, 0), tag, font=f_tag)
            draw.text(
                ((WIDTH - (tb[2] - tb[0])) // 2, 552),
                tag,
                font=f_tag,
                fill=(ACCENT[0], ACCENT[1], ACCENT[2], a2),
            )

            pill = "LIVE OPEN-METEO TELEMETRY  ·  GEMINI AI  ·  FAMILY CARE"
            pb = draw.textbbox((0, 0), pill, font=f_pill)
            draw.text(
                ((WIDTH - (pb[2] - pb[0])) // 2, 640),
                pill,
                font=f_pill,
                fill=(MUTED[0], MUTED[1], MUTED[2], a2),
            )

            composed = Image.alpha_composite(base_bg.convert("RGBA"), layer).convert("RGB")
            zoom = 1.0 + 0.03 * prog
            cw, ch = int(WIDTH / zoom), int(HEIGHT / zoom)
            left, top = (WIDTH - cw) // 2, (HEIGHT - ch) // 2
            cropped = composed.crop((left, top, left + cw, top + ch)).resize(
                (WIDTH, HEIGHT), Image.Resampling.BILINEAR
            )
            yield np.asarray(cropped, dtype=np.uint8)

    _stream_frames_to_mp4(frames(), out, total)
    return out


def render_scene7_end_slate() -> Path:
    """Scene 7 finale card: BREATHEWISE / Breathe Smarter. Live Better. / Because every breath matters."""
    out = ASSETS_DIR / "scene7_end.mp4"
    duration = 6.2
    total = int(duration * FPS)
    base_bg = _create_atmospheric_backdrop(1.2)
    f_brand = _font(FONT_DISPLAY, 90)
    f_tag = _font(FONT_REGULAR, 36)
    f_closing = _font(FONT_LIGHT, 30)

    def frames():
        for i in range(total):
            t = i / FPS
            fade_out = 1.0 if t < 5.2 else max(0.0, 1.0 - (t - 5.2) / 1.0)
            a_logo = int(255 * _ease_out_cubic(min(1.0, t / 0.7)) * fade_out)
            a_tag = int(255 * _ease_out_cubic(max(0.0, min(1.0, (t - 0.5) / 0.8))) * fade_out)
            a_end = int(255 * _ease_out_cubic(max(0.0, min(1.0, (t - 1.3) / 0.9))) * fade_out)

            layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
            draw = ImageDraw.Draw(layer)
            _draw_breathewise_logo(draw, WIDTH // 2, 315, 134, a_logo)

            brand = "BREATHEWISE"
            bb = draw.textbbox((0, 0), brand, font=f_brand)
            draw.text(
                ((WIDTH - (bb[2] - bb[0])) // 2, 415),
                brand,
                font=f_brand,
                fill=(TEXT[0], TEXT[1], TEXT[2], a_logo),
            )

            tag = "Breathe Smarter. Live Better."
            tb = draw.textbbox((0, 0), tag, font=f_tag)
            draw.text(
                ((WIDTH - (tb[2] - tb[0])) // 2, 535),
                tag,
                font=f_tag,
                fill=(ACCENT[0], ACCENT[1], ACCENT[2], a_tag),
            )

            closing = "Because every breath matters."
            cb = draw.textbbox((0, 0), closing, font=f_closing)
            draw.text(
                ((WIDTH - (cb[2] - cb[0])) // 2, 622),
                closing,
                font=f_closing,
                fill=(TEAL[0], TEAL[1], TEAL[2], a_end),
            )

            composed = Image.alpha_composite(base_bg.convert("RGBA"), layer).convert("RGB")
            yield np.asarray(composed, dtype=np.uint8)

    _stream_frames_to_mp4(frames(), out, total)
    return out


def render_lower_third_badges() -> None:
    """Create sleek corner badge overlays for Scenes 3-6."""
    badges = [
        ("badge_scene3.png", "01 / DASHBOARD", "Real-Time AQI, Weather & Hourly Forecast"),
        ("badge_scene4.png", "02 / AI AIR ADVISOR", "Grounded Guidance Powered by Google Gemini"),
        ("badge_scene5.png", "03 / SMART DAILY ROUTINE", "Forecast-Driven Activity Timing"),
        ("badge_scene6.png", "04 / INDOOR & SUSTAINABILITY", "Room Protection, Swaps & Impact Tracking"),
    ]
    f_kicker = _font(FONT_MONO, 18)
    f_label = _font(FONT_DISPLAY, 24)
    for fname, kicker, label in badges:
        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        w1 = draw.textbbox((0, 0), kicker, font=f_kicker)[2]
        w2 = draw.textbbox((0, 0), label, font=f_label)[2]
        box_w = max(w1, w2) + 56
        x0, y0 = 48, HEIGHT - 122
        draw.rounded_rectangle(
            [x0, y0, x0 + box_w, y0 + 84],
            radius=14,
            fill=(11, 16, 14, 222),
            outline=(183, 243, 107, 110),
            width=2,
        )
        draw.rectangle([x0 + 14, y0 + 18, x0 + 18, y0 + 66], fill=(183, 243, 107, 255))
        draw.text((x0 + 32, y0 + 14), kicker, font=f_kicker, fill=(88, 214, 160, 255))
        draw.text((x0 + 32, y0 + 40), label, font=f_label, fill=(244, 247, 243, 255))
        img.save(ASSETS_DIR / fname)


def synthesize_soundtrack(total_duration: float = 70.0) -> Path:
    """Synthesize an atmospheric eco-tech ambient soundtrack + subtle UI chimes."""
    sr = 48000
    n = int(total_duration * sr)
    t = np.linspace(0.0, total_duration, n, endpoint=False)

    # Warm Dmaj9 -> Bm9 -> Gmaj7 -> Aadd9 progression (each chord 4.0s = 16s loop)
    chords = [
        [146.83, 220.00, 277.18, 329.63, 369.99],  # Dmaj9
        [123.47, 185.00, 220.00, 293.66, 369.99],  # Bm9
        [98.00, 146.83, 196.00, 246.94, 369.99],   # Gmaj7
        [110.00, 164.81, 220.00, 277.18, 329.63],  # Aadd9
    ]

    pad_l = np.zeros(n, dtype=np.float64)
    pad_r = np.zeros(n, dtype=np.float64)

    chord_len = 4.0
    num_chords = int(math.ceil(total_duration / chord_len))
    for c_idx in range(num_chords):
        start_s = c_idx * chord_len
        end_s = min(total_duration, (c_idx + 1) * chord_len)
        i0, i1 = int(start_s * sr), int(end_s * sr)
        if i1 <= i0:
            continue
        seg_t = t[i0:i1] - start_s
        dur = (i1 - i0) / sr
        # Smooth crossfade envelope per chord
        env = np.sin(np.pi * np.clip(seg_t / max(dur, 0.01), 0.0, 1.0)) ** 0.55
        freqs = chords[c_idx % len(chords)]
        for k, f in enumerate(freqs):
            detune = 1.0 + (k - 2) * 0.0016
            wave_l = np.sin(2.0 * np.pi * f * seg_t) + 0.25 * np.sin(2.0 * np.pi * f * 2.0 * seg_t)
            wave_r = np.sin(2.0 * np.pi * f * detune * seg_t + 0.4) + 0.25 * np.sin(
                2.0 * np.pi * f * 2.0 * detune * seg_t + 0.7
            )
            gain = 0.085 if k == 0 else 0.052
            pad_l[i0:i1] += wave_l * env * gain
            pad_r[i0:i1] += wave_r * env * gain

    # Subtle pulsing harmonic arpeggio (clean minimalist tech feel)
    arp_notes = [587.33, 659.25, 739.99, 880.00, 739.99, 659.25, 554.37, 659.25]
    step = 0.5  # 120 eighth-notes/min
    for step_idx in range(int(total_duration / step)):
        st = step_idx * step
        i0 = int(st * sr)
        i1 = min(n, int((st + 0.48) * sr))
        if i1 <= i0:
            continue
        seg = t[i0:i1] - st
        freq = arp_notes[step_idx % len(arp_notes)]
        # Fade in after 6s, fade out before 67s
        global_gate = min(1.0, max(0.0, (st - 5.5) / 3.0)) * min(1.0, max(0.0, (66.5 - st) / 3.0))
        env = np.exp(-seg * 7.5) * (1.0 - np.exp(-seg * 120.0)) * 0.055 * global_gate
        tone = np.sin(2.0 * np.pi * freq * seg)
        pan = 0.5 + 0.25 * math.sin(step_idx * 0.7)
        pad_l[i0:i1] += tone * env * (1.0 - pan * 0.5)
        pad_r[i0:i1] += tone * env * (0.5 + pan * 0.5)

    # Scene transition soft airy chimes
    cue_times = [6.8, 12.8, 24.8, 39.8, 48.8, 58.8]
    for idx, ct in enumerate(cue_times):
        i0 = int(ct * sr)
        i1 = min(n, int((ct + 1.4) * sr))
        if i1 <= i0:
            continue
        seg = t[i0:i1] - ct
        f0 = 587.33 if idx % 2 == 0 else 739.99
        chime = (
            0.7 * np.sin(2.0 * np.pi * f0 * seg)
            + 0.3 * np.sin(2.0 * np.pi * f0 * 1.5 * seg)
        ) * np.exp(-seg * 4.2) * (1.0 - np.exp(-seg * 90.0)) * 0.11
        pad_l[i0:i1] += chime
        pad_r[i0:i1] += chime

    # Master fade in/out & soft limiter
    master_env = np.minimum(1.0, t / 1.5) * np.minimum(1.0, np.maximum(0.0, (total_duration - t) / 2.2))
    stereo = np.stack([pad_l * master_env, pad_r * master_env], axis=1)
    stereo = np.tanh(stereo * 1.25) * 0.85
    pcm = (stereo * 32767.0).astype(np.int16)

    out_wav = ASSETS_DIR / "soundtrack.wav"
    wavfile.write(str(out_wav), sr, pcm)
    return out_wav


if __name__ == "__main__":
    print("Rendering Scene 1 opening...")
    render_scene1_opening()
    print("Rendering Scene 2 brand reveal...")
    render_scene2_intro()
    print("Rendering Scene 7 end slate...")
    render_scene7_end_slate()
    print("Rendering lower-third badges...")
    render_lower_third_badges()
    print("Synthesizing soundtrack...")
    synthesize_soundtrack(70.0)
    print("All assets generated in", ASSETS_DIR)
