# Unified Product Requirements Document (PRD) for RetroClamp (with Batch Integration)

**Version:** 2.1
**Date:** 2025-05-16
**Author:** ChatGPT (Synthesized, with user guidance)

---

## 1. Purpose

RetroClamp provides a modern, user-friendly GUI for CHDMAN-based disk image management, targeting both single-file and batch workflows.
**Goal:** Refactor backend processing to unify batch and single-file operations, maximize maintainability, and offer robust error handling and checkpointing, while keeping batch processing features (pause/resume, checkpointing, recovery, drag-and-drop) first-class.

---

## 2. Scope

### **In Scope**
- **Unified Job/Task Manager**: Both batch and single-file tasks go through a single queue/manager.
- **Centralized Archive Handling**: One utility for extracting/pruning disk images from archives.
- **Batch Module**: Exposes pause/resume, checkpointing, error handling, progress tracking, recovery, drag-and-drop.
- **Temporary Directory Management**: One registry for all temp dirs, with orphan cleanup on startup/shutdown.
- **Comprehensive Logging**: All jobs (batch or single) write to the same log pane and file.
- **UI Parity**: Both "Batch" and "Single File" tabs get the same feedback, progress, and error display.

### **Out of Scope**
- Media playback/emulation, direct CHD editing, online database lookup.

---

## 3. Architecture Overview

### **Revised Core Flow**

```
+----------------------+ +-------------------------+
| CompressionTab/BatchTab |-->| JobManager (singleton) |
+----------------------+ +-------------------------+
                             |
          +------------------------+--------------------+
          |                        |                    |
+-----------------+ +-----------------+ +-------------------+
|   ArchiveUtils  | |  TempDirManager | | CheckpointManager |
+-----------------+ +-----------------+ +-------------------+
          |                        |
          |              [Central registry for
          |              temp dirs, startup
          |              orphan cleanup]
          |
    +---------------+
    | CHDMan/CHDTask|
    +---------------+
          |
    [Runs CHDMAN]
```

- **JobManager**: Orchestrates all jobs, whether launched from batch or single-file. Handles queueing, progress, cancellation, and signals.
- **ArchiveUtils**: Extracts and prunes all input archives.
- **TempDirManager**: Registers temp dirs, cleans up on shutdown/startup.
- **CheckpointManager**: Batch processing state is checkpointed and can be resumed.
- **UI Tabs**: Both batch and single share signals for status, error, progress.

---

## 4. Functional Requirements

### **Batch Processing (Unified Approach)**

- Batch and single jobs are queued and processed identically via JobManager.
- **Pause/Resume**: Users can pause/resume batch (and future multi-file single jobs).
- **Checkpointing**: Processing state saved after each file; can resume after crash or app restart.
- **Error Handling**: If a file fails, it is logged, user can skip, retry, or abort batch.
- **Drag-and-drop**: BatchTab supports multi-file/folder drag/drop with recursive scan option.

### **Single File Processing**

- Uses the same JobManager and ArchiveUtils as batch.
- Progress and errors shown in unified log/progress area.

### **Checkpointing & Recovery**

- Checkpoint files contain:
  - Version, metadata, input/output paths, processing status, error info.
- CheckpointManager validates file existence on restore.
- User is prompted to recover last state if available on startup.

### **Temporary Directory Handling**

- All temp dirs (from archive extraction, etc.) registered in TempDirManager.
- On startup, orphaned temp dirs older than 1 hour are flagged for user cleanup.
- All temp dirs are deleted on app exit, unless user requests preservation (for debugging).

---

## 5. Non-Functional Requirements

- **Thread-Safety**: All progress and results signaled to UI via Qt signals/slots.
- **Performance**: Multi-core processing supported; thread count auto-tuned to CPU.
- **Responsiveness**: UI must remain responsive; main thread never blocked by jobs.
- **Logging**: All jobs write to unified JSON and human-readable logs, viewable in app.

---

## 6. Acceptance Criteria

1. All jobs, single or batch, use the same backend modules for queueing, error handling, and logging.
2. Archive extraction, temp dir cleanup, and checkpoint recovery are handled the same in all tabs.
3. No code duplication for archive/pruning/error logic.
4. User is always notified about orphaned temp dirs and can choose to clean them.
5. Checkpoint recovery reliably resumes interrupted batch jobs.
