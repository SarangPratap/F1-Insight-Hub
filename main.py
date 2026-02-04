"""
F1 INSIGHT HUB - Main Launcher
Persistent menu for Year/Round selection and module launching
"""

import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QGroupBox,
    QRadioButton,
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QPixmap
import subprocess
import tempfile
import uuid

from data_engine import get_race_weekends_by_year, enable_cache


class FetchScheduleWorker(QThread):
    """Worker thread to fetch race schedule without blocking UI"""

    result = Signal(object)
    error = Signal(str)

    def __init__(self, year, parent=None):
        super().__init__(parent)
        self.year = year

    def run(self):
        try:
            enable_cache()
            events = get_race_weekends_by_year(self.year)
            self.result.emit(events)
        except Exception as e:
            self.error.emit(str(e))


class F1InsightHubLauncher(QMainWindow):
    """Main launcher window for F1 Insight Hub"""

    def __init__(self):
        super().__init__()
        self.worker = None
        self.events_data = []
        self.selected_event = None

        self.setWindowTitle("F1 Insight Hub - Race Analysis Platform")
        self._setup_ui()
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        # Load initial schedule
        self.load_schedule()

    def _setup_ui(self):
        """Setup the main UI layout"""
        
        # --- GLOBAL STYLESHEET ---
        # Sets White Background, Jura Font, Black Text, and Red Radio Buttons globally
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #FFFFFF;
                color: #000000;
                font-family: 'Jura', sans-serif;
            }
            QLabel {
                color: #000000;
            }
            QGroupBox {
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: #000000;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            /* --- RED RADIO BUTTONS --- */
            QRadioButton {
                spacing: 8px;
                color: #000000;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
                border-radius: 9px;
                border: 2px solid #555555;
            }
            QRadioButton::indicator:checked {
                background-color: #e10600; /* F1 Red */
                border: 2px solid #e10600;
            }
            QRadioButton::indicator:unchecked:hover {
                border: 2px solid #e10600;
            }
            /* --- TREE WIDGET STYLING --- */
            QTreeWidget {
                border: 1px solid #ccc;
                font-size: 13px;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # ====================================================================
        # 1. NEW HEADER WITH LOGO IMAGE
        # ====================================================================
        header_container = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(10)
        header_container.setLayout(header_layout)

        # A. The Logo Image
        logo_label = QLabel()
        logo_pixmap = QPixmap("f1_logo.png") 
        
        if not logo_pixmap.isNull():
            scaled_logo = logo_pixmap.scaledToHeight(85, Qt.SmoothTransformation)
            logo_label.setPixmap(scaled_logo)
        else:
            # Fallback if image missing
            logo_label.setText("F1") 
            logo_label.setStyleSheet("font-size: 30px; font-weight: bold; color: #e10600;")
        
        # B. The Text
        title_text = QLabel("Insight Hub")
        title_text.setStyleSheet("font-size: 53px; margin-left: 0px;")
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_text)
        main_layout.addWidget(header_container)

        subtitle = QLabel("Telemetry Visualization & Machine Learning Analytics")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("font-size: 20px; margin-bottom: 20px;")
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(10)

        # ====================================================================
        # 2. Year Selection
        # ====================================================================
        year_layout = QHBoxLayout()
        year_label = QLabel("Select Year:")
        year_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                min-width: 100px;
                font-size: 14px;
            }
        """)
        current_year = 2025
        for year in range(current_year, 2009, -1):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))
        self.year_combo.currentTextChanged.connect(self.load_schedule)

        year_layout.addWidget(year_label)
        year_layout.addWidget(self.year_combo)
        year_layout.addStretch()
        main_layout.addLayout(year_layout)

        # ====================================================================
        # 3. Calendar (Left) and Sessions (Right)
        # ====================================================================
        content_layout = QHBoxLayout()
        
        # --- LEFT SIDE: Calendar ---
        calendar_group = QGroupBox("Race Calendar")
        calendar_layout = QVBoxLayout()
        
        self.schedule_tree = QTreeWidget()
        self.schedule_tree.setHeaderLabels(["Round", "Event", "Country", "Date"])
        self.schedule_tree.setColumnWidth(0, 90)
        self.schedule_tree.setColumnWidth(1, 330)
        self.schedule_tree.setColumnWidth(2, 240)
        self.schedule_tree.setAlternatingRowColors(True)
        self.schedule_tree.itemClicked.connect(self.on_event_selected)
        
        calendar_layout.addWidget(self.schedule_tree)
        calendar_group.setLayout(calendar_layout)
        
        content_layout.addWidget(calendar_group, 3)

        # --- RIGHT SIDE: Session Selection ---
        right_panel_layout = QVBoxLayout()
        
        session_group = QGroupBox("Select Session Type")
        # Global stylesheet handles font-family, we just set bold here
        session_group.setStyleSheet("font-weight: bold;")
        
        session_layout = QVBoxLayout()
        session_layout.setSpacing(15) 

        self.session_race = QRadioButton("Race")
        self.session_race.setChecked(True)
        self.session_sprint = QRadioButton("Sprint")
        
        # Increase font size for options
        opt_style = "font-size: 14px;"
        self.session_race.setStyleSheet(opt_style)
        self.session_sprint.setStyleSheet(opt_style)

        session_layout.addWidget(self.session_race)
        session_layout.addWidget(self.session_sprint)
        session_layout.addStretch()
        session_group.setLayout(session_layout)
        
        right_panel_layout.addWidget(session_group)
        right_panel_layout.addStretch()
        
        content_layout.addLayout(right_panel_layout, 1)
        main_layout.addLayout(content_layout)

        # ====================================================================
        # 4. Big Square Module Buttons
        # ====================================================================
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20)

        # 1. Vision Module Button
        self.btn_vision = QPushButton("RaceVision")
        self.btn_vision.setFixedSize(370, 220)
        self.btn_vision.clicked.connect(self.launch_vision_module)
        self.btn_vision.setStyleSheet('''
            QPushButton {
                background-color: #e10600;
                color: white;
                font-size: 46px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ff1e00;
                border: 2px solid white;
            }''')

        # 2. Analytics Module Button
        self.btn_analytics = QPushButton("RaceAnalytics")
        self.btn_analytics.setFixedSize(370, 220)
        self.btn_analytics.setEnabled(True)
        self.btn_analytics.clicked.connect(self.launch_analytics_module)
        self.btn_analytics.setStyleSheet("""
            QPushButton {
                background-color: #e10600;
                color: white;
                font-size: 46px;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ff1e00;
                border: 2px solid white;
            }""")

        # 3. Intelligence Module Button
        self.btn_intelligence = QPushButton("RaceIntelligence")
        self.btn_intelligence.setFixedSize(370, 220)
        self.btn_intelligence.setEnabled(False)
        self.btn_intelligence.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: white;
                font-size: 46px;
                border-radius: 15px;
                border: 1px solid #444;
            }
        """)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_vision)
        buttons_layout.addWidget(self.btn_analytics)
        buttons_layout.addWidget(self.btn_intelligence)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        main_layout.addSpacing(10)

        # Status bar
        self.status_label = QLabel("Ready. Select a race to begin analysis.")
        self.status_label.setStyleSheet("""
            padding: 8px; 
            background-color: #ff2800; 
            font-size: 16px; 
            color: white; 
            border-radius: 4px;
        """)
        main_layout.addWidget(self.status_label)

    def load_schedule(self):
        """Load race schedule for selected year"""
        year = int(self.year_combo.currentText())
        self.status_label.setText(f"Loading {year} race calendar...")

        self.worker = FetchScheduleWorker(year)
        self.worker.result.connect(self.on_schedule_loaded)
        self.worker.error.connect(self.on_schedule_error)
        self.worker.start()

    def on_schedule_loaded(self, events):
        """Handle schedule data loaded"""
        self.events_data = events
        self.schedule_tree.clear()

        for event in events:
            item = QTreeWidgetItem(
                [
                    str(event["round_number"]),
                    event["event_name"],
                    event.get("country", "N/A"),
                    event["date"],
                    event["type"],
                ]
            )
            item.setData(0, Qt.UserRole, event)
            self.schedule_tree.addTopLevelItem(item)

        self.status_label.setText(
            f"Loaded {len(events)} races. Select an event to continue."
        )

    def on_schedule_error(self, error_msg):
        """Handle schedule loading error"""
        QMessageBox.critical(self, "Error", f"Failed to load schedule: {error_msg}")
        self.status_label.setText("Error loading schedule.")

    def on_event_selected(self, item, column):
        """Handle race event selection"""
        self.selected_event = item.data(0, Qt.UserRole)
        event_name = self.selected_event["event_name"]
        self.status_label.setText(
            f"Selected: {event_name}. Choose a session and launch a module."
        )

    def get_selected_session_type(self):
        """Get the selected session type code"""
        if self.session_sprint.isChecked():
            return "S"
        else:
            return "R"

    def launch_vision_module(self):
        """Launch the Vision Module (Race Replay)"""
        if not self.selected_event:
            QMessageBox.warning(
                self,
                "No Event Selected",
                "Please select a race event from the calendar first.",
            )
            return

        year = int(self.year_combo.currentText())
        round_number = self.selected_event["round_number"]
        session_type = self.get_selected_session_type()

        session_names = {
            "R": "Race",
            "S": "Sprint",
        }
        session_name = session_names.get(session_type, "Session")

        # Validate session type exists for this event
        event_type = self.selected_event.get("type", "").lower()
        
        if session_type == "S" and "sprint" not in event_type:
            error_msg = f"❌ Error: Session type '{session_name}' does not exist for {self.selected_event['event_name']}"
            self.status_label.setText(error_msg)
            # QMessageBox.warning(
            #     self,
            #     "Session Not Available",
            #     f"Sprint session is not available for this event.\nPlease select a different session.",
            # )
            return

        self.status_label.setText(
            f"Loading {session_name} data for {self.selected_event['event_name']}..."
        )

        # Launch vision module in separate process
        ready_file = os.path.join(
            tempfile.gettempdir(), f"f1hub_ready_{uuid.uuid4().hex}.tmp"
        )

        cmd = [
            sys.executable,
            "module_vision.py",
            "--year",
            str(year),
            "--round",
            str(round_number),
            "--session",
            session_type,
            "--ready-file",
            ready_file,
        ]

        try:
            subprocess.Popen(cmd)
            self.status_label.setText(
                f"Vision Module launched: {self.selected_event['event_name']} - {session_name}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Launch Error", f"Failed to launch Vision Module: {str(e)}"
            )
            self.status_label.setText("Error launching module.")

    def launch_analytics_module(self):
        """Launch the Analytics Module"""
        if not self.selected_event:
            QMessageBox.warning(self, "No Event Selected", "Please select a race event first.")
            return

        year = int(self.year_combo.currentText())
        round_number = self.selected_event["round_number"]
        session_type = self.get_selected_session_type()

        self.status_label.setText(f"Launching Analytics for {self.selected_event['event_name']}...")

        cmd = [
            sys.executable,
            "module_analytics.py",
            "--year", str(year),
            "--round", str(round_number),
            "--session", session_type,
        ]

        try:
            subprocess.Popen(cmd)
        except Exception as e:
            QMessageBox.critical(self, "Launch Error", f"Failed to launch Analytics: {str(e)}")


def main():
    """Main entry point"""
    enable_cache()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look

    launcher = F1InsightHubLauncher()
    launcher.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
