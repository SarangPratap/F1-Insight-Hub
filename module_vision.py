# ============================================================================
#F1 INSIGHT HUB - RaceVision
# ============================================================================

import os
import sys
import arcade
import arcade.color
import numpy as np
import argparse
from typing import List, Optional, Tuple, Dict, Any
import time

from config import (
    FPS,
    SCREEN_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_TITLE_RACE,
    SCREEN_TITLE_QUALIFYING,
    PLAYBACK_SPEEDS,
    DEFAULT_TRACK_WIDTH,
    UI_LEFT_MARGIN,
    UI_RIGHT_MARGIN,
    format_time,
    get_tyre_color,
    get_tyre_compound_str,
)
from data_engine import (
    enable_cache,
    load_session,
    get_race_telemetry,
    get_quali_telemetry,
    get_circuit_rotation,
)


# ============================================================================
# UI COMPONENTS (ARCADE 3.0+ WITH MODERN SYNTAX)
# ============================================================================


class BaseComponent:
    """Base class for all UI components"""

    def on_resize(self, window):
        """Handle window resize events"""
        pass

    def draw(self, window):
        """Draw the component"""
        pass

    def on_mouse_press(
        self, window, x: float, y: float, button: int, modifiers: int
    ) -> bool:
        """Handle mouse press events. Returns True if event was handled."""
        return False


class LeaderboardComponent(BaseComponent):
    """Refactored Leaderboard with clean Arcade 3.0+ syntax"""

    def __init__(self, x: int = 20, width: int = 240, visible: bool = True):
        self.x = x
        self.width = width
        self.visible = visible
        self.entries = []
        self.selected_drivers = set()

        self.row_height = 24  # Increased slightly for better spacing
        self.header_height = 40
        self.padding = 10

    def set_entries(self, entries: List[Dict[str, Any]]):
        self.entries = entries

    def on_resize(self, window):
        """Dynamic positioning relative to window edge"""
        self.x = max(20, window.width - UI_RIGHT_MARGIN + 12)

    def draw(self, window):
        if not self.visible or not self.entries:
            return

        # 1. Calculate Layout Constants
        top_y = window.height - 60
        content_height = len(self.entries) * self.row_height
        total_height = self.header_height + content_height + 10

        # Center coordinates for XYWH rectangles (Arcade 3.x uses center-based rects)
        center_x = self.x + (self.width / 2)
        center_y = top_y - (total_height / 2)

        # 2. Draw Background Panel (Single Call)
        panel_rect = arcade.rect.XYWH(center_x, center_y, self.width, total_height)
        arcade.draw_rect_filled(panel_rect, (20, 20, 25, 220))  # Glassmorphism dark
        arcade.draw_rect_outline(panel_rect, (255, 255, 255, 40), border_width=1)

        # 3. Draw Header
        header_y = top_y - 20
        # Red Accent Bar
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.x + 4, header_y, 4, 24), (255, 40, 40)
        )
        arcade.draw_text(
            "LEADERBOARD",
            self.x + 18,
            header_y,
            arcade.color.WHITE,
            14,
            bold=True,
            italic=True,
            anchor_y="center",
        )

        # 4. Draw Rows
        list_top_y = top_y - self.header_height

        for i, entry in enumerate(self.entries):
            # Row Center Y
            row_y = list_top_y - (i * self.row_height) - (self.row_height / 2)

            driver = entry.get("driver", "???")
            driver_color = entry.get("color", arcade.color.WHITE)
            tyre_str = get_tyre_compound_str(entry.get("tyre", -1))
            tyre_color = get_tyre_color(tyre_str)

            # Highlight Selection or Zebra Striping
            if driver in self.selected_drivers:
                row_rect = arcade.rect.XYWH(
                    center_x, row_y, self.width - 4, self.row_height - 2
                )
                arcade.draw_rect_filled(row_rect, (225, 6, 0, 80))
            elif i % 2 == 0:
                row_rect = arcade.rect.XYWH(
                    center_x, row_y, self.width - 4, self.row_height - 2
                )
                arcade.draw_rect_filled(row_rect, (255, 255, 255, 10))

            # Data Points
            arcade.draw_text(
                f"P{entry.get('position', 0)}",
                self.x + 10,
                row_y,
                arcade.color.GOLD if i == 0 else arcade.color.WHITE,
                11,
                bold=True,
                anchor_y="center",
            )

            arcade.draw_text(
                driver.upper(),
                self.x + 45,
                row_y,
                driver_color,
                12,
                bold=True,
                anchor_y="center",
            )

            # Tyre Visual
            tyre_x = (
                self.x + self.width - 30
            )  #  increase the constant to move tyre icon left -30 on x axis for me
            arcade.draw_circle_filled(tyre_x, row_y, 12, (10, 10, 10))
            arcade.draw_circle_outline(tyre_x, row_y, 9.5, tyre_color, border_width=2)
            arcade.draw_text(
                tyre_str[:1],
                tyre_x,
                row_y,
                arcade.color.WHITE,
                10,
                bold=True,
                anchor_x="center",
                anchor_y="center",
            )

    def on_mouse_press(
        self, window, x: float, y: float, button: int, modifiers: int
    ) -> bool:
        if not self.visible or not self.entries:
            return False

        # 1. Horizontal Boundary Check
        if not (self.x <= x <= self.x + self.width):
            return False

        list_start_y = window.height - 60 - self.header_height

        # 2. Iterate through rows to find the click target
        for i, entry in enumerate(self.entries):
            row_top = list_start_y - (i * self.row_height)
            row_bottom = row_top - self.row_height

            if row_bottom <= y <= row_top:
                driver = entry.get("driver")
                if driver:
                    # Check if the clicked driver is already the one selected
                    was_selected = driver in self.selected_drivers

                    # SINGLE SELECTION: Clear all previous highlights
                    self.selected_drivers.clear()

                    # If it wasn't selected before, select it now.
                    # (This allows you to click a driver once to highlight, and again to un-highlight)
                    if not was_selected:
                        self.selected_drivers.add(driver)

                return True  # Event handled, stop checking other rows

        return False


