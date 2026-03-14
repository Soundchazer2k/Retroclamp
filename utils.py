"""Utility functions for RetroClamp.

This module provides common utility functions used throughout the application.
"""

import logging
import os
from typing import Any, List, Optional, Tuple, TypeVar, cast

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication,  # Added import for QApplication
    QFileDialog,
    QInputDialog,
    QLineEdit,  # Added import for QLineEdit to use QLineEdit.EchoMode
    QMessageBox,
    QWidget,
)

# Type variable for generic type hinting
T = TypeVar("T")


def setup_logging(level=logging.INFO, log_file: Optional[str] = None) -> None:
    """Set up basic logging configuration.

    Args:
        level: Logging level (default: logging.INFO)
        log_file: Optional path to log file. If None, logs to console only.
    """
    handlers: List[logging.Handler] = [logging.StreamHandler()]

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


# Helper function to satisfy mypy's strict parent widget requirement
def _get_effective_parent(parent: Optional[QWidget]) -> QWidget:
    """
    Returns the provided parent if not None, otherwise QApplication.activeWindow().
    This helps satisfy mypy's strictness for QWidget arguments in some static methods
    while still allowing Optional[QWidget] in the function signature.
    """
    if parent is None:
        # Fallback to the currently active window if no parent is explicitly provided.
        # This is a common pattern for dialogs that need a parent for modality/positioning.
        active_window = QApplication.activeWindow()
        if active_window:
            return active_window
        # As a last resort, if no active window is available, create a dummy widget.
        # This case should be rare in a running application.
        return QWidget()
    return parent


def show_info(
    message: str, title: str = "Information", parent: Optional[QWidget] = None
) -> None:
    """Show an information message box.

    Args:
        message: Message to display
        title: Window title (default: "Information")
        parent: Parent widget (optional)
    """
    # Fix: Pass the effective parent to satisfy mypy
    QMessageBox.information(_get_effective_parent(parent), title, message)


def show_error(
    message: str, title: str = "Error", parent: Optional[QWidget] = None
) -> None:
    """Show an error message box.

    Args:
        message: Error message to display
        title: Window title (default: "Error")
        parent: Parent widget (optional)
    """
    # Fix: Pass the effective parent to satisfy mypy
    QMessageBox.critical(_get_effective_parent(parent), title, message)


def show_warning(
    message: str, title: str = "Warning", parent: Optional[QWidget] = None
) -> None:
    """Show a warning message box.

    Args:
        message: Warning message to display
        title: Window title (default: "Warning")
        parent: Parent widget (optional)
    """
    # Fix: Pass the effective parent to satisfy mypy
    QMessageBox.warning(_get_effective_parent(parent), title, message)


def show_question(
    message: str,
    title: str = "Confirm",
    # Fix: Use QMessageBox.StandardButton enum for buttons
    buttons: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes
    | QMessageBox.StandardButton.No,
    # Fix: Use QMessageBox.StandardButton enum for default_button
    default_button: QMessageBox.StandardButton = QMessageBox.StandardButton.NoButton,
    parent: Optional[QWidget] = None,
) -> QMessageBox.StandardButton:
    """Show a question dialog with Yes/No buttons.

    Args:
        message: Question to ask
        title: Window title (default: "Confirm")
        buttons: Buttons to show (default: Yes/No)
        default_button: Default button (default: NoButton)
        parent: Parent widget (optional)

    Returns:
        QMessageBox.StandardButton: The button that was clicked
    """
    # Fix: Pass the effective parent to satisfy mypy
    return QMessageBox.question(
        _get_effective_parent(parent), title, message, buttons, default_button
    )


def get_open_file_name(
    parent: Optional[QWidget] = None,
    caption: str = "Open File",
    dir: str = "",
    filter: str = "All Files (*)",
    selected_filter: str = "",
    # Fix: Type hint must be Optional because default is None (mypy's no_implicit_optional)
    options: Optional[QFileDialog.Option] = None,
) -> Tuple[str, str]:
    """Show a file open dialog and return the selected file.

    Args:
        parent: Parent widget (optional)
        caption: Dialog caption (default: "Open File")
        dir: Starting directory (default: current directory)
        filter: File filter string (default: "All Files (*)")
        selected_filter: The selected filter (default: "")
        options: Additional options (default: 0)

    Returns:
        Tuple[str, str]: (selected file, selected filter) or ("", "") if canceled
    """
    if options is None:
        options = QFileDialog.Option(0)
    result = QFileDialog.getOpenFileName(
        parent, caption, dir, filter, selected_filter, options
    )
    return cast(Tuple[str, str], result)


def get_save_file_name(
    parent: Optional[QWidget] = None,
    caption: str = "Save File",
    dir: str = "",
    filter: str = "All Files (*)",
    selected_filter: str = "",
    # Fix: Type hint must be Optional because default is None
    options: Optional[QFileDialog.Option] = None,
) -> Tuple[str, str]:
    """Show a file save dialog and return the selected file.

    Args:
        parent: Parent widget (optional)
        caption: Dialog caption (default: "Save File")
        dir: Starting directory (default: current directory)
        filter: File filter string (default: "All Files (*)")
        selected_filter: The selected filter (default: "")
        options: Additional options (default: 0)

    Returns:
        Tuple[str, str]: (selected file, selected filter) or ("", "") if canceled
    """
    if options is None:
        options = QFileDialog.Option(0)
    result = QFileDialog.getSaveFileName(
        parent, caption, dir, filter, selected_filter, options
    )
    return cast(Tuple[str, str], result)


