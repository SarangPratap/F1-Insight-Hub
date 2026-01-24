"""
F1 INSIGHT HUB - Vision Module
Race and Qualifying replay with advanced telemetry visualization
Compatible with Arcade 3.0+ Modern API

This module provides real-time race replay visualization with:
- Track rendering with DRS zones
- Driver position tracking
- Telemetry display (speed, gear, throttle, brake, DRS)
- Weather information
- Race events timeline
- Interactive controls
"""

import os
import sys
import arcade
import arcade.color
import numpy as np
import argparse
from typing import List, Optional, Tuple, Dict, Any

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
    """Display race leaderboard with positions and driver info"""

    def __init__(self, x: int = 20, width: int = 240, visible: bool = True):
        self.x = x
        self.width = width
        self.visible = visible
        self.entries = []
        self.selected_drivers = set()

    def set_entries(self, entries: List[Dict[str, Any]]):
        """Update leaderboard entries"""
        self.entries = entries

    def on_resize(self, window):
        """Handle window resize"""
        self.x = max(20, window.width - UI_RIGHT_MARGIN + 12)

    def draw(self, window):
        """Draw the leaderboard"""
        if not self.visible or not self.entries:
            return

        y = window.height - 60

        # Draw background panel using Arcade 3.0+ syntax
        panel_rect = arcade.rect.XYWH(
            self.x + self.width / 2,
            y - len(self.entries) * 20,
            self.width,
            len(self.entries) * 40 + 40,
        )
        arcade.draw_rect_filled(panel_rect, (40, 40, 45, 200))

        # Draw header
        arcade.draw_text(
            "LEADERBOARD", self.x + 10, y, arcade.color.WHITE, 14, bold=True
        )
        y -= 30

        # Draw entries
        for entry in self.entries:
            pos = entry.get("position", 0)
            driver = entry.get("driver", "???")
            lap = entry.get("lap", 0)
            tyre = get_tyre_compound_str(entry.get("tyre", -1))

            # Highlight if selected
            if driver in self.selected_drivers:
                highlight_rect = arcade.rect.XYWH(
                    self.x + self.width / 2, y - 10, self.width - 10, 22
                )
                arcade.draw_rect_filled(highlight_rect, (225, 6, 0, 100))

            # Position number
            arcade.draw_text(
                f"P{pos}", self.x + 5, y, arcade.color.WHITE, 12, bold=True
            )

            # Driver code
            color = entry.get("color", (255, 255, 255))
            arcade.draw_text(driver, self.x + 40, y, color, 12, bold=True)

            # Lap info
            arcade.draw_text(f"L{lap}", self.x + 100, y, arcade.color.LIGHT_GRAY, 10)

            # Tyre compound
            tyre_color = get_tyre_color(tyre)
            arcade.draw_circle_filled(self.x + 150, y + 6, 6, tyre_color)
            arcade.draw_text(tyre[:1], self.x + 165, y, arcade.color.WHITE, 10)

            y -= 22

    def on_mouse_press(
        self, window, x: float, y: float, button: int, modifiers: int
    ) -> bool:
        """Handle mouse clicks on leaderboard entries"""
        if not self.visible:
            return False

        y_pos = window.height - 90

        for entry in self.entries:
            if self.x <= x <= self.x + self.width and y_pos - 11 <= y <= y_pos + 11:
                driver = entry.get("driver")

                # Toggle selection
                if driver in self.selected_drivers:
                    self.selected_drivers.remove(driver)
                else:
                    if modifiers & arcade.key.MOD_SHIFT:
                        self.selected_drivers.add(driver)
                    else:
                        self.selected_drivers.clear()
                        self.selected_drivers.add(driver)
                return True

            y_pos -= 22

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
    """Progress bar showing race completion and events"""

    # Event type constants
    EVENT_DNF = "dnf"
    EVENT_YELLOW_FLAG = "yellow"
    EVENT_SAFETY_CAR = "safety_car"
    EVENT_RED_FLAG = "red"
    EVENT_VSC = "vsc"

    def __init__(
        self,
        center_x: float = 640,
        y: float = 30,
        width: float = 800,
        height: float = 20,
        visible: bool = True,
    ):
        self.center_x = center_x
        self.y = y
        self.width = width
        self.height = height
        self.visible = visible
        self.progress = 0.0  # 0.0 to 1.0
        self.events = []

    def set_events(self, events: List[Dict[str, Any]]):
        """Set race events for display"""
        self.events = events

    def set_progress(self, progress: float):
        """Set progress (0.0 to 1.0)"""
        self.progress = max(0.0, min(1.0, progress))

    def on_resize(self, window):
        """Handle window resize"""
        self.center_x = window.width / 2
        self.width = min(800, window.width - 400)

    def draw(self, window):
        """Draw progress bar"""
        if not self.visible:
            return

        left = self.center_x - self.width / 2

        # Draw background using Arcade 3.0+ syntax
        bg_rect = arcade.rect.XYWH(self.center_x, self.y, self.width, self.height)
        arcade.draw_rect_filled(bg_rect, (60, 60, 60))

        # Draw progress
        progress_width = self.width * self.progress
        if progress_width > 0:
            progress_rect = arcade.rect.XYWH(
                left + progress_width / 2, self.y, progress_width, self.height
            )
            arcade.draw_rect_filled(progress_rect, (225, 6, 0))

        # Draw current position marker
        marker_x = left + self.width * self.progress
        arcade.draw_triangle_filled(
            marker_x,
            self.y + self.height / 2 + 10,
            marker_x - 5,
            self.y + self.height / 2,
            marker_x + 5,
            self.y + self.height / 2,
            arcade.color.WHITE,
        )

        # Draw border
        border_rect = arcade.rect.XYWH(self.center_x, self.y, self.width, self.height)
        arcade.draw_rect_outline(border_rect, arcade.color.WHITE, 2)