class WeatherComponent(BaseComponent):
    """Display weather information"""

    def __init__(self, left: int = 20, top_offset: int = 170, visible: bool = True):
        self.left = left
        self.top_offset = top_offset
        self.visible = visible
        self.weather_data = None

    def set_weather(self, weather_data: Optional[Dict[str, float]]):
        """Update weather data"""
        self.weather_data = weather_data

    def draw(self, window):
        """Draw weather panel"""
        if not self.visible or not self.weather_data:
            return

        y = window.height - self.top_offset

        # Draw background using Arcade 3.0+ syntax
        weather_rect = arcade.rect.XYWH(self.left + 100, y - 60, 200, 120)
        arcade.draw_rect_filled(weather_rect, (40, 40, 45, 200))

        # Draw header
        arcade.draw_text(
            "WEATHER", self.left + 10, y, arcade.color.WHITE, 12, bold=True
        )
        y -= 25

        # Draw weather info
        if "air_temp" in self.weather_data:
            arcade.draw_text(
                f"Air: {self.weather_data['air_temp']:.1f}°C",
                self.left + 10,
                y,
                arcade.color.WHITE,
                10,
            )
            y -= 18

        if "track_temp" in self.weather_data:
            arcade.draw_text(
                f"Track: {self.weather_data['track_temp']:.1f}°C",
                self.left + 10,
                y,
                arcade.color.WHITE,
                10,
            )
            y -= 18

        if "humidity" in self.weather_data:
            arcade.draw_text(
                f"Humidity: {self.weather_data['humidity']:.0f}%",
                self.left + 10,
                y,
                arcade.color.WHITE,
                10,
            )
            y -= 18

        if "wind_speed" in self.weather_data:
            arcade.draw_text(
                f"Wind: {self.weather_data['wind_speed']:.1f} km/h",
                self.left + 10,
                y,
                arcade.color.WHITE,
                10,
            )


class RaceProgressBarComponent(BaseComponent):
    """Vertical progress bar anchored to the left side"""

    # Event type constants (Same as before)
    EVENT_DNF = "dnf"
    EVENT_YELLOW_FLAG = "yellow"
    EVENT_SAFETY_CAR = "safety_car"
    EVENT_RED_FLAG = "red"
    EVENT_VSC = "vsc"

    def __init__(
        self,
        x: float = 30,      # Fixed X position (Left side)
        width: float = 16,  # Thickness of the bar
        visible: bool = True,
    ):
        self.x = x
        self.width = width
        self.visible = visible
        self.progress = 0.0
        self.events = []
        
        # Dimensions calculated in on_resize
        self.height = 0
        self.center_y = 0

    def set_events(self, events: List[Dict[str, Any]]):
        self.events = events

    def set_progress(self, progress: float):
        self.progress = max(0.0, min(1.0, progress))

    def on_resize(self, window):
        """Resize vertically based on window height"""
        # Leave 60px padding at top and bottom
        vertical_padding = 60
        self.height = window.height - (vertical_padding * 2)
        self.center_y = window.height / 2

    def draw(self, window):
        if not self.visible:
            return

        # Calculate coordinates
        bottom_y = self.center_y - (self.height / 2)
        
        # 1. Draw Background Track (Vertical)
        bg_rect = arcade.rect.XYWH(self.x, self.center_y, self.width, self.height)
        arcade.draw_rect_filled(bg_rect, (40, 40, 45))
        arcade.draw_rect_outline(bg_rect, (100, 100, 100), 1)

        # 2. Draw Progress Fill (Growing Upwards)
        fill_height = self.height * self.progress
        if fill_height > 0:
            # Center of the fill rect must be calculated carefully
            fill_center_y = bottom_y + (fill_height / 2)
            fill_rect = arcade.rect.XYWH(self.x, fill_center_y, self.width, fill_height)
            arcade.draw_rect_filled(fill_rect, (225, 6, 0)) # F1 Red

        # 3. Draw Current Position Marker (Triangle pointing Right)
        marker_y = bottom_y + fill_height
        arcade.draw_triangle_filled(
            self.x + (self.width / 2) + 2, marker_y,       # Tip (Right)
            self.x - (self.width / 2) - 4, marker_y + 5,   # Top-Left
            self.x - (self.width / 2) - 4, marker_y - 5,   # Bottom-Left
            arcade.color.WHITE
        )


