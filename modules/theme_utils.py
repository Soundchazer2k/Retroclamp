"""Theme utilities module for RetroClamp.

This module provides utilities for working with themes, including color
conversion, contrast calculation, and accessibility validation.
"""

import re
from typing import Any, Dict, List, Tuple

from PySide6.QtGui import QColor


def get_color_from_hex(hex_color: str) -> Tuple[int, int, int]:
    """Convert a hex color string to RGB values.

    This is an alias for hex_to_rgb for compatibility with other modules.

    Args:
        hex_color: Hex color string (e.g., '#ff0000' or '#f00')

    Returns:
        Tuple of (R, G, B) values (0-255)
    """
    return hex_to_rgb(hex_color)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert a hex color string to RGB values.

    Args:
        hex_color: Hex color string (e.g., '#ff0000' or '#f00')

    Returns:
        Tuple of (R, G, B) values (0-255)

    Raises:
        ValueError: If the hex color string is invalid
    """
    # Remove the leading '#' if present
    hex_color = hex_color.lstrip("#")

    # Handle shorthand hex notation (e.g., #f00 -> #ff0000)
    if len(hex_color) == 3:
        hex_color = "".join([c * 2 for c in hex_color])

    # Validate hex color format
    if not re.match(r"^[0-9a-fA-F]{6}$", hex_color):
        raise ValueError(f"Invalid hex color: {hex_color}")

    # Convert to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return (r, g, b)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to a hex color string.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hex color string (e.g., '#ff0000')

    Raises:
        ValueError: If any RGB value is out of range
    """
    # Validate RGB values
    if not all(0 <= c <= 255 for c in (r, g, b)):
        raise ValueError(f"Invalid RGB values: ({r}, {g}, {b})")

    # Convert to hex
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_luminance(r: int, g: int, b: int) -> float:
    """Calculate the relative luminance of an RGB color.

    Uses the formula from WCAG 2.0: https://www.w3.org/TR/WCAG20/#relativeluminancedef

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Relative luminance value (0-1)
    """
    # Convert RGB values to sRGB
    r_srgb = r / 255
    g_srgb = g / 255
    b_srgb = b / 255

    # Convert sRGB to linear RGB
    r_linear = (
        r_srgb / 12.92 if r_srgb <= 0.03928 else ((r_srgb + 0.055) / 1.055) ** 2.4
    )
    g_linear = (
        g_srgb / 12.92 if g_srgb <= 0.03928 else ((g_srgb + 0.055) / 1.055) ** 2.4
    )
    b_linear = (
        b_srgb / 12.92 if b_srgb <= 0.03928 else ((b_srgb + 0.055) / 1.055) ** 2.4
    )

    # Calculate luminance
    return 0.2126 * r_linear + 0.7152 * g_linear + 0.0722 * b_linear


def hex_to_luminance(hex_color: str) -> float:
    """Calculate the relative luminance of a hex color.

    Args:
        hex_color: Hex color string (e.g., '#ff0000')

    Returns:
        Relative luminance value (0-1)
    """
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_luminance(r, g, b)