def get_existing_directory(
    parent: Optional[QWidget] = None,
    caption: str = "Select Directory",
    dir: str = "",
    # Fix: Type hint must be Optional because default is None
    options: Optional[QFileDialog.Option] = None,
) -> str:
    """Show a directory selection dialog and return the selected directory.

    Args:
        parent: Parent widget (optional)
        caption: Dialog caption (default: "Select Directory")
        dir: Starting directory (default: current directory)
        options: Additional options (default: ShowDirsOnly)

    Returns:
        str: Selected directory or "" if canceled
    """
    if options is None:
        options = QFileDialog.Option(QFileDialog.Option.ShowDirsOnly)
    return str(QFileDialog.getExistingDirectory(parent, caption, dir, options))


def get_text_input(
    parent: Optional[QWidget] = None,
    title: str = "Input",
    label: str = "Enter text:",
    text: str = "",
    # Fix: Use QLineEdit.EchoMode enum instead of int
    echo: QLineEdit.EchoMode = QLineEdit.EchoMode.Normal,
    # Fix: Type hint must be Optional because default is None
    flags: Optional[Qt.WindowType] = None,
    # Fix: Type hint must be Optional because default is None
    input_method_hints: Optional[Qt.InputMethodHint] = None,
) -> str:
    """Show a text input dialog and return the entered text.

    Args:
        parent: Parent widget (optional)
        title: Dialog title (default: "Input")
        label: Input label (default: "Enter text:")
        text: Default text (default: "")
        echo: Echo mode (default: QLineEdit.Normal)
        flags: Window flags (default: 0)
        input_method_hints: Input method hints (default: ImhNone)

    Returns:
        str: Entered text or "" if canceled
    """
    if flags is None:
        flags = Qt.WindowType(0)
    if input_method_hints is None:
        input_method_hints = Qt.InputMethodHint(0)
    # Fix: Pass the effective parent to satisfy mypy
    text, ok = QInputDialog.getText(
        _get_effective_parent(parent),
        title,
        label,
        echo,
        text,
        flags,
        input_method_hints,
    )
    return str(text) if ok else ""


def get_item_input(
    parent: Optional[QWidget] = None,
    title: str = "Select Item",
    label: str = "Select an item:",
    items: Optional[List[Any]] = None,
    current: int = 0,
    editable: bool = True,
    # Fix: Type hint must be Optional because default is None
    flags: Optional[Qt.WindowType] = None,
    # Fix: Type hint must be Optional because default is None
    input_method_hints: Optional[Qt.InputMethodHint] = None,
) -> Tuple[str, bool]:
    """Show an item selection dialog and return the selected item.

    Args:
        parent: Parent widget (optional)
        title: Dialog title (default: "Select Item")
        label: Selection label (default: "Select an item:")
        items: List of items to select from
        current: Index of current item (default: 0)
        editable: Whether the input is editable (default: True)
        flags: Window flags (default: 0)
        input_method_hints: Input method hints (default: ImhNone)

    Returns:
        Tuple[str, bool]: (selected item, ok) where ok is True if user pressed OK
    """
    if items is None:
        items = []
    if flags is None:
        flags = Qt.WindowType(0)
    if input_method_hints is None:
        input_method_hints = Qt.InputMethodHint.ImhNone
    # Fix: Pass the effective parent to satisfy mypy
    result = QInputDialog.getItem(
        _get_effective_parent(parent),
        title,
        label,
        items,
        current,
        editable,
        flags,
        input_method_hints,
    )
    return (str(result[0]), bool(result[1]))


def create_icon_from_svg(svg_data: str, color: Optional[QColor] = None) -> QIcon:
    """Create a QIcon from SVG data with optional color.

    Args:
        svg_data: SVG data as a string
        color: Optional color to apply to the icon

    Returns:
        QIcon: The created icon
    """
    # Create a buffer with the SVG data
    svg_bytes = QByteArray(svg_data.encode("utf-8"))
    buffer = QBuffer(svg_bytes)
    # Fix: Use QIODevice.OpenModeFlag enum for ReadOnly
    buffer.open(QIODevice.OpenModeFlag.ReadOnly)

    # Create a pixmap from the SVG
    renderer = QSvgRenderer()
    # Fix: QSvgRenderer.load expects QByteArray or str, not QBuffer
    if not renderer.load(svg_bytes):
        return QIcon()

    # Create a pixmap and paint the SVG onto it
    pixmap = QPixmap(renderer.defaultSize())
    # Fix: Use Qt.GlobalColor enum for transparent
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    # Apply color if specified
    if color is not None:
        image = pixmap.toImage()
        for x in range(image.width()):
            for y in range(image.height()):
                pixel_color = image.pixelColor(x, y)
                if pixel_color.alpha() > 0:  # Only recolor non-transparent pixels
                    # Preserve original alpha when applying new color
                    new_color = QColor(
                        color.red(), color.green(), color.blue(), pixel_color.alpha()
                    )
                    image.setPixelColor(x, y, new_color)
        pixmap = QPixmap.fromImage(image)

    return QIcon(pixmap)


def human_readable_size(size_bytes: int) -> str:
    """Convert a size in bytes to a human-readable string.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Human-readable size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1

    # Fix: Format the 'size' variable (float) to 2 decimal places for larger units.
    # For 'B' (bytes), format as an integer.
    if i == 0:
        return f"{int(size)} {units[i]}"
    else:
        return f"{size:.2f} {units[i]}"
