"""Create a GitHub Pages-ready, web-optimised distribution without touching source media."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE_HTML = ROOT / "preview.html"
SOURCE_CSS = ROOT / "src" / "styles.css"
SOURCE_ASSETS = ROOT / "public" / "assets"
OUTPUT = ROOT / "docs"
FFMPEG = Path(r"C:\Users\PC\AppData\Local\JianyingPro\Apps\11.1.0.14287\ffmpeg.exe")
ASSET_PATTERN = re.compile(r"/assets/[^\"'\s<]+")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
HIGH_QUALITY_VIDEOS = {"game-ad-1.mp4"}
# These two full-screen information boards must remain in their original high-detail files.
HIGH_QUALITY_IMAGES = {"about-confirmed.png", "contact-final.png"}
# Preserve visible detail while still creating web-friendly video files. The opening film
# receives a higher bitrate because it fills the entire first screen.
DEFAULT_VIDEO_BITRATE = "2200k"
VIDEO_BITRATES = {"game-ad-1.mp4": "4200k"}
# A new URL makes browsers and the GitHub Pages CDN discard earlier web-optimised cache entries.
HIGH_QUALITY_CACHE_VERSION = "20260729-clear-boards"


def web_image(source: Path, target: Path) -> None:
    """Create a responsive JPEG copy, large enough for the site modal viewer."""
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode in {"RGBA", "LA"}:
            backdrop = Image.new("RGB", image.size, "#101211")
            backdrop.paste(image, mask=image.getchannel("A"))
            image = backdrop
        else:
            image = image.convert("RGB")
        image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, "JPEG", quality=86, optimize=True, progressive=True)


def web_video(source: Path, target: Path, bitrate: str) -> None:
    """Make an H.264/fast-start playback copy for browsers and GitHub Pages."""
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(FFMPEG),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-vf",
        "scale='min(1280,iw)':-2",
        "-c:v",
        "h264_mf",
        "-rate_control",
        "cbr",
        "-b:v",
        bitrate,
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(target),
    ]
    subprocess.run(command, check=True)


def main() -> int:
    if not SOURCE_HTML.exists() or not SOURCE_CSS.exists() or not SOURCE_ASSETS.exists():
        raise FileNotFoundError("Expected portfolio source files were not found.")
    if not FFMPEG.exists():
        raise FileNotFoundError(f"FFmpeg was not found: {FFMPEG}")
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise FileExistsError("docs already contains a build. Keep it for review or rename it before rebuilding.")

    html = SOURCE_HTML.read_text(encoding="utf-8")
    # GitHub project Pages live below /<repository>/, so published assets must be relative.
    html = html.replace('href="/src/styles.css"', 'href="./src/styles.css"')
    # Ignore JavaScript template strings used to derive poster paths at runtime.
    references = sorted(reference for reference in set(ASSET_PATTERN.findall(html)) if "${" not in reference)
    if not references:
        raise RuntimeError("No /assets references were found in preview.html.")

    output_assets = OUTPUT / "assets"
    (OUTPUT / "src").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_CSS, OUTPUT / "src" / "styles.css")
    print(f"Preparing {len(references)} referenced assets for GitHub Pages…", flush=True)

    for index, reference in enumerate(references, start=1):
        relative = Path(reference.removeprefix("/assets/"))
        source = SOURCE_ASSETS / relative
        if not source.exists():
            raise FileNotFoundError(f"Referenced asset is missing: {reference}")

        if source.suffix.lower() == ".mp4":
            target = output_assets / relative
            print(f"[{index}/{len(references)}] video  {relative}", flush=True)
            web_video(source, target, VIDEO_BITRATES.get(relative.name, DEFAULT_VIDEO_BITRATE))
            continue

        if source.suffix.lower() in IMAGE_EXTENSIONS:
            if relative.name in HIGH_QUALITY_IMAGES:
                target = output_assets / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
                html = html.replace(reference, "./assets/" + relative.as_posix())
                print(f"[{index}/{len(references)}] image  {relative} (original quality)", flush=True)
                continue
            target_relative = relative.with_suffix(".jpg")
            target = output_assets / target_relative
            print(f"[{index}/{len(references)}] image  {relative}", flush=True)
            web_image(source, target)
            html = html.replace(reference, "./assets/" + target_relative.as_posix())
            continue

        target = output_assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    html = html.replace('"/assets/', '"./assets/')
    for asset_name in sorted(HIGH_QUALITY_VIDEOS | HIGH_QUALITY_IMAGES):
        html = html.replace(
            f'./assets/{asset_name}"',
            f'./assets/{asset_name}?v={HIGH_QUALITY_CACHE_VERSION}"',
        )
    # GitHub Pages serves docs as the site root. The current preview is the real portfolio entry.
    (OUTPUT / "index.html").write_text(html, encoding="utf-8")
    (OUTPUT / ".nojekyll").touch()
    print("GitHub Pages distribution created in docs/", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"Build failed: {error}", file=sys.stderr)
        raise