def calculate_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate the contrast ratio between two colors.

    Uses the formula from WCAG 2.0: https://www.w3.org/TR/WCAG20/#contrast-ratiodef

    Args:
        color1: First color in hex format (e.g., '#ff0000')
        color2: Second color in hex format (e.g., '#ffffff')

    Returns:
        Contrast ratio (1-21)
    """
    # Calculate luminance for each color
    l1 = hex_to_luminance(color1)
    l2 = hex_to_luminance(color2)

    # Calculate contrast ratio (ensure lighter color is first)
    if l1 > l2:
        return (l1 + 0.05) / (l2 + 0.05)
    else:
        return (l2 + 0.05) / (l1 + 0.05)


def meets_wcag_aa(contrast_ratio: float, is_large_text: bool = False) -> bool:
    """Check if a contrast ratio meets WCAG 2.0 AA standards.

    Args:
        contrast_ratio: Contrast ratio to check
        is_large_text: Whether the text is large (>=18pt or >=14pt bold)

    Returns:
        True if the contrast ratio meets WCAG 2.0 AA standards, False otherwise
    """
    if is_large_text:
        return contrast_ratio >= 3.0  # AA for large text
    else:
        return contrast_ratio >= 4.5  # AA for normal text


def meets_wcag_aaa(contrast_ratio: float, is_large_text: bool = False) -> bool:
    """Check if a contrast ratio meets WCAG 2.0 AAA standards.

    Args:
        contrast_ratio: Contrast ratio to check
        is_large_text: Whether the text is large (>=18pt or >=14pt bold)

    Returns:
        True if the contrast ratio meets WCAG 2.0 AAA standards, False otherwise
    """
    if is_large_text:
        return contrast_ratio >= 4.5
    else:
        return contrast_ratio >= 7.0


def is_accessible(
    contrast_ratio: float, level: str = "AA", is_large_text: bool = False
) -> bool:
    """Check if a contrast ratio meets WCAG 2.0 accessibility standards.

    Args:
        contrast_ratio: Contrast ratio to check
        level: Accessibility level to check ('AA' or 'AAA')
        is_large_text: Whether the text is large (>=18pt or >=14pt bold)

    Returns:
        True if the contrast ratio meets the specified accessibility
        standards, False otherwise
    """
    if level.upper() == "AAA":
        return meets_wcag_aaa(contrast_ratio, is_large_text)
    else:  # Default to AA
        return meets_wcag_aa(contrast_ratio, is_large_text)  # AAA for normal text


def validate_theme_contrast(theme_config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Validate the contrast ratios in a theme configuration.

    Args:
        theme_config: Theme configuration dictionary

    Returns:
        List of validation results, each containing:
        - pair: Description of the color pair
        - foreground: Foreground color
        - background: Background color
        - ratio: Contrast ratio
        - meets_aa: Whether the ratio meets WCAG AA standards
        - meets_aaa: Whether the ratio meets WCAG AAA standards
    """
    results = []
    colors = theme_config.get("colors", {})

    # Define color pairs to validate
    color_pairs = [
        (
            "Text on Background",
            colors.get("foreground", "#f8f8f2"),
            colors.get("background", "#282a36"),
        ),
        (
            "Secondary Text on Background",
            colors.get("secondaryForeground", "#6272a4"),
            colors.get("background", "#282a36"),
        ),
        (
            "Text on Secondary Background",
            colors.get("foreground", "#f8f8f2"),
            colors.get("secondaryBackground", "#44475a"),
        ),
        (
            "Primary on Background",
            colors.get("primary", "#bd93f9"),
            colors.get("background", "#282a36"),
        ),
        (
            "Secondary on Background",
            colors.get("secondary", "#ff79c6"),
            colors.get("background", "#282a36"),
        ),
        (
            "Accent on Background",
            colors.get("accent", "#50fa7b"),
            colors.get("background", "#282a36"),
        ),
        (
            "Error on Background",
            colors.get("error", "#ff5555"),
            colors.get("background", "#282a36"),
        ),
        (
            "Warning on Background",
            colors.get("warning", "#ffb86c"),
            colors.get("background", "#282a36"),
        ),
        (
            "Info on Background",
            colors.get("info", "#8be9fd"),
            colors.get("background", "#282a36"),
        ),
        (
            "Success on Background",
            colors.get("success", "#50fa7b"),
            colors.get("background", "#282a36"),
        ),
        (
            "Text on Primary",
            colors.get("foreground", "#f8f8f2"),
            colors.get("primary", "#bd93f9"),
        ),
        (
            "Text on Secondary",
            colors.get("foreground", "#f8f8f2"),
            colors.get("secondary", "#ff79c6"),
        ),
        (
            "Text on Accent",
            colors.get("foreground", "#f8f8f2"),
            colors.get("accent", "#50fa7b"),
        ),
    ]

    # Validate each color pair
    for pair_name, fg, bg in color_pairs:
        try:
            ratio = calculate_contrast_ratio(fg, bg)
            meets_aa = meets_wcag_aa(ratio)
            meets_aaa = meets_wcag_aaa(ratio)

            results.append(
                {
                    "pair": pair_name,
                    "foreground": fg,
                    "background": bg,
                    "ratio": round(ratio, 2),
                    "meets_aa": meets_aa,
                    "meets_aaa": meets_aaa,
                }
            )
        except ValueError:
            # Skip invalid colors
            pass

    return results


