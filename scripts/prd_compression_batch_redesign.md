# Product Requirements Document (PRD)
## RetroClamp Compression & Batch Tabs Redesign

---

## 1. Objective
Redesign the CompressionTab and BatchCompressionTab modules in RetroClamp for a modern, robust, and user-friendly experience, drawing inspiration from the PyDracula GUI style and adhering to best practices in GUI and logging design.

---

## 2. Scope
### Core Functionality
- **Compression/Decompression:** GUI for CHDMAN's createcd, createdvd, createhd, extract, info, and verify.
- **Archive Handling:** Automatic extraction of .zip, .7z, .rar before compression; optional re-archiving after decompression.
- **Batch Processing:** Recursive folder scanning, drag-and-drop, pause/resume, checkpoint persistence.
- **Logging:** Real-time, structured, color-coded logs (batch-style) with export/copy functionality.
- **Progress Feedback:** Per-file and overall progress bars, status text, and error/info dialogs.
- **Navigation:** QTabWidget for clear switching between Single File and Batch Processing.
- **Profile Management:** Support for compression profiles and hunk sizes.
- **Temporary Directory Management:** Automatic cleanup and low disk space alerts.

### Out of Scope
- Editing CHD file contents beyond metadata.
- Media playback/emulation.
- Online/network features (offline-first design).

---

## 3. User Experience & Visual Design
- **Inspiration:** Modern GUI PyDracula (https://github.com/Wanderson-Magalhaes/Modern_GUI_PyDracula_PySide6_or_PyQt6)
- **Consistency:** Uniform colors, icons, typography, and layouts across all tabs.
- **Simplicity:** Minimalist, progressive disclosure for advanced options.
- **Accessibility:** Contrast, font size, focus cues; QSS-based theming meeting WCAG-AA.
- **Navigation:** Familiar tabbed layout, matching the rest of the app.
- **Feedback:** Immediate, clear, real-time updates for all actions and errors.

---

## 4. Logging Philosophy
- Structured logs: timestamp, log level, message.
- Color-coded: info, warning, error.
- Real-time updates and batch-style formatting.
- Log panel is scrollable, copyable, and exportable.
- Consistent log format across single and batch tabs.

---

## 5. Architecture & Components
- **CompressionTab:** Handles single-file/archived compression.
- **BatchCompressionTab:** Handles batch workflows, folder scanning, pause/resume.
- **CHDManWrapper:** Class-based interface for all CHDMAN operations.
- **LogManager:** Structured, color-coded, exportable logs.
- **ProfileManager:** Compression profiles and hunk sizes.
- **UI Components:**
  - QTabWidget: Navigation
  - QTableWidget: File list (file, status, progress)
  - QProgressBar: Themed, per-file and overall
  - QTextEdit/QTableWidget: Log panel
  - QPushButton: Start, Pause, Cancel, Cleanup, Export Log
  - QFileDialog: File/folder selection
  - QMessageBox: Error/info popups

---

## 6. Implementation Roadmap
1. Project & UI Skeleton: Module/class skeletons, QTabWidget navigation, static UI.
2. Core Logic: File/archive selection, extraction, validation, CHDMan integration, progress/log updates, error handling.
3. Batch Processing: Recursive scanning, queueing, batch progress, pause/resume/cancel, checkpoint persistence.
4. Theming & Accessibility: Apply PyDracula QSS, accessibility testing.
5. Final Polish: Tooltips, onboarding, help, code/documentation updates.

---

## 7. References & Inspirations
- Modern GUI PyDracula (PySide6/PyQt6)
- 🎨 GUI DESIGN PRINCIPLES TUTORIAL.md
- AI Debug Logging Guidelines.md
- consolidated_retroclamp_prd.md
- fixescompresstab.md
- compression_profiles.md

---

## 8. Special Notes
- Ensure CompressionTab and BatchCompressionTab have a coherent, unified user experience.
- Match the design language and theming of the rest of RetroClamp.
- Prioritize user feedback, error clarity, and accessibility throughout.
- All logs and progress indicators must be real-time and actionable.