class DriverInfoComponent(BaseComponent):
    """Display detailed info with Full Name, No DRS, and Gear Label"""

    def __init__(self, left: int = 20, width: int = 200, driver_names: Dict = None):
        self.left = left
        self.width = width
        self.driver_data = None
        self.visible = False
        # Store the name mapping (Abbreviation -> Full Name)
        self.driver_names = driver_names or {}

    def set_driver_data(self, driver_data: Optional[Dict[str, Any]]):
        self.driver_data = driver_data
        self.visible = driver_data is not None

    def draw(self, window):
        if not self.visible or not self.driver_data:
            return

        # 1. Calculate Panel Coordinates
        panel_center_y = window.height / 2
        panel_height = 240
        center_x = self.left + (self.width / 2)
        
        # Background
        panel_rect = arcade.rect.XYWH(center_x, panel_center_y, self.width, panel_height)
        arcade.draw_rect_filled(panel_rect, (40, 40, 45, 230))
        arcade.draw_rect_outline(panel_rect, (255, 255, 255, 30), 1)

        # ---------------------------------------------------------
        # TOP SECTION: Text Info
        # ---------------------------------------------------------
        current_y = panel_center_y + (panel_height / 2) - 35
        
        # --- DRIVER NAME (Full Name) ---
        driver_code = self.driver_data.get("driver", "???")
        # Lookup full name, default to code if not found
        full_name = self.driver_names.get(driver_code, driver_code)
        
        # Adjust font size: Smaller for full names (e.g. "Max Verstappen"), larger for codes
        font_size = 17
        
        arcade.draw_text(
            full_name, 
            self.left + 20, 
            current_y, 
            arcade.color.WHITE, 
            font_size, 
            bold=True
        )

        current_y -= 45

        # --- SPEED (Left Side) ---
        speed = int(self.driver_data.get("speed", 0))
        arcade.draw_text(f"{speed}", self.left + 20, current_y, arcade.color.WHITE, 27, bold=True)
        arcade.draw_text("km/h", self.left + 95, current_y, arcade.color.GRAY, 16)
        
        # --- GEAR (Right Side) ---
        gear = self.driver_data.get("gear", 0)
        gear_str = str(gear) if gear > 0 else "N"
        
        # Gear Box Position
        gear_x = self.left + self.width - 40
        gear_box_y = current_y + 15
        
        # Box
        arcade.draw_rect_outline(arcade.rect.XYWH(gear_x, gear_box_y, 30, 30), arcade.color.WHITE, 2)
        
        # Number
        arcade.draw_text(gear_str, gear_x, gear_box_y, arcade.color.CYAN, 20, 
                         bold=True, anchor_x="center", anchor_y="center")
        
        # "GEAR" Label (Below the box)
        arcade.draw_text("GEAR", gear_x, gear_box_y - 32, arcade.color.GRAY, 9, 
                         anchor_x="center", bold=True)

        # ---------------------------------------------------------
        # BOTTOM SECTION: Animated Pedals
        # ---------------------------------------------------------
        bar_width = 40
        max_bar_height = 80
        bars_bottom_y = panel_center_y - (panel_height / 2) + 20
        
        throttle = self.driver_data.get("throttle", 0)
        brake = self.driver_data.get("brake", 0)

        # --- THROTTLE (Green) ---
        thr_x = center_x + 30
        # Background
        arcade.draw_rect_filled(arcade.rect.XYWH(thr_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (20, 20, 20))
        arcade.draw_rect_outline(arcade.rect.XYWH(thr_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (100, 100, 100), 1)
        # Fill
        thr_height = (throttle / 100) * max_bar_height
        if thr_height > 0:
            arcade.draw_rect_filled(arcade.rect.XYWH(thr_x, bars_bottom_y + thr_height/2, bar_width - 4, thr_height), (0, 255, 0))
        # Label
        arcade.draw_text("THR", thr_x, bars_bottom_y - 12, arcade.color.GRAY, 10, anchor_x="center")

        # --- BRAKE (Red) ---
        brk_x = center_x - 30
        # Background
        arcade.draw_rect_filled(arcade.rect.XYWH(brk_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (20, 20, 20))
        arcade.draw_rect_outline(arcade.rect.XYWH(brk_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (100, 100, 100), 1)
        # Fill
        safe_brake = min(100, max(0, brake))
        brk_height = (safe_brake / 100) * max_bar_height
        if brk_height > 0:
            arcade.draw_rect_filled(arcade.rect.XYWH(brk_x, bars_bottom_y + brk_height/2, bar_width - 4, brk_height), (255, 0, 0))
        # Label
        arcade.draw_text("BRK", brk_x, bars_bottom_y - 12, arcade.color.GRAY, 10, anchor_x="center")


class LegendComponent(BaseComponent):
    """Display controls legend anchored to the bottom-right"""

    def __init__(self, visible: bool = True):
        # We drop the 'x' argument because position is now dynamic
        self.visible = visible
        # Define the static dimensions of the panel for layout math
        self.width = 180
        self.height = 160
        # Placeholder for calculated position
        self.x = 0
        self.y = 0

    def on_resize(self, window):
        """Calculate position relative to the bottom-right corner"""
        padding = 20  # Space from the edge of the window
        self.x = window.width - self.width - padding
        self.y = padding  # Start 20 pixels up from the bottom edge (y=0 in Arcade)

    def draw(self, window):
        """Draw legend"""
        if not self.visible:
            return

        # Use the calculated self.x and self.y
        bottom_left_x = self.x
        # The starting Y coordinate for the text block (top of the panel area)
        current_y = self.y + self.height - 30

        # Draw Background Panel
        arcade.draw_rect_filled(
            arcade.rect.XYWH(
                bottom_left_x + self.width / 2,  # Center X
                self.y + self.height / 2,  # Center Y
                self.width,
                self.height,
            ),
            (20, 20, 25, 220),  # Semi-transparent dark background
        )

        # Draw Header
        arcade.draw_text(
            "CONTROLS", bottom_left_x + 10, current_y, arcade.color.CYAN, 12, bold=True
        )
        current_y -= 25  # Move down for the first list item

        # Draw list items
        arcade.draw_text(
            "SPACE: Pause/Resume", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "←/→: Rewind/Forward", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "↑/↓: Speed Up/Down", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "R: Restart", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "D: Toggle DRS Zones", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "L: Toggle Labels", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )
        current_y -= 16
        arcade.draw_text(
            "H: Toggle Help", bottom_left_x + 10, current_y, arcade.color.WHITE, 10
        )


class SessionInfoComponent(BaseComponent):
    """Display session information banner"""

    def __init__(self, session_info: Optional[Dict[str, Any]] = None):
        self.session_info = session_info or {}

    def draw(self, window):
        """Draw session info banner"""
        if not self.session_info:
            return

        y = window.height - 20

        event_name = self.session_info.get("event_name", "")
        year = self.session_info.get("year", "")

        info_text = f"{event_name} {year}"
        arcade.draw_text(
            info_text,
            window.width / 2,
            y,
            arcade.color.WHITE,
            14,
            anchor_x="center",
            bold=True,
        )


# ============================================================================
# TRACK RENDERING UTILITIES
# ============================================================================


def build_track_from_example_lap(
    example_lap, track_width: float = DEFAULT_TRACK_WIDTH
) -> Tuple:
    """
    Build track geometry from example lap telemetry

    Args:
        example_lap: Telemetry data with X, Y coordinates (pandas DataFrame)
        track_width: Width of track in meters

    Returns:
        Tuple with track geometry data:
        (plot_x_ref, plot_y_ref, x_inner, y_inner, x_outer, y_outer,
         x_min, x_max, y_min, y_max, drs_zones)

    Raises:
        ValueError: If example_lap is invalid or missing required columns
    """
    # Validation 1: Check if example_lap exists
    if example_lap is None:
        raise ValueError("example_lap cannot be None")

    # Validation 2: Check if DataFrame is empty
    if hasattr(example_lap, "empty") and example_lap.empty:
        raise ValueError("example_lap DataFrame is empty")

    # Validation 3: Check required columns
    required_columns = ["X", "Y", "DRS"]
    for col in required_columns:
        if col not in example_lap.columns:
            raise ValueError(f"Missing required column: {col}")

    # Validation 4: Check if we have enough data points
    if len(example_lap) < 10:
        raise ValueError(
            f"Insufficient data points: {len(example_lap)} (need at least 10)"
        )

    # Extract DRS zones
    try:
        drs_zones = plot_drs_zones(example_lap)
    except Exception as e:
        print(f"⚠️ Warning: Could not extract DRS zones: {e}")
        drs_zones = []

    plot_x_ref = example_lap["X"]
    plot_y_ref = example_lap["Y"]

    # Validation 5: Check for NaN or infinite values
    if plot_x_ref.isna().any() or plot_y_ref.isna().any():
        print("⚠️ Warning: NaN values found in coordinates, removing...")
        valid_mask = ~(plot_x_ref.isna() | plot_y_ref.isna())
        plot_x_ref = plot_x_ref[valid_mask]
        plot_y_ref = plot_y_ref[valid_mask]

        if len(plot_x_ref) < 10:
            raise ValueError("Too many invalid coordinates")

    # Compute tangents
    dx = np.gradient(plot_x_ref)
    dy = np.gradient(plot_y_ref)

    norm = np.sqrt(dx**2 + dy**2)
    norm[norm == 0] = 1.0  # Avoid division by zero
    dx /= norm
    dy /= norm

    # Compute normals
    nx = -dy
    ny = dx

    # Calculate track edges
    half_width = track_width / 2
    x_outer = plot_x_ref + nx * half_width
    y_outer = plot_y_ref + ny * half_width
    x_inner = plot_x_ref - nx * half_width
    y_inner = plot_y_ref - ny * half_width

    # World bounds
    x_min = min(plot_x_ref.min(), x_inner.min(), x_outer.min())
    x_max = max(plot_x_ref.max(), x_inner.max(), x_outer.max())
    y_min = min(plot_y_ref.min(), y_inner.min(), y_outer.min())
    y_max = max(plot_y_ref.max(), y_inner.max(), y_outer.max())

    # Validation 6: Check for valid bounds
    if x_min == x_max or y_min == y_max:
        raise ValueError("Track has zero width or height")

    return (
        plot_x_ref,
        plot_y_ref,
        x_inner,
        y_inner,
        x_outer,
        y_outer,
        x_min,
        x_max,
        y_min,
        y_max,
        drs_zones,
    )


def plot_drs_zones(example_lap) -> List[Dict[str, Any]]:
    """Extract DRS zones from telemetry
    """
    # Validation: Check if DRS column exists
    if "DRS" not in example_lap.columns:
        print("⚠️ Warning: No DRS column in telemetry data")
        return []

    # Validation: Check if X, Y columns exist
    if "X" not in example_lap.columns or "Y" not in example_lap.columns:
        print("⚠️ Warning: Missing X or Y coordinates for DRS zones")
        return []

    x_val = example_lap["X"]
    y_val = example_lap["Y"]
    drs_data = example_lap["DRS"]

    drs_zones = []
    drs_start = None

    try:
        for i, val in enumerate(drs_data):
            # Check for DRS active states (10=available, 12=enabled, 14=enabled)
            if val in [10, 12, 14]:
                if drs_start is None:
                    drs_start = i
            else:
                if drs_start is not None:
                    drs_end = i - 1

                    # Validation: Check indices are valid
                    if drs_start < len(x_val) and drs_end < len(x_val):
                        zone = {
                            "start": {
                                "x": float(x_val.iloc[drs_start]),
                                "y": float(y_val.iloc[drs_start]),
                                "index": drs_start,
                            },
                            "end": {
                                "x": float(x_val.iloc[drs_end]),
                                "y": float(y_val.iloc[drs_end]),
                                "index": drs_end,
                            },
                        }
                        drs_zones.append(zone)

                    drs_start = None

        # Handle DRS zone extending to end of lap
        if drs_start is not None:
            drs_end = len(drs_data) - 1

            if drs_start < len(x_val) and drs_end < len(x_val):
                zone = {
                    "start": {
                        "x": float(x_val.iloc[drs_start]),
                        "y": float(y_val.iloc[drs_start]),
                        "index": drs_start,
                    },
                    "end": {
                        "x": float(x_val.iloc[drs_end]),
                        "y": float(y_val.iloc[drs_end]),
                        "index": drs_end,
                    },
                }
                drs_zones.append(zone)

    except Exception as e:
        print(f"⚠️ Warning: Error extracting DRS zones: {e}")
        return []

    if drs_zones:
        print(f"✓ Found {len(drs_zones)} DRS zone(s)")

    return drs_zones


def extract_race_events(
    frames: List[Dict], track_statuses: List[Dict], total_laps: int
) -> List[Dict[str, Any]]:
    """
    Extract race events from frame data

    Args:
        frames: List of telemetry frames
        track_statuses: List of track status events
        total_laps: Total number of laps

    Returns:
        List of event dictionaries for timeline display
    """
    events = []

    if not frames:
        return events

    # Sample frames for DNF detection
    sample_rate = 25
    prev_drivers = set()

    for i in range(0, len(frames), sample_rate):
        frame = frames[i]
        current_drivers = set(frame.get("drivers", {}).keys())

        if prev_drivers:
            dnf_drivers = prev_drivers - current_drivers
            for driver_code in dnf_drivers:
                events.append(
                    {
                        "type": RaceProgressBarComponent.EVENT_DNF,
                        "frame": i,
                        "label": driver_code,
                    }
                )

        prev_drivers = current_drivers

    # Add flag events
    for status in track_statuses:
        status_code = str(status.get("status", ""))
        start_frame = int(status.get("start_time", 0) * FPS)

        event_type = None
        if status_code == "2":
            event_type = RaceProgressBarComponent.EVENT_YELLOW_FLAG
        elif status_code == "4":
            event_type = RaceProgressBarComponent.EVENT_SAFETY_CAR
        elif status_code == "5":
            event_type = RaceProgressBarComponent.EVENT_RED_FLAG
        elif status_code in ("6", "7"):
            event_type = RaceProgressBarComponent.EVENT_VSC

        if event_type:
            events.append(
                {
                    "type": event_type,
                    "frame": start_frame,
                    "label": "",
                }
            )

    return events

class EventOverlayComponent(BaseComponent):
    """Displays blinking status text at the bottom of the screen"""

    def __init__(self, track_statuses):
        self.track_statuses = track_statuses
        self.visible = True

    def draw(self, window, current_time):
        if not self.visible or not self.track_statuses:
            return

        # 1. Find the active status for the current replay time
        # We look for the latest status that started before 'current_time'
        active_status = "1" # Default to Green/Normal
        for status in self.track_statuses:
            if status["start_time"] > current_time:
                break
            active_status = str(status["status"])

        # 2. Determine Text and Color
        text = ""
        color = arcade.color.WHITE
        
        if active_status == "1":    # Green Flag
            return # Don't draw anything for normal racing
            
        elif active_status == "2":  # Yellow Flag
            text = "YELLOW FLAG"
            color = (255, 255, 0)
            
        elif active_status == "4":  # Safety Car
            text = "SAFETY CAR"
            color = (255, 165, 0)   # Orange
            
        elif active_status == "5":  # Red Flag
            text = "RED FLAG"
            color = (255, 0, 0)
            
        elif active_status in ["6", "7"]: # VSC
            text = "VIRTUAL SAFETY CAR"
            color = (255, 215, 0)   # Gold

        # 3. Blinking Effect (Real-time blinking, even if paused)
        if text and (time.time() % 0.8) < 0.5: 
            arcade.draw_text(
                text,
                window.width / 2,
                30,  # Height from bottom
                color,
                24,  # Font size
                anchor_x="center",
                anchor_y="center",
                bold=True
            )
# ============================================================================
# RACE REPLAY WINDOW
# ============================================================================


class F1RaceReplayWindow(arcade.Window):
    """Main window for race replay visualization"""

    def __init__(
        self,
        frames: List[Dict],
        track_statuses: List[Dict],
        example_lap,
        drivers: List,
        title: str,
        playback_speed: float = 1.0,
        driver_colors: Optional[Dict] = None,
        circuit_rotation: float = 0.0,
        total_laps: Optional[int] = None,
        visible_hud: bool = True,
        session_info: Optional[Dict] = None,
        driver_names: Optional[Dict] = None,
    ):
        """
        Initialize the race replay window

        Args:
            frames: List of telemetry frames
            track_statuses: List of track status events
            example_lap: Reference lap for track layout
            drivers: List of driver codes
            title: Window title
            playback_speed: Initial playback speed
            driver_colors: Dictionary of driver colors
            circuit_rotation: Track rotation angle in degrees
            total_laps: Total number of laps in race
            visible_hud: Show/hide HUD elements
            session_info: Session metadata for display
        """
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, title, resizable=True)
        self.maximize()

        self.frames = frames
        self.track_statuses = track_statuses
        self.n_frames = len(frames)
        self.drivers = list(drivers)
        self.playback_speed = (
            playback_speed if playback_speed in PLAYBACK_SPEEDS else 1.0
        )
        self.driver_colors = driver_colors or {}
        self.frame_index = 0.0
        self.paused = False
        self.total_laps = total_laps
        self.visible_hud = visible_hud

        # Circuit rotation
        self.circuit_rotation = circuit_rotation
        self._rot_rad = float(np.deg2rad(circuit_rotation))
        self._cos_rot = float(np.cos(self._rot_rad))
        self._sin_rot = float(np.sin(self._rot_rad))

        self.toggle_drs_zones = False
        self.show_driver_labels = False

        # UI components
        self.leaderboard_comp = LeaderboardComponent(visible=visible_hud)
        self.weather_comp = WeatherComponent(left=70,visible=visible_hud)
        self.driver_names = driver_names or {}
        self.legend_comp = LegendComponent(visible=visible_hud)
        self.driver_info_comp = DriverInfoComponent(left=70, driver_names=self.driver_names)
        self.progress_bar_comp = RaceProgressBarComponent(visible=visible_hud)
        self.session_info_comp = SessionInfoComponent(session_info)
        self.event_overlay_comp = EventOverlayComponent(track_statuses)

        # Extract and set events
        events = extract_race_events(frames, track_statuses, total_laps or 0)
        self.progress_bar_comp.set_events(events)

        # Build track
        track_data = build_track_from_example_lap(example_lap, track_width=350.0)
        (
            self.plot_x_ref,
            self.plot_y_ref,
            self.x_inner,
            self.y_inner,
            self.x_outer,
            self.y_outer,
            self.x_min,
            self.x_max,
            self.y_min,
            self.y_max,
            self.drs_zones,
        ) = track_data

        self.track_center_x = (self.x_min + self.x_max) / 2
        self.track_center_y = (self.y_min + self.y_max) / 2

        self._calculate_scale_and_offsets()

    def _calculate_scale_and_offsets(self):
        """Calculate scaling for track rendering"""
        track_width_m = self.x_max - self.x_min
        track_height_m = self.y_max - self.y_min

        available_width = self.width - UI_LEFT_MARGIN - UI_RIGHT_MARGIN
        available_height = self.height - 120

        scale_x = available_width / track_width_m if track_width_m > 0 else 1.0
        scale_y = available_height / track_height_m if track_height_m > 0 else 1.0

        # Use track_scale to avoid conflict with arcade.Window.scale property
        self.track_scale = min(scale_x, scale_y) * 0.9

        self.offset_x = self.width / 2
        self.offset_y = self.height / 2

    def _world_to_screen(self, x: float, y: float) -> Tuple[float, float]:
        """
        Convert world coordinates to screen coordinates with rotation

        Args:
            x: World X coordinate
            y: World Y coordinate

        Returns:
            Tuple of (screen_x, screen_y)
        """
        # Translate to origin
        tx = x - self.track_center_x
        ty = y - self.track_center_y

        # Rotate
        rx = tx * self._cos_rot - ty * self._sin_rot
        ry = tx * self._sin_rot + ty * self._cos_rot

        # Scale and translate to screen
        sx = rx * self.track_scale + self.offset_x
        sy = ry * self.track_scale + self.offset_y

        return sx, sy

    def on_draw(self):
        """Render the race replay"""
        self.clear()
        arcade.set_background_color((20, 20, 25))

        if self.n_frames == 0:
            arcade.draw_text(
                "No data available",
                self.width / 2,
                self.height / 2,
                arcade.color.WHITE,
                20,
                anchor_x="center",
            )
            return

        # Get current frame
        frame_idx = int(self.frame_index) % self.n_frames
        frame = self.frames[frame_idx]

        # Draw track
        self._draw_track()

        # Draw DRS zones
        if self.toggle_drs_zones:
            self._draw_drs_zones()

        # Draw drivers
        self._draw_drivers(frame)

        # Draw UI components
        if self.visible_hud:
            self._update_and_draw_ui(frame)
            current_time = frame.get("time", 0)
            self.event_overlay_comp.draw(self, current_time)

        # Draw playback info
        self._draw_playback_info(frame)

    def _draw_track(self):
        """Draw the race track with alternating red/white curbs"""
        
        # 1. Draw the Center Line (remains a continuous strip)
        center_points = [
            self._world_to_screen(x, y)
            for x, y in zip(self.plot_x_ref, self.plot_y_ref)
        ]
        if len(center_points) > 1:
            arcade.draw_line_strip(center_points, (255, 255, 255, 100), 1)

        
        def draw_curbs(x_coords, y_coords):
            segment_length = 4 
            
            points = [self._world_to_screen(x, y) for x, y in zip(x_coords, y_coords)]
            total_points = len(points)

            if total_points < 2:
                return

            # Loop through points in chunks
            for i in range(0, total_points - 1, segment_length):
                # Get the chunk of points for this segment
                # We do i : i + segment_length + 1 to ensure lines connect seamlessly
                segment = points[i : i + segment_length + 1]
                
                # Determine color based on even/odd chunk index
                # (i // segment_length) gives us 0, 1, 2, 3...
                if (i // segment_length) % 2 == 0:
                    color = (255, 0, 0)      # Red
                else:
                    color = (255, 255, 255)  # White

                # Draw this specific segment
                arcade.draw_line_strip(segment, color, 2) # 2 is the border thickness

        # ---------------------------------------------------------
        # 2. Draw Inner and Outer Curbs using the helper
        # ---------------------------------------------------------
        draw_curbs(self.x_inner, self.y_inner)
        draw_curbs(self.x_outer, self.y_outer)

        # 3. Draw start/finish line (unchanged)
        if len(self.plot_x_ref) > 0:
            start_x, start_y = self._world_to_screen(
                self.plot_x_ref.iloc[0], self.plot_y_ref.iloc[0]
            )
            arcade.draw_circle_filled(start_x, start_y, 8, (255, 255, 255))
            arcade.draw_circle_filled(start_x, start_y, 6, (0, 0, 0))

    def _draw_drs_zones(self):
        """Draw DRS zones on track"""
        for zone in self.drs_zones:
            # 1. Get the start and end indices from the data
            start_idx = zone["start"]["index"]
            end_idx = zone["end"]["index"]

            # 2. Collect all screen coordinates for points inside this zone
            drs_points = []
            
            # We loop through every point in the reference path belonging to this zone
            for i in range(start_idx, end_idx + 1):
                # Get the world X, Y from the stored reference lap
                wx = self.plot_x_ref.iloc[i]
                wy = self.plot_y_ref.iloc[i]
                
                # Convert to screen coordinates
                sx, sy = self._world_to_screen(wx, wy)
                drs_points.append((sx, sy))

            # Draw DRS zone
            if drs_points:
                arcade.draw_line_strip(drs_points, (100, 255, 100, 150), 10)

    def _draw_drivers(self, frame: Dict):
        """Draw driver positions on track"""
        drivers_data = frame.get("drivers", {})

        for driver_code, data in drivers_data.items():
            x, y = self._world_to_screen(data["x"], data["y"])

            # Get driver color
            color = self.driver_colors.get(driver_code, (255, 255, 255))

            # Highlight if selected
            if driver_code in self.leaderboard_comp.selected_drivers:
                arcade.draw_circle_filled(x, y, 12, (255, 255, 0, 100))

            # Draw car
            arcade.draw_circle_filled(x, y, 5, color)

            # Draw driver label if enabled
            if self.show_driver_labels:
                arcade.draw_text(
                    driver_code, x + 12, y + 5, arcade.color.WHITE, 9, bold=True
                )

    def _update_and_draw_ui(self, frame: Dict):
        """Update and draw all UI components"""
        drivers_data = frame.get("drivers", {})

        # Update leaderboard
        entries = []
        for driver_code, data in sorted(
            drivers_data.items(), key=lambda x: x[1].get("position", 999)
        ):
            entries.append(
                {
                    "position": data.get("position"),
                    "driver": driver_code,
                    "lap": data.get("lap"),
                    "tyre": data.get("tyre"),
                    "color": self.driver_colors.get(driver_code, (255, 255, 255)),
                }
            )
        self.leaderboard_comp.set_entries(entries)
        self.leaderboard_comp.draw(self)

        # Update weather
        weather = frame.get("weather")
        if weather:
            self.weather_comp.set_weather(weather)
            self.weather_comp.draw(self)

        # Draw legend
        self.legend_comp.draw(self)

        # Draw session info
        self.session_info_comp.draw(self)

        # Update progress bar
        self.progress_bar_comp.set_progress(
            self.frame_index / self.n_frames if self.n_frames > 0 else 0
        )
        self.progress_bar_comp.draw(self)

        # Draw driver info for selected drivers
        if self.leaderboard_comp.selected_drivers:
            driver_code = list(self.leaderboard_comp.selected_drivers)[0]
            if driver_code in drivers_data:
                self.driver_info_comp.set_driver_data(
                    {
                        "driver": driver_code,
                        "speed": drivers_data[driver_code].get("speed"),
                        "gear": drivers_data[driver_code].get("gear"),
                        "throttle": drivers_data[driver_code].get("throttle"),
                        "brake": drivers_data[driver_code].get("brake"),
                        "drs": drivers_data[driver_code].get("drs"),
                    }
                )
                self.driver_info_comp.draw(self)

    def _draw_playback_info(self, frame: Dict):
        """Draw playback controls and info"""
        # Playback speed
        speed_text = f"Speed: {self.playback_speed}x"
        arcade.draw_text(speed_text, 70, 50, arcade.color.WHITE, 12)

        # Pause indicator
        if self.paused:
            arcade.draw_text("⏸ PAUSED", 70, 30, arcade.color.YELLOW, 14, bold=True)

        # Current time
        current_time = frame.get("time", 0)
        time_text = format_time(current_time)
        arcade.draw_text(time_text, 70, 10, arcade.color.WHITE, 12)

    def on_update(self, delta_time: float):
        """Update animation"""
        if not self.paused and self.n_frames > 0:
            self.frame_index += delta_time * FPS * self.playback_speed
            if self.frame_index >= self.n_frames:
                self.frame_index = 0.0

    def on_key_press(self, key: int, modifiers: int):
        """Handle keyboard input"""
        if key == arcade.key.SPACE:
            self.paused = not self.paused
        elif key == arcade.key.R:
            self.frame_index = 0.0
        elif key == arcade.key.LEFT:
            self.frame_index = max(0, self.frame_index - FPS * 5)
        elif key == arcade.key.RIGHT:
            self.frame_index = min(self.n_frames - 1, self.frame_index + FPS * 5)
        elif key == arcade.key.UP:
            try:
                idx = PLAYBACK_SPEEDS.index(self.playback_speed)
                if idx < len(PLAYBACK_SPEEDS) - 1:
                    self.playback_speed = PLAYBACK_SPEEDS[idx + 1]
            except ValueError:
                self.playback_speed = 1.0
        elif key == arcade.key.DOWN:
            try:
                idx = PLAYBACK_SPEEDS.index(self.playback_speed)
                if idx > 0:
                    self.playback_speed = PLAYBACK_SPEEDS[idx - 1]
            except ValueError:
                self.playback_speed = 1.0
        elif key == arcade.key.D:
            self.toggle_drs_zones = not self.toggle_drs_zones
        elif key == arcade.key.L:
            self.show_driver_labels = not self.show_driver_labels
        elif key == arcade.key.H:
            self.legend_comp.visible = not self.legend_comp.visible

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        """Handle mouse clicks"""
        self.leaderboard_comp.on_mouse_press(self, x, y, button, modifiers)

    def on_resize(self, width: int, height: int):
        """Handle window resize"""
        super().on_resize(width, height)
        self._calculate_scale_and_offsets()
        self.leaderboard_comp.on_resize(self)
        self.progress_bar_comp.on_resize(self)
        self.legend_comp.on_resize(self)


# ============================================================================
# MODULE ENTRY POINT
# ============================================================================


def run_vision_module(
    year: int,
    round_number: int,
    session_type: str = "R",
    ready_file: Optional[str] = None,
):
    """
    Launch the vision module

    Args:
        year: Season year
        round_number: Round number
        session_type: 'R' (Race), 'Q' (Qualifying), 'S' (Sprint), or 'SQ' (Sprint Qualifying)
        ready_file: Optional file path to signal readiness to parent process
    """
    print(f"🏎️ F1 Insight Hub - Vision Module")
    print(f"Loading: {year} Season, Round {round_number}, Session {session_type}")

    # Load session
    session = load_session(year, round_number, session_type)
    if not session:
        print("❌ Failed to load session")
        return

    print(f"✓ Loaded: {session.event['EventName']}")

    # Get telemetry data
    if session_type in ("Q", "SQ"):
        print("⚠️ Qualifying visualization not yet implemented in Vision Module")
        print("   Race replay only for now")
        return
    else:
        print("📊 Processing race telemetry...")

        # Get race telemetry data
        race_data = get_race_telemetry(session, session_type)

        if not race_data:
            print("❌ Failed to process telemetry")
            return

        # Validate race_data has required keys
        if "frames" not in race_data or not race_data["frames"]:
            print("❌ No frame data available")
            return

        # Get example lap with proper error handling
        example_lap = None

        # Try to get qualifying lap first
        try:
            print("Attempting to load qualifying session for track layout...")
            quali_session = load_session(year, round_number, "Q")

            if (
                quali_session
                and hasattr(quali_session, "laps")
                and len(quali_session.laps) > 0
            ):
                fastest_quali = quali_session.laps.pick_fastest()

                if fastest_quali is not None:
                    quali_telemetry = fastest_quali.get_telemetry()

                    # Check if telemetry has required columns
                    if quali_telemetry is not None and not quali_telemetry.empty:
                        if (
                            "X" in quali_telemetry.columns
                            and "Y" in quali_telemetry.columns
                        ):
                            example_lap = quali_telemetry
                            print("✓ Using qualifying lap for track layout")
        except Exception as e:
            print(f"⚠️ Could not load qualifying session: {e}")

        # Fallback: Use fastest race lap
        if example_lap is None:
            try:
                print("Attempting to use fastest race lap for track layout...")

                if hasattr(session, "laps") and len(session.laps) > 0:
                    fastest_lap = session.laps.pick_fastest()

                    if fastest_lap is not None:
                        race_telemetry = fastest_lap.get_telemetry()

                        # Check if telemetry has required columns
                        if race_telemetry is not None and not race_telemetry.empty:
                            if (
                                "X" in race_telemetry.columns
                                and "Y" in race_telemetry.columns
                            ):
                                example_lap = race_telemetry
                                print("✓ Using fastest race lap for track layout")
            except Exception as e:
                print(f"⚠️ Could not load race lap: {e}")

        # CRITICAL: Check if example_lap exists before proceeding
        if example_lap is None or example_lap.empty:
            print("❌ Error: No valid lap data found for track layout")
            print("   Cannot render track without position data")
            return

        # Validate example_lap has required columns
        required_columns = ["X", "Y", "Distance", "DRS"]
        missing_columns = [
            col for col in required_columns if col not in example_lap.columns
        ]

        if missing_columns:
            print(f"⚠️ Warning: Missing columns in lap data: {missing_columns}")
            # Add default DRS column if missing
            if "DRS" in missing_columns:
                example_lap["DRS"] = 0
                print("   Added default DRS column")

        # Get circuit rotation
        try:
            circuit_rotation = get_circuit_rotation(session)
        except Exception as e:
            print(f"⚠️ Could not determine circuit rotation: {e}")
            circuit_rotation = 0.0

        # Prepare session info
        session_info = {
            "event_name": session.event.get("EventName", "Unknown Event"),
            "year": year,
            "round": round_number,
        }

        # Create driver name mapping (Abbreviation -> Full Name)
        driver_names = {}
        if hasattr(session, "drivers"):
            for driver_id in session.drivers:
                try:
                    drv = session.get_driver(driver_id)
                    driver_names[drv['Abbreviation']] = drv['FullName']
                except:
                    pass

        # Create and run window
        print("🚀 Launching visualization...")

        try:
            session_name = {"R": "Race", "S": "Sprint"}.get(session_type, "Session")
            title = f"{SCREEN_TITLE_RACE} - {session.event['EventName']} {session_name}"

            window = F1RaceReplayWindow(
                frames=race_data["frames"],
                track_statuses=race_data.get("track_statuses", []),
                example_lap=example_lap,
                drivers=session.drivers if hasattr(session, "drivers") else [],
                title=title,
                playback_speed=1.0,
                driver_colors=race_data.get("driver_colors", {}),
                circuit_rotation=circuit_rotation,
                total_laps=race_data.get("total_laps", 0),
                visible_hud=True,
                session_info=session_info,
                driver_names=driver_names,
            )

            # Signal readiness
            if ready_file:
                try:
                    with open(ready_file, "w") as f:
                        f.write("ready")
                except Exception as e:
                    print(f"⚠️ Could not write ready file: {e}")

            arcade.run()

        except Exception as e:
            print(f"❌ Error launching window: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="F1 Insight Hub - Vision Module")
    parser.add_argument("--year", type=int, required=True, help="Season year")
    parser.add_argument("--round", type=int, required=True, help="Round number")
    parser.add_argument(
        "--session",
        type=str,
        default="R",
        choices=["R", "Q", "S", "SQ"],
        help="Session type (R=Race, Q=Qualifying, S=Sprint, SQ=Sprint Qualifying)",
    )
    parser.add_argument("--ready-file", type=str, help="File to signal readiness")

    args = parser.parse_args()

    # Initialize
    enable_cache()

    # Run
    run_vision_module(args.year, args.round, args.session, args.ready_file)
