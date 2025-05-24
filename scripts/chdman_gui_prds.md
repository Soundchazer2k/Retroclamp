# CHDMAN GUI Enhancement PRDs

## Phase 1: Foundation + Quick Wins

---

## PRD-001: Debug Logging System
**Priority:** Foundation | **Difficulty:** Low | **Estimated Time:** 2-4 hours

### Overview
Implement a comprehensive debug logging system to aid development and user troubleshooting.

### Requirements

#### Functional Requirements
1. **Debug Mode Toggle**
   - Add checkbox in Advanced tab: "Enable debug logging"
   - Setting key: `debug_logging_enabled` (boolean, default: False)
   - Apply immediately when toggled (no restart required)

2. **Log File Management**
   - Log file location: `{app_data_dir}/chdman_gui_debug.log`
   - Maximum file size: 10MB
   - When limit reached: rename to `.old`, start new file
   - Automatic cleanup: keep only current + 1 backup file

3. **Debug Information Capture**
   - All CHDMAN command executions (full command line)
   - Process start/end times and exit codes
   - File operations (source/destination paths, file sizes)
   - Error messages and stack traces
   - User actions (button clicks, setting changes)
   - System information on first run per session

4. **Log Format**
   ```
   [YYYY-MM-DD HH:MM:SS.mmm] [LEVEL] [MODULE] Message
   ```
   - Levels: DEBUG, INFO, WARNING, ERROR
   - Modules: MAIN, CHDMAN, SETTINGS, UI, FILE_OPS

#### Technical Implementation
1. **Logger Class** (`debug_logger.py`)
   ```python
   class DebugLogger:
       def __init__(self, log_file_path, max_size_mb=10):
           # Initialize rotating file handler

       def debug(self, module, message):
       def info(self, module, message):
       def warning(self, module, message):
       def error(self, module, message):

       def log_system_info(self):
           # Platform, Python version, Qt version, available memory

       def log_chdman_execution(self, command, working_dir, exit_code, duration):

       def is_enabled(self):
           # Check app_settings for debug_logging_enabled
   ```

2. **Integration Points**
   - Import logger in main application file
   - Add logging calls to CHDManWorker class
   - Add logging to file operations
   - Add logging to settings save/load