class DriverInfoComponent(BaseComponent):
    """Display detailed info for selected driver"""

    def __init__(self, left: int = 20, width: int = 300):
        self.left = left
        self.width = width
        self.driver_data = None
        self.visible = False

    def set_driver_data(self, driver_data: Optional[Dict[str, Any]]):
        """Set driver data to display"""
        self.driver_data = driver_data
        self.visible = driver_data is not None

    def draw(self, window):
        """Draw driver info panel"""
        if not self.visible or not self.driver_data:
            return

        y = window.height / 2

        # Draw background using Arcade 3.0+ syntax
        info_rect = arcade.rect.XYWH(self.left + self.width / 2, y, self.width, 200)
        arcade.draw_rect_filled(info_rect, (40, 40, 45, 230))

        # Driver name
        driver = self.driver_data.get("driver", "Unknown")
        arcade.draw_text(
            driver, self.left + 10, y + 80, arcade.color.WHITE, 16, bold=True
        )

        y -= 10

        # Speed
        speed = self.driver_data.get("speed", 0)
        arcade.draw_text(
            f"Speed: {int(speed)} km/h", self.left + 10, y, arcade.color.WHITE, 12
        )
        y -= 20

        # Gear
        gear = self.driver_data.get("gear", 0)
        arcade.draw_text(f"Gear: {gear}", self.left + 10, y, arcade.color.WHITE, 12)
        y -= 20

        # Throttle
        throttle = self.driver_data.get("throttle", 0)
        arcade.draw_text(
            f"Throttle: {throttle:.0f}%", self.left + 10, y, arcade.color.WHITE, 12
        )
        y -= 20

        # Brake
        brake = self.driver_data.get("brake", 0)
        if brake > 0:
            arcade.draw_text(f"Brake: {brake:.0f}%", self.left + 10, y, (255, 0, 0), 12)
        y -= 20

        # DRS status
        drs = self.driver_data.get("drs", 0)
        if drs >= 10:
            arcade.draw_text(
                "DRS: ACTIVE", self.left + 10, y, (0, 255, 0), 12, bold=True
            )


