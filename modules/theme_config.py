"""Theme configuration module for RetroClamp.

This module provides functionality for loading theme configurations from JSON files
and generating QSS stylesheets dynamically.
"""

import os
import json
from typing import Dict, Any, Optional, List

from PySide6.QtCore import QObject, Signal


class ThemeConfigSignals(QObject):
    """Signals for theme configuration operations.
    
    Signals:
        loaded: Emitted when a theme is loaded
        error: Emitted when an error occurs
    """
    loaded = Signal(str)  # Theme name
    error = Signal(str)  # Error message


class ThemeConfig:
    """Manager for theme configurations.
    
    This class provides functionality for loading theme configurations from JSON files
    and generating QSS stylesheets dynamically.
    """
    
    def __init__(self, config_dir: str = None):
        """Initialize the ThemeConfig.
        
        Args:
            config_dir: Directory containing theme configuration files
        """
        self.config_dir = config_dir or os.path.join(os.getcwd(), "config")
        self.signals = ThemeConfigSignals()
        self.current_theme: Optional[Dict[str, Any]] = None
    
    def load_theme(self, theme_name: str = "theme") -> Optional[Dict[str, Any]]:
        """Load a theme configuration from a JSON file.
        
        Args:
            theme_name: Name of the theme to load (without .json extension)
            
        Returns:
            Theme configuration dictionary or None if loading fails
        """
        theme_path = os.path.join(self.config_dir, f"{theme_name}.json")
        
        if not os.path.exists(theme_path):
            self.signals.error.emit(f"Theme file not found: {theme_path}")
            return None
        
        try:
            with open(theme_path, 'r') as f:
                theme_config = json.load(f)
                
            self.current_theme = theme_config
            self.signals.loaded.emit(theme_name)
            
            return theme_config
        except Exception as e:
            self.signals.error.emit(f"Error loading theme: {str(e)}")
            return None
    
    def generate_qss(self, theme_config: Optional[Dict[str, Any]] = None) -> str:
        """Generate a QSS stylesheet from a theme configuration.
        
        Args:
            theme_config: Theme configuration dictionary (uses current_theme if None)
            
        Returns:
            QSS stylesheet as a string
        """
        config = theme_config or self.current_theme
        
        if not config:
            self.signals.error.emit("No theme configuration loaded")
            return ""
        
        # Extract color values for easier access
        colors = config.get("colors", {})
        primary = colors.get("primary", "#bd93f9")
        secondary = colors.get("secondary", "#ff79c6")
        accent = colors.get("accent", "#50fa7b")
        background = colors.get("background", "#282a36")
        secondary_bg = colors.get("secondaryBackground", "#44475a")
        foreground = colors.get("foreground", "#f8f8f2")
        secondary_fg = colors.get("secondaryForeground", "#6272a4")
        error = colors.get("error", "#ff5555")
        warning = colors.get("warning", "#ffb86c")
        info = colors.get("info", "#8be9fd")
        success = colors.get("success", "#50fa7b")
        border = colors.get("border", "#44475a")
        shadow = colors.get("shadow", "rgba(0, 0, 0, 0.4)")
        
        # Extract font values
        fonts = config.get("fonts", {})
        font_family = fonts.get("family", "Segoe UI")
        font_size = fonts.get("size", 10)
        title_size = fonts.get("titleSize", 12)
        header_size = fonts.get("headerSize", 14)
        
        # Extract border values
        borders = config.get("borders", {})
        border_radius = borders.get("radius", 4)
        border_width = borders.get("width", 1)
        
        # Extract spacing values
        spacing = config.get("spacing", {})
        spacing_small = spacing.get("small", 4)
        spacing_medium = spacing.get("medium", 8)
        spacing_large = spacing.get("large", 16)
        
        # Extract animation values
        animation = config.get("animation", {})
        animation_duration = animation.get("duration", 300)
        
        # Generate the QSS stylesheet
        qss = f"""
        /* RetroClamp QSS Theme: {config.get('name', 'default')} */
        /* Generated from theme configuration */
        
        /* Global Styles */
        QWidget {{
            background-color: {background};
            color: {foreground};
            font-family: "{font_family}";
            font-size: {font_size}pt;
            border: none;
        }}
        
        /* Main Window */
        #bgApp {{
            background-color: {background};
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
        }}
        
        /* Left Menu */
        #leftMenuBg {{
            background-color: {secondary_bg};
        }}
        
        #topLogo {{
            background-color: {secondary_bg};
            background-position: centered;
            background-repeat: no-repeat;
        }}
        
        #titleLeftApp {{
            font-size: {title_size}pt;
            font-weight: bold;
            color: {foreground};
        }}
        
        #titleLeftDescription {{
            font-size: {font_size}pt;
            color: {secondary_fg};
        }}
        
        /* Top Menu */
        #topMenu .QPushButton {{
            background-position: left center;
            background-repeat: no-repeat;
            border: none;
            background-color: transparent;
            text-align: left;
            border-left: 32px solid transparent;
            padding-left: 56px;
            font-size: 11pt;
            color: {foreground};
            border-radius: 6px;
            margin: 5px 10px;
        }}
        
        #topMenu .QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.05);
        }}
        
        #topMenu .QPushButton:pressed {{
            background-color: transparent;
            border-left: 4px solid {primary};
            padding-left: 56px;
            color: {primary};
        }}
        
        #topMenu .QPushButton:checked {{
            background-color: transparent;
            border-left: 4px solid {primary};
            padding-left: 56px;
            color: {primary};
        }}
        
        /* Bottom Menu */
        #bottomMenu .QPushButton {{
            background-position: left center;
            background-repeat: no-repeat;
            border: none;
            background-color: transparent;
            text-align: left;
            border-left: 32px solid transparent;
            padding-left: 56px;
            font-size: 11pt;
            color: {foreground};
            border-radius: 6px;
            margin: 5px 10px;
        }}
        
        #bottomMenu .QPushButton:hover {{
            background-color: rgba(255, 255, 255, 0.05);
        }}
        
        #bottomMenu .QPushButton:pressed {{
            background-color: transparent;
            border-left: 4px solid {primary};
            padding-left: 56px;
            color: {primary};
        }}
        
        #bottomMenu .QPushButton:checked {{
            background-color: transparent;
            border-left: 4px solid {primary};
            padding-left: 56px;
            color: {primary};
        }}
        
        /* Toggle Button */
        #toggleButton {{
            background-position: left center;
            background-repeat: no-repeat;
            border: none;
            background-color: transparent;
            text-align: left;
            border-left: 32px solid transparent;
            padding-left: 56px;
            font-size: 11pt;
            color: {foreground};
            border-radius: 6px;
            margin: 5px 10px;
        }}
        
        #toggleButton:hover {{
            background-color: rgba(68, 71, 90, 0.6);
        }}
        
        #toggleButton:pressed {{
            background-color: transparent;
            border-left: 4px solid {primary};
            padding-left: 56px;
            color: {primary};
        }}
        
        /* Tab Widget */
        QTabBar::tab {{
            background: rgba(68, 71, 90, 0.6);
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            color: {foreground};
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background: {primary};
            color: {background};
            font-weight: bold;
        }}
        
        QTabWidget::pane {{
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 12px;
        }}
        
        /* Scrollbar Styling */
        QScrollBar:vertical {{
            width: 8px;
            background: transparent;
        }}
        
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            min-height: 20px;
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ 
            height: 0; 
        }}
        
        QScrollBar:horizontal {{
            height: 8px;
            background: transparent;
        }}
        
        QScrollBar::handle:horizontal {{
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            min-width: 20px;
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ 
            width: 0; 
        }}
        
        /* Page Headers and Content Spacing */
        QLabel[objectName="pageTitle"] {{
            font-size: 18pt;
            font-weight: bold;
            color: {foreground};
            margin-bottom: -8px;  /* Negative margin to reduce space below title */
            padding-bottom: 0px;
        }}
        
        QGroupBox {{
            margin-top: 16px;  /* Reduced from default */
            font-weight: bold;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 12px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0 6px;
            color: {primary};
        }}
        
        /* Toggle Button */
        #toggleButton {{
            background-position: left center;
            background-repeat: no-repeat;
            border: none;
            border-left: 20px solid transparent;
            background-color: transparent;
            text-align: left;
            padding-left: 44px;
            color: {foreground};
        }}
        
        #toggleButton:hover {{
            background-color: {secondary_bg};
        }}
        
        #toggleButton:pressed {{
            background-color: {primary};
            color: {background};
        }}
        
        /* Title Menu */
        #titleRightInfo {{
            padding-left: 10px;
        }}
        
        /* Top Buttons */
        #rightButtons .QPushButton {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: none;
            padding: 5px;
        }}
        
        #rightButtons .QPushButton:hover {{
            background-color: {border};
        }}
        
        #rightButtons .QPushButton:pressed {{
            background-color: {primary};
        }}
        
        /* Content */
        #contentTopBg {{
            background-color: {background};
        }}
        
        #contentBottom {{
            background-color: {background};
            border-top: 3px solid {border};
        }}
        
        /* Extra Content */
        #extraContent {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
        }}
        
        /* Buttons */
        QPushButton {{
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
            padding: {spacing_medium}px;
            background-color: {secondary_bg};
            color: {foreground};
        }}
        
        QPushButton:hover {{
            background-color: {border};
        }}
        
        QPushButton:pressed {{
            background-color: {primary};
            color: {background};
        }}
        
        /* Primary Button */
        QPushButton[Primary="true"] {{
            background-color: {primary};
            color: {background};
        }}
        
        QPushButton[Primary="true"]:hover {{
            background-color: {secondary};
        }}
        
        QPushButton[Primary="true"]:pressed {{
            background-color: {accent};
        }}
        
        /* Line Edit */
        QLineEdit {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            padding: {spacing_medium}px;
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        QLineEdit:focus {{
            border: {border_width}px solid {primary};
        }}
        
        /* Text Edit */
        QTextEdit {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            padding: {spacing_medium}px;
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        QTextEdit:focus {{
            border: {border_width}px solid {primary};
        }}
        
        /* Combo Box */
        QComboBox {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            padding: {spacing_medium}px;
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        QComboBox:hover {{
            border: {border_width}px solid {primary};
        }}
        
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 24px;
            border-left: {border_width}px solid {border};
            border-top-right-radius: {border_radius}px;
            border-bottom-right-radius: {border_radius}px;
            background-color: {secondary_bg};
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        /* Spin Box */
        QSpinBox, QDoubleSpinBox {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            padding: {spacing_medium}px;
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        QSpinBox:hover, QDoubleSpinBox:hover {{
            border: {border_width}px solid {primary};
        }}
        
        /* Slider */
        QSlider::groove:horizontal {{
            height: 5px;
            background-color: {secondary_bg};
            border-radius: 2px;
        }}
        
        QSlider::handle:horizontal {{
            background-color: {primary};
            border-radius: 7px;
            width: 14px;
            margin: -5px 0px;
        }}
        
        QSlider::add-page:horizontal {{
            background-color: {border};
            border-radius: 2px;
        }}
        
        QSlider::sub-page:horizontal {{
            background-color: {primary};
            border-radius: 2px;
        }}
        
        /* Progress Bar */
        QProgressBar {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
            color: {foreground};
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background-color: {primary};
            border-radius: {border_radius}px;
        }}
        
        /* Table Widget */
        QTableWidget {{
            background-color: {background};
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            gridline-color: {border};
            color: {foreground};
            selection-background-color: {primary};
            selection-color: {background};
        }}
        
        QTableWidget::item {{
            padding: {spacing_small}px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {primary};
            color: {background};
        }}
        
        QHeaderView::section {{
            background-color: {secondary_bg};
            color: {foreground};
            padding: {spacing_medium}px;
            border: none;
            border-right: {border_width}px solid {border};
            border-bottom: {border_width}px solid {border};
        }}
        
        /* Scroll Bar */
        QScrollBar:vertical {{
            border: none;
            background-color: {secondary_bg};
            width: 14px;
            margin: 15px 0 15px 0;
            border-radius: 0px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {border};
            min-height: 30px;
            border-radius: 7px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {primary};
        }}
        
        QScrollBar::handle:vertical:pressed {{
            background-color: {secondary};
        }}
        
        QScrollBar::sub-line:vertical {{
            border: none;
            background-color: {secondary_bg};
            height: 15px;
            border-top-left-radius: 7px;
            border-top-right-radius: 7px;
            subcontrol-position: top;
            subcontrol-origin: margin;
        }}
        
        QScrollBar::add-line:vertical {{
            border: none;
            background-color: {secondary_bg};
            height: 15px;
            border-bottom-left-radius: 7px;
            border-bottom-right-radius: 7px;
            subcontrol-position: bottom;
            subcontrol-origin: margin;
        }}
        
        QScrollBar::horizontal {{
            border: none;
            background-color: {secondary_bg};
            height: 14px;
            margin: 0px 15px 0 15px;
            border-radius: 0px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {border};
            min-width: 30px;
            border-radius: 7px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {primary};
        }}
        
        QScrollBar::handle:horizontal:pressed {{
            background-color: {secondary};
        }}
        
        QScrollBar::sub-line:horizontal {{
            border: none;
            background-color: {secondary_bg};
            width: 15px;
            border-top-left-radius: 7px;
            border-bottom-left-radius: 7px;
            subcontrol-position: left;
            subcontrol-origin: margin;
        }}
        
        QScrollBar::add-line:horizontal {{
            border: none;
            background-color: {secondary_bg};
            width: 15px;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            subcontrol-position: right;
            subcontrol-origin: margin;
        }}
        
        /* Check Box */
        QCheckBox {{
            color: {foreground};
            spacing: 5px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: {border_radius}px;
            border: {border_width}px solid {border};
            background-color: {secondary_bg};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {primary};
            border: {border_width}px solid {primary};
        }}
        
        QCheckBox::indicator:unchecked:hover {{
            border: {border_width}px solid {primary};
        }}
        
        /* Radio Button */
        QRadioButton {{
            color: {foreground};
            spacing: 5px;
        }}
        
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: {border_width}px solid {border};
            background-color: {secondary_bg};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {primary};
            border: {border_width}px solid {primary};
        }}
        
        QRadioButton::indicator:unchecked:hover {{
            border: {border_width}px solid {primary};
        }}
        
        /* Tab Widget */
        QTabWidget::pane {{
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
            background-color: {background};
        }}
        
        QTabBar::tab {{
            background-color: {secondary_bg};
            color: {foreground};
            padding: {spacing_medium}px;
            border-top-left-radius: {border_radius}px;
            border-top-right-radius: {border_radius}px;
            margin-right: 2px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {primary};
            color: {background};
        }}
        
        QTabBar::tab:hover {{
            background-color: {border};
        }}
        
        /* Group Box */
        QGroupBox {{
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
            margin-top: 20px;
            padding-top: 10px;
            color: {foreground};
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
            color: {foreground};
            background-color: {background};
        }}
        
        /* Menu Bar */
        QMenuBar {{
            background-color: {background};
            color: {foreground};
        }}
        
        QMenuBar::item {{
            background-color: transparent;
            padding: {spacing_medium}px;
        }}
        
        QMenuBar::item:selected {{
            background-color: {secondary_bg};
            border-radius: {border_radius}px;
        }}
        
        QMenu {{
            background-color: {secondary_bg};
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
            color: {foreground};
        }}
        
        QMenu::item {{
            padding: {spacing_medium}px 30px {spacing_medium}px 20px;
        }}
        
        QMenu::item:selected {{
            background-color: {primary};
            color: {background};
        }}
        
        QMenu::separator {{
            height: 1px;
            background-color: {border};
            margin: 4px 0px;
        }}
        
        /* Status Bar */
        QStatusBar {{
            background-color: {background};
            color: {foreground};
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        
        /* Tool Tip */
        QToolTip {{
            background-color: {secondary_bg};
            border: {border_width}px solid {border};
            border-radius: {border_radius}px;
            color: {foreground};
            padding: {spacing_small}px;
        }}
        """
        
        return qss
    
    def list_themes(self) -> List[Dict[str, Any]]:
        """List all available themes.
        
        Returns:
            List of theme metadata (name, displayName, isDark)
        """
        themes = []
        
        for filename in os.listdir(self.config_dir):
            if filename.endswith(".json") and filename.startswith("theme"):
                try:
                    theme_path = os.path.join(self.config_dir, filename)
                    with open(theme_path, 'r') as f:
                        data = json.load(f)
                        
                    themes.append({
                        "name": data.get("name", os.path.splitext(filename)[0]),
                        "displayName": data.get("displayName", data.get("name", os.path.splitext(filename)[0])),
                        "isDark": data.get("isDark", True)
                    })
                except Exception:
                    # Skip invalid theme files
                    pass
        
        return themes
    
    def save_theme(self, theme_config: Dict[str, Any], theme_name: Optional[str] = None) -> bool:
        """Save a theme configuration to a JSON file.
        
        Args:
            theme_config: Theme configuration dictionary
            theme_name: Name to save the theme as (uses theme_config['name'] if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not theme_name and "name" not in theme_config:
            self.signals.error.emit("No theme name specified")
            return False
        
        name = theme_name or theme_config.get("name")
        theme_path = os.path.join(self.config_dir, f"{name}.json")
        
        try:
            with open(theme_path, 'w') as f:
                json.dump(theme_config, f, indent=2)
                
            return True
        except Exception as e:
            self.signals.error.emit(f"Error saving theme: {str(e)}")
            return False