3. **UI Changes**
   - Add to Advanced tab (create if doesn't exist)
   - Checkbox with label "Enable debug logging"
   - Info label: "Logs saved to: {log_file_path}"
   - Button: "Open Log Folder"

#### Acceptance Criteria
- [ ] Debug logging can be enabled/disabled via UI
- [ ] Setting persists across application restarts
- [ ] Log file is created only when logging is enabled
- [ ] Log rotation works correctly at 10MB limit
- [ ] All specified events are logged with correct format
- [ ] No performance impact when logging is disabled
- [ ] "Open Log Folder" button works on all platforms

---

## PRD-002: Settings Import/Export
**Priority:** Foundation | **Difficulty:** Low-Medium | **Estimated Time:** 3-5 hours

### Overview
Allow users to backup, restore, and share their application settings.

### Requirements

#### Functional Requirements
1. **Export Settings**
   - Export all settings from `app_settings.py` to JSON file
   - Default filename: `chdman_gui_settings_YYYY-MM-DD.json`
   - File dialog starts in user's Documents folder
   - Include metadata: export date, app version, setting count

2. **Import Settings**
   - Import settings from JSON file
   - Validate file structure before applying
   - Show confirmation dialog with changes summary
   - Backup current settings before import
   - Option to selectively import sections

3. **Settings Validation**
   - Verify JSON structure matches expected format
   - Validate data types for each setting
   - Check for required vs optional settings
   - Handle version compatibility (ignore unknown settings)

#### UI Implementation
1. **Menu Location**
   - Add "Settings" menu to menu bar (if not exists)
   - Menu items:
     - "Export Settings..." (Ctrl+E)
     - "Import Settings..." (Ctrl+I)
     - Separator
     - "Reset All Settings..." (with confirmation)

2. **Export Dialog**
   - QFileDialog for save location
   - Filter: "JSON files (*.json)"
   - Success message: "Settings exported successfully to {filepath}"

3. **Import Dialog**
   - QFileDialog for file selection
   - Preview dialog showing:
     - Source file info (date, version)
     - Settings that will change (current → new values)
     - Checkboxes for selective import by category
   - Confirmation: "Import X settings? Current settings will be backed up."

4. **Reset Confirmation**
   - Warning dialog: "Reset all settings to defaults? This cannot be undone."
   - "Reset" and "Cancel" buttons

#### Technical Implementation
1. **Settings Manager Class** (`settings_manager.py`)
   ```python
   class SettingsManager:
       def export_settings(self, filepath):
           # Read all from app_settings, add metadata, save as JSON

       def import_settings(self, filepath, selected_categories=None):
           # Validate, backup current, apply new settings

       def validate_settings_file(self, filepath):
           # Return (valid, errors, preview_data)

       def backup_current_settings(self):
           # Create backup with timestamp

       def reset_to_defaults(self):
           # Clear all settings, reload defaults

       def get_settings_preview(self, import_data):
           # Compare current vs import, return changes
   ```

2. **JSON Structure**
   ```json
   {
     "metadata": {
       "export_date": "2025-05-24T10:30:00Z",
       "app_version": "1.0.0",
       "settings_count": 15
     },
     "settings": {
       "general": {
         "confirm_exit": true,
         "window_geometry": "..."
       },
       "chdman": {
         "default_path": "/usr/bin/chdman"
       }
     }
   }
   ```

#### Acceptance Criteria
- [ ] Export creates valid JSON file with all current settings
- [ ] Import validates file structure and shows preview
- [ ] Selective import works by category
- [ ] Current settings are backed up before import
- [ ] Invalid files show appropriate error messages
- [ ] Reset function clears all settings and restores defaults
- [ ] All operations show appropriate success/error messages

---

## PRD-003: Window Position and Size Memory
**Priority:** Foundation | **Difficulty:** Low | **Estimated Time:** 2-3 hours

### Overview
Automatically save and restore the main window's position and size between application sessions.

### Requirements

#### Functional Requirements
1. **Save Window State**
   - Capture window geometry (x, y, width, height)
   - Capture window state (normal, maximized, minimized)
   - Save on window close or geometry change (with debouncing)
   - Handle multi-monitor setups gracefully

2. **Restore Window State**
   - Apply saved geometry on application startup
   - Validate geometry is within available screen bounds
   - Fall back to default size/position if saved state is invalid
   - Respect maximized state

3. **Settings Storage**
   - Setting keys in `app_settings.py`:
     - `window_geometry` (string): "x,y,width,height"
     - `window_maximized` (boolean): True if maximized
     - `remember_window_position` (boolean): Enable/disable feature

#### Technical Implementation
1. **Window State Manager**
   ```python
   class WindowStateManager:
       def __init__(self, main_window, settings_module):
           self.window = main_window
           self.settings = settings_module
           self.save_timer = QTimer()  # For debouncing

       def save_window_state(self):
           # Save geometry and maximized state

       def restore_window_state(self):
           # Apply saved state, validate screen bounds

       def is_geometry_valid(self, geometry):
           # Check if geometry fits within available screens

       def get_default_geometry(self):
           # Return sensible default size and center position
   ```

2. **Integration with Main Window**
   - Connect to `resizeEvent` and `moveEvent` (with debouncing)
   - Save state in `closeEvent`
   - Restore state after window creation but before show

3. **Settings UI** (Optional Toggle)
   - Add to General tab: "Remember window position and size"
   - Setting key: `remember_window_position` (default: True)

#### Multi-Monitor Handling
1. **Screen Validation**
   - Check if saved position is within any available screen
   - If outside all screens, center on primary screen
   - Handle screen resolution/configuration changes

2. **Edge Cases**
   - Minimized state: restore to normal, then apply geometry
   - Invalid geometry: use default centered position
   - Screen disconnected: move to primary screen

#### Acceptance Criteria
- [ ] Window size and position are saved when changed
- [ ] Window state is restored correctly on next startup
- [ ] Maximized state is preserved across sessions
- [ ] Invalid positions fall back to default gracefully
- [ ] Works correctly with multiple monitors
- [ ] Debouncing prevents excessive saving during resize/move
- [ ] Feature can be disabled via settings

---

## PRD-004: Exit Confirmation Dialog
**Priority:** Quick Win | **Difficulty:** Low | **Estimated Time:** 1-2 hours

### Overview
Show a confirmation dialog when user attempts to close the application to prevent accidental closure.

### Requirements

#### Functional Requirements
1. **Confirmation Dialog**
   - Triggered on main window close event
   - Dialog title: "Confirm Exit"
   - Message: "Are you sure you want to exit CHDMAN GUI?"
   - Buttons: "Exit" and "Cancel"
   - Default focus on "Cancel" button

2. **Smart Behavior**
   - Only show if CHDMAN operations are running
   - OR if setting is enabled AND no operations running
   - Remember "Don't ask again" choice per session

3. **Settings Integration**
   - Setting key: `confirm_exit_dialog` (boolean, default: True)
   - UI toggle in General tab

#### Technical Implementation
1. **Override closeEvent**
   ```python
   def closeEvent(self, event):
       if self.should_show_exit_confirmation():
           dialog = ExitConfirmationDialog(self)
           if dialog.exec_() == QDialog.Accepted:
               event.accept()
           else:
               event.ignore()
       else:
           event.accept()
   ```

2. **Confirmation Logic**
   ```python
   def should_show_exit_confirmation(self):
       # Check if operations are running
       if self.chdman_worker and self.chdman_worker.isRunning():
           return True

       # Check user setting
       return app_settings.get('confirm_exit_dialog', True)
   ```

3. **Dialog Implementation**
   ```python
   class ExitConfirmationDialog(QDialog):
       def __init__(self, parent=None):
           # Standard dialog with custom message
           # "Don't ask again" checkbox (session only)
   ```

#### Special Cases
1. **Operations Running**
   - Different message: "CHDMAN operations are running. Exit anyway?"
   - Warning icon
   - More prominent "Cancel" button

2. **Force Close**
   - Handle system shutdown requests
   - Alt+F4, Cmd+Q keyboard shortcuts
   - Task manager kills (no confirmation possible)

#### Acceptance Criteria
- [ ] Dialog appears when closing application (if enabled)
- [ ] Dialog prevents closure when "Cancel" is clicked
- [ ] Dialog allows closure when "Exit" is clicked
- [ ] Special handling when operations are running
- [ ] Setting toggle works correctly
- [ ] "Don't ask again" works for current session
- [ ] Handles keyboard shortcuts and system close requests

---

## PRD-005: Recent Files Limit
**Priority:** Quick Win | **Difficulty:** Low | **Estimated Time:** 1-2 hours

### Overview
Allow users to configure the maximum number of recent files displayed in the File menu.

### Requirements

#### Functional Requirements
1. **Configurable Limit**
   - Setting key: `max_recent_files` (integer, default: 10)
   - Range: 1-50 files
   - UI: Spin box in General tab

2. **Recent Files Management**
   - Maintain list of recently opened files
   - Remove excess files when limit is reduced
   - Update menu immediately when setting changes

3. **File List Behavior**
   - Most recent files at top
   - Remove duplicates (move to top if re-opened)
   - Remove non-existent files on access attempt
   - Clear all option in menu

#### Technical Implementation
1. **Recent Files Manager**
   ```python
   class RecentFilesManager:
       def __init__(self, settings_module, max_files=10):
           self.settings = settings_module
           self.max_files = max_files

       def add_file(self, filepath):
           # Add to top, remove duplicates, enforce limit

       def get_files(self):
           # Return list of valid files

       def clear_all(self):
           # Clear the list

       def set_max_files(self, count):
           # Update limit and trim list if needed
   ```

2. **Settings Integration**
   - Load max_files from settings on startup
   - Update RecentFilesManager when setting changes
   - Immediate UI update (no restart required)

3. **UI Components**
   - General tab: "Maximum recent files: [spinbox] (1-50)"
   - File menu: "Recent Files" submenu
   - Menu items: File paths with keyboard shortcuts (1-9)
   - Separator and "Clear Recent Files" at bottom

#### Menu Structure
```
File
├── Open...
├── Recent Files →  ├── /path/to/file1.chd    Ctrl+1
│                   ├── /path/to/file2.chd    Ctrl+2
│                   ├── ...
│                   ├── ──────────────────
│                   └── Clear Recent Files
```

#### Acceptance Criteria
- [ ] Setting is configurable via spin box (1-50 range)
- [ ] Recent files list updates immediately when limit changes
- [ ] Menu shows correct number of recent files
- [ ] Files are ordered by most recent first
- [ ] Duplicate files are handled correctly
- [ ] Non-existent files are removed from list
- [ ] "Clear Recent Files" empties the list
- [ ] Keyboard shortcuts work (Ctrl+1-9)

---

## PRD-006: Progress Update Frequency
**Priority:** Quick Win | **Difficulty:** Low | **Estimated Time:** 1-2 hours

### Overview
Allow users to configure how frequently the progress bar and status updates are refreshed during CHDMAN operations.

### Requirements

#### Functional Requirements
1. **Configurable Frequency**
   - Setting key: `progress_update_frequency` (integer, milliseconds)
   - Default: 500ms (2 updates per second)
   - Range: 100ms to 2000ms
   - UI: Slider or spin box in Performance tab

2. **Update Behavior**
   - Controls QTimer interval for progress polling
   - Affects both progress bar and status text updates
   - Balance between responsiveness and CPU usage
   - Apply immediately when changed

#### Technical Implementation
1. **Progress Timer Management**
   ```python
   class ProgressUpdater:
       def __init__(self):
           self.timer = QTimer()
           self.timer.timeout.connect(self.update_progress)
           self.update_frequency = 500  # Default 500ms

       def set_update_frequency(self, milliseconds):
           self.update_frequency = milliseconds
           if self.timer.isActive():
               self.timer.setInterval(milliseconds)

       def start_updates(self):
           self.timer.start(self.update_frequency)

       def stop_updates(self):
           self.timer.stop()
   ```

2. **Settings Integration**
   - Load frequency from settings on startup
   - Update timer interval when setting changes
   - No restart required for changes

3. **UI Implementation**
   - Performance tab: "Progress update frequency"
   - Slider: 100ms to 2000ms with labeled ticks
   - Current value display: "Update every 500ms"
   - Helper text: "Lower values = more responsive, higher CPU usage"

#### Performance Considerations
1. **CPU Impact**
   - More frequent updates = higher CPU usage
   - Especially important for slower systems
   - Provide reasonable defaults and guidance

2. **Visual Smoothness**
   - Balance smooth progress vs performance
   - 500ms default provides good balance
   - Power users can adjust based on preference

#### Acceptance Criteria
- [ ] Setting is configurable with appropriate range
- [ ] Progress updates use the configured frequency
- [ ] Changes apply immediately without restart
- [ ] UI provides clear indication of current value
- [ ] Performance impact is documented in UI
- [ ] Default value provides good balance

---

## PRD-007: Completion/Error Sound Notifications
**Priority:** Quick Win | **Difficulty:** Low | **Estimated Time:** 2-3 hours

### Overview
Play audio notifications when CHDMAN operations complete successfully or encounter errors.

### Requirements

#### Functional Requirements
1. **Sound Settings**
   - Setting keys:
     - `play_completion_sound` (boolean, default: False)
     - `play_error_sound` (boolean, default: False)
     - `notification_volume` (integer, 0-100, default: 50)

2. **Sound Events**
   - **Completion**: Successful CHDMAN operation finish
   - **Error**: CHDMAN operation fails or crashes
   - **Volume Control**: User-configurable volume level
   - **Sound Selection**: Use system default sounds or custom files

3. **Sound Sources**
   - System default notification sounds (preferred)
   - Fallback to built-in Qt sounds
   - Optional: Custom sound file selection

#### Technical Implementation
1. **Sound Manager**
   ```python
   class SoundNotificationManager:
       def __init__(self):
           self.completion_enabled = False
           self.error_enabled = False
           self.volume = 50

       def play_completion_sound(self):
           if self.completion_enabled:
               self._play_system_sound('completion')

       def play_error_sound(self):
           if self.error_enabled:
               self._play_system_sound('error')

       def _play_system_sound(self, sound_type):
           # Use QSound or platform-specific APIs

       def set_volume(self, volume):
           # 0-100 scale
   ```

2. **Integration Points**
   - Connect to CHDMAN operation completion signals
   - Connect to error/exception handlers
   - Integrate with existing worker thread callbacks

3. **UI Implementation**
   - General tab section: "Sound Notifications"
   - Checkboxes: "Play sound on completion" and "Play sound on error"
   - Volume slider: 0-100 with mute icon at 0
   - Test buttons to preview sounds

#### Platform Considerations
1. **Cross-Platform Sounds**
   - Windows: Use system notification sounds
   - macOS: Use NSSound for system sounds
   - Linux: Use system notification daemon or Qt fallback

2. **Fallback Strategy**
   - Primary: System notification sounds
   - Secondary: Qt built-in sounds (QSound)
   - Tertiary: Disable gracefully if no audio available

#### UI Layout
```
Sound Notifications
├── □ Play sound on completion
├── □ Play sound on error
├── Volume: [────●──────] 50%
└── [Test Completion] [Test Error]
```

#### Acceptance Criteria
- [ ] Completion sound plays when operations finish successfully
- [ ] Error sound plays when operations fail
- [ ] Volume control affects notification volume
- [ ] Settings persist across application restarts
- [ ] Test buttons allow previewing sounds
- [ ] Works on Windows, macOS, and Linux
- [ ] Graceful fallback when audio is unavailable
- [ ] No sound plays when checkboxes are disabled

---

## PRD-008: Open Output Folder After Compression
**Priority:** Quick Win | **Difficulty:** Low | **Estimated Time:** 1-2 hours

### Overview
Automatically open the output folder in the system file manager after successful CHDMAN operations.

### Requirements

#### Functional Requirements
1. **Auto-Open Setting**
   - Setting key: `open_output_folder` (boolean, default: False)
   - UI toggle in General tab: "Open output folder after compression"
   - Only trigger on successful operations (not errors)

2. **Folder Opening Behavior**
   - Open containing folder of output file
   - Select/highlight the created file if possible
   - Handle multiple output files (open folder of first file)
   - Use system default file manager

3. **Cross-Platform Support**
   - Windows: Explorer with file selection
   - macOS: Finder with file selection
   - Linux: Default file manager (nautilus, dolphin, etc.)

#### Technical Implementation
1. **File Manager Integration**
   ```python
   class FileManagerUtils:
       @staticmethod
       def open_folder_and_select_file(filepath):
           """Open file manager and select the specified file"""
           import subprocess
           import os
           import platform

           if platform.system() == "Windows":
               subprocess.run(['explorer', '/select,', filepath])
           elif platform.system() == "Darwin":  # macOS
               subprocess.run(['open', '-R', filepath])
           else:  # Linux
               # Try common file managers
               folder = os.path.dirname(filepath)
               try:
                   subprocess.run(['xdg-open', folder])
               except:
                   # Fallback options

       @staticmethod
       def open_folder(folder_path):
           """Open folder without file selection"""
           # Similar cross-platform implementation
   ```

2. **Integration with CHDMAN Operations**
   - Connect to successful completion signal
   - Extract output file path from operation results
   - Call file manager function if setting is enabled

3. **UI Implementation**
   - General tab checkbox: "Open output folder after compression"
   - Tooltip: "Automatically opens the file manager after successful operations"

#### Edge Cases
1. **Multiple Files**
   - Batch operations creating multiple files
   - Open folder containing the first successful file
   - Or open common parent folder if files in different locations

2. **Permission Issues**
   - Handle cases where file manager can't be opened
   - Show error message or fail silently based on severity

3. **File Manager Not Available**
   - Graceful degradation if system has no file manager
   - Log warning in debug mode

#### Acceptance Criteria
- [ ] Folder opens automatically after successful operations
- [ ] Setting can be enabled/disabled via UI
- [ ] Works on Windows, macOS, and Linux
- [ ] Handles multiple output files appropriately
- [ ] No action taken on failed operations
- [ ] Graceful handling of permission or system issues
- [ ] File is selected/highlighted when possible

---

## PRD-008.5: Basic Operation Cancellation
**Priority:** Foundation Bridge | **Difficulty:** Low-Medium | **Estimated Time:** 2-3 hours

### Overview
Provide users with the ability to safely cancel running CHDMAN operations, offering a safety net for long-running or mistakenly initiated processes.

### Requirements

#### Functional Requirements
1. **Cancel Button**
   - Prominent "Cancel" button that replaces "Start" during operations
   - Button state changes: "Start" → "Cancel" → "Cancelling..." → "Start"
   - Keyboard shortcut: Escape key to cancel current operation

2. **Process Termination**
   - Graceful termination of CHDMAN subprocess
   - Send SIGTERM first, then SIGKILL if process doesn't respond within 5 seconds
   - Clean up any temporary files created during the operation
   - Reset progress indicators and status displays

3. **User Feedback**
   - Status message: "Operation cancelled by user"
   - Progress bar resets to 0%
   - Estimated time remaining clears
   - Log entry indicating cancellation

4. **Batch Operation Handling**
   - For batch operations: cancel current file and stop queue
   - Show summary: "Cancelled after processing X of Y files"
   - Option to resume from where cancellation occurred (if checkpointing is implemented)

#### Technical Implementation
1. **Cancellation Manager**
   ```python
   class OperationCancellationManager:
       def __init__(self):
           self.current_process = None
           self.is_cancelling = False
           self.cancel_requested = False

       def start_operation(self, process):
           """Register a process for potential cancellation."""
           self.current_process = process
           self.cancel_requested = False
           self.is_cancelling = False

       def request_cancellation(self):
           """Request cancellation of current operation."""
           if not self.current_process or self.is_cancelling:
               return False

           self.cancel_requested = True
           self.is_cancelling = True
           return True

       def execute_cancellation(self):
           """Actually terminate the process."""
           if not self.current_process:
               return

           try:
               # Try graceful termination first
               self.current_process.terminate()

               # Wait up to 5 seconds for graceful shutdown
               try:
                   self.current_process.wait(timeout=5)
               except subprocess.TimeoutExpired:
                   # Force kill if graceful termination failed
                   self.current_process.kill()
                   self.current_process.wait()

               self.cleanup_after_cancellation()

           except Exception as e:
               self.logger.error(f"Error during cancellation: {e}")
           finally:
               self.reset_state()

       def cleanup_after_cancellation(self):
           """Clean up temporary files and reset state."""
           # Remove any partial output files
           # Clean up temporary extraction folders
           # Reset progress tracking

       def reset_state(self):
           """Reset cancellation manager state."""
           self.current_process = None
           self.is_cancelling = False
           self.cancel_requested = False
   ```

2. **UI Integration**
   ```python
   class OperationControlWidget:
       def __init__(self):
           self.start_button = QPushButton("Start")
           self.cancel_manager = OperationCancellationManager()
           self.setup_ui()

       def setup_ui(self):
           # Connect button to start/cancel handler
           self.start_button.clicked.connect(self.handle_button_click)

           # Connect Escape key to cancellation
           self.cancel_shortcut = QShortcut(QKeySequence.Cancel, self)
           self.cancel_shortcut.activated.connect(self.request_cancellation)

       def handle_button_click(self):
           if self.start_button.text() == "Start":
               self.start_operation()
           elif self.start_button.text() == "Cancel":
               self.request_cancellation()

       def start_operation(self):
           # Start CHDMAN operation
           process = self.launch_chdman_process()
           self.cancel_manager.start_operation(process)

           # Update UI
           self.start_button.setText("Cancel")
           self.start_button.setIcon(self.load_icon("stop"))

       def request_cancellation(self):
           if self.cancel_manager.request_cancellation():
               self.start_button.setText("Cancelling...")
               self.start_button.setEnabled(False)

               # Execute cancellation in background thread
               cancel_thread = CancellationThread(self.cancel_manager)
               cancel_thread.finished.connect(self.on_cancellation_complete)
               cancel_thread.start()

       def on_cancellation_complete(self):
           # Reset UI to initial state
           self.start_button.setText("Start")
           self.start_button.setIcon(self.load_icon("play"))
           self.start_button.setEnabled(True)

           # Update status and progress
           self.update_status("Operation cancelled by user")
           self.reset_progress_indicators()
   ```

3. **Integration with Existing Worker Thread**
   - Modify CHDManWorker to check for cancellation requests
   - Add cancellation checkpoints in long-running operations
   - Emit cancellation signals to update UI appropriately

#### Cancellation Safety
1. **File System Safety**
   - Never leave partially written CHD files
   - Remove incomplete output files on cancellation
   - Preserve original input files
   - Clean up extracted temporary files

2. **Process Safety**
   - Always attempt graceful termination first
   - Use appropriate timeouts before force-killing
   - Handle subprocess cleanup properly
   - Log cancellation events for debugging

3. **Batch Operation Safety**
   - Complete current file before stopping (if nearly finished)
   - OR stop immediately and clean up current file
   - Preserve completed files from batch
   - Provide clear feedback on what was accomplished

#### UI Behavior
1. **Button States**
   ```
   [Start] → Click → [Cancel] → Click → [Cancelling...] → Complete → [Start]
   ```

2. **Progress Indicators**
   - Progress bar: Pause animation, then reset to 0%
   - Status text: "Operation cancelled by user"
   - Time remaining: Clear/hide
   - File counter (batch): "Stopped after X of Y files"

3. **Keyboard Shortcuts**
   - Escape: Cancel current operation
   - Space: Start/Stop operation (alternative)

#### Edge Cases
1. **Rapid Cancellation Requests**
   - Ignore subsequent cancel requests while cancelling
   - Prevent UI spam-clicking issues

2. **Process Already Finished**
   - Handle race condition where process completes during cancellation
   - Show appropriate completion message instead of cancellation

3. **Cancellation During Cleanup**
   - Allow cleanup operations to complete
   - Don't allow re-cancellation during cleanup phase

#### Acceptance Criteria
- [ ] Cancel button appears and functions during operations
- [ ] Escape key cancels current operation
- [ ] Process terminates gracefully within 5 seconds
- [ ] Force-kill works if graceful termination fails
- [ ] Partial/temporary files are cleaned up after cancellation
- [ ] UI resets to initial state after cancellation
- [ ] Status message clearly indicates user cancellation
- [ ] Batch operations stop cleanly with progress summary
- [ ] Rapid clicking or multiple cancel requests handled gracefully
- [ ] Cancellation works for all supported CHDMAN operations

---

## Phase 2: High-Impact Medium Difficulty Features

---

## PRD-009: System Tray Integration
**Priority:** High Impact | **Difficulty:** Medium | **Estimated Time:** 4-6 hours

### Overview
Minimize the application to the system tray instead of taskbar, with tray icon menu and notifications.

### Requirements

#### Functional Requirements
1. **Tray Icon**
   - Application icon in system tray
   - Tooltip shows current status
   - Right-click context menu
   - Double-click to restore window

2. **Minimize Behavior**
   - Setting: `minimize_to_tray` (boolean, default: False)
   - When enabled, minimize goes to tray instead of taskbar
   - Close button can also minimize to tray (separate setting)

3. **Tray Context Menu**
   - "Show/Hide Window" (toggle)
   - "Current Operation: [status]" (disabled, info only)
   - Separator
   - "Pause/Resume" (if operation running)
   - "Cancel Operation" (if operation running)
   - Separator
   - "Exit"

4. **Window Management**
   - Restore from tray to previous position
   - Restore when clicking notification
   - Handle multiple monitor scenarios

#### Technical Implementation
1. **System Tray Manager**
   ```python
   class SystemTrayManager:
       def __init__(self, main_window):
           self.main_window = main_window
           self.tray_icon = QSystemTrayIcon()
           self.setup_tray_icon()
           self.setup_context_menu()

       def setup_tray_icon(self):
           # Set icon, tooltip, connect signals

       def setup_context_menu(self):
           # Create context menu with actions

       def show_window(self):
           # Restore and activate main window

       def hide_to_tray(self):
           # Hide window, show tray message if first time

       def update_status(self, status_text):
           # Update tooltip and menu items
   ```

2. **Integration with Main Window**
   - Override `changeEvent` to detect minimize
   - Modify close behavior based on settings
   - Connect operation status updates to tray manager

3. **Settings UI**
   - General tab options:
     - "Minimize to system tray"
     - "Close to system tray instead of exit"
   - Show warning if system tray not available

#### Tray Notifications
1. **Operation Status**
   - Show balloon notification on completion/error
   - Update tray tooltip with current operation
   - Different icon states (idle, working, error)

2. **First-Time Usage**
   - Show balloon: "Application minimized to tray" on first minimize
   - Explain how to restore window

#### Platform Considerations
1. **System Tray Availability**
   - Check `QSystemTrayIcon.isSystemTrayAvailable()`
   - Graceful fallback if not available
   - Different behavior on different desktop environments

2. **Icon States**
   - Normal: Default application icon
   - Working: Animated or different color
   - Error: Red indicator or warning overlay

#### Acceptance Criteria
- [ ] Tray icon appears when tray integration is enabled
- [ ] Right-click menu shows appropriate options
- [ ] Double-click restores window correctly
- [ ] Window minimizes to tray when setting is enabled
- [ ] Context menu updates based on operation status
- [ ] Balloon notifications work for operations
- [ ] Graceful handling when system tray unavailable
- [ ] Works across different operating systems

---

## PRD-010: Desktop Notifications
**Priority:** High Impact | **Difficulty:** Medium | **Estimated Time:** 3-5 hours

### Overview
Show native desktop notifications for operation completion, errors, and important events.

### Requirements

#### Functional Requirements
1. **Notification Types**
   - **Completion**: "Operation completed successfully"
   - **Error**: "Operation failed: [error message]"
   - **Warning**: "Operation completed with warnings"
   - **Information**: General status updates

2. **Notification Settings**
   - Setting keys:
     - `show_desktop_notifications` (boolean, default: True)
     - `notification_duration` (integer, seconds, default: 5)
     - `notify_on_completion` (boolean, default: True)
     - `notify_on_error` (boolean, default: True)
     - `notify_when_minimized_only` (boolean, default: False)

3. **Notification Content**
   - Title: "CHDMAN GUI"
   - Message: Status-specific text
   - Icon: Application icon or status-specific icon
   - Action: Click to bring window to front

#### Technical Implementation
1. **Notification Manager**
   ```python
   class DesktopNotificationManager:
       def __init__(self, main_window):
           self.main_window = main_window
           self.tray_icon = None  # Will be set if tray is available

       def show_completion_notification(self, filename):
           if self._should_show_notification('completion'):
               self._show_notification(
                   "Operation Completed",
                   f"Successfully processed: {filename}",
                   QSystemTrayIcon.Information
               )

       def show_error_notification(self, error_message):
           if self._should_show_notification('error'):
               self._show_notification(
                   "Operation Failed",
                   error_message,
                   QSystemTrayIcon.Critical
               )

       def _should_show_notification(self, notification_type):
           # Check settings and window state

       def _show_notification(self, title, message, icon_type):
           # Use QSystemTrayIcon or platform-specific APIs
   ```

2. **Platform-Specific Implementation**
   - **Windows**: Use QSystemTrayIcon or Windows Toast notifications
   - **macOS**: Use QSystemTrayIcon or NSUserNotification
   - **Linux**: Use QSystemTrayIcon or libnotify

3. **Integration Points**
   - Connect to CHDMAN operation completion/error signals
   - Integrate with system tray manager if available
   - Fallback to status bar messages if notifications unavailable

#### Notification Scenarios
1. **Operation Complete**
   - Title: "CHDMAN GUI - Operation Completed"
   - Message: "Successfully converted [filename]"
   - Duration: User-configured (default 5 seconds)

2. **Operation Error**
   - Title: "CHDMAN GUI - Operation Failed"
   - Message: First line of error message (truncated if long)
   - Duration: Longer (8 seconds) for errors

3. **Batch Operations**
   - Title: "CHDMAN GUI - Batch Completed"
   - Message: "Processed X files (Y successful, Z failed)"

#### Settings UI
```
Desktop Notifications
├── □ Show desktop notifications
├── □ Notify on completion
├── □ Notify on errors
├── □ Only when window is minimized
└── Duration: [5] seconds
```

#### Acceptance Criteria
- [ ] Notifications appear for successful operations
- [ ] Error notifications show appropriate error information
- [ ] Notifications respect user settings (on/off, duration)
- [ ] "Only when minimized" setting works correctly
- [ ] Clicking notification brings window to front
- [ ] Works on Windows, macOS, and Linux
- [ ] Graceful fallback when notifications unavailable
- [ ] Batch operations show summary notifications

---

## PRD-011: Alternative CHDMAN Paths
**Priority:** Medium Impact | **Difficulty:** Medium | **Estimated Time:** 3-4 hours

### Overview
Allow users to configure multiple CHDMAN executable paths as fallbacks, improving reliability across different system configurations.

### Requirements

#### Functional Requirements
1. **Multiple Path Configuration**
   - Primary path: Current single path setting
   - Fallback paths: List of alternative paths
   - Auto-detection: Scan common installation locations
   - Path validation: Test each path for CHDMAN executable

2. **Path Management**
   - Add/remove paths via UI
   - Reorder paths (priority)
   - Test individual paths
   - Auto-remove invalid paths option

3. **Fallback Behavior**
   - Try primary path first
   - On failure, try fallback paths in order
   - Remember last successful path for next operation
   - Log which path was used (debug mode)

#### Technical Implementation
1. **CHDMAN Path Manager**
   ```python
   class CHDMANPathManager:
       def __init__(self):
           self.paths = []  # List of paths in priority order
           self.last_successful_path = None

       def add_path(self, path):
           # Add path if valid and not duplicate

       def remove_path(self, path):
           # Remove from list

       def validate_path(self, path):
           # Test if path points to valid CHDMAN executable
           # Return (valid, version, error_message)

       def get_working_path(self):
           # Return first working path from the list

       def auto_detect_paths(self):
           # Scan common locations for CHDMAN
           common_paths = [
               # Windows
               "C:/mame/chdman.exe",
               "C:/MAME/chdman.exe",
               # macOS
               "/usr/local/bin/chdman",
               "/opt/homebrew/bin/chdman",
               "/Applications/MAME.app/Contents/MacOS/chdman",
               # Linux
               "/usr/bin/chdman",
               "/usr/local/bin/chdman",
               "/opt/mame/chdman"
           ]
           return [path for path in common_paths if self.validate_path(path)[0]]
   ```

2. **Settings Integration**
   - Setting key: `chdman_paths` (list of strings)
   - Migrate existing single path to first item in list
   - Auto-save when paths are modified

3. **UI Implementation - CHDMAN Tab Enhancement**
   ```
   CHDMAN Executable Paths
   ┌─────────────────────────────────────────────────────┐
   │ Primary:   [/usr/bin/chdman              ] [Browse] │
   │ Fallbacks: [path1                        ] [Test  ] │
   │            [path2                        ] [Test  ] │
   │            [                             ] [Add   ] │
   │                                                     │
   │ [Auto-Detect Paths] [Remove Invalid] [Move Up/Down]│
   └─────────────────────────────────────────────────────┘
   ```

#### Path Detection Logic
1. **Auto-Detection Strategy**
   - Check common installation directories
   - Search system PATH environment variable
   - Look for MAME installations with bundled CHDMAN
   - Platform-specific locations (registry on Windows, etc.)

2. **Validation Process**
   ```python
   def validate_chdman_path(self, path):
       try:
           # Try to run 'chdman' with no arguments
           result = subprocess.run([path], capture_output=True, timeout=5)
           output = result.stderr.decode()

           # Look for CHDMAN version info in output
           if "chdman" in output.lower():
               version = self.extract_version(output)
               return True, version, None
           else:
               return False, None, "Not a valid CHDMAN executable"
       except Exception as e:
           return False, None, str(e)
   ```

#### UI Features
1. **Path List Widget**
   - QListWidget with custom items
   - Drag-and-drop reordering
   - Context menu: Test, Remove, Move Up/Down
   - Status indicators: ✓ (valid), ✗ (invalid), ? (untested)

2. **Path Testing**
   - Individual "Test" buttons for each path
   - "Test All" button to validate entire list
   - Progress indicator for testing
   - Results show version information

3. **Bulk Operations**
   - "Auto-Detect" scans system for CHDMAN installations
   - "Remove Invalid" cleans up broken paths
   - "Import from..." loads paths from file

#### Error Handling and Fallback
1. **Operation Failure Handling**
   ```python
   def execute_chdman_with_fallback(self, command, args):
       paths_to_try = self.path_manager.get_all_paths()

       for path in paths_to_try:
           try:
               # Attempt operation with this path
               result = self.run_chdman(path, command, args)
               self.path_manager.mark_successful(path)
               return result
           except Exception as e:
               self.logger.debug(f"Failed with {path}: {e}")
               continue

       # All paths failed
       raise CHDMANExecutionError("All CHDMAN paths failed")
   ```

2. **User Feedback**
   - Show which path is being used in status
   - Warn when falling back to secondary paths
   - Suggest path configuration if all paths fail

#### Acceptance Criteria
- [ ] Multiple CHDMAN paths can be configured and prioritized
- [ ] Auto-detection finds CHDMAN in common locations
- [ ] Path validation correctly identifies working executables
- [ ] Fallback mechanism tries paths in order on failure
- [ ] UI allows easy management of path list
- [ ] Individual and bulk testing of paths works
- [ ] Last successful path is remembered and prioritized
- [ ] Migration from single path setting works seamlessly

---

## PRD-012: Automatic Temporary File Cleanup
**Priority:** Medium Impact | **Difficulty:** Medium | **Estimated Time:** 4-5 hours

### Overview
Automatically clean up temporary files created during CHDMAN operations after a configurable period to prevent disk space issues.

### Requirements

#### Functional Requirements
1. **Cleanup Configuration**
   - Setting keys:
     - `auto_cleanup_enabled` (boolean, default: True)
     - `cleanup_after_days` (integer, default: 7)
     - `cleanup_on_startup` (boolean, default: True)
     - `temp_file_extensions` (list, default: ['.tmp', '.temp', '.partial'])

2. **Cleanup Scope**
   - Application-specific temp directory
   - User-specified temp directories from operations
   - Orphaned partial files from interrupted operations
   - Log files older than specified period (separate setting)

3. **Cleanup Triggers**
   - Application startup (if enabled)
   - Daily background check while running
   - Manual cleanup via UI
   - After successful operations (immediate cleanup of that operation's temp files)

#### Technical Implementation
1. **Temp File Manager**
   ```python
   class TempFileManager:
       def __init__(self):
           self.temp_dir = self.get_app_temp_dir()
           self.tracked_files = []  # Files created by current session
           self.cleanup_timer = QTimer()

       def get_app_temp_dir(self):
           # Create app-specific temp directory
           import tempfile
           app_temp = os.path.join(tempfile.gettempdir(), "chdman_gui")
           os.makedirs(app_temp, exist_ok=True)
           return app_temp

       def track_temp_file(self, filepath):
           # Add file to tracking list with timestamp
           self.tracked_files.append({
               'path': filepath,
               'created': datetime.now(),
               'operation_id': self.current_operation_id
           })

       def cleanup_old_files(self, days_old=7):
           # Remove files older than specified days
           cutoff_date = datetime.now() - timedelta(days=days_old)
           cleaned_files = []

           for root, dirs, files in os.walk(self.temp_dir):
               for file in files:
                   filepath = os.path.join(root, file)
                   if self.should_cleanup_file(filepath, cutoff_date):
                       try:
                           os.remove(filepath)
                           cleaned_files.append(filepath)
                       except Exception as e:
                           self.logger.warning(f"Failed to cleanup {filepath}: {e}")

           return cleaned_files

       def cleanup_operation_files(self, operation_id):
           # Clean up files from specific operation immediately

       def should_cleanup_file(self, filepath, cutoff_date):
           # Check if file should be cleaned up based on age and type
   ```

2. **Background Cleanup Service**
   ```python
   class CleanupService:
       def __init__(self, temp_manager):
           self.temp_manager = temp_manager
           self.daily_timer = QTimer()
           self.daily_timer.timeout.connect(self.daily_cleanup)
           self.start_daily_timer()

       def start_daily_timer(self):
           # Set timer for next 3 AM or next day if past 3 AM
           self.daily_timer.start(self.ms_until_next_cleanup())

       def daily_cleanup(self):
           if app_settings.get('auto_cleanup_enabled', True):
               days = app_settings.get('cleanup_after_days', 7)
               self.temp_manager.cleanup_old_files(days)
           self.start_daily_timer()  # Reset for next day
   ```

3. **Settings UI - General Tab**
   ```
   Temporary File Cleanup
   ├── □ Automatically cleanup old temporary files
   ├── Clean up files older than: [7] days
   ├── □ Clean up on application startup
   ├── Temp directory: [/tmp/chdman_gui] [Change]
   └── [Clean Up Now] [View Temp Files]
   ```

#### Manual Cleanup Interface
1. **Cleanup Dialog**
   ```python
   class CleanupDialog(QDialog):
       def __init__(self, temp_manager, parent=None):
           # Show temp files that would be cleaned
           # Allow user to select specific files
           # Preview of space that will be freed
           # "Clean Selected" and "Clean All Old" buttons
   ```

2. **Temp File Viewer**
   - List of current temporary files
   - File sizes and creation dates
   - Filter by age, size, or file type
   - Select individual files for deletion

#### Safety Features
1. **Confirmation Dialogs**
   - Confirm before cleaning large amounts of data (>100MB)
   - Show list of files to be deleted
   - Option to exclude specific files/patterns

2. **Protected Files**
   - Never delete files from currently running operations
   - Exclude files modified within last hour
   - Respect file locks and access permissions

3. **Cleanup Logging**
   ```python
   def log_cleanup_action(self, files_cleaned, space_freed):
       self.logger.info(f"Cleanup completed: {len(files_cleaned)} files, "
                       f"{space_freed/1024/1024:.1f}MB freed")

       if app_settings.get('debug_logging_enabled'):
           for file in files_cleaned:
               self.logger.debug(f"Cleaned: {file}")
   ```

#### Startup Cleanup Process
1. **Startup Integration**
   ```python
   def perform_startup_cleanup(self):
       if not app_settings.get('cleanup_on_startup', True):
           return

       # Non-blocking cleanup in background thread
       cleanup_thread = CleanupThread(self.temp_manager)
       cleanup_thread.finished.connect(self.on_cleanup_finished)
       cleanup_thread.start()
   ```

2. **Progress Indication**
   - Show cleanup progress in status bar during startup
   - Don't block main window display
   - Option to skip cleanup if taking too long

#### Acceptance Criteria
- [ ] Automatic cleanup runs daily when enabled
- [ ] Startup cleanup works without blocking UI
- [ ] Manual cleanup dialog shows files and sizes
- [ ] Configurable cleanup age threshold works
- [ ] Currently running operations are protected
- [ ] Cleanup logging provides appropriate detail
- [ ] Settings persist and apply correctly
- [ ] Large cleanup operations ask for confirmation
- [ ] Temp directory can be changed by user
- [ ] "Clean Up Now" button provides immediate cleanup

---

## Implementation Notes

### Development Order Recommendation
1. **Phase 1 Foundation** (PRD-001 to PRD-003) - Essential infrastructure
2. **Phase 1 Quick Wins** (PRD-004 to PRD-008) - User-visible improvements
3. **Phase 2 High Impact** (PRD-009 to PRD-012) - Major feature additions

### Code Architecture Considerations
1. **Settings Management**: All PRDs assume a centralized `app_settings.py` module that can get/set values with defaults
2. **Signal/Slot Connections**: Most features need to connect to existing CHDMAN operation signals
3. **Thread Safety**: Background operations (cleanup, notifications) must be thread-safe
4. **Platform Compatibility**: All features should work on Windows, macOS, and Linux
5. **Error Handling**: Each feature should fail gracefully and provide meaningful error messages

### Testing Strategy
1. **Unit Tests**: Each manager class should have comprehensive unit tests
2. **Integration Tests**: Test interaction between features (e.g., tray + notifications)
3. **Platform Testing**: Verify cross-platform functionality
4. **Settings Migration**: Test upgrading from older versions
5. **Edge Cases**: Handle missing permissions, full disks, etc.

### Performance Considerations
1. **Settings Loading**: Cache settings in memory, only read file on startup
2. **File Operations**: Use background threads for I/O intensive operations
3. **Timer Management**: Consolidate timers where possible to reduce overhead
4. **Memory Usage**: Clean up resources properly, especially for long-running operations

These PRDs provide comprehensive specifications that should allow for implementation with minimal ambiguity while maintaining consistency with the existing Qt-based architecture.