class LegendComponent(BaseComponent):
    """Display controls legend"""

    def __init__(self, x: int = 20, visible: bool = True):
        self.x = x
        self.visible = visible

    def draw(self, window):
        """Draw legend"""
        if not self.visible:
            return

        y = window.height - 300

        arcade.draw_text("CONTROLS", self.x, y, arcade.color.CYAN, 12, bold=True)
        y -= 20
        arcade.draw_text("SPACE: Pause/Resume", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("←/→: Rewind/Forward", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("↑/↓: Speed Up/Down", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("R: Restart", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("D: Toggle DRS Zones", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("L: Toggle Labels", self.x, y, arcade.color.WHITE, 10)
        y -= 16
        arcade.draw_text("H: Toggle Help", self.x, y, arcade.color.WHITE, 10)


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
    """
    Extract DRS zones from telemetry

    Args:
        example_lap: Telemetry data with DRS status (pandas DataFrame)

    Returns:
        List of DRS zone dictionaries with start/end coordinates
        Empty list if no zones found or error occurs
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

        self.toggle_drs_zones = True
        self.show_driver_labels = False

        # UI components
        self.leaderboard_comp = LeaderboardComponent(visible=visible_hud)
        self.weather_comp = WeatherComponent(visible=visible_hud)
        self.legend_comp = LegendComponent(visible=visible_hud)
        self.driver_info_comp = DriverInfoComponent()
        self.progress_bar_comp = RaceProgressBarComponent(visible=visible_hud)
        self.session_info_comp = SessionInfoComponent(session_info)

        # Extract and set events
        events = extract_race_events(frames, track_statuses, total_laps or 0)
        self.progress_bar_comp.set_events(events)

        # Build track
        track_data = build_track_from_example_lap(example_lap)
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

        # Draw playback info
        self._draw_playback_info(frame)

    def _draw_track(self):
        """Draw the race track"""
        # Draw center line
        points = [
            self._world_to_screen(x, y)
            for x, y in zip(self.plot_x_ref, self.plot_y_ref)
        ]
        if len(points) > 1:
            arcade.draw_line_strip(points, (255, 255, 255, 100), 2)

        # Draw inner edge
        points_inner = [
            self._world_to_screen(x, y) for x, y in zip(self.x_inner, self.y_inner)
        ]
        if len(points_inner) > 1:
            arcade.draw_line_strip(points_inner, (200, 200, 200), 3)

        # Draw outer edge
        points_outer = [
            self._world_to_screen(x, y) for x, y in zip(self.x_outer, self.y_outer)
        ]
        if len(points_outer) > 1:
            arcade.draw_line_strip(points_outer, (200, 200, 200), 3)

        # Draw start/finish line
        if len(self.plot_x_ref) > 0:
            start_x, start_y = self._world_to_screen(
                self.plot_x_ref.iloc[0], self.plot_y_ref.iloc[0]
            )
            arcade.draw_circle_filled(start_x, start_y, 8, (255, 255, 255))
            arcade.draw_circle_filled(start_x, start_y, 6, (0, 0, 0))

    def _draw_drs_zones(self):
        """Draw DRS zones on track"""
        for zone in self.drs_zones:
            start_x, start_y = self._world_to_screen(
                zone["start"]["x"], zone["start"]["y"]
            )
            end_x, end_y = self._world_to_screen(zone["end"]["x"], zone["end"]["y"])
            arcade.draw_line(start_x, start_y, end_x, end_y, (100, 255, 100, 150), 15)

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
            arcade.draw_circle_filled(x, y, 8, color)
            arcade.draw_circle_outline(x, y, 8, (255, 255, 255), 2)

            # Draw position number
            pos = data.get("position", "?")
            arcade.draw_text(str(pos), x - 5, y - 5, (0, 0, 0), 10, bold=True)

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
        arcade.draw_text(speed_text, 10, 50, arcade.color.WHITE, 12)

        # Pause indicator
        if self.paused:
            arcade.draw_text("⏸ PAUSED", 10, 30, arcade.color.YELLOW, 14, bold=True)

        # Current time
        current_time = frame.get("time", 0)
        time_text = format_time(current_time)
        arcade.draw_text(time_text, 10, 10, arcade.color.WHITE, 12)

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
