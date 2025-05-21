"""UI utility functions for RetroClamp.

This module provides common UI-related functions used across the application,
such as icon loading, theming, and other UI utilities.
"""

import os
from pathlib import Path
from typing import Optional, Union

from PySide6.QtGui import QIcon, QPixmap, QColor
from PySide6.QtWidgets import QApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt, QByteArray, QBuffer, QIODevice

def get_icon(icon_name: str, color: Optional[Union[str, QColor]] = None, size: int = 24) -> QIcon:
    """Load an icon with optional color and size.
    
    Args:
        icon_name: Name of the icon file (without extension)
        color: Optional color to apply to the icon (hex string or QColor)
        size: Size of the icon in pixels (default: 24)
        
    Returns:
        QIcon: The loaded and optionally colored icon
        
    Raises:
        FileNotFoundError: If the icon file cannot be found
    """
    # First try to find the icon in the resources
    icon_path = f":/icons/{icon_name}.svg"
    
    if not QIcon.hasThemeIcon(icon_name):
        # If not found in resources, try the icons directory
        icons_dir = Path(__file__).parent / "icons"
        if icons_dir.exists():
            for ext in ['.svg', '.png', '.ico']:
                icon_file = icons_dir / f"{icon_name}{ext}"
                if icon_file.exists():
                    icon_path = str(icon_file)
                    break
    
    # Create icon from path
    icon = QIcon(icon_path)
    
    # If no color is specified, return the icon as-is
    if not color:
        return icon
    
    # Convert color to QColor if it's a string
    if isinstance(color, str):
        color = QColor(color)
    
    # Create a pixmap from the icon
    pixmap = icon.pixmap(size, size)
    
    # Apply color to the pixmap
    if not pixmap.isNull():
        # For SVG icons, we can recolor them directly
        if icon_path.endswith('.svg'):
            renderer = QSvgRenderer(icon_path)
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            
            # Create a painter to draw the SVG with the new color
            painter = QPainter(pixmap)
            renderer.render(painter)
            
            # Apply color to the image
            image = pixmap.toImage()
            for x in range(image.width()):
                for y in range(image.height()):
                    pixel_color = image.pixelColor(x, y)
                    if pixel_color.alpha() > 0:  # Only recolor non-transparent pixels
                        pixel_color.setRed(color.red())
                        pixel_color.setGreen(color.green())
                        pixel_color.setBlue(color.blue())
                        image.setPixelColor(x, y, pixel_color)
            
            # Convert back to pixmap
            pixmap = QPixmap.fromImage(image)
            painter.end()
        else:
            # For other image formats, use a simpler colorization approach
            image = pixmap.toImage()
            for x in range(image.width()):
                for y in range(image.height()):
                    pixel_color = image.pixelColor(x, y)
                    if pixel_color.alpha() > 0:  # Only recolor non-transparent pixels
                        pixel_color.setRed(color.red())
                        pixel_color.setGreen(color.green())
                        pixel_color.setBlue(color.blue())
                        image.setPixelColor(x, y, pixel_color)
            pixmap = QPixmap.fromImage(image)
    
    return QIcon(pixmap)

def set_application_style(app: QApplication, theme: str = 'dark') -> None:
    """Set the application style and theme.
    
    Args:
        app: The QApplication instance
        theme: Theme name ('dark' or 'light')
    """
    # Set style
    app.setStyle('Fusion')
    
    # Set palette based on theme
    if theme.lower() == 'dark':
        from PySide6.QtGui import QPalette, QColor
        
        dark_palette = QPalette()
        
        # Base colors
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)
        
        # Disabled colors
        dark_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
        dark_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
        dark_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
        
        app.setPalette(dark_palette)
    
    # Apply stylesheet
    app.setStyleSheet("""
        QToolTip {
            border: 1px solid #3a3a3a;
            background-color: #2a2a2a;
            color: #ffffff;
            padding: 2px;
        }
        
        QMenuBar::item:selected {
            background-color: #3a3a3a;
        }
        
        QMenu::item:selected {
            background-color: #3a3a3a;
        }
    """)
