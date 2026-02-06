"""
F1 INSIGHT HUB - Analytics Module
Post-race data analysis and visualization
"""

import sys
import argparse
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QStackedWidget, QListWidget, QListWidgetItem, QFrame, 
    QGridLayout, QSplitter
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor, QIcon
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import seaborn as sns

matplotlib.rcParams['font.family'] = 'sans-serif'
matplotlib.rcParams['font.sans-serif'] = ['Jura', 'Arial', 'DejaVu Sans']

# Project imports
from data_engine import load_session, enable_cache
from config import (
    get_driver_color, TEAM_COLORS, 
    format_time, format_speed
)

# --- STYLING CONSTANTS ---
BG_COLOR = "#FFFFFF"
TEXT_COLOR = "#000000"
ACCENT_COLOR = "#e10600"
MENU_BG = "#F5F5F5"
MENU_SEL_BG = "#e10600"
MENU_SEL_TEXT = "#FFFFFF"

class AnalyticsWindow(QMainWindow):
    def __init__(self, year, round_number, session_type="R"):
        super().__init__()
        self.setWindowTitle(f"F1 Insight Hub - Analytics ({year} Round {round_number})")
        self.resize(1300, 850)
        
        # Load Data
        self.year = year
        self.round = round_number
        self.session_type = session_type
        self.session = None
        self.laps = None
        self.drivers_list = []
        
        # Setup UI
        self._setup_loading_ui()
        
        # Load data immediately (blocking for simplicity, can be threaded)
        self._load_data()
        self._setup_main_ui()

    def _setup_loading_ui(self):
        self.loading_label = QLabel("Loading Session Data...\nPlease Wait.")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setFont(QFont("Jura", 16))
        self.setCentralWidget(self.loading_label)

    def _load_data(self):
        try:
            enable_cache()
            self.session = load_session(self.year, self.round, self.session_type)
            if self.session:
                self.laps = self.session.laps
                # Get list of drivers for the menu
                if hasattr(self.session, 'drivers'):
                    self.drivers_list = self.session.drivers
        except Exception as e:
            print(f"Error loading data: {e}")

    def _setup_main_ui(self):
        if self.laps is None or self.laps.empty:
            self.loading_label.setText("Error: Could not load lap data.")
            return

        # --- MAIN CONTAINER ---
        central_widget = QWidget()
        central_widget.setStyleSheet(f"background-color: {BG_COLOR}; color: {TEXT_COLOR}; font-family: 'Jura';")
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- LEFT SIDEBAR (VERTICAL MENU) ---
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"background-color: {MENU_BG}; border-right: 1px solid #ddd;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Header in Sidebar
        header = QLabel("ANALYTICS")
        header.setFixedHeight(60)
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"background-color: {ACCENT_COLOR}; color: white; font-size: 24px;")
        sidebar_layout.addWidget(header)

        # Menu List
        self.menu_list = QListWidget()
        self.menu_list.setFocusPolicy(Qt.NoFocus)
        self.menu_list.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background-color: {MENU_BG};
                font-size: 14px;
            }}
            QListWidget::item {{
                height: 50px;
                padding-left: 15px;
                border-bottom: 1px solid #e0e0e0;
            }}
            QListWidget::item:selected {{
                background-color: {ACCENT_COLOR};
                color: {MENU_SEL_TEXT};
            }}
            QListWidget::item:hover:!selected {{
                background-color: #e0e0e0;
            }}
        """)
        
        # Add Menu Items
        items = [
            ("Race Summary", 0),
            ("Fastest Laps", 1),
            ("Lap Progression", 2)
        ]
        for name, idx in items:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, idx)
            item.setTextAlignment(Qt.AlignCenter)
            self.menu_list.addItem(item)

        self.menu_list.currentRowChanged.connect(self.switch_page)
        sidebar_layout.addWidget(self.menu_list)
        
        # Footer in Sidebar
        event_label = QLabel(f"{self.session.event['EventName']}\n{self.year}")
        event_label.setAlignment(Qt.AlignCenter)
        event_label.setStyleSheet("color: #e10600; font-size: 18px; padding: 10px;")
        sidebar_layout.addWidget(event_label)

        main_layout.addWidget(sidebar)

        # --- RIGHT CONTENT AREA ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self._create_summary_tab())       # Index 0
        self.stack.addWidget(self._create_fastest_laps_tab())  # Index 1
        self.stack.addWidget(self._create_pace_tab())          # Index 2
        
        main_layout.addWidget(self.stack)

        # Select first item by default
        self.menu_list.setCurrentRow(0)

    def switch_page(self, row):
        self.stack.setCurrentIndex(row)

    # ------------------------------------------------------------------------
    # PAGE 1: RACE SUMMARY (Updated with Sectors & Tyres)
    # ------------------------------------------------------------------------
    def _create_summary_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("RACE SUMMARY")
        title.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(20)

        # Helper for cards
        def create_card(title, value, subtext="", color="#e10600"):
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    border-left: 6px solid {color};
                }}
            """)
            card_layout = QVBoxLayout(card)
            lbl_title = QLabel(title.upper())
            lbl_title.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
            lbl_val = QLabel(str(value))
            lbl_val.setStyleSheet("color: #000; font-size: 22px; font-weight: bold;")
            lbl_sub = QLabel(subtext)
            lbl_sub.setStyleSheet("color: #666; font-size: 12px;")
            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_val)
            card_layout.addWidget(lbl_sub)
            return card

        # 1. Winner
        try:
            if hasattr(self.session, 'results') and not self.session.results.empty:
                winner = self.session.results.iloc[0]
                name = winner['Abbreviation']
                team = winner['TeamName']
                color = f"#{''.join([f'{c:02x}' for c in get_driver_color(name, self.session)])}"
                grid.addWidget(create_card("Race Winner", name, team, color), 0, 0)
        except:
            grid.addWidget(create_card("Race Winner", "N/A", "", "#999"), 0, 0)

        # 2. Fastest Lap
        try:
            fl = self.laps.pick_fastest()
            if fl is not None:
                driver = fl['Driver']
                time_str = format_time(fl['LapTime'].total_seconds())
                color = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver, self.session)])}"
                grid.addWidget(create_card("Fastest Lap", time_str, driver, color), 0, 1)
        except:
            grid.addWidget(create_card("Fastest Lap", "N/A", "", "#999"), 0, 1)

        # 3. Top Speed
        try:
            if fl is not None:
                tel = fl.get_telemetry()
                top_speed = int(tel['Speed'].max())
                grid.addWidget(create_card("Top Speed", f"{top_speed} km/h", f"{fl['Driver']} (Main Straight)", "#333"), 0, 2)
        except:
            grid.addWidget(create_card("Top Speed", "N/A", "", "#999"), 0, 2)

        # 4. Most Used Tyre
        try:
            # Calculate mode of compound
            tyre_counts = self.laps['Compound'].value_counts()
            if not tyre_counts.empty:
                most_used = tyre_counts.index[0]
                count = tyre_counts.iloc[0]
                grid.addWidget(create_card("Dominant Tyre", most_used, f"{count} Laps total", "#555"), 1, 0)
        except:
            grid.addWidget(create_card("Dominant Tyre", "N/A", "", "#999"), 1, 0)

        # 5. Sector Fastest (S1, S2, S3)
        sectors = [('Sector1Time', 'Fastest Sector 1'), ('Sector2Time', 'Fastest Sector 2'), ('Sector3Time', 'Fastest Sector 3')]
        col_idx = 1
        row_idx = 1
        
        for col_name, title in sectors:
            try:
                # Find row with min time for this sector
                # We need to drop NaNs first
                valid_laps = self.laps.dropna(subset=[col_name])
                if not valid_laps.empty:
                    best_sec = valid_laps.loc[valid_laps[col_name].idxmin()]
                    sec_time = best_sec[col_name].total_seconds()
                    driver = best_sec['Driver']
                    color = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver, self.session)])}"
                    
                    grid.addWidget(create_card(title, format_time(sec_time), driver, color), row_idx, col_idx)
                
                # Layout logic for 3 columns
                col_idx += 1
                if col_idx > 2:
                    col_idx = 0
                    row_idx += 1
            except:
                continue

        layout.addLayout(grid)
        layout.addStretch()
        return page

    # ------------------------------------------------------------------------
    # PAGE 2: FASTEST LAPS (Bar Chart)
    # ------------------------------------------------------------------------
    def _create_fastest_laps_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)

        canvas = FigureCanvas(Figure(figsize=(10, 6)))
        ax = canvas.figure.subplots()

        drivers = pd.unique(self.laps['Driver'])
        fastest_laps = []

        for drv in drivers:
            dr_laps = self.laps.pick_drivers(drv)
            if not dr_laps.empty:
                fl = dr_laps.pick_fastest()
                if fl is not None and pd.notna(fl['LapTime']):
                    fastest_laps.append({
                        'Driver': drv,
                        'LapTime': fl['LapTime'].total_seconds(),
                        'Color': f"#{''.join([f'{c:02x}' for c in get_driver_color(drv, self.session)])}"
                    })

        if fastest_laps:
            df = pd.DataFrame(fastest_laps).sort_values('LapTime')
            p1_time = df.iloc[0]['LapTime']
            df['Delta'] = df['LapTime'] - p1_time

            bars = ax.bar(df['Driver'], df['Delta'], color=df['Color'])
            ax.set_title("Fastest Lap Delta", fontsize=14, fontweight='bold')
            ax.set_ylabel("Gap to P1 (s)")
            ax.grid(axis='y', linestyle='--', alpha=0.3)

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                        f'+{height:.3f}', ha='center', va='bottom', fontsize=8)
        else:
            ax.text(0.5, 0.5, "No Data Available", ha='center')

        canvas.figure.tight_layout()
        layout.addWidget(canvas)
        return page

    # ------------------------------------------------------------------------
    # PAGE 3: LAP PROGRESSION (Driver Menu + Graph)
    # ------------------------------------------------------------------------
    def _create_pace_tab(self):
        page = QWidget()
        # Splitter to hold Driver List (Left) and Graph (Right)
        splitter = QHBoxLayout(page)
        splitter.setContentsMargins(0, 0, 0, 0)
        splitter.setSpacing(0)

        # --- LEFT: Driver List ---
        driver_panel = QWidget()
        driver_panel.setFixedWidth(180)
        driver_panel.setStyleSheet("background-color: #F9F9F9; border-right: 1px solid #ccc;")
        p_layout = QVBoxLayout(driver_panel)
        p_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl = QLabel("SELECT DRIVER")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("padding: 15px; font-weight: bold; color: #555;")
        p_layout.addWidget(lbl)

        self.driver_list_widget = QListWidget()
        self.driver_list_widget.setStyleSheet("""
            QListWidget { border: none; background-color: #F9F9F9; }
            QListWidget::item { height: 40px; padding-left: 10px; }
            QListWidget::item:selected { background-color: #e10600; color: white; }
        """)
        
        # Populate Drivers (Sort by finishing position if available, else name)
        # Using self.session.drivers gives driver numbers. We want Abbreviations.
        drivers_to_show = []
        try:
            # Try to get results to sort by position
            if hasattr(self.session, 'results') and not self.session.results.empty:
                for drv_code in self.session.results['Abbreviation']:
                    drivers_to_show.append(drv_code)
            else:
                # Fallback to unsorted unique drivers from laps
                drivers_to_show = sorted(pd.unique(self.laps['Driver']))
        except:
             drivers_to_show = sorted(pd.unique(self.laps['Driver']))

        for drv in drivers_to_show:
            self.driver_list_widget.addItem(drv)

        self.driver_list_widget.itemClicked.connect(self._update_pace_plot)
        p_layout.addWidget(self.driver_list_widget)
        
        splitter.addWidget(driver_panel)

        # --- RIGHT: Graph ---
        graph_panel = QWidget()
        g_layout = QVBoxLayout(graph_panel)
        g_layout.setContentsMargins(20, 20, 20, 20)

        self.pace_canvas = FigureCanvas(Figure(figsize=(10, 6)))
        self.pace_ax = self.pace_canvas.figure.subplots()
        
        g_layout.addWidget(self.pace_canvas)
        splitter.addWidget(graph_panel)

        # Select first driver by default if available
        if self.driver_list_widget.count() > 0:
            self.driver_list_widget.setCurrentRow(0)
            self._update_pace_plot(self.driver_list_widget.item(0))

        return page

    def _update_pace_plot(self, item):
        driver = item.text()
        self.pace_ax.clear()

        # 1. Determine Threshold for "Clean" Laps
        # We filter out very slow laps (Safety Car, In/Out laps) to keep the graph readable.
        # Threshold = 115% of the absolute fastest lap of the race.
        threshold = 9999
        try:
            fastest_lap = self.laps.pick_fastest()
            if fastest_lap is not None:
                fastest_time = fastest_lap['LapTime'].total_seconds()
                threshold = fastest_time * 1.15
        except:
            pass

        # 2. Identify the Race Leader (Winner)
        leader_code = None
        try:
            if hasattr(self.session, 'results') and not self.session.results.empty:
                leader_code = self.session.results.iloc[0]['Abbreviation']
        except:
            pass

        # 3. Plot Leader Comparison (Dotted Line)
        # We plot this FIRST so it stays in the background
        if leader_code and driver != leader_code:
            leader_laps = self.laps.pick_drivers(leader_code)
            if not leader_laps.empty:
                leader_laps = leader_laps.dropna(subset=['LapTime'])
                # Filter leader's laps using same threshold so scales match
                clean_leader = leader_laps[leader_laps['LapTime'].dt.total_seconds() < threshold]
                
                if not clean_leader.empty:
                    lx = clean_leader['LapNumber']
                    ly = clean_leader['LapTime'].dt.total_seconds()
                    
                    self.pace_ax.plot(
                        lx, ly, 
                        color='#999999',       # Grey color
                        linestyle='--',        # Dotted/Dashed
                        linewidth=1.5, 
                        alpha=0.7, 
                        label=f"Leader ({leader_code})"
                    )

        # 4. Plot Selected Driver (Solid Line)
        drv_laps = self.laps.pick_drivers(driver)
        
        if not drv_laps.empty:
            drv_laps = drv_laps.dropna(subset=['LapTime'])
            # Filter slow laps
            clean_drv = drv_laps[drv_laps['LapTime'].dt.total_seconds() < threshold]
            
            if not clean_drv.empty:
                x = clean_drv['LapNumber']
                y = clean_drv['LapTime'].dt.total_seconds()
                
                # Get Team Color
                color = f"#{''.join([f'{c:02x}' for c in get_driver_color(driver, self.session)])}"
                
                self.pace_ax.plot(
                    x, y, 
                    color=color, 
                    marker='o', 
                    markersize=4, 
                    linestyle='-', 
                    linewidth=2, 
                    label=driver
                )
                
                stint_changes = clean_drv.loc[clean_drv['Compound'] != clean_drv['Compound'].shift(1)]
                
                for idx, row in stint_changes.iterrows():
                    lap = row['LapNumber']
                    compound = row['Compound']
                    # Draw a vertical line for the pit stop/change
                    self.pace_ax.axvline(x=lap, color=color, linestyle=':', alpha=0.4)
                    self.pace_ax.text(lap, self.pace_ax.get_ylim()[0], f" {compound}", 
                                    rotation=90, verticalalignment='bottom', fontsize=8, color='#333')
            else:
                 self.pace_ax.text(0.5, 0.5, "No Representative Lap Data (Too Slow/DNF)", ha='center')

            # Graph Styling
            self.pace_ax.set_title(f"Pace Comparison: {driver} vs Leader", fontsize=14, fontweight='bold')
            self.pace_ax.set_xlabel("Lap Number")
            self.pace_ax.set_ylabel("Lap Time (s)")
            self.pace_ax.grid(True, linestyle='--', alpha=0.3)
            self.pace_ax.legend()
            
        else:
            self.pace_ax.text(0.5, 0.5, "No Data for Driver", ha='center')

        self.pace_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--session", type=str, default="R")
    args = parser.parse_args()

    window = AnalyticsWindow(args.year, args.round, args.session)
    window.show()
    sys.exit(app.exec())