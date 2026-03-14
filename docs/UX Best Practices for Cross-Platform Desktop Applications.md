

# UI/UX Best Practices for Cross-Platform Desktop Applications

## Cross-Platform Consistency in Layout and Behavior

Designing for Linux, macOS, and Windows simultaneously means balancing a unified user experience with native platform conventions. A consistent core design helps users who switch between platforms, as they won’t be “dazzled” by a completely different interface on each system. However, respecting certain OS-specific behaviors is equally important for familiarity:

- **Layout & Navigation**
  Keep the overall layout structure and workflows consistent across platforms so users don’t have to relearn the app on each OS. For example, if your app uses a sidebar and top toolbar on Windows, do the same on macOS and Linux. Ensure common interface elements (navigation bars, panels, dialogs) appear in similar places and work the same way everywhere.

- **Menu and Controls**
  Account for platform differences in placement of system UI. On Windows the menu bar lives in the app window; on macOS it lives at the top of the screen. Qt’s `QMenuBar` will integrate with the macOS global menu bar for you. Use native dialogs (file pickers, color pickers, etc.) via Qt to get the appropriate look and feel on each OS.

- **Interactions & Shortcuts**
  Use consistent interaction patterns but swap in platform-standard conventions.

  - Copy/Paste: `Ctrl+C/V` on Windows/Linux, `⌘C/V` on macOS.

  - Use standard pointer behaviors (right-click for context menus, double-click to open, drag-and-drop).
    Small tweaks like using the proper scroll bar style or system default cursor go a long way to making the app feel “right.”

- **Window Management**
  Let the OS handle window chrome unless you have a compelling reason to customize it. Users expect the standard window controls (close, minimize, maximize) in the usual location. If you do use a custom title bar, implement drag-to-move, double-click to maximize, etc., to preserve expected behavior. Also remember window state: restore last window size/position and which screen it was on.

- **Preferences & Integration**
  Integrate with host OS conventions when possible. Follow the macOS style for Preferences (under the application menu), and on Windows use a standard Settings dialog layout. Support auto-start on login, system tray icons, etc., in a platform-appropriate way so your app feels native rather than “just ported.”

---

## Modern Visual Design Elements

Modern desktop applications benefit from clean, scalable design elements that adapt to different screen densities and user preferences. Key practices include using icon fonts, embracing dark/light modes, and designing resolution-independent UIs:

- **Icon Fonts and Scalable Graphics**
  Use vector icons (SVGs) or icon fonts (e.g. FontAwesome, Material Icons) instead of bitmaps. In Qt 6.9+ you can load an icon font and do:

  ```cpp
  QIcon icon = QIcon::fromTheme("icon_name");
  ```

  This guarantees crisp icons on high-DPI displays and lets you recolor or resize via font point size.

- **Adaptive Dark/Light Mode**
  Detect the system theme (e.g. via `QStyleHints::colorScheme` in Qt 6.5) and derive colors from the system palette (`QPalette` roles: `Window`, `Text`, `Highlight`). Test every custom UI element in both modes and provide alternate icons (white vs black) when needed.

- **Responsive Layout and High-DPI Support**
  Use Qt’s layout managers (`QHBoxLayout`, `QGridLayout`, etc.) so widgets expand/contract and reflow, rather than fixed pixels. Enable Qt’s high-DPI scaling (in Qt 6 it’s on by default). Provide vector or multi-scale pixmap assets using `QIcon.addFile()` or `QT_DEVICE_PIXEL_RATIO` so images stay sharp at 1×, 2×, etc.

---

## Typography and Spacing Across Platforms

Clear typography and consistent spacing are fundamental for readability and a polished look, especially in text-heavy or dense control interfaces:

- **System Fonts for Familiarity**
  Use the default UI fonts of each platform:

  - macOS: San Francisco

  - Windows: Segoe UI

  - Linux (GNOME): Inter / Ubuntu Sans
    Qt uses the system default unless overridden; leverage that.

- **Readable Font Sizes**
  Aim for ~11–12 pt (14–16px) body text. Avoid going below ~9 pt. Do not hard-code pixel sizes; let OS or Qt accessibility settings scale text if needed.

- **Consistent Spacing and Layout Grid**
  Follow an 8px (or 4px) grid for padding and margins. Group related controls with smaller gaps (e.g. 8px) and separate major sections with larger gaps (16px or 24px). Use Qt’s `QStyle::PM_Layout*Spacing` hints or layout properties to stick to platform defaults.

- **Padding and Touch Targets**
  Ensure click/touch targets are ≥40×40 px. Add interior padding inside buttons and space between icons so nothing feels cramped. Maintain consistent line heights for text elements.

---

## Visual Hierarchy and Clarity in Complex Workflows

Productivity and creative tools often have many panels and controls. To keep users oriented:

- **Divide the Workspace into Clear Sections**
  Delineate areas (e.g. sidebar, canvas, mixer) with borders, background shading or spacing. In OBS Studio, for instance, Scenes, Sources, Audio Mixer, etc., each live in their own panel.

- **Use Typography and Contrast for Hierarchy**

  - Section headers: larger font or heavier weight

  - Primary actions: filled/accent buttons

  - Secondary actions: neutral style
    Adhere to accessibility contrast ratios (WCAG AA).

- **Minimize Visual Clutter**
  Embrace flat design: simple icons, subtle accents, avoid excessive gradients. Show only what’s needed; let the content (document, canvas, video) take center stage.

- **Logical Grouping and Alignment**
  Group related controls and align them neatly (e.g. right-aligned labels with left-aligned fields in forms). Use extra whitespace around groups to visually associate items.

- **Iconography and Labels**
  In dense toolbars, combine icons with text labels or tooltips so users never have to guess. Stick to common metaphors (gear = settings, folder = open, trash = delete).

- **Highlight Focus and Selection**
  Visibly indicate the active panel, selected items, and keyboard focus (e.g. dotted outline). Qt handles focus painting by default—don’t override it away.

---

## Custom Widgets Without Breaking Native Look-and-Feel

When building unique controls in Qt/PySide6:

- **Follow Style Guidelines**
  Query colors and metrics from `QPalette` and `QStyle` so corner radii, border widths, shadows, etc., match native widgets.

- **Leverage `QStyle` and Style Hints**
  For a custom toggle switch, base its size on `QStyle::PM_IndicatorWidth` of a checkbox and use `QStyle::drawControl()` for groove/handle, then tint with your colors.

- **Respect Platform Conventions**
  Mimic expected behaviors (e.g. single-click select, double-click open on macOS; right-click doesn’t select on Windows). Consult Apple HIG and Microsoft Fluent for guidance.

- **Keyboard and Accessibility**
  Implement `keyPressEvent` so Space/Enter activates widgets. Set accessible names/descriptions for assistive tech. Use Qt’s model-view roles to expose data.

- **Test Across Platforms**
  Verify your custom widget on Linux, Windows and macOS, and under different themes (light/dark) and DPI settings. Handle `QEvent::StyleChange` or palette changes to redraw when the system theme toggles.

---

## Consistent Theming with Qt Style Systems

Qt offers multiple styling approaches:

- **Unified Cross-Platform Style**
  Use the **Fusion** style for a polished, brandable, platform-agnostic look:

  ```cpp
  QApplication::setStyle("Fusion");
  ```

  Customize via `QPalette` or QSS stylesheet to support light/dark variants.

- **Native Styles with Caution**
  The default native style on Windows (called “windowsvista”) doesn’t properly support dark mode. macOS native style does. Linux depends on the user’s Qt theme (e.g. Breeze, Adwaita).

- **Custom QStyle or QSS**
  For ultimate control, subclass `QStyle` or use QSS. If you do, build atop a stable base (Fusion) and test extensively: QSS can introduce quirks or performance issues.

- **Let Users Choose**
  Offer “Light,” “Dark,” “System” and (optionally) “Native” theme options. OBS Studio, for example, defaults to its custom dark theme but also offers a “System” mode.

