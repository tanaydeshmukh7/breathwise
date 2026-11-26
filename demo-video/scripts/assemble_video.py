"""Assemble the final 1920x1080 30fps H.264 MP4 BreatheWise demo video using FFmpeg.

Combines:
- Scene 1 (0-7s): Opening urban atmosphere + logo transition (assets/scene1_opening.mp4)
- Scene 2 (7-13s): Brand reveal (assets/scene2_intro.mp4) -> live landing page (raw-recordings/scene2_landing.webm)
- Scene 3 (13-25s): Real Dashboard (raw-recordings/scene3_dashboard.webm) + subtle zoom/pan + badge
- Scene 4 (25-40s): Real AI Air Advisor with live Gemini response (raw-recordings/scene4_advisor.webm) + badge
- Scene 5 (40-49s): Real Smart Daily Routine (raw-recordings/scene5_routine.webm) + badge
- Scene 6 (49-59s): Real Indoor Guide, Sustainable Alternatives, and Impact Tracker + badge
- Scene 7 (59-70s): Rhythmic montage of real screens -> final BreatheWise end slate
- Audio: Original synthesized ambient eco-tech soundtrack + transition chimes (assets/soundtrack.wav)
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw-recordings"
ASSETS_DIR = ROOT / "assets"
WORK_DIR = ASSETS_DIR / "_segments"
WORK_DIR.mkdir(parents=True, exist_ok=True)
FINAL_MP4 = ROOT / "breathewise-demo.mp4"

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
WIDTH, HEIGHT = 1920, 1080


def run_ffmpeg(args: list[str], label: str) -> None:
    print(f"[ffmpeg] starting: {label}", flush=True)
    cmd = [FFMPEG, "-y", *args]
    proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed ({label}):\n{proc.stderr[-1500:]}")
    print(f"[ffmpeg] finished: {label}", flush=True)


def get_duration(media_path: Path) -> float:
    proc = subprocess.run(
        [FFMPEG, "-i", str(media_path)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        return 0.0
    h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
    return h * 3600 + m * 60 + s


def prepare_clip(
    src: Path,
    out: Path,
    target_dur: float,
    start_offset: float = 0.0,
    badge_png: Path | None = None,
    subtle_zoom: float = 1.03,
) -> Path:
    """Trim/speed-fit a real Playwright recording to target_dur at 1920x1080 30fps with optional badge & subtle zoom."""
    src_dur = get_duration(src)
    avail = max(0.5, src_dur - start_offset)
    # Adjust speed slightly if source clip is longer/shorter so we capture the entire interaction cleanly
    pts_factor = target_dur / avail
    pts_factor = max(0.55, min(1.35, pts_factor))

    # Build clean video filter: scale to 1920x1080, mild zoom/crop, optional lower-third badge overlay
    zoom_w = int(WIDTH * subtle_zoom)
    zoom_h = int(HEIGHT * subtle_zoom)
    vf_parts = [
        f"setpts={pts_factor:.5f}*PTS",
        f"fps={FPS}",
        f"scale={zoom_w}:{zoom_h}:flags=lanczos",
        # Subtle slow pan/zoom-in via animated crop across clip duration
        f"crop={WIDTH}:{HEIGHT}:'({zoom_w}-{WIDTH})/2*t/{target_dur:.2f}':'({zoom_h}-{HEIGHT})/2*(1-t/{target_dur:.2f})'",
        "format=yuv420p",
    ]

    if badge_png is not None and badge_png.exists():
        filter_complex = (
            f"[0:v]{','.join(vf_parts)}[base];"
            f"[1:v]format=rgba,fade=t=in:st=0.25:d=0.45:alpha=1,"
            f"fade=t=out:st={max(0.5, target_dur - 0.55):.2f}:d=0.45:alpha=1[ov];"
            f"[base][ov]overlay=0:0:shortest=1[vout]"
        )
        run_ffmpeg(
            [
                "-ss", f"{start_offset:.2f}",
                "-i", str(src),
                "-loop", "1",
                "-t", f"{target_dur:.2f}",
                "-i", str(badge_png),
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-t", f"{target_dur:.2f}",
                "-an",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "16",
                "-pix_fmt", "yuv420p",
                str(out),
            ],
            out.name,
        )
    else:
        run_ffmpeg(
            [
                "-ss", f"{start_offset:.2f}",
                "-i", str(src),
                "-vf", ",".join(vf_parts),
                "-t", f"{target_dur:.2f}",
                "-an",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "16",
                "-pix_fmt", "yuv420p",
                str(out),
            ],
            out.name,
        )
    return out


def build_montage_clip(clips_with_offsets: list[tuple[Path, float]], out: Path, slice_dur: float = 1.2) -> Path:
    """Create a rapid, clean 4-cut montage from real recorded scenes."""
    parts = []
    for idx, (src, offset) in enumerate(clips_with_offsets):
        part = WORK_DIR / f"montage_part_{idx}.mp4"
        run_ffmpeg(
            [
                "-ss", f"{offset:.2f}",
                "-i", str(src),
                "-vf", f"fps={FPS},scale={WIDTH}:{HEIGHT}:flags=lanczos,format=yuv420p",
                "-t", f"{slice_dur:.2f}",
                "-an",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "16",
                str(part),
            ],
            part.name,
        )
        parts.append(part)

    concat_list = WORK_DIR / "montage_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in parts),
        encoding="utf-8",
    )
    run_ffmpeg(
        [
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "16",
            str(out),
        ],
        out.name,
    )
    return out


def assemble_final_video() -> None:
    """Concatenate all scenes with smooth xfade transitions and mix the soundtrack."""
    # Exact scene timing budget (with 0.45s xfade overlaps):
    # s1 (7.3s) -> xfade 0.45 -> s2_intro (3.9s) -> xfade 0.45 -> s2_land (3.0s)
    # -> xfade 0.45 -> s3_dash (12.45s) -> xfade 0.45 -> s4_adv (15.45s)
    # -> xfade 0.45 -> s5_rout (9.45s) -> xfade 0.45 -> s6_indoor (3.8s)
    # -> xfade 0.35 -> s6_sust (3.35s) -> xfade 0.35 -> s6_impact (3.9s)
    # -> xfade 0.45 -> s7_montage (4.9s) -> xfade 0.45 -> s7_end (6.2s)
    # Total runtime ~ 69.5 seconds (strictly inside 60-75s spec!)

    s1 = ASSETS_DIR / "scene1_opening.mp4"
    s2_intro = ASSETS_DIR / "scene2_intro.mp4"
    s7_end = ASSETS_DIR / "scene7_end.mp4"

    s2_land = prepare_clip(
        RAW_DIR / "scene2_landing.webm",
        WORK_DIR / "s2_landing.mp4",
        target_dur=3.4,
        start_offset=4.0,
        subtle_zoom=1.03,
    )
    s3_dash = prepare_clip(
        RAW_DIR / "scene3_dashboard.webm",
        WORK_DIR / "s3_dashboard.mp4",
        target_dur=12.4,
        start_offset=7.5,
        badge_png=ASSETS_DIR / "badge_scene3.png",
        subtle_zoom=1.04,
    )
    s4_adv = prepare_clip(
        RAW_DIR / "scene4_advisor.webm",
        WORK_DIR / "s4_advisor.mp4",
        target_dur=15.4,
        start_offset=5.0,
        badge_png=ASSETS_DIR / "badge_scene4.png",
        subtle_zoom=1.03,
    )
    s5_rout = prepare_clip(
        RAW_DIR / "scene5_routine.webm",
        WORK_DIR / "s5_routine.mp4",
        target_dur=9.4,
        start_offset=8.0,
        badge_png=ASSETS_DIR / "badge_scene5.png",
        subtle_zoom=1.03,
    )
    s6_in = prepare_clip(
        RAW_DIR / "scene6_indoor.webm",
        WORK_DIR / "s6_indoor.mp4",
        target_dur=3.8,
        start_offset=7.5,
        badge_png=ASSETS_DIR / "badge_scene6.png",
        subtle_zoom=1.03,
    )
    s6_su = prepare_clip(
        RAW_DIR / "scene6_sustainable.webm",
        WORK_DIR / "s6_sustainable.mp4",
        target_dur=3.4,
        start_offset=10.5,
        badge_png=ASSETS_DIR / "badge_scene6.png",
        subtle_zoom=1.03,
    )
    s6_im = prepare_clip(
        RAW_DIR / "scene6_impact.webm",
        WORK_DIR / "s6_impact.mp4",
        target_dur=3.9,
        start_offset=9.2,
        badge_png=ASSETS_DIR / "badge_scene6.png",
        subtle_zoom=1.03,
    )

    s7_montage = build_montage_clip(
        [
            (RAW_DIR / "scene3_dashboard.webm", 10.0),
            (RAW_DIR / "scene4_advisor.webm", 27.0),
            (RAW_DIR / "scene5_routine.webm", 13.0),
            (RAW_DIR / "scene6_impact.webm", 13.0),
        ],
        WORK_DIR / "s7_montage.mp4",
        slice_dur=1.25,
    )

    segments = [
        (s1, 0.45),
        (s2_intro, 0.45),
        (s2_land, 0.45),
        (s3_dash, 0.45),
        (s4_adv, 0.45),
        (s5_rout, 0.45),
        (s6_in, 0.35),
        (s6_su, 0.35),
        (s6_im, 0.45),
        (s7_montage, 0.45),
        (s7_end, 0.0),
    ]

    # Measure actual segment durations for exact xfade offsets
    durs = [get_duration(seg[0]) for seg in segments]
    inputs: list[str] = []
    for seg_path, _ in segments:
        inputs.extend(["-i", str(seg_path)])

    filter_chains: list[str] = []
    prev_label = "0:v"
    running_dur = durs[0]
    for idx in range(1, len(segments)):
        fade_d = segments[idx - 1][1]
        offset = max(0.0, running_dur - fade_d)
        out_label = f"v{idx}" if idx < len(segments) - 1 else "vfinal"
        trans = "fade" if idx in (1, 10) else "smoothleft"
        if idx in (2, 7, 8):
            trans = "dissolve"
        filter_chains.append(
            f"[{prev_label}][{idx}:v]xfade=transition={trans}:duration={fade_d:.2f}:offset={offset:.2f}[{out_label}]"
        )
        prev_label = out_label
        running_dur = offset + durs[idx]

    video_only = WORK_DIR / "assembled_video.mp4"
    run_ffmpeg(
        [
            *inputs,
            "-filter_complex", ";".join(filter_chains),
            "-map", "[vfinal]",
            "-r", str(FPS),
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "16",
            "-pix_fmt", "yuv420p",
            str(video_only),
        ],
        "xfade_assembly",
    )

    final_dur = get_duration(video_only)
    soundtrack = ASSETS_DIR / "soundtrack.wav"
    fade_out_start = max(1.0, final_dur - 2.2)

    run_ffmpeg(
        [
            "-i", str(video_only),
            "-i", str(soundtrack),
            "-filter_complex",
            f"[1:a]atrim=0:{final_dur:.2f},afade=t=in:st=0:d=1.2,afade=t=out:st={fade_out_start:.2f}:d=2.2[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            str(FINAL_MP4),
        ],
        "audio_mux",
    )
    print(f"Rendered final video: {FINAL_MP4} (duration={get_duration(FINAL_MP4):.2f}s)")


if __name__ == "__main__":
    assemble_final_video()
