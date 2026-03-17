"""
F1 INSIGHT HUB - Intelligence Module
Machine Learning, Predictive Modeling, and Deep Telemetry Analysis
"""

import sys
import argparse
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QStackedWidget, QListWidget, QListWidgetItem, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Matplotlib integration
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

# Force JURA font for ML Graphs
matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Jura', 'Arial', 'DejaVu Sans']

# Project imports
from data_engine import load_session, enable_cache
from config import get_driver_color

# --- STYLING CONSTANTS ---
BG_COLOR = "#FFFFFF"
TEXT_COLOR = "#000000"
ACCENT_COLOR = "#e10600" 
MENU_BG = "#F5F5F5"
MENU_SEL_TEXT = "#FFFFFF"

class IntelligenceWindow(QMainWindow):
    def __init__(self, year, round_number, session_type="R"):
        super().__init__()
        self.setWindowTitle(f"F1 Insight Hub - ML Intelligence ({year} Round {round_number})")
        self.resize(1300, 850)
        
        self.year = year
        self.round = round_number
        self.session_type = session_type
        self.session = None
        self.laps = None
        
        self._setup_loading_ui()
        self._load_data()
        self._setup_main_ui()

    def _setup_loading_ui(self):
        self.loading_label = QLabel("Initializing Machine Learning Models...\nPlease Wait.")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("Jura", 16))
        self.setCentralWidget(self.loading_label)

    def _load_data(self):
        try:
            enable_cache()
            self.session = load_session(self.year, self.round, self.session_type)
            if self.session:
                self.laps = self.session.laps
        except Exception as e:
            print(f"Error loading data: {e}")

    def _setup_main_ui(self):
        if self.laps is None or self.laps.empty:
            self.loading_label.setText("Error: Insufficient data for ML processing.")
            return

        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR}; font-family: 'Jura';")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- LEFT SIDEBAR (VERTICAL MENU) ---
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet(f"background-color: {MENU_BG}; border-right: 1px solid #ddd;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Header
        header = QLabel("INTELLIGENCE")
        header.setFixedHeight(60)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"background-color: {ACCENT_COLOR}; color: white; font-size: 24px;")
        sidebar_layout.addWidget(header)

        # Menu List
        self.menu_list = QListWidget()
        self.menu_list.setStyleSheet(f"""
            QListWidget {{ border: none; background-color: {MENU_BG}; font-size: 15px; }}
            QListWidget::item {{ height: 60px; padding-left: 15px; border-bottom: 1px solid #e0e0e0; }}
            QListWidget::item:selected {{ background-color: {ACCENT_COLOR}; color: {MENU_SEL_TEXT}; font-weight: bold; }}
        """)
        
        items = [
            ("Driver Score", 0),
            ("Tyre Deg Predictor", 1),
            ("Cornering Style", 2)
        ]
        for name, idx in items:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, idx)
            self.menu_list.addItem(item)

        self.menu_list.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.menu_list)
        main_layout.addWidget(sidebar)

        # Footer in Sidebar
        event_label = QLabel(f"{self.session.event['EventName']}\n{self.year}")
        event_label.setAlignment(Qt.AlignCenter)
        event_label.setStyleSheet("color: #e10600; font-size: 18px; padding: 10px;")
        sidebar_layout.addWidget(event_label)

        main_layout.addWidget(sidebar)

        # --- RIGHT CONTENT AREA ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_radar_tab())     # Index 0
        self.stack.addWidget(self._create_tyre_ml_tab())   # Index 1
        self.stack.addWidget(self._create_cornering_tab()) # Index 2
        
        main_layout.addWidget(self.stack)
        self.menu_list.setCurrentRow(0)

    def switch_page(self, row):
        self.stack.setCurrentIndex(row)

    def _get_driver_list(self):
        """Helper to get sorted driver list"""
        try:
            if hasattr(self.session, 'results') and not self.session.results.empty:
                return self.session.results['Abbreviation'].tolist()
        except:
            pass
        return sorted(pd.unique(self.laps['Driver']))

    # ========================================================================
    # MODEL 1: DRIVER DNA (RADAR CHART COMPARISON)
    # ========================================================================
    def _create_radar_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Controls Layout (Now supports two drivers)
        ctrl_layout = QHBoxLayout()
        
        lbl1 = QLabel("Driver 1:")
        lbl1.setStyleSheet("font-weight:bold; font-size:16px;")
        self.radar_combo1 = QComboBox()
        self.radar_combo1.addItems(self._get_driver_list())
        self.radar_combo1.currentTextChanged.connect(self._update_radar)
        
        lbl2 = QLabel("Driver 2 (Compare):")
        lbl2.setStyleSheet("font-weight:bold; font-size:16px;")
        self.radar_combo2 = QComboBox()
        self.radar_combo2.addItem("None") # Allow single driver view
        self.radar_combo2.addItems(self._get_driver_list())
        self.radar_combo2.currentTextChanged.connect(self._update_radar)
        
        ctrl_layout.addWidget(lbl1)
        ctrl_layout.addWidget(self.radar_combo1)
        ctrl_layout.addSpacing(30) # Gap between the two selectors
        ctrl_layout.addWidget(lbl2)
        ctrl_layout.addWidget(self.radar_combo2)
        ctrl_layout.addStretch()
        
        layout.addLayout(ctrl_layout)

        # Matplotlib Canvas
        self.radar_canvas = FigureCanvas(Figure(figsize=(8, 8)))
        self.radar_ax = self.radar_canvas.figure.add_subplot(111, polar=True)
        layout.addWidget(self.radar_canvas)

        # Trigger initial plot
        self._update_radar()
        return page

    def _calculate_driver_scores(self, driver):
        """Core ML Algorithm to transform raw lap data into 0-100 scores"""
        drv_laps = self.laps.pick_drivers(driver)
        if drv_laps.empty: 
            return None
        
        # 1. Pace
        try:
            fastest_overall = self.laps.pick_fastest()['LapTime'].total_seconds()
            drv_fastest = drv_laps.pick_fastest()['LapTime'].total_seconds()
            pace_score = max(0, 100 - ((drv_fastest - fastest_overall) * 15))
        except:
            pace_score = 50
        
        # 2. Consistency
        clean_laps = drv_laps.pick_quicklaps(1.07)
        if not clean_laps.empty:
            std_dev = clean_laps['LapTime'].dt.total_seconds().std()
            cons_score = max(0, min(100, 100 - (std_dev * 10)))
        else:
            cons_score = 50

        # 3. Top Speed
        try:
            max_speed = drv_laps.pick_fastest().get_telemetry()['Speed'].max()
            grid_max = 350
            speed_score = min(100, (max_speed / grid_max) * 100)
        except:
            speed_score = 70

        # 4. Race Craft (Overtake / Grid Progression)
        try:
            # Get the driver's result row
            drv_result = self.session.results.loc[self.session.results['Abbreviation'] == driver].iloc[0]
            grid_pos = drv_result['GridPosition']
            finish_pos = drv_result['Position']
            
            # Handle pit lane starts or missing grid data
            if pd.isna(grid_pos) or grid_pos == 0: 
                grid_pos = 20  
                
            if pd.isna(finish_pos):
                prog_score = 30 # Heavy penalty for DNF
            else:
                positions_gained = grid_pos - finish_pos
                # Base score is 70. Earn +5 per overtake, lose -5 per position lost
                prog_score = 70 + (positions_gained * 5)
                
                # Winner's / Podium Bonus:
                # If you start P1 and finish P1, you gained 0 positions, but you drove a perfect race.
                if finish_pos == 1:
                    prog_score = max(prog_score, 95)
                elif finish_pos <= 3:
                    prog_score = max(prog_score, 85)
                    
            prog_score = max(0, min(100, prog_score)) # Clamp between 0-100
        except:
            prog_score = 60
            
        # 5. Tyre Management
        if not clean_laps.empty:
            avg_pace = clean_laps['LapTime'].dt.total_seconds().mean()
            tyre_score = max(0, min(100, 100 - ((avg_pace - drv_fastest) * 8)))
        else:
            tyre_score = 50

        return [pace_score, cons_score, speed_score, prog_score, tyre_score]

    def _update_radar(self, *args):
        self.radar_ax.clear()
        
        driver1 = self.radar_combo1.currentText()
        driver2 = self.radar_combo2.currentText()
        
        # Updated Categories Array
        categories = ['Pure Pace', 'Consistency', 'Top Speed', 'Race Craft\n(Progression)', 'Tyre Mgt']
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1] # Close the circle
        
        valid_drivers_plotted = 0

        # Plot Driver 1
        if driver1 and driver1 != "None":
            scores1 = self._calculate_driver_scores(driver1)
            if scores1:
                scores1 += scores1[:1]
                color1 = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver1, self.session)])}"
                self.radar_ax.plot(angles, scores1, color=color1, linewidth=2.5, linestyle='solid', label=driver1)
                self.radar_ax.fill(angles, scores1, color=color1, alpha=0.25)
                valid_drivers_plotted += 1

        # Plot Driver 2 (Comparison)
        if driver2 and driver2 != "None" and driver2 != driver1:
            scores2 = self._calculate_driver_scores(driver2)
            if scores2:
                scores2 += scores2[:1]
                color2 = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver2, self.session)])}"
                self.radar_ax.plot(angles, scores2, color=color2, linewidth=2.5, linestyle='solid', label=driver2)
                self.radar_ax.fill(angles, scores2, color=color2, alpha=0.25)
                valid_drivers_plotted += 1

        # Styling
        self.radar_ax.set_xticks(angles[:-1])
        self.radar_ax.set_xticklabels(categories, fontsize=12, fontweight='bold')
        self.radar_ax.set_yticks([20, 40, 60, 80, 100])
        self.radar_ax.set_yticklabels(["20", "40", "60", "80", "100"], color="grey", size=9)
        self.radar_ax.set_ylim(0, 100)
        
        # Update Title dynamically based on selection
        if valid_drivers_plotted == 2:
            self.radar_ax.set_title(f"DNA Comparison: {driver1} vs {driver2}", size=16, fontweight='bold', pad=20)
        elif valid_drivers_plotted == 1:
            self.radar_ax.set_title(f"DNA Profile Score: {driver1}", size=16, fontweight='bold', pad=20)
        else:
            self.radar_ax.set_title("Driver DNA Profile", size=16, fontweight='bold', pad=20)

        # Show legend if we plotted anything
        if valid_drivers_plotted > 0:
            self.radar_ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1.1), prop={'weight':'bold', 'size':12})
        
        self.radar_canvas.draw()

    # ========================================================================
    # MODEL 2: TYRE DEGRADATION PREDICTOR (REGRESSION ML)
    # ========================================================================
    def _create_tyre_ml_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        # Dual-dropdown layout
        ctrl_layout = QHBoxLayout()
        
        lbl_driver = QLabel("Driver:")
        lbl_driver.setStyleSheet("font-weight:bold; font-size:16px;")
        
        self.tyre_combo = QComboBox()
        self.tyre_combo.addItems(self._get_driver_list())
        
        lbl_stint = QLabel("Select Tyre Stint:")
        lbl_stint.setStyleSheet("font-weight:bold; font-size:16px;")
        
        self.stint_combo = QComboBox()
        
        # Connect the signals so changing driver rebuilds the stint list
        self.tyre_combo.currentTextChanged.connect(self._on_tyre_driver_changed)
        self.stint_combo.currentIndexChanged.connect(self._update_tyre_ml)
        
        ctrl_layout.addWidget(lbl_driver)
        ctrl_layout.addWidget(self.tyre_combo)
        ctrl_layout.addSpacing(30)
        ctrl_layout.addWidget(lbl_stint)
        ctrl_layout.addWidget(self.stint_combo)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.tyre_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.tyre_ax = self.tyre_canvas.figure.subplots()
        layout.addWidget(self.tyre_canvas)

        # Trigger initial plot
        self._on_tyre_driver_changed(self.tyre_combo.currentText())
        return page

    def _on_tyre_driver_changed(self, driver):
        """Rebuild the stint dropdown menu for the newly selected driver"""
        self.stint_combo.blockSignals(True)
        self.stint_combo.clear()
        
        if driver and self.laps is not None and not self.laps.empty:
            drv_laps = self.laps.pick_drivers(driver)
            if not drv_laps.empty and 'Stint' in drv_laps.columns:
                stints = drv_laps['Stint'].dropna().unique()
                
                for st in stints:
                    stint_data = drv_laps[drv_laps['Stint'] == st]
                    if not stint_data.empty:
                        compound_series = stint_data['Compound'].dropna()
                        compound = compound_series.iloc[0] if not compound_series.empty else "UNKNOWN"
                        num_laps = len(stint_data)
                        
                        # Add ALL stints to the UI so the user knows they exist
                        text = f"Stint {int(st)} - {compound} ({num_laps} laps)"
                        self.stint_combo.addItem(text, userData=st)
        
        self.stint_combo.blockSignals(False)
        self._update_tyre_ml()

    def _update_tyre_ml(self, *args):
        self.tyre_ax.clear()
        driver = self.tyre_combo.currentText()
        
        if self.stint_combo.count() == 0 or not driver:
            self.tyre_ax.text(0.5, 0.5, "No valid tyre data found for this driver.", ha='center', va='center')
            self.tyre_canvas.draw()
            return
            
        stint_num = self.stint_combo.currentData()
        
        drv_laps = self.laps.pick_drivers(driver)
        stint_laps = drv_laps[drv_laps['Stint'] == stint_num]

        if stint_laps.empty: 
            return

        compound_series = stint_laps['Compound'].dropna()
        compound = compound_series.iloc[0] if not compound_series.empty else "UNKNOWN"

        # Attempt to clean data to find "representative" laps (ignore SC, out laps)
        clean = stint_laps.pick_quicklaps(1.07)
        
        # If the stint was extremely chaotic (like a wet race) or very short (like Monaco Lap 1),
        # the filter might drop everything. Fall back to raw laps.
        if len(clean) < 3:
            clean = stint_laps.dropna(subset=['LapTime'])

        # ML requires at least 3 points to draw a quadratic curve.
        if len(clean) < 3:
            self.tyre_ax.text(0.5, 0.5, f"Stint too short for ML Prediction.\nOnly {len(clean)} valid lap(s) recorded.\nMathematical models require ≥ 3 laps.", ha='center', va='center', fontsize=12)
            self.tyre_ax.set_title(f"Tyre ML Predictor: {driver} ({compound} Tyre, Stint {int(stint_num)})", fontsize=14, fontweight='bold')
            self.tyre_ax.grid(True, linestyle='--', alpha=0.3)
            self.tyre_canvas.draw()
            return

        # Prepare ML Regression Data
        x = clean['LapNumber'].values
        y = clean['LapTime'].dt.total_seconds().values
        
        # 1. Fit Polynomial Regression (Degree 2 fits tyre wear curves best)
        try:
            z = np.polyfit(x, y, 2)
            p = np.poly1d(z)

            # 2. Predict the future (Extrapolate 5 laps into the future)
            future_x = np.arange(x[0], x[-1] + 6)
            future_y = p(future_x)
            
            # Plot ML Trendline
            self.tyre_ax.plot(future_x, future_y, color='black', linestyle='--', linewidth=2, label="ML Deg. Prediction")
        except:
            pass # Failsafe if math breaks on weird data

        # Plotting Data
        color = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver, self.session)])}"
        
        # Actual Data Points
        self.tyre_ax.scatter(x, y, color=color, label="Actual Laps", s=50)
        
        # Critical Drop-off Threshold (The "Cliff")
        cliff_time = y.min() + 2.5
        self.tyre_ax.axhline(cliff_time, color='red', linestyle=':', linewidth=2, label="Tyre Cliff Limit")

        self.tyre_ax.set_title(f"Tyre ML Predictor: {driver} ({compound} Tyre, Stint {int(stint_num)})", fontsize=14, fontweight='bold')
        self.tyre_ax.set_xlabel("Lap Number")
        self.tyre_ax.set_ylabel("Lap Time (s)")
        self.tyre_ax.grid(True, linestyle='--', alpha=0.3)
        self.tyre_ax.legend()
        
        self.tyre_canvas.draw()

    # ========================================================================
    # MODEL 3: CORNERING STYLE CLASSIFIER (TELEMETRY)
    # ========================================================================
    def _create_cornering_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        
        ctrl_layout = QHBoxLayout()
        lbl = QLabel("Cornering Style Telemetry (Heavy Braking Zone):")
        lbl.setStyleSheet("font-weight:bold; font-size:16px;")
        
        self.corner_combo = QComboBox()
        self.corner_combo.addItems(self._get_driver_list())
        self.corner_combo.currentTextChanged.connect(self._update_cornering)
        
        ctrl_layout.addWidget(lbl)
        ctrl_layout.addWidget(self.corner_combo)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Dual Axis Plot
        self.corner_canvas = FigureCanvas(Figure(figsize=(10, 8)))
        # Create 2 subplots (Top for Speed, Bottom for Brake/Throttle)
        self.ax_spd, self.ax_pedals = self.corner_canvas.figure.subplots(2, 1, sharex=True)
        layout.addWidget(self.corner_canvas)

        self._update_cornering(self.corner_combo.currentText())
        return page

    def _update_cornering(self, driver):
        self.ax_spd.clear()
        self.ax_pedals.clear()
        
        if not driver: return
        
        drv_laps = self.laps.pick_drivers(driver)
        if drv_laps.empty: return

        # Get their absolute fastest lap to analyze perfect telemetry
        fastest_lap = drv_laps.pick_fastest()
        if fastest_lap is None: return
        
        try:
            tel = fastest_lap.get_telemetry()
        except:
            self.ax_spd.text(0.5, 0.5, "Telemetry Data Unavailable", ha='center')
            self.corner_canvas.draw()
            return

        # 1. Identify Heaviest Braking Zone (Find max deceleration)
        speed = tel['Speed'].values
        # Derivative of speed (acceleration)
        accel = np.diff(speed)
        # Find index of maximum negative acceleration (hardest braking point)
        hardest_brake_idx = np.argmin(accel)
        
        # Get the distance at that point
        distance = tel['Distance'].values
        brake_dist = distance[hardest_brake_idx]

        # 2. Extract Window around the corner (300m before, 200m after)
        corner_mask = (distance > (brake_dist - 300)) & (distance < (brake_dist + 200))
        corner_tel = tel[corner_mask]

        if corner_tel.empty: return

        color = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver, self.session)])}"

        # --- PLOT 1: Speed Trace ---
        self.ax_spd.plot(corner_tel['Distance'], corner_tel['Speed'], color=color, linewidth=2)
        self.ax_spd.set_title(f"Cornering Analysis - Heaviest Braking Zone (Lap {fastest_lap['LapNumber']})", fontweight='bold')
        self.ax_spd.set_ylabel("Speed (km/h)")
        self.ax_spd.grid(True, linestyle='--', alpha=0.3)

        # --- PLOT 2: Brake & Throttle ---
        # Normalize brake boolean to 0-100 for visual consistency
        brake = corner_tel['Brake'].astype(float) * 100 
        throttle = corner_tel['Throttle']
        
        # Plot Throttle (Green)
        self.ax_pedals.plot(corner_tel['Distance'], throttle, color='green', label='Throttle %', linewidth=2)
        # Plot Brake (Red)
        self.ax_pedals.plot(corner_tel['Distance'], brake, color='red', label='Brake %', linewidth=2)
        
        self.ax_pedals.fill_between(corner_tel['Distance'], 0, brake, color='red', alpha=0.2)
        self.ax_pedals.fill_between(corner_tel['Distance'], 0, throttle, color='green', alpha=0.2)
        
        self.ax_pedals.set_xlabel("Track Distance (meters)")
        self.ax_pedals.set_ylabel("Input %")
        self.ax_pedals.legend(loc='upper right')
        self.ax_pedals.grid(True, linestyle='--', alpha=0.3)

        self.corner_canvas.figure.tight_layout()
        self.corner_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--session", type=str, default="R")
    args = parser.parse_args()

    window = IntelligenceWindow(args.year, args.round, args.session)
    window.show()
    sys.exit(app.exec())