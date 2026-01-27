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
from PySide6.QtGui import QFont
import subprocess
import tempfile
import uuid

from data_engine import get_race_weekends_by_year, enable_cache, load_session


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
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # 1. Header
        header_label = QLabel("F1 Insight Hub")
        header_font = QFont()
        header_font.setPointSize(24)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header_label)

        subtitle = QLabel(
            "Telemetry Visualization & Machine Learning Analytics"
        )
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle.setFont(subtitle_font)
        main_layout.addWidget(subtitle)
        
        main_layout.addSpacing(20) # Add some breathing room

        # 2. Year Selection (Remains at top)
        year_layout = QHBoxLayout()
        year_label = QLabel("Select Year:")
        year_label_font = QFont()
        year_label_font.setPointSize(16)
        year_label.setFont(year_label_font)

        self.year_combo = QComboBox()
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
        # NEW: Horizontal Layout for Calendar (Left) and Sessions (Right)
        # ====================================================================
        content_layout = QHBoxLayout()
        
        # --- LEFT SIDE: Calendar ---
        calendar_group = QGroupBox("Race Calendar")
        calendar_layout = QVBoxLayout()
        
        self.schedule_tree = QTreeWidget()
        self.schedule_tree.setHeaderLabels(
            ["Round", "Event", "Country", "Date"]
        )
        self.schedule_tree.setColumnWidth(0, 90)
        self.schedule_tree.setColumnWidth(1, 330)
        self.schedule_tree.setColumnWidth(2, 240)
        self.schedule_tree.itemClicked.connect(self.on_event_selected)
        
        calendar_layout.addWidget(self.schedule_tree)
        calendar_group.setLayout(calendar_layout)
        
        # Add to content layout with Stretch=3 (takes up ~75% width)
        content_layout.addWidget(calendar_group, 3)

        # --- RIGHT SIDE: Session Selection ---
        right_panel_layout = QVBoxLayout()
        
        # Session Type Box
        session_group = QGroupBox("Select Session Type")
        session_font = QFont()
        session_font.setBold(True)
        session_group.setFont(session_font)
        
        session_layout = QVBoxLayout()
        session_layout.setSpacing(15) # Space out the radio buttons

        self.session_race = QRadioButton("Race")
        self.session_race.setChecked(True)
        self.session_qualifying = QRadioButton("Qualifying")
        self.session_sprint = QRadioButton("Sprint")
        self.session_sprint_qual = QRadioButton("Sprint Qualifying")
        
        # Increase font size for options
        opt_font = QFont()
        opt_font.setPointSize(11)
        self.session_race.setFont(opt_font)
        self.session_qualifying.setFont(opt_font)
        self.session_sprint.setFont(opt_font)
        self.session_sprint_qual.setFont(opt_font)

        session_layout.addWidget(self.session_race)
        session_layout.addWidget(self.session_qualifying)
        session_layout.addWidget(self.session_sprint)
        session_layout.addWidget(self.session_sprint_qual)
        session_layout.addStretch() # Push radio buttons to top
        session_group.setLayout(session_layout)
        
        # Add to right panel
        right_panel_layout.addWidget(session_group)
        right_panel_layout.addStretch() # Push everything up
        
        # Add to content layout with Stretch=1 (takes up ~25% width)
        content_layout.addLayout(right_panel_layout, 1)

        # Add the combined layout to main
        main_layout.addLayout(content_layout)

        # ====================================================================
        # NEW: Big Square Module Buttons
        # ====================================================================
        
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(20) # Gap between squares

        # 1. Vision Module Button
        self.btn_vision = QPushButton("RaceVision")
        self.btn_vision.setFixedSize(370, 220) # MAKE IT SQUARE
        self.btn_vision.clicked.connect(self.launch_vision_module)
        self.btn_vision.setStyleSheet('''
            QPushButton {
                background-color: #e10600;
                color: white;
                font-size: 46px;
                font-weight: bold;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ff1e00;
                border: 2px solid white;
            }''')

        # 2. Analytics Module Button
        self.btn_analytics = QPushButton("RaceAnalytics")
        self.btn_analytics.setFixedSize(370, 220) # MAKE IT SQUARE
        self.btn_analytics.setEnabled(False)
        self.btn_analytics.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #888888;
                font-size: 46px;
                font-weight: bold;
                border-radius: 15px;
                border: 1px solid #444;
            }
        """)

        # 3. Intelligence Module Button
        self.btn_intelligence = QPushButton("RaceIntelligence")
        self.btn_intelligence.setFixedSize(370, 220) # MAKE IT SQUARE
        self.btn_intelligence.setEnabled(False)
        self.btn_intelligence.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                color: #888888;
                font-size: 46px;
                font-weight: bold;
                border-radius: 15px;
                border: 1px solid #444;
            }
        """)

        buttons_layout.addStretch() # Center the buttons group
        buttons_layout.addWidget(self.btn_vision)
        buttons_layout.addWidget(self.btn_analytics)
        buttons_layout.addWidget(self.btn_intelligence)
        buttons_layout.addStretch() # Center the buttons group
        
        main_layout.addLayout(buttons_layout)
        main_layout.addSpacing(10)

        # Status bar
        self.status_label = QLabel("Ready. Select a race to begin analysis.")
        self.status_label.setStyleSheet("padding: 8px; background-color: #f0f0f0;font-size: 20px;color: #333333; border-radius: 4px;")
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

        # Enable/disable sprint options based on event type
        has_sprint = "sprint" in self.selected_event["type"].lower()
        self.session_sprint.setEnabled(has_sprint)
        self.session_sprint_qual.setEnabled(has_sprint)

    def get_selected_session_type(self):
        """Get the selected session type code"""
        if self.session_qualifying.isChecked():
            return "Q"
        elif self.session_sprint.isChecked():
            return "S"
        elif self.session_sprint_qual.isChecked():
            return "SQ"
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
            "Q": "Qualifying",
            "S": "Sprint",
            "SQ": "Sprint Qualifying",
        }
        session_name = session_names.get(session_type, "Session")

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
