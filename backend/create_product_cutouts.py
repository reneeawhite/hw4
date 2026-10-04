"""Create transparent PNG product cutouts from the catalogue JPGs.

The source images use a uniform black or white border. This script removes
only the border-connected background, preserving enclosed white lettering and
other product details.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from statistics import median

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_ROOT / "data" / "products"
OUTPUT_DIR = PROJECT_ROOT / "data" / "product_cutouts"


def background_color(pixels: list[tuple[int, int, int]], width: int, height: int) -> tuple[int, int, int]:
    border: list[tuple[int, int, int]] = []
    for x in range(width):
        border.extend((pixels[x], pixels[(height - 1) * width + x]))
    for y in range(1, height - 1):
        border.extend((pixels[y * width], pixels[y * width + width - 1]))
    return tuple(int(median([pixel[channel] for pixel in border])) for channel in range(3))


def make_cutout(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        width, height = rgb.size
        pixels = list(rgb.getdata())

    background = background_color(pixels, width, height)
    brightness = sum(background) / 3
    tolerance = 18 if brightness < 40 else 28 if brightness > 215 else 36

    def is_background(pixel: tuple[int, int, int]) -> bool:
        return max(abs(pixel[channel] - background[channel]) for channel in range(3)) <= tolerance

    transparent = bytearray(width * height)
    queue: deque[int] = deque()

    for x in range(width):
        queue.extend((x, (height - 1) * width + x))
    for y in range(1, height - 1):
        queue.extend((y * width, y * width + width - 1))

    while queue:
        index = queue.popleft()
        if transparent[index] or not is_background(pixels[index]):
            continue
        transparent[index] = 1
        x, y = index % width, index // width
        if x:
            queue.append(index - 1)
        if x + 1 < width:
            queue.append(index + 1)
        if y:
            queue.append(index - width)
        if y + 1 < height:
            queue.append(index + width)

    rgba = [(*pixel, 0 if transparent[index] else 255) for index, pixel in enumerate(pixels)]
    output = Image.new("RGBA", (width, height))
    output.putdata(rgba)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.save(destination, "PNG", optimize=True)


def main() -> None:
    sources = sorted(SOURCE_DIR.glob("*.jpg"))
    for source in sources:
        make_cutout(source, OUTPUT_DIR / f"{source.stem}.png")
    print(f"Created {len(sources)} transparent product cutouts in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
