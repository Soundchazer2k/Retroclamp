"""Layout utilities for consistent UI across RetroClamp.

Provides standardized layout patterns and form building functions
to ensure consistent spacing, alignment, and behavior.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class StandardFormLayout:
    """Utility class for creating consistent form layouts."""

    # Standard spacing constants
    FORM_SPACING = 8
    GROUP_SPACING = 12
    SECTION_SPACING = 16

    # Standard column widths
    LABEL_WIDTH = 140
    FIELD_MIN_WIDTH = 200
    FIELD_MAX_WIDTH = 400

    @staticmethod
    def create_form_group(
        title: str, parent_layout: QVBoxLayout | None = None
    ) -> tuple[QGroupBox, QFormLayout]:
        """Create a standardized form group with consistent styling.

        Args:
            title: Group box title
            parent_layout: Optional parent layout to add the group to

        Returns:
            Tuple of (group_box, form_layout)
        """
        group = QGroupBox(title)
        form_layout = QFormLayout(group)

        # Set consistent spacing and margins
        form_layout.setSpacing(StandardFormLayout.FORM_SPACING)
        form_layout.setContentsMargins(12, 16, 12, 12)

        # Set label/field column policies
        form_layout.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        # Set consistent column widths
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        if parent_layout:
            parent_layout.addWidget(group)

        return group, form_layout

    @staticmethod
    def add_form_field(form_layout: QFormLayout, label: str, widget: QWidget) -> None:
        """Add a field to a form layout with consistent sizing policies.

        Args:
            form_layout: The QFormLayout to add to
            label: Label text
            widget: Widget to add
        """
        # Set size policies for consistent behavior
        widget.setMinimumWidth(StandardFormLayout.FIELD_MIN_WIDTH)
        widget.setMaximumWidth(StandardFormLayout.FIELD_MAX_WIDTH)

        # For certain widget types, adjust sizing
        widget_type = type(widget).__name__
        if widget_type in ["QLineEdit", "QComboBox"]:
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        elif widget_type == "QSpinBox":
            widget.setMinimumWidth(100)
            widget.setMaximumWidth(150)
            widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        form_layout.addRow(label, widget)

    @staticmethod
    def create_button_bar(
        buttons: list[QPushButton], parent_layout: QVBoxLayout | None = None
    ) -> QHBoxLayout:
        """Create a standardized button bar with proper spacing.

        Args:
            buttons: List of buttons to add
            parent_layout: Optional parent layout to add the button bar to

        Returns:
            The button bar layout
        """
        button_layout = QHBoxLayout()

        # Add stretch to push buttons to the right
        button_layout.addStretch()

        # Add buttons with consistent spacing
        for i, button in enumerate(buttons):
            if i > 0:
                button_layout.addSpacing(8)
            button.setMinimumWidth(120)
            button.setMinimumHeight(32)
            button_layout.addWidget(button)

        if parent_layout:
            # Add spacing before button bar
            parent_layout.addSpacing(StandardFormLayout.SECTION_SPACING)
            parent_layout.addLayout(button_layout)

        return button_layout

    @staticmethod
    def create_main_layout(
        widget: QWidget,
        title: str | None = None,
        description: str | None = None,
    ) -> QVBoxLayout:
        """Create a standardized main layout for a tab/page.

        Args:
            widget: Widget to set the layout on
            title: Optional page title
            description: Optional page description

        Returns:
            The main VBoxLayout
        """
        from PySide6.QtWidgets import QLabel

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(StandardFormLayout.GROUP_SPACING)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("pageTitle")
            layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setObjectName("pageDescription")
            layout.addWidget(desc_label)

        return layout


class TableLayoutUtils:
    """Utilities for consistent table layouts."""

    @staticmethod
    def setup_table_headers(table_widget: QWidget, columns: dict[str, int]) -> None:
        """Set up table headers with proper sizing.

        Args:
            table_widget: QTableWidget instance
            columns: Dict of column_name: width_percentage
        """
        header = table_widget.horizontalHeader()  # type: ignore[attr-defined]

        # Set up each column
        total_percent = sum(columns.values())
        for i, (_name, percent) in enumerate(columns.items()):
            if i == len(columns) - 1:
                # Last column stretches to fill remaining space
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                # Other columns use fixed percentage
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                width = int((percent / total_percent) * 100)
                table_widget.setColumnWidth(i, width)  # type: ignore[attr-defined]

        # Prevent header truncation
        header.setStretchLastSection(True)
        table_widget.setAlternatingRowColors(True)  # type: ignore[attr-defined]


# Note: remove_conflicting_stylesheets function removed
# We're using unified global stylesheet instead of clearing individual widgets