- **Test and Refine**
  Check every widget—standard and custom—for hover effects, focus rects, default button styling, etc., and tweak accent colors (`QPalette::Highlight`) to match your brand.

---

## Responsiveness and High-DPI Considerations

To handle varying screen sizes, aspect ratios and pixel densities:

- **Fluid Resizing**
  Use layout managers and stretch factors so UI adapts when the window is narrow or ultra-wide. Allow collapsible panels or `QSplitter` for user-adjustable layouts.

- **High-DPI Support (“Retina”)**
  Qt 6+ handles DPI scaling, but you must supply vector assets or multi-scale pixmaps (using `QIcon.addFile()` or `QT_DEVICE_PIXEL_RATIO`). Test on 200% scaling (Windows VM or macOS).

- **Touch and Hybrid Input**
  Ensure touch devices (e.g. Surface) can interact—buttons ≥40×40 px help. Qt widgets receive touch as mouse events by default on Windows.

- **Performance on Resize**
  Avoid heavy custom drawing on every resize. Coalesce rapid resize events with a `QTimer` so you only redraw once the user stops dragging.

- **Test Multiple Environments**
  Font rendering differs: macOS often looks larger than Windows at the same point size. Linux users choose custom DPI/fonts. Test light/dark and DPI settings on all platforms.

---

## Examples of Modern Cross-Platform Apps and Design Inspiration

1. **Visual Studio Code**
   Electron-based, uniform on all OSes, uses icon fonts (Codicons), responsive panels, and respects native menu placement on macOS.

2. **Slack / Discord**
   Singular design language, dark/light themes, consistent typography and spacing, subtle accent highlights.

3. **Krita**
   Qt-based painting app, default dark theme, scalable UI, custom widgets that match the overall style.

4. **OBS Studio**
   Qt-based, custom dark theme by default, “System” theme option, dockable panels, clear grouping and labels.

5. **JetBrains IDEs**
   Custom Java UI, light/dark themes, excellent high-DPI support, subtle platform adjustments (font, title bar).

6. **Microsoft Office**
   Native Cocoa on Mac vs Win32 on Windows—but core structure (Ribbon, canvas, status bar) remains the same for familiarity.

---

## Conclusion

Designing a cross-platform desktop application with excellent UX is challenging but rewarding. By following these best practices in:

- Consistent layout & behavior

- Scalable visual elements & adaptive theming

- Thoughtful typography & spacing

- Strong visual hierarchy & clarity

- Seamless custom widgets

- Robust theming strategies

- Responsive, high-DPI-aware design

…you’ll create a Qt/PySide6 app that feels professional and intuitive on Linux, macOS and Windows alike. Great design is ultimately about empathy for the user—anticipate their needs and contexts, and deliver a smooth, unified experience everywhere.

---

### References

A selection of the guidelines and examples cited above:

- [Should a cross-platform desktop application use a uniform UI? (UX StackExchange)](https://ux.stackexchange.com/questions/125509/should-a-cross-platform-desktop-application-use-a-uniform-ui-and-design-language)

- [Designing desktop apps for cross-platform UX | ToDesktop Blog](https://www.todesktop.com/blog/posts/designing-desktop-apps-cross-platform-ux)

- [Qt for Python: QIcon Documentation](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QIcon.html)

- [Dark Mode on Windows 11 with Qt 6.5](https://www.qt.io/blog/dark-mode-on-windows-11-with-qt-6.5)

- [KDE Human Interface Guidelines: Layout & Navigation](https://develop.kde.org/hig/layout_and_nav/)

- [Qt 6 High-DPI Support](https://doc.qt.io/qt-6/highdpi.html)

- [GNOME Typography Guidelines](https://developer.gnome.org/hig/guidelines/typography.html)

- [Microsoft Fluent Spacing & Sizing](https://learn.microsoft.com/en-us/windows/apps/design/style/spacing)

Feel free to adjust link formatting or add/remove references as needed!
