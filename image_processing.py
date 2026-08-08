"""Shared image post-processing helpers."""

from __future__ import annotations

from PIL import Image


def remove_halo(
    image: Image.Image,
    soft_threshold: int = 40,
) -> Image.Image:
    """Reduce low-opacity background-colored fringe around the foreground.

    Pixels below the threshold become transparent. Remaining alpha values are
    remapped smoothly so anti-aliased edges remain natural instead of jagged.
    """
    rgba = image.convert("RGBA")
    red, green, blue, alpha = rgba.split()
    if soft_threshold <= 0:
        return rgba
    threshold = min(254, soft_threshold)
    alpha = alpha.point(
        lambda value: 0
        if value < threshold
        else int(255 * (value - threshold) / (255 - threshold))
    )
    return Image.merge("RGBA", (red, green, blue, alpha))


def crop_transparent(
    image: Image.Image,
    padding: int = 20,
    alpha_threshold: int = 8,
) -> Image.Image:
    """Crop an RGBA image to its visible alpha bounds with a small margin.

    A low alpha threshold prevents nearly invisible anti-aliased pixels from
    keeping the original canvas unnecessarily large.
    """
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    visible_alpha = alpha.point(
        lambda value: 255 if value > alpha_threshold else 0
    )
    bbox = visible_alpha.getbbox()

    # Keep a valid transparent image if the model returned no foreground.
    if bbox is None:
        return rgba

    left, top, right, bottom = bbox
    width, height = rgba.size
    bounds = (
        max(0, left - padding),
        max(0, top - padding),
        min(width, right + padding),
        min(height, bottom + padding),
    )
    return rgba.crop(bounds)
