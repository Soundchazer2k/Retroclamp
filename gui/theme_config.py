"""Theme configuration for RetroClamp.

This module provides theme configuration and styling for the application UI.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ThemeConfig:
    """Configuration for a UI theme."""
    
    name: str
    is_dark: bool = True
    primary_color: str = "#2a82da"
    secondary_color: str = "#1e6cb3"
    background_color: str = "#2d2d2d"
    text_color: str = "#ffffff"
    highlight_color: str = "#3a3a3a"
    disabled_color: str = "#666666"
    error_color: str = "#e74c3c"
    success_color: str = "#2ecc71"
    warning_color: str = "#f39c12"
    
    @property
    def to_dict(self) -> Dict[str, Any]:
        """Convert theme configuration to a dictionary."""
        return {
            "name": self.name,
            "is_dark": self.is_dark,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "highlight_color": self.highlight_color,
            "disabled_color": self.disabled_color,
            "error_color": self.error_color,
            "success_color": self.success_color,
            "warning_color": self.warning_color,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ThemeConfig':
        """Create a ThemeConfig from a dictionary."""
        return cls(**data)

# Default themes
DARK_THEME = ThemeConfig(
    name="dark",
    is_dark=True,
    primary_color="#2a82da",
    secondary_color="#1e6cb3",
    background_color="#2d2d2d",
    text_color="#ffffff",
    highlight_color="#3a3a3a",
    disabled_color="#666666",
    error_color="#e74c3c",
    success_color="#2ecc71",
    warning_color="#f39c12"
)

LIGHT_THEME = ThemeConfig(
    name="light",
    is_dark=False,
    primary_color="#2a82da",
    secondary_color="#1e6cb3",
    background_color="#f5f5f5",
    text_color="#333333",
    highlight_color="#e0e0e0",
    disabled_color="#b0b0b0",
    error_color="#e74c3c",
    success_color="#2ecc71",
    warning_color="#f39c12"
)

def get_theme(theme_name: str) -> ThemeConfig:
    """Get a theme by name.
    
    Args:
        theme_name: Name of the theme ('dark' or 'light')
        
    Returns:
        ThemeConfig: The requested theme configuration
        
    Raises:
        ValueError: If the theme name is invalid
    """
    theme_name = theme_name.lower()
    if theme_name == 'dark':
        return DARK_THEME
    elif theme_name == 'light':
        return LIGHT_THEME
    else:
        raise ValueError(f"Unknown theme: {theme_name}")
