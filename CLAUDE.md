# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A lightweight PyQt6 desktop app for playing multi-angle dashcam/DVR footage from `NOR` directories. It groups video files by timestamp, supports 5 camera angles (F/B/L/R/S) plus a synchronized 4-camera "All" view, and provides continuous playback.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python3 main.py

# Test scanner standalone
python3 dvr_scanner.py

# Package as macOS app
pip install pyinstaller
pyinstaller --windowed --name="DVR_Player" main.py
```

## Architecture

Two-file architecture with model-view separation:

- **`dvr_scanner.py`** — `DVRScanner` class: scans a directory for files matching `NOR_YYYYMMDD_HHMMSS_[FBLRS].mp4`, groups them by timestamp.

- **`main.py`** — `DVRPlayer(QMainWindow)`: two-panel layout (3:1 ratio). Left panel has `QStackedWidget` for single view or a 2x2 grid (S, B, L, R) "ALL" view. Right panel is a `QTreeWidget` timeline.

### Key behaviors
- **All View**: Plays Front Wide (S), Back (B), Left (L), and Right (R) in a 2x2 grid, synchronized.
- **Angle fallback**: when Front (`F`) is missing, automatically uses Front Wide (`S`).
- **Angle switching**: preserves playback position when changing angles.
- **Auto-advance**: `mediaStatusChanged` signal triggers `play_next_group()` on `EndOfMedia`.

## Author

lican
