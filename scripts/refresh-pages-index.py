"""Regenerate only docs/index.html from the source preview without re-encoding assets."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
SOURCE_HTML = ROOT / "preview.html"
OUTPUT_HTML = ROOT / "docs" / "index.html"
ASSETS = ROOT / "public" / "assets"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
HIGH_QUALITY_VIDEOS = {"game-ad-1.mp4"}
HIGH_QUALITY_IMAGES = {"about-confirmed.png", "contact-final.png"}
CACHE_VERSION = "20260729-clear-boards"
ASSET_PATTERN = re.compile(r"/assets/[^\"'\s<]+")


def main() -> None:
    html = SOURCE_HTML.read_text(encoding="utf-8")
    html = html.replace('href="/src/styles.css"', 'href="./src/styles.css"')

    # Ignore JavaScript template strings used to derive poster paths at runtime.
    for reference in sorted(reference for reference in set(ASSET_PATTERN.findall(html)) if "${" not in reference):
        relative = Path(reference.removeprefix("/assets/"))
        source = ASSETS / relative
        if not source.exists():
            raise FileNotFoundError(f"Missing source asset: {reference}")
        target_relative = relative
        if source.suffix.lower() in IMAGE_EXTENSIONS and relative.name not in HIGH_QUALITY_IMAGES:
            target_relative = relative.with_suffix(".jpg")
        html = html.replace(reference, "./assets/" + target_relative.as_posix())

    for asset_name in sorted(HIGH_QUALITY_VIDEOS | HIGH_QUALITY_IMAGES):
        html = html.replace(
            f'./assets/{asset_name}"',
            f'./assets/{asset_name}?v={CACHE_VERSION}"',
        )

    OUTPUT_HTML.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
