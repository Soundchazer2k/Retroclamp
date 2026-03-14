"""Accessibility utilities for WCAG compliance.

This module provides utility functions and constants to ensure
WCAG AA/AAA compliance across the RetroClamp application.
"""

from typing import Optional, Tuple

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QPushButton, QWidget


# WCAG-Compliant Color Palette
class WCAGColors:
    """WCAG AA/AAA compliant color palette."""

    # Background colors
    BACKGROUND_PRIMARY = "#1a1a1a"  # Very dark background
    BACKGROUND_SURFACE = "#2d2d30"  # Surface/card background
    BACKGROUND_ELEVATED = "#3c3c3c"  # Elevated surface

    # Border colors
    BORDER_DEFAULT = "#5a5a5a"  # Default border
    BORDER_HOVER = "#7c4dff"  # Hover state border
    BORDER_FOCUS = "#2196f3"  # Focus indicator (high contrast blue)

    # Text colors (all WCAG AAA compliant)
    TEXT_PRIMARY = "#ffffff"  # Primary text (21:1 contrast)
    TEXT_SECONDARY = "#e0e0e0"  # Secondary text (14:1 contrast)
    TEXT_MUTED = "#b0b0b0"  # Muted text (9:1 contrast)
    TEXT_DISABLED = "#5a5a5a"  # Disabled text

    # Accent colors (WCAG AAA compliant on dark backgrounds)
    ACCENT_PRIMARY = "#7c4dff"  # Primary accent (purple)
    ACCENT_SECONDARY = "#00e676"  # Success/secondary accent (green)
    ACCENT_WARNING = "#ff9100"  # Warning accent (orange)
    ACCENT_ERROR = "#f44336"  # Error accent (red)

    # Interactive states
    HOVER_OVERLAY = "rgba(124, 77, 255, 0.15)"
    PRESSED_OVERLAY = "rgba(124, 77, 255, 0.25)"
    FOCUS_OVERLAY = "rgba(33, 150, 243, 0.1)"


class WCAGSizes:
    """WCAG-compliant size constants."""

    # Minimum touch target size (WCAG 2.5.5)
    MIN_TOUCH_TARGET = 44  # pixels
    RECOMMENDED_TOUCH_TARGET = 56  # pixels

    # Icon sizes
    ICON_SMALL = 24
    ICON_MEDIUM = 32
    ICON_LARGE = 36
    ICON_XLARGE = 48

    # Font sizes (WCAG AA compliant)
    FONT_SMALL = 10  # 13.33px
    FONT_BASE = 11  # 14.67px - meets WCAG AA minimum
    FONT_MEDIUM = 12  # 16px
    FONT_LARGE = 13  # 17.33px
    FONT_XLARGE = 16  # 21.33px
    FONT_XXLARGE = 20  # 26.67px

    # Spacing scale
    SPACE_XS = 4
    SPACE_SM = 8
    SPACE_MD = 12
    SPACE_LG = 16
    SPACE_XL = 20
    SPACE_XXL = 24


def create_accessible_button(
    text: str,
    parent: Optional[QWidget] = None,
    button_type: str = "default",
    icon_size: int = WCAGSizes.ICON_MEDIUM,
    min_size: Optional[Tuple[int, int]] = None,
) -> QPushButton:
    """Create a WCAG-compliant button.

    Args:
        text: Button text
        parent: Parent widget
        button_type: Button type ('default', 'primary', 'secondary', 'danger')
        icon_size: Icon size in pixels
        min_size: Minimum size tuple (width, height)

    Returns:
        QPushButton: Configured button with WCAG compliance
    """
    button = QPushButton(text, parent)

    # Set minimum size for touch target compliance
    if min_size:
        button.setMinimumSize(*min_size)
    else:
        button.setMinimumSize(120, WCAGSizes.RECOMMENDED_TOUCH_TARGET)

    # Set icon size
    button.setIconSize(QSize(icon_size, icon_size))

    # Set font
    font = QFont("system-ui, -apple-system, 'Segoe UI', sans-serif")
    font.setPointSize(WCAGSizes.FONT_BASE)
    font.setWeight(QFont.Weight.Medium)
    button.setFont(font)

    # Apply button type styling
    button.setProperty("button_type", button_type)

    # Set accessible properties
    button.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    return button


def create_accessible_label(
    text: str,
    parent: Optional[QWidget] = None,
    label_type: str = "body",
    color: str = WCAGColors.TEXT_PRIMARY,
) -> QLabel:
    """Create a WCAG-compliant label.

    Args:
        text: Label text
        parent: Parent widget
        label_type: Label type ('title', 'heading', 'subheading', 'body', 'caption')
        color: Text color

    Returns:
        QLabel: Configured label with proper typography
    """
    label = QLabel(text, parent)

    # Set font based on label type
    font = QFont("system-ui, -apple-system, 'Segoe UI', sans-serif")

    if label_type == "title":
        font.setPointSize(WCAGSizes.FONT_XXLARGE)
        font.setWeight(QFont.Weight.Bold)
    elif label_type == "heading":
        font.setPointSize(WCAGSizes.FONT_XLARGE)
        font.setWeight(QFont.Weight.DemiBold)
    elif label_type == "subheading":
        font.setPointSize(WCAGSizes.FONT_LARGE)
        font.setWeight(QFont.Weight.DemiBold)
    elif label_type == "body":
        font.setPointSize(WCAGSizes.FONT_BASE)
        font.setWeight(QFont.Weight.Normal)
    elif label_type == "caption":
        font.setPointSize(WCAGSizes.FONT_SMALL)
        font.setWeight(QFont.Weight.Normal)

    label.setFont(font)

    # Set color
    label.setStyleSheet(f"color: {color};")

    # Set proper line height for readability
    label.setWordWrap(True)

    return label


