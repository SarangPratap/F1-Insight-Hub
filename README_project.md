# F1 Insight Hub — Technical Project Report

<div align="center">
  <img src="./assets/Banner.png" alt="F1 Insight Hub" width="100%" style="border-radius: 10px;">
</div>

> **A Python-based interactive Formula 1 dashboard for telemetry visualization, race replay, and post-race analytics — powered by live data from the FastF1 API.**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Target User](#2-target-user)
3. [Complexity Criteria](#3-complexity-criteria)
4. [System Architecture](#4-system-architecture)
5. [Modules & Features](#5-modules--features)
6. [Tech Stack](#6-tech-stack)
7. [Installation & Setup](#7-installation--setup)
8. [How to Run](#8-how-to-run)
9. [Project Structure](#9-project-structure)
10. [Data Flow](#10-data-flow)
11. [Current Status & Roadmap](#11-current-status--roadmap)
12. [Contributors](#12-contributors)
13. [Acknowledgments](#13-acknowledgments)

---

## 1. Project Overview

**F1 Insight Hub** is an interactive desktop dashboard built in Python that allows users to explore Formula 1 race data through three specialized modules:

| Module | Description | Status |
|---|---|---|
| **RaceVision** | Real-time 2D race replay with animated telemetry (Arcade engine) | ✅ Completed |
| **RaceAnalytics** | Post-race statistical analysis with interactive charts (Matplotlib/PySide6) | ✅ Completed |
| **RaceIntelligence** | ML-powered predictive modeling and strategy insights | � Future Work |

The dashboard fetches **live data** from the official Formula 1 timing servers via the **FastF1 API** — covering every session from 2018 to the current season. Data is not bundled as static files; it is pulled on-demand from the API and cached locally for performance.

---

## 2. Target User

The primary user of this dashboard is a **Formula 1 data enthusiast, analyst, or engineering student** who wants to:

- **Replay and visualize** any F1 race or sprint session with full car positions, tyre compounds, weather conditions, and DRS zones rendered on a 2D track map.
- **Analyze race performance** through interactive charts — comparing driver pace, fastest laps, tyre strategies, and sector times.
- **Understand race dynamics** (e.g., safety car periods, weather transitions from day to night, pit stop windows) through data rather than broadcast footage.

Secondary users include:
- **Fantasy F1 players** looking for data-driven insights into driver and team performance.
- **Aspiring F1 data engineers** studying how telemetry pipelines are built.

The dashboard requires **no prior programming knowledge** to operate — users interact entirely through a graphical interface with point-and-click controls.

---

## 3. Complexity Criteria

This project satisfies **multiple** complexity criteria as defined in the assignment brief:

### 3.1 Complex from a Data Engineering Perspective

| Criterion | How We Fulfill It |
|---|---|
| **Data source is not a file, but data from an API** | All race data is fetched live from the **FastF1 API**, which wraps the official F1 Live Timing API. No CSV/JSON files are bundled with the project. |
| **Data gets continuously updated and is not static** | The schedule, telemetry, and results update as new races happen each season. Selecting a new year or round triggers a fresh API call. Users can analyze races from 2018 up to the latest completed Grand Prix. |

**Details:**
- The `data_engine.py` module manages API communication via `fastf1.get_session()` and `fastf1.get_event_schedule()`.
- Raw telemetry (X/Y coordinates, speed, gear, throttle, brake, DRS, tyre compound) is fetched per-driver, per-lap — then resampled to 25 FPS for smooth replay.
- Weather data (rainfall, humidity, air/track temperature, wind) is pulled from the same API and interpolated to the unified timeline.
- Processed data is cached locally as `.pkl` files under `data/cache/computed/` to avoid redundant API calls, but users can force a refresh.

### 3.2 Complex from a Human-Computer Interaction Perspective

| Criterion | How We Fulfill It |
|---|---|
| **Complex dashboard with advanced interactions** | The dashboard has three distinct modules, each with unique UI paradigms — a PySide6 launcher, an Arcade-based real-time visualization, and a Matplotlib-backed analytics panel with sidebar navigation. |

**Details:**
- **Main Launcher** (`main.py`): PySide6 GUI with year selection, interactive race calendar (QTreeWidget), session type radio buttons, and module launch buttons. Schedule fetching runs on a background thread (`QThread`) to keep the UI responsive.
- **RaceVision** (`module_vision.py`): Full real-time race replay using the Arcade engine with:
  - Animated car positions on a track map (inner/outer boundaries, center line)
  - Live leaderboard with position sorting, tyre compound icons, and lap counter
  - Animated weather widget (sun rotation, rain drops, moon phases, fog effects — dynamically switching between day/night based on actual race start time from the API)
  - Race progress bar, driver info panel (speed, gear, throttle/brake pedal animations)
  - DRS zone visualization on the track
  - Playback controls (pause, speed up/down from 0.1× to 256×, rewind, restart)
  - Click-to-select driver on the leaderboard
  - Keyboard shortcuts (Space, arrows, R, D, L, H)
- **RaceAnalytics** (`module_analytics.py`): PySide6 window with a vertical sidebar menu and stacked pages:
  - **Race Summary**: Card-based KPIs (Winner, Fastest Lap, Top Speed, Dominant Tyre, Best Sector Times)
  - **Fastest Laps**: Vertical bar chart showing gap-to-P1 for every driver
  - **Lap Progression**: Interactive driver selector with per-driver pace plot vs. race leader, including tyre stint markers

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Main Dashboard (main.py)                     │
│                        PySide6 GUI                               │
│                                                                  │
│  • Year Selector (2018–2025)    • Race Calendar (QTreeWidget)    │
│  • Session Type (Race/Sprint)   • Module Launch Buttons          │
└────────────────────────┬────────────────────────────────────────┘
                         │ subprocess.Popen
           ┌─────────────┼─────────────┐
           │             │             │
    ┌──────▼──────┐ ┌───▼───────┐ ┌──▼──────────────┐
    │ RaceVision  │ │  Race     │ │ RaceIntelligence │
    │ (Arcade 3)  │ │ Analytics │ │  (Coming Soon)   │
    │             │ │ (PySide6 +│ │                  │
    │ • Track Map │ │ Matplotlib│ │ • Scikit-learn   │
    │ • Replay    │ │ )         │ │ • Predictions    │
    │ • Weather   │ │           │ │                  │
    │ • Telemetry │ │ • Summary │ │                  │
    │ • DRS Zones │ │ • Charts  │ │                  │
    └──────┬──────┘ └───┬───────┘ └──┬───────────────┘
           │            │            │
           └────────────┼────────────┘
                        │
           ┌────────────▼────────────┐
           │   Data Engine            │
           │   (data_engine.py)       │
           │                          │
           │ • load_session()         │
           │ • get_race_telemetry()   │
           │ • get_quali_telemetry()  │
           │ • Weather processing     │
           │ • Multiprocess telemetry │
           │ • Local caching (.pkl)   │
           └────────────┬─────────────┘
                        │
           ┌────────────▼─────────────┐
           │   FastF1 API              │
           │   (F1 Official Timing)    │
           │                           │
           │ • Event Schedules         │
           │ • Lap-by-lap Telemetry    │
           │ • Car Positions (X, Y)    │
           │ • Weather Data            │
           │ • Track Status Events     │
           └───────────────────────────┘
```

Each module is launched as a **separate process** (`subprocess.Popen`) from the main launcher, ensuring that a crash in one module does not bring down the dashboard.

---

## 5. Modules & Features

### 5.1 Main Dashboard (`main.py`)

The entry point. A PySide6 desktop window where the user:

1. Selects a **season year** (2018–2025) from a dropdown.
2. Browses the full **race calendar** for that year in a table (Round, Event Name, Country, Date).
3. Chooses **Race** or **Sprint** session type via radio buttons.
4. Clicks one of three large module buttons to launch an analysis.

The schedule is fetched asynchronously on a background `QThread` so the UI remains responsive.

### 5.2 RaceVision (`module_vision.py`) — ✅ Completed

A **real-time 2D race replay** powered by the Arcade 3.0 game engine (1,744 lines).

**Key features:**
- Animated car dots moving on a track outline (inner/outer boundaries computed from telemetry)
- Live-updating **leaderboard** sorted by race distance, showing driver codes, team colors, tyre icons, and lap counter
- **Weather widget** with animated icons — rotating sun, falling rain, moon phases, fog layers — driven by actual API weather data and dynamically detecting night races based on session start times and GMT offsets
- **Driver info panel**: click a driver on the leaderboard to see speed (km/h), gear, and animated throttle/brake pedal bars
- **DRS zone** overlay on the track (toggleable)
- **Race progress bar** showing percentage of race completed
- **Playback controls**: pause/resume, variable speed (0.1× to 256×), frame-step rewind/forward, restart
- **Keyboard shortcuts**: Space (pause), Arrow keys (speed/seek), R (restart), D (DRS toggle), L (label toggle), H (help)

Data pipeline for RaceVision:
1. `load_session()` fetches the session from FastF1 API
2. `get_race_telemetry()` processes all drivers in parallel using Python `multiprocessing.Pool`
3. Telemetry is resampled to a unified 25 FPS timeline
4. Frame data includes positions, tyre compounds, speed, gear, DRS, throttle, brake, weather
5. Results are cached as `.pkl` for instant reload

### 5.3 RaceAnalytics (`module_analytics.py`) — ✅ Completed

A **post-race statistical analysis** window built with PySide6 and Matplotlib (499 lines).

**Pages:**

| Page | Content |
|---|---|
| **Race Summary** | Card-based KPIs — Race Winner, Fastest Lap Time, Top Speed, Dominant Tyre Compound, Fastest Sector 1/2/3 — with team-colored accent borders |
| **Fastest Laps** | Vertical bar chart showing each driver's fastest lap delta to P1, colored by team |
| **Lap Progression** | Select any driver from a sidebar list → see their lap-by-lap pace plotted against the race leader. Tyre stint changes are marked with vertical lines and compound labels. Slow laps (>115% of fastest) are filtered out for readability. |

### 5.4 RaceIntelligence — � Future Work

Planned ML module using Scikit-learn for:
- Race outcome prediction
- Tyre degradation modeling
- Strategy optimization suggestions

Placeholder functions (`prepare_ml_features()`, `calculate_driver_performance_scores()`) exist in `data_engine.py`.

---

## 6. Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Main GUI** | PySide6 (Qt 6) | Dashboard launcher, analytics window |
| **Race Replay Engine** | Arcade 3.0+ | 2D animated race visualization |
| **Data Source** | FastF1 ≥ 3.0 | Official F1 timing & telemetry API |
| **Data Processing** | Pandas, NumPy | Telemetry resampling, aggregation |
| **Charting** | Matplotlib | Analytics charts and plots |
| **Parallel Processing** | multiprocessing (stdlib) | Multi-core telemetry processing |
| **ML (planned)** | Scikit-learn, SciPy | Predictive models |
| **Caching** | pickle (stdlib) | Local computed data cache |
| **Language** | Python 3.11+ | — |

---

## 7. Installation & Setup

### Prerequisites

- **Python 3.11 or higher** (tested on 3.11 and 3.12)
- **pip** (comes with Python)
- An **internet connection** (required on first run to fetch data from the FastF1 API)

### Step-by-step

```bash
# 1. Clone the repository
git clone https://github.com/SarangPratap/F1-Insight-Hub.git
cd F1-MainV2

# 2. (Recommended) Create a virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt
```

### Dependency List (`requirements.txt`)

```
fastf1>=3.0.0
pandas>=2.0.0
numpy>=1.24.0
arcade>=2.6.17
PySide6>=6.5.0
scikit-learn>=1.3.0
scipy>=1.11.0
matplotlib>=3.7.0
seaborn>=0.12.0
questionary>=2.0.0
rich>=13.0.0
numba>=0.57.0
python-dateutil>=2.8.0
pytz>=2023.3
```

> **Note:** The first time you select a race, FastF1 will download and cache the session data. This can take 1–3 minutes depending on your internet speed. Subsequent loads of the same session are instant (loaded from local cache under `data/cache/`).

---

## 8. How to Run

```bash
python main.py
```

This opens the **F1 Insight Hub** main dashboard window.

### Usage Steps

1. **Select a year** from the dropdown (default: 2025). The race calendar loads automatically.
2. **Click on a race** in the calendar table to select it.
3. **Choose session type**: Race or Sprint (Sprint is only available for sprint weekends).
4. **Click a module button**:
   - **RaceVision** → Opens the real-time race replay window (Arcade engine). Use keyboard shortcuts to control playback.
   - **RaceAnalytics** → Opens the analytics window with summary cards, charts, and pace plots.
   - **RaceIntelligence** → Currently disabled (coming soon).

### RaceVision Controls

| Key | Action |
|---|---|
| `Space` | Pause / Resume |
| `←` / `→` | Rewind / Forward |
| `↑` / `↓` | Increase / Decrease playback speed |
| `R` | Restart from beginning |
| `D` | Toggle DRS zone overlay |
| `L` | Toggle driver labels on track |
| `H` | Toggle controls help panel |
| `Click` on leaderboard | Select driver to view detailed info |

---

## 9. Project Structure

```
F1-MainV2/
├── main.py                 # Main dashboard launcher (PySide6)
├── config.py               # Shared settings: colors, constants, formatting utilities
├── data_engine.py          # Core data layer: API calls, telemetry processing, caching
├── module_vision.py        # RaceVision: real-time 2D race replay (Arcade 3.0)
├── module_analytics.py     # RaceAnalytics: post-race charts & statistics (PySide6 + Matplotlib)
├── requirements.txt        # Python dependencies
├── README.md               # Original project README
├── README_project.md       # This technical report
├── assets/
│   └── Banner.png          # Project banner image
└── data/
    └── cache/
        ├── .fastf1/        # Raw FastF1 API cache (auto-generated)
        └── computed/        # Pre-computed telemetry frames (.pkl files)
```

### File Descriptions

| File | Lines | Description |
|---|---|---|
| `main.py` | ~480 | PySide6 launcher with year/round selection, calendar, session picker, and module launch buttons. Background thread for API calls. |
| `config.py` | ~270 | Centralized configuration — FPS (25), screen dimensions, team/driver color maps, tyre compound mappings, UI theme colors, formatting utilities. |
| `data_engine.py` | ~879 | Data backbone — session loading, parallel telemetry processing (multiprocessing.Pool), weather analysis, night race detection, frame generation, local caching (pickle), and placeholder ML functions. |
| `module_vision.py` | ~1744 | Full race replay engine — track rendering, leaderboard, weather widget (animated sun/rain/moon/fog), driver info panel, DRS zones, progress bar, playback controls. |
| `module_analytics.py` | ~499 | Analytics window — race summary cards, fastest lap bar chart, lap progression plot with leader comparison and tyre stint markers. |

---

## 10. Data Flow

```
User selects Year + Round + Session
          │
          ▼
   main.py calls FastF1 API
   (fastf1.get_event_schedule)
          │
          ▼
   Race calendar displayed
   User clicks a race → selects module
          │
          ▼
   Module launched as subprocess
          │
          ▼
   data_engine.py:
   ├── load_session(year, round, type)     ← FastF1 API call
   │
   ├─── IF RaceVision:
   │    ├── get_race_telemetry(session)     ← Parallel processing (multiprocessing)
   │    │   ├── For each driver:
   │    │   │   ├── Fetch all laps & telemetry
   │    │   │   ├── Extract X, Y, Speed, Gear, DRS, Throttle, Brake, Tyre
   │    │   │   └── Concatenate & sort by time
   │    │   ├── Create unified 25 FPS timeline
   │    │   ├── Resample all drivers to timeline (np.interp)
   │    │   ├── Fetch weather data & interpolate
   │    │   ├── Build frame-by-frame data structure
   │    │   └── Cache result as .pkl
   │    └── Arcade draws track + cars + weather + UI
   │
   └─── IF RaceAnalytics:
        ├── Uses session.laps directly (Pandas DataFrame)
        ├── Aggregates lap times, sectors, tyre compounds
        └── Matplotlib renders charts in PySide6 window
```

---

## 11. Current Status & Roadmap

### Completed ✅

- [x] Main dashboard with race calendar and year selection
- [x] RaceVision module — full race replay with all telemetry
- [x] RaceAnalytics module — summary, fastest laps, pace comparison
- [x] Weather system with day/night detection and animated icons
- [x] Multi-core parallel telemetry processing
- [x] Local caching system for fast reloads
- [x] Sprint session support

### Future Work 🔮

- [ ] **RaceIntelligence module** — ML-based predictions (scikit-learn)
  - Race outcome prediction
  - Tyre degradation modeling
  - Strategy optimization

### Planned 🗓️

- [ ] Historical season comparison tools
- [ ] Export analytics to PDF/Excel
- [ ] Qualifying session replay in RaceVision

---

## 12. Contributors

| Name | Role |
|---|---|
| **Sarang Pratap** | Core development, visualization architecture, data processing |
| **Avishkar Sanjay Potale** | Core development, analytics module, visualization architecture |

---

## 13. Acknowledgments

- [**FastF1**](https://github.com/theOehrly/Fast-F1) — Official F1 telemetry data API by Philipp Schilk
- [**F1 Race Replay**](https://github.com/IAmTomShaw/f1-race-replay) by Tom Shaw — Inspiration for telemetry visualization and race replay mechanics
- [**Arcade**](https://api.arcade.academy/) — Python game engine used for the RaceVision module
- [**PySide6 (Qt)**](https://doc.qt.io/qtforpython-6/) — GUI framework for the dashboard and analytics
