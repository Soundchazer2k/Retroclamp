"""UI utility functions for RetroClamp.

This module provides common UI-related functions used across the application,
such as icon loading, theming, and other UI utilities.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QByteArray, QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from ..main import MainWindow  # For type hinting

# Global cache for icons to avoid redundant processing
# ...


def get_icon(
    icon_name: str, color: str | QColor | None = None, size: int = 32
) -> QIcon:
    """Load an icon with optional color and size.

    Args:
        icon_name: Name of the icon file (without extension)
        color: Optional color to apply to the icon (hex string or QColor)
        size: Size of the icon in pixels (default: 24)

    Returns:
        QIcon: The loaded and optionally colored icon
    """
    # Try QtAwesome first if available, then fall back to filesystem
    try:
        import qtawesome as qta

        # Check if this looks like a QtAwesome icon name
        if "." in icon_name and any(
            icon_name.startswith(prefix) for prefix in ["fa5s", "fa6s", "mdi"]
        ):
            qta_icon = qta.icon(icon_name, color=color)
            if not qta_icon.isNull():
                return qta_icon  # type: ignore[no-any-return]
    except Exception:
        pass  # Fall back to filesystem loading

    # Skip resource loading (:/icons/) to avoid conflicts with QtAwesome
    icon = QIcon()  # Start with empty icon
    icon_file_path_str = ""

    if True:  # Always try filesystem paths
        # If not found in resources, try filesystem paths
        project_root: Path | None = None
        try:
            # Assuming ui_functions.py is in 'gui' directory, so parent.parent is project root
            project_root = Path(__file__).resolve().parent.parent
        except Exception:
            # Fallback for environments where __file__ might not be standard (e.g. frozen)
            project_root = Path(".").resolve()

        # Define potential filesystem locations for icons, ordered by preference
        icon_search_paths: list[Path] = []
        if project_root:
            icon_search_paths.extend(
                [
                    project_root
                    / "resources"
                    / "icons"
                    / "tabler-icons"
                    / "icons"
                    / "outline",
                    project_root / "gui" / "icons",  # Original fallback path
                ]
            )
        # else: # If project_root determination failed, could add pure relative paths as last resort
        # icon_search_paths.append(Path("resources/icons/tabler-icons/icons/outline"))
        # icon_search_paths.append(Path("gui/icons"))

        found_on_disk = False
        for search_dir in icon_search_paths:
            if search_dir.exists() and search_dir.is_dir():
                for ext in [".svg", ".png", ".ico"]:  # Common icon extensions
                    disk_icon_file = search_dir / f"{icon_name}{ext}"
                    if disk_icon_file.is_file():
                        icon_file_path_str = str(disk_icon_file)
                        icon = QIcon(icon_file_path_str)
                        if not icon.isNull():
                            found_on_disk = True
                            break  # Found in this directory
                if found_on_disk:
                    break  # Found in one of the search_paths

        if (
            not found_on_disk and icon.isNull()
        ):  # Still not found on disk after checking all paths
            # Try loading from the system theme as a last resort for common icons
            if QIcon.hasThemeIcon(icon_name):
                icon = QIcon.fromTheme(icon_name)
                if not icon.isNull():
                    # For theme icons, we don't have a direct file path for SVG check later
                    icon_file_path_str = ""  # Indicate it's not a direct file path

            if icon.isNull():  # Still not found anywhere
                # logging.warning(f"Icon '{icon_name}' not found in resources, disk, or theme.")
                return QIcon()  # Return an empty icon

    if color is None:
        return icon

    if isinstance(color, str):
        try:
            color_obj = QColor(color)
            if not color_obj.isValid():
                # logging.warning(f"Invalid color string for icon '{icon_name}': {color}")
                return icon  # Return original icon if color is invalid
            color = color_obj
        except Exception:  # pylint: disable=broad-except
            # logging.warning(f"Could not parse color string '{color}' for icon '{icon_name}'.", exc_info=True)
            return icon  # Return original icon on parsing error

    # Ensure color is a QColor object
    if not isinstance(color, QColor):
        # logging.warning(f"Invalid color type for icon '{icon_name}'.")
        return icon

    # Create a pixmap for drawing. We want to draw the icon at the requested size.
    # For SVG, rendering at the target size is best.
    # For PNG/other rasters, we get the pixmap at the target size.

    # If it's an SVG and we have a valid file path for it
    if icon_file_path_str and icon_file_path_str.lower().endswith(".svg"):
        renderer = QSvgRenderer(icon_file_path_str)
        if not renderer.isValid():
            # logging.warning(f"Invalid SVG file for icon '{icon_name}': {icon_file_path_str}")
            # Fallback to rendering the QIcon's pixmap if SVG load fails
            pixmap = icon.pixmap(size, size)
        else:
            target_pixmap = QPixmap(size, size)
            target_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(target_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            renderer.render(painter)
            painter.end()
            pixmap = target_pixmap
    else:
        # For non-SVG icons or if SVG direct rendering failed/not applicable
        pixmap = icon.pixmap(size, size)

    if pixmap.isNull():
        # logging.warning(f"Could not create pixmap for icon '{icon_name}'.")
        return icon  # Or QIcon() if preferred on pixmap failure

    # Apply color to the pixmap's image data
    image = pixmap.toImage()
    if image.isNull():
        # logging.warning(f"Could not convert pixmap to image for icon '{icon_name}'.")
        return QIcon(pixmap)  # Return colored (if possible) or original pixmap

    for x in range(image.width()):
        for y in range(image.height()):
            pixel = image.pixelColor(x, y)
            # Only change RGB of non-transparent pixels, keep original alpha
            if pixel.alpha() > 0:
                # Preserve original alpha for the new color
                new_pixel_color = QColor(
                    color.red(), color.green(), color.blue(), pixel.alpha()
                )
                image.setPixelColor(x, y, new_pixel_color)

    return QIcon(QPixmap.fromImage(image))


def set_application_style(app: QApplication, theme: str = "dark") -> None:
    """Set the application style and theme.

    Args:
        app: The QApplication instance
        theme: Theme name ('dark' or 'light')
    """
    app.setStyle("Fusion")

    if theme.lower() == "dark":
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.WindowText,
            QColor(127, 127, 127),
        )
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127)
        )
        dark_palette.setColor(
            QPalette.ColorGroup.Disabled,
            QPalette.ColorRole.ButtonText,
            QColor(127, 127, 127),
        )
        app.setPalette(dark_palette)
    # Add 'light' theme handling here if needed
    # else:
    #     # Use default system palette or define a light palette
    #     app.setPalette(QApplication.style().standardPalette())

    # Common stylesheet adjustments (can be theme-dependent too)
    app.setStyleSheet(
        """
        QToolTip {
            border: 1px solid #3a3a3a; /* Dark theme specific */
            background-color: #2a2a2a; /* Dark theme specific */
            color: #ffffff; /* Dark theme specific */
            padding: 2px;
        }
        QMenuBar::item:selected {
            background-color: #3a3a3a; /* Dark theme specific */
        }
        QMenu::item:selected {
            background-color: #3a3a3a; /* Dark theme specific */
        }
        /* Add more general or light theme specific styles if needed */
    """
    )


# Example of a function that might use WA_TranslucentBackground if it were in this file:
# def create_translucent_window(parent=None):
#     from PySide6.QtWidgets import QWidget
#     window = QWidget(parent)
#     window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Corrected enum usage
#     return window


def toggle_left_menu(
    main_window: MainWindow, max_width: int, enable: bool, animate: bool = True
):
    if not hasattr(main_window, "ui") or not hasattr(main_window.ui, "left_menu"):
        return

    left_menu = main_window.ui.left_menu
    width = left_menu.width()

    if enable:
        width_extended = max_width
    else:
        width_extended = main_window.ui.left_menu_button.width()

    if width == width_extended and not enable:  # Already collapsed
        if animate:
            # Ensure animation attribute exists and is of the correct type
            if not hasattr(main_window, "animation") or not isinstance(
                main_window.animation, QPropertyAnimation
            ):
                main_window.animation = QPropertyAnimation(
                    left_menu, QByteArray(b"minimumWidth")
                )
            main_window.animation.setDuration(500)
            main_window.animation.setStartValue(width)
            main_window.animation.setEndValue(width_extended)
            main_window.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
            main_window.animation.start()
        else:
            left_menu.setMinimumWidth(width_extended)
        return

    if animate:
        if not hasattr(main_window, "animation") or not isinstance(
            main_window.animation, QPropertyAnimation
        ):
            main_window.animation = QPropertyAnimation(
                left_menu, QByteArray(b"minimumWidth")
            )
        main_window.animation.setDuration(500)
        main_window.animation.setStartValue(width)
        main_window.animation.setEndValue(width_extended)
        main_window.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        main_window.animation.start()
    else:
        left_menu.setMinimumWidth(width_extended)


def toggle_right_menu(
    main_window: MainWindow, max_width: int, enable: bool, animate: bool = True
):
    if not hasattr(main_window, "ui") or not hasattr(main_window.ui, "right_menu"):
        return

    right_menu = main_window.ui.right_menu
    width = right_menu.width()

    if enable:
        width_extended = max_width
    else:
        width_extended = main_window.ui.right_menu_button.width()

    if width == width_extended and not enable:  # Already collapsed
        if animate:
            # Ensure animation attribute exists and is of the correct type
            if not hasattr(main_window, "animation") or not isinstance(
                main_window.animation, QPropertyAnimation
            ):
                main_window.animation = QPropertyAnimation(
                    right_menu, QByteArray(b"minimumWidth")
                )
            main_window.animation.setDuration(500)
            main_window.animation.setStartValue(width)
            main_window.animation.setEndValue(width_extended)
            main_window.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
            main_window.animation.start()
        else:
            right_menu.setMinimumWidth(width_extended)
        return

    if animate:
        if not hasattr(main_window, "animation") or not isinstance(
            main_window.animation, QPropertyAnimation
        ):
            main_window.animation = QPropertyAnimation(
                right_menu, QByteArray(b"minimumWidth")
            )
        main_window.animation.setDuration(500)
        main_window.animation.setStartValue(width)
        main_window.animation.setEndValue(width_extended)
        main_window.animation.setEasingCurve(QEasingCurve.Type.InOutQuart)
        main_window.animation.start()
    else:
        right_menu.setMinimumWidth(width_extended)


def apply_theme(widget: QWidget, theme: dict) -> None:
    """Apply a theme to a widget.

    Args:
        widget: The widget to apply the theme to
        theme: A dictionary containing theme settings
    """
    # Apply base palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(127, 127, 127),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(127, 127, 127),
    )
    widget.setPalette(palette)

    # Apply specific colors from theme
    if "text_color" in theme:
        palette.setColor(QPalette.ColorRole.WindowText, QColor(theme["text_color"]))
        palette.setColor(QPalette.ColorRole.Text, QColor(theme["text_color"]))
    if "bg_color" in theme:
        palette.setColor(QPalette.ColorRole.Window, QColor(theme["bg_color"]))
    if "button_color" in theme:
        palette.setColor(QPalette.ColorRole.Button, QColor(theme["button_color"]))
    if "button_text_color" in theme:
        palette.setColor(
            QPalette.ColorRole.ButtonText, QColor(theme["button_text_color"])
        )

    widget.setPalette(palette)

    # Handle translucency
    if theme.get("translucent_background", False):
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        widget.setAutoFillBackground(False)  # Important for translucency
    else:
        widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