def adjust_color_for_contrast(
    color: str, background: str, target_ratio: float = 4.5
) -> str:
    """Adjust a color to meet a target contrast ratio with a background.

    Args:
        color: Color to adjust in hex format
        background: Background color in hex format
        target_ratio: Target contrast ratio (default: 4.5 for WCAG AA)

    Returns:
        Adjusted color in hex format
    """
    # Calculate current contrast ratio
    current_ratio = calculate_contrast_ratio(color, background)

    # If already meeting target, return the original color
    if current_ratio >= target_ratio:
        return color

    # Convert colors to RGB
    r, g, b = hex_to_rgb(color)
    bg_r, bg_g, bg_b = hex_to_rgb(background)

    # Determine if we need to lighten or darken the color
    color_luminance = rgb_to_luminance(r, g, b)
    bg_luminance = rgb_to_luminance(bg_r, bg_g, bg_b)

    # Lighten if background is darker, darken if background is lighter
    lighten = bg_luminance < color_luminance

    # Adjust color until target ratio is met
    step = 0.05  # Adjustment step size
    max_iterations = 100  # Prevent infinite loops
    iterations = 0

    while current_ratio < target_ratio and iterations < max_iterations:
        iterations += 1

        if lighten:
            # Lighten the color
            r = min(255, r + int(step * 255))
            g = min(255, g + int(step * 255))
            b = min(255, b + int(step * 255))
        else:
            # Darken the color
            r = max(0, r - int(step * 255))
            g = max(0, g - int(step * 255))
            b = max(0, b - int(step * 255))

        # Calculate new contrast ratio
        adjusted_color = rgb_to_hex(r, g, b)
        current_ratio = calculate_contrast_ratio(adjusted_color, background)

    return rgb_to_hex(r, g, b)


def generate_color_palette(
    base_color: str, count: int = 5, variation: float = 0.1
) -> List[str]:
    """Generate a color palette based on a base color.

    Args:
        base_color: Base color in hex format
        count: Number of colors to generate
        variation: Amount of variation between colors (0-1)

    Returns:
        List of hex color strings
    """
    palette = [base_color]
    r, g, b = hex_to_rgb(base_color)

    # Generate lighter and darker variations
    for i in range(1, count):
        # Alternate between lighter and darker
        if i % 2 == 0:
            # Lighter
            factor = 1 + (i // 2) * variation
            new_r = min(255, int(r * factor))
            new_g = min(255, int(g * factor))
            new_b = min(255, int(b * factor))
        else:
            # Darker
            factor = 1 - ((i + 1) // 2) * variation
            new_r = max(0, int(r * factor))
            new_g = max(0, int(g * factor))
            new_b = max(0, int(b * factor))

        palette.append(rgb_to_hex(new_r, new_g, new_b))

    return palette


def generate_complementary_color(color: str) -> str:
    """Generate a complementary color.

    Args:
        color: Color in hex format

    Returns:
        Complementary color in hex format
    """
    r, g, b = hex_to_rgb(color)

    # Complementary color is the inverse
    return rgb_to_hex(255 - r, 255 - g, 255 - b)


def color_to_qcolor(color: str) -> QColor:
    """Convert a hex color string to a QColor object.

    Args:
        color: Color in hex format

    Returns:
        QColor object
    """
    r, g, b = hex_to_rgb(color)
    return QColor(r, g, b)


def qcolor_to_hex(color: QColor) -> str:
    """Convert a QColor object to a hex color string.

    Args:
        color: QColor object

    Returns:
        Color in hex format
    """
    return rgb_to_hex(color.red(), color.green(), color.blue())