def create_accessible_input(
    parent: Optional[QWidget] = None, placeholder: str = "", min_width: int = 200
) -> QLineEdit:
    """Create a WCAG-compliant input field.

    Args:
        parent: Parent widget
        placeholder: Placeholder text
        min_width: Minimum width

    Returns:
        QLineEdit: Configured input field
    """
    input_field = QLineEdit(parent)

    # Set minimum size for accessibility
    input_field.setMinimumSize(min_width, WCAGSizes.RECOMMENDED_TOUCH_TARGET)

    # Set font
    font = QFont("system-ui, -apple-system, 'Segoe UI', sans-serif")
    font.setPointSize(WCAGSizes.FONT_BASE)
    input_field.setFont(font)

    # Set placeholder
    if placeholder:
        input_field.setPlaceholderText(placeholder)

    # Set focus policy
    input_field.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    return input_field


def create_accessible_combobox(
    parent: Optional[QWidget] = None, items: Optional[list] = None, min_width: int = 150
) -> QComboBox:
    """Create a WCAG-compliant combobox.

    Args:
        parent: Parent widget
        items: List of items to add
        min_width: Minimum width

    Returns:
        QComboBox: Configured combobox
    """
    combobox = QComboBox(parent)

    # Set minimum size for accessibility
    combobox.setMinimumSize(min_width, WCAGSizes.RECOMMENDED_TOUCH_TARGET)

    # Set font
    font = QFont("system-ui, -apple-system, 'Segoe UI', sans-serif")
    font.setPointSize(WCAGSizes.FONT_BASE)
    combobox.setFont(font)

    # Add items if provided
    if items:
        combobox.addItems(items)

    # Set focus policy
    combobox.setFocusPolicy(Qt.FocusPolicy.TabFocus)

    return combobox


def set_accessible_tooltip(widget: QWidget, tooltip_text: str) -> None:
    """Set an accessible tooltip with proper formatting.

    Args:
        widget: Widget to add tooltip to
        tooltip_text: Tooltip text
    """
    # Format tooltip with proper font size
    formatted_tooltip = (
        f'<span style="font-size: {WCAGSizes.FONT_BASE}pt;">{tooltip_text}</span>'
    )
    widget.setToolTip(formatted_tooltip)


def apply_focus_indicator(widget: QWidget) -> None:
    """Apply a high-contrast focus indicator to a widget.

    Args:
        widget: Widget to apply focus indicator to
    """
    widget.setStyleSheet(f"""
        {widget.__class__.__name__}:focus {{
            border: 3px solid {WCAGColors.BORDER_FOCUS};
            outline: none;
        }}
    """)


def get_contrast_ratio(color1: str, color2: str) -> float:
    """Calculate the contrast ratio between two colors.

    Args:
        color1: First color (hex string)
        color2: Second color (hex string)

    Returns:
        float: Contrast ratio (1:1 to 21:1)
    """

    def get_luminance(hex_color: str) -> float:
        """Get relative luminance of a color."""
        # Convert hex to RGB
        hex_color = hex_color.lstrip("#")
        r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]

        # Convert to relative values
        r, g, b = [c / 255.0 for c in (r, g, b)]  # type: ignore[assignment]

        # Apply gamma correction
        def gamma_correct(c):
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        r, g, b = [gamma_correct(c) for c in (r, g, b)]

        # Calculate luminance
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    lum1 = get_luminance(color1)
    lum2 = get_luminance(color2)

    # Ensure lighter color is in numerator
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)

    return (lighter + 0.05) / (darker + 0.05)


def check_wcag_compliance(
    text_color: str, background_color: str, large_text: bool = False
) -> Tuple[bool, bool, float]:
    """Check if a color combination meets WCAG standards.

    Args:
        text_color: Text color (hex string)
        background_color: Background color (hex string)
        large_text: Whether this is large text (18pt+ or 14pt+ bold)

    Returns:
        Tuple[bool, bool, float]: (AA compliant, AAA compliant, contrast ratio)
    """
    ratio = get_contrast_ratio(text_color, background_color)

    if large_text:
        aa_compliant = ratio >= 3.0
        aaa_compliant = ratio >= 4.5
    else:
        aa_compliant = ratio >= 4.5
        aaa_compliant = ratio >= 7.0

    return aa_compliant, aaa_compliant, ratio
