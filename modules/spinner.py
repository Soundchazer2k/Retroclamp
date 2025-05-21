#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Custom Spinner Widget for RetroClamp.

This module provides a custom waiting spinner widget for indicating busy states.
"""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget


class WaitingSpinner(QWidget):
    """Custom waiting spinner widget for RetroClamp.
    
    This widget displays an animated spinner to indicate that the application
    is busy processing a task.
    """
    
    def __init__(self, parent=None, centered=True, disable_parent_when_spinning=False):
        """Initialize the waiting spinner widget.
        
        Args:
            parent: Parent widget
            centered: Whether to center the spinner in the parent widget
            disable_parent_when_spinning: Whether to disable the parent widget when spinning
        """
        super().__init__(parent)
        
        # Initialize properties
        self._centered = centered
        self._disable_parent_when_spinning = disable_parent_when_spinning
        
        # Set up the spinner properties
        self._color = QColor(189, 147, 249)  # Default color: #bd93f9 (Dracula purple)
        self._roundness = 70.0
        self._minimum_trail_opacity = 15.0
        self._trail_fade_percentage = 70.0
        self._revolutions_per_second = 1.5
        self._number_of_lines = 12
        self._line_length = 10
        self._line_width = 3
        self._inner_radius = 10
        
        # Set up the timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.rotate)
        self._current_counter = 0
        self._is_spinning = False
        
        # Set up the widget
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Hide by default
        self.hide()
        
        # Set size policy
        self.setFixedSize(60, 60)
    
    def paintEvent(self, event):
        """Paint the spinner."""
        self.updatePosition()
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.transparent)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        if self._is_spinning:
            painter.setPen(Qt.NoPen)
            for i in range(self._number_of_lines):
                painter.save()
                painter.translate(self.width() / 2, self.height() / 2)
                rotate_angle = float(360 * i) / float(self._number_of_lines)
                painter.rotate(rotate_angle)
                painter.translate(self._inner_radius, 0)
                
                # Calculate distance and opacity for trail effect
                distance = self._current_counter - i
                if distance < 0:
                    distance += self._number_of_lines
                opacity = ((100.0 - self._trail_fade_percentage) / float(self._number_of_lines) * distance) + self._minimum_trail_opacity
                
                # Set the color with opacity
                color = QColor(self._color)
                color.setAlphaF(opacity / 100.0)
                
                # Draw the line
                pen = QPen(color)
                pen.setWidth(self._line_width)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawLine(0, 0, self._line_length, 0)
                painter.restore()
    
    def start(self):
        """Start the spinner animation."""
        self._is_spinning = True
        self.show()
        
        if self.parentWidget() and self._disable_parent_when_spinning:
            self.parentWidget().setEnabled(False)
        
        if not self._timer.isActive():
            self._timer.start(1000 / (self._number_of_lines * self._revolutions_per_second))
            self._current_counter = 0
    
    def stop(self):
        """Stop the spinner animation."""
        self._is_spinning = False
        self.hide()
        
        if self.parentWidget() and self._disable_parent_when_spinning:
            self.parentWidget().setEnabled(True)
        
        if self._timer.isActive():
            self._timer.stop()
    
    def rotate(self):
        """Rotate the spinner by one step."""
        self._current_counter += 1
        if self._current_counter >= self._number_of_lines:
            self._current_counter = 0
        self.update()
    
    def updatePosition(self):
        """Update the position of the spinner."""
        if self.parentWidget() and self._centered:
            rect = self.parentWidget().rect()
            self.move(
                rect.center().x() - self.width() / 2,
                rect.center().y() - self.height() / 2
            )
    
    def setColor(self, color):
        """Set the color of the spinner.
        
        Args:
            color: QColor object or color name string
        """
        self._color = QColor(color)
    
    def setRoundness(self, roundness):
        """Set the roundness of the spinner lines.
        
        Args:
            roundness: Roundness value (0-100)
        """
        self._roundness = min(max(0.0, roundness), 100.0)
    
    def setRevolutionsPerSecond(self, revolutions_per_second):
        """Set the revolutions per second of the spinner.
        
        Args:
            revolutions_per_second: Number of revolutions per second
        """
        self._revolutions_per_second = revolutions_per_second
        if self._is_spinning:
            self._timer.setInterval(1000 / (self._number_of_lines * self._revolutions_per_second))
    
    def setNumberOfLines(self, lines):
        """Set the number of lines in the spinner.
        
        Args:
            lines: Number of lines
        """
        self._number_of_lines = lines
        if self._is_spinning:
            self._timer.setInterval(1000 / (self._number_of_lines * self._revolutions_per_second))
    
    def setLineLength(self, length):
        """Set the length of the spinner lines.
        
        Args:
            length: Line length in pixels
        """
        self._line_length = length
    
    def setLineWidth(self, width):
        """Set the width of the spinner lines.
        
        Args:
            width: Line width in pixels
        """
        self._line_width = width
    
    def setInnerRadius(self, radius):
        """Set the inner radius of the spinner.
        
        Args:
            radius: Inner radius in pixels
        """
        self._inner_radius = radius
    
    def setMinimumTrailOpacity(self, opacity):
        """Set the minimum opacity of the trailing lines.
        
        Args:
            opacity: Minimum opacity (0-100)
        """
        self._minimum_trail_opacity = opacity
