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
    """Refactored Leaderboard with Lap Count in Header"""

    # 1. Update __init__ to accept total_laps
    def __init__(self, x: int = 20, width: int = 240, visible: bool = True, total_laps: int = 0):
        self.x = x
        self.width = width
        self.visible = visible
        self.total_laps = total_laps  # Store it
        self.entries = []
        self.selected_drivers = set()

        self.row_height = 24
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

        center_x = self.x + (self.width / 2)
        center_y = top_y - (total_height / 2)

        # 2. Draw Background Panel
        panel_rect = arcade.rect.XYWH(center_x, center_y, self.width, total_height)
        arcade.draw_rect_filled(panel_rect, (20, 20, 25, 220))
        arcade.draw_rect_outline(panel_rect, (255, 255, 255, 40), border_width=1)

        # 3. Draw Header
        header_y = top_y - 20
        
        # Red Accent Bar
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.x + 4, header_y, 4, 24), (255, 40, 40)
        )
        
        # Title "LEADERBOARD"
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

        # --- NEW: Draw Lap Count (Right Aligned) ---
        if self.entries:
            # Get lap from the leader (index 0)
            current_lap = int(self.entries[0].get("lap", 0))
            # Ensure it doesn't exceed total (visual fix for finish line)
            display_lap = min(current_lap, self.total_laps)
            
            lap_text = f"LAP {display_lap}/{self.total_laps}"
            
            arcade.draw_text(
                lap_text,
                self.x + self.width - 15,  # Right align with some padding
                header_y,
                arcade.color.LIGHT_GRAY,   # Subtle gray color
                12,
                bold=True,
                anchor_x="right",
                anchor_y="center",
            )

        # 4. Draw Rows
        list_top_y = top_y - self.header_height

        for i, entry in enumerate(self.entries):
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

            # Position
            arcade.draw_text(
                f"P{entry.get('position', 0)}",
                self.x + 10,
                row_y,
                arcade.color.GOLD if i == 0 else arcade.color.WHITE,
                11,
                bold=True,
                anchor_y="center",
            )

            # Driver Name
            arcade.draw_text(
                driver.upper(),
                self.x + 45,
                row_y,
                driver_color,
                12,
                bold=True,
                anchor_y="center",
            )

            # Tyre Icon
            tyre_x = self.x + self.width - 30
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

    def on_mouse_press(self, window, x: float, y: float, button: int, modifiers: int) -> bool:
        if not self.visible or not self.entries:
            return False

        if not (self.x <= x <= self.x + self.width):
            return False

        list_start_y = window.height - 60 - self.header_height

        for i, entry in enumerate(self.entries):
            row_top = list_start_y - (i * self.row_height)
            row_bottom = row_top - self.row_height

            if row_bottom <= y <= row_top:
                driver = entry.get("driver")
                if driver:
                    was_selected = driver in self.selected_drivers
                    self.selected_drivers.clear()
                    if not was_selected:
                        self.selected_drivers.add(driver)
                return True

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
        #if weather_data:
            #print(f"Weather: {weather_data.get('weather', 'Unknown')} (rainfall: {weather_data.get('rainfall', 0)}, humidity: {weather_data.get('humidity', 0)})")

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

        # Enhanced weather icon rendering with night support
        icon_x = self.left + 150
        icon_y = y - 10
        icon_size = 28
        weather_condition = self.weather_data.get("weather", "").lower()
        
        # Get current time for animations
        import time
        current_time = time.time()

        # Handle night conditions first (highest priority)
        if "night" in weather_condition:
            if "rain" in weather_condition:
                # Night rain with darker colors
                cloud_color = (100, 100, 120)
                rain_color = (60, 120, 180)
                
                # Draw dark night clouds
                arcade.draw_ellipse_filled(icon_x, icon_y, icon_size+10, icon_size-8, cloud_color)
                arcade.draw_ellipse_filled(icon_x-12, icon_y-6, icon_size-6, icon_size-14, cloud_color)
                arcade.draw_ellipse_filled(icon_x+12, icon_y-6, icon_size-8, icon_size-16, cloud_color)
                
                # Animated falling rain drops
                for i, dx in enumerate([-10, 0, 10]):
                    fall_speed = 30 + (i * 10)
                    phase_offset = i * 0.5
                    drop_cycle = (current_time * fall_speed + phase_offset * 100) % 40
                    drop_start_y = icon_y - 12 - (drop_cycle * 0.3)
                    drop_end_y = drop_start_y - 8
                    
                    for j in range(3):
                        offset = j * 15
                        arcade.draw_line(
                            icon_x + dx, drop_start_y - offset, 
                            icon_x + dx, drop_end_y - offset, 
                            (*rain_color[:3], max(0, 255 - offset * 8)), 3
                        )
                        
            elif "cloud" in weather_condition:
                # Night cloudy - show dark clouds with subtle moon glow behind
                base_color = 100
                pulse = 1 + 0.08 * np.sin(current_time * 1.5)  # Subtle breathing
                cloud_color = (int(base_color * pulse), int(base_color * pulse), base_color + 20)
                
                # Realistic moon glow behind clouds (dimmed for cloudy effect)
                moon_pulse = 1 + 0.1 * np.sin(current_time * 1.2)  # Gentle moon pulsing
                moon_radius = (icon_size // 2) * moon_pulse
                moon_offset_x = icon_x + 8
                moon_offset_y = icon_y + 5
                
                # Multiple glow layers for realistic moon (warm yellowish glow)
                for glow_layer in range(3):
                    glow_alpha = (60 - (glow_layer * 15))  # Brighter glow
                    glow_size = moon_radius + (glow_layer * 3)
                    arcade.draw_circle_filled(moon_offset_x, moon_offset_y, glow_size, (255, 235, 200, glow_alpha))
                
                # Main crescent moon body
                main_moon_radius = moon_radius * 0.8
                arcade.draw_circle_filled(moon_offset_x, moon_offset_y, main_moon_radius, (240, 230, 190, 180))
                
                # Create crescent shadow (draw darker circle to create crescent effect)
                shadow_offset = main_moon_radius * 0.3
                shadow_x = moon_offset_x + shadow_offset
                shadow_y = moon_offset_y
                shadow_radius = main_moon_radius * 0.85
                arcade.draw_circle_filled(shadow_x, shadow_y, shadow_radius, (15, 20, 28, 200))  # Match background color
                
                # Subtle moon crater on visible crescent part
                crater_x = moon_offset_x - main_moon_radius * 0.2
                crater_y = moon_offset_y + main_moon_radius * 0.1
                arcade.draw_circle_filled(crater_x, crater_y, 1, (200, 180, 140, 120))
                
                # Dark night clouds
                arcade.draw_ellipse_filled(icon_x, icon_y, (icon_size+10) * pulse, (icon_size-8) * pulse, cloud_color)
                arcade.draw_ellipse_filled(icon_x-12, icon_y-6, (icon_size-6) * pulse, (icon_size-14) * pulse, cloud_color)
                arcade.draw_ellipse_filled(icon_x+12, icon_y-6, (icon_size-8) * pulse, (icon_size-16) * pulse, cloud_color)
                
            elif "clear" in weather_condition:
                # Draw animated moon for night clear conditions
                moon_pulse = 1 + 0.15 * np.sin(current_time * 1.5)  # Gentle moon glow
                moon_radius = (icon_size // 2) * moon_pulse
                
                # Moon glow layers
                for glow_layer in range(3):
                    glow_alpha = 80 - (glow_layer * 20)
                    glow_size = moon_radius + (glow_layer * 4)
                    arcade.draw_circle_filled(icon_x, icon_y, glow_size, (200, 220, 255, glow_alpha))
                
                # Main moon body
                arcade.draw_circle_filled(icon_x, icon_y, moon_radius, (220, 230, 255))
                
                # Moon craters (static)
                arcade.draw_circle_filled(icon_x - 4, icon_y + 2, 2, (180, 190, 220))
                arcade.draw_circle_filled(icon_x + 2, icon_y - 3, 1.5, (190, 200, 230))
                
                # Twinkling stars around moon
                for angle in range(0, 360, 60):
                    star_angle = angle + (current_time * 10)  # Slow rotation
                    rad = np.deg2rad(star_angle)
                    star_distance = moon_radius + 15 + 5 * np.sin(current_time * 3 + angle / 60)
                    
                    star_x = icon_x + np.cos(rad) * star_distance
                    star_y = icon_y + np.sin(rad) * star_distance
                    star_alpha = int(150 + 100 * np.sin(current_time * 4 + angle / 30))
                    
                    arcade.draw_circle_filled(star_x, star_y, 1.5, (255, 255, 255, star_alpha))
                
        # Daytime weather conditions
        elif "rain" in weather_condition:
            # Daytime rain with lighter colors
            cloud_color = (180, 180, 190)
            rain_color = (80, 180, 255)
            
            # Draw light day clouds
            arcade.draw_ellipse_filled(icon_x, icon_y, icon_size+10, icon_size-8, cloud_color)
            arcade.draw_ellipse_filled(icon_x-12, icon_y-6, icon_size-6, icon_size-14, cloud_color)
            arcade.draw_ellipse_filled(icon_x+12, icon_y-6, icon_size-8, icon_size-16, cloud_color)
            
            # Animated falling rain drops
            for i, dx in enumerate([-10, 0, 10]):
                fall_speed = 30 + (i * 10)
                phase_offset = i * 0.5
                drop_cycle = (current_time * fall_speed + phase_offset * 100) % 40
                drop_start_y = icon_y - 12 - (drop_cycle * 0.3)
                drop_end_y = drop_start_y - 8
                
                for j in range(3):
                    offset = j * 15
                    arcade.draw_line(
                        icon_x + dx, drop_start_y - offset, 
                        icon_x + dx, drop_end_y - offset, 
                        (*rain_color[:3], max(0, 255 - offset * 8)), 3
                    )
                    
        elif "cloud" in weather_condition or "overcast" in weather_condition:
            # Daytime clouds with lighter colors
            base_color = 180
            pulse = 1 + 0.1 * np.sin(current_time * 2)
            cloud_color = (int(base_color * pulse), int(base_color * pulse), base_color + 10)
            
            arcade.draw_ellipse_filled(icon_x, icon_y, (icon_size+10) * pulse, (icon_size-8) * pulse, cloud_color)
            arcade.draw_ellipse_filled(icon_x-12, icon_y-6, (icon_size-6) * pulse, (icon_size-14) * pulse, cloud_color)
            arcade.draw_ellipse_filled(icon_x+12, icon_y-6, (icon_size-8) * pulse, (icon_size-16) * pulse, cloud_color)
            
        elif "fog" in weather_condition or "mist" in weather_condition:
            # Draw fog/mist effect
            fog_intensity = 0.8 if "fog" in weather_condition else 0.5
            fog_color = (200, 200, 210, int(180 * fog_intensity))
            
            # Multiple overlapping fog layers with drift animation
            for layer in range(4):
                drift_offset = np.sin(current_time * 0.8 + layer * 0.5) * 3
                layer_y = icon_y + (layer - 2) * 4
                
                arcade.draw_ellipse_filled(
                    icon_x + drift_offset, layer_y, 
                    icon_size + 5 - layer * 2, icon_size // 3, 
                    fog_color
                )
                
        elif "sun" in weather_condition or ("clear" in weather_condition and "night" not in weather_condition):
            # Draw rotating sun with glowing effect (enhanced)
            rotation_angle = current_time * 45  # Rotate 45 degrees per second
            
            # Determine sun intensity
            is_sunny = "sunny" in weather_condition
            base_intensity = 1.3 if is_sunny else 1.0
            
            # Glowing sun core with pulsing effect
            glow_pulse = base_intensity + 0.2 * np.sin(current_time * 3)
            sun_radius = (icon_size // 2) * glow_pulse
            
            # Enhanced glow layers for sunny conditions
            glow_layers = 4 if is_sunny else 3
            for glow_layer in range(glow_layers):
                glow_alpha = (120 if is_sunny else 100) - (glow_layer * 25)
                glow_size = sun_radius + (glow_layer * 4)
                sun_color = (255, 200 if is_sunny else 220, 40 if is_sunny else 40)
                arcade.draw_circle_filled(icon_x, icon_y, glow_size, (*sun_color, glow_alpha))
            
            # Main sun body
            sun_color = (255, 200, 0) if is_sunny else (255, 220, 40)
            arcade.draw_circle_filled(icon_x, icon_y, sun_radius, sun_color)
            
            # Enhanced rotating sun rays
            ray_count = 12 if is_sunny else 8
            for angle in range(0, 360, 360 // ray_count):
                animated_angle = angle + rotation_angle
                rad = np.deg2rad(animated_angle)
                
                # Main rays
                ray_length = 12 if is_sunny else 10
                x1 = icon_x + np.cos(rad) * sun_radius
                y1 = icon_y + np.sin(rad) * sun_radius
                x2 = icon_x + np.cos(rad) * (sun_radius + ray_length)
                y2 = icon_y + np.sin(rad) * (sun_radius + ray_length)
                arcade.draw_line(x1, y1, x2, y2, sun_color, 3)
                
                # Smaller secondary rays (offset by half angle)
                if is_sunny:
                    secondary_angle = animated_angle + (360 // ray_count) / 2
                    rad2 = np.deg2rad(secondary_angle)
                    x3 = icon_x + np.cos(rad2) * (sun_radius + 2)
                    y3 = icon_y + np.sin(rad2) * (sun_radius + 2)
                    x4 = icon_x + np.cos(rad2) * (sun_radius + 8)
                    y4 = icon_y + np.sin(rad2) * (sun_radius + 8)
                    arcade.draw_line(x3, y3, x4, y4, (255, 240, 80), 2)
        
        else:
            # Default fallback - simple weather icon
            arcade.draw_circle_filled(icon_x, icon_y, icon_size // 2, (200, 200, 200))

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
        
        # --- DRIVER NAME ---
        driver_code = self.driver_data.get("driver", "???")
        full_name = self.driver_names.get(driver_code, driver_code)
        
        font_size = 17
        arcade.draw_text(full_name, self.left + 20, current_y, arcade.color.WHITE, font_size, bold=True)

        current_y -= 45

        # --- SPEED ---
        speed = int(self.driver_data.get("speed", 0))
        arcade.draw_text(f"{speed}", self.left + 20, current_y, arcade.color.WHITE, 27, bold=True)
        arcade.draw_text("km/h", self.left + 95, current_y, arcade.color.GRAY, 16)
        
        # --- GEAR ---
        gear = self.driver_data.get("gear", 0)
        gear_str = str(gear) if gear > 0 else "N"
        
        gear_x = self.left + self.width - 40
        gear_box_y = current_y + 15
        
        arcade.draw_rect_outline(arcade.rect.XYWH(gear_x, gear_box_y, 30, 30), arcade.color.WHITE, 2)
        arcade.draw_text(gear_str, gear_x, gear_box_y, arcade.color.CYAN, 20, bold=True, anchor_x="center", anchor_y="center")
        arcade.draw_text("GEAR", gear_x, gear_box_y - 32, arcade.color.GRAY, 9, anchor_x="center", bold=True)

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
        arcade.draw_rect_filled(arcade.rect.XYWH(thr_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (20, 20, 20))
        arcade.draw_rect_outline(arcade.rect.XYWH(thr_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (100, 100, 100), 1)
        
        thr_height = (throttle / 100) * max_bar_height
        if thr_height > 0:
            arcade.draw_rect_filled(arcade.rect.XYWH(thr_x, bars_bottom_y + thr_height/2, bar_width - 4, thr_height), (0, 255, 0))
        arcade.draw_text("THR", thr_x, bars_bottom_y - 12, arcade.color.GRAY, 10, anchor_x="center")

        # --- BRAKE (Red - Binary/Full) ---
        brk_x = center_x - 30
        arcade.draw_rect_filled(arcade.rect.XYWH(brk_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (20, 20, 20))
        arcade.draw_rect_outline(arcade.rect.XYWH(brk_x, bars_bottom_y + max_bar_height/2, bar_width, max_bar_height), (100, 100, 100), 1)
        
        # LOGIC FIX: Check against 0.1 instead of 1
        # This catches boolean True (1.0) AND percentage pressure (>1%)
        if brake > 0.1: 
            brk_height = max_bar_height
            arcade.draw_rect_filled(
                arcade.rect.XYWH(brk_x, bars_bottom_y + brk_height/2, bar_width - 4, brk_height), 
                (255, 0, 0)
            )
            
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
        """Draw legend with transparent background"""
        if not self.visible:
            return

        # Use the calculated self.x and self.y
        bottom_left_x = self.x
        current_y = self.y + self.height - 30

        # Draw Header
        arcade.draw_text(
            "CONTROLS", bottom_left_x + 10, current_y, arcade.color.CYAN, 12, bold=True
        )
        current_y -= 25

        # Draw list items
        # Added a slight shadow effect (black text behind white) to make it readable on any background
        labels = [
            "SPACE: Pause/Resume",
            "←/→: Rewind/Forward",
            "↑/↓: Speed Up/Down",
            "R: Restart",
            "D: Toggle DRS Zones",
            "L: Toggle Labels",
            "H: Toggle Help"
        ]

        for label in labels:
            # Draw shadow for readability
            arcade.draw_text(label, bottom_left_x + 11, current_y - 1, (0, 0, 0, 200), 10)
            # Draw actual text
            arcade.draw_text(label, bottom_left_x + 10, current_y, arcade.color.WHITE, 10)
            current_y -= 16


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

        # Background effects
        self.background_time = 0.0

        # UI components
        self.leaderboard_comp = LeaderboardComponent(visible=visible_hud, total_laps=self.total_laps)
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

    def _draw_dynamic_background(self):
        """Draw clean HUD-style background"""
        # Get current weather for color scheme
        weather_condition = "clear"
        if self.n_frames > 0:
            frame_idx = int(self.frame_index) % self.n_frames
            frame = self.frames[frame_idx]
            weather_data = frame.get("weather", {})
            if weather_data:
                weather_condition = weather_data.get("weather", "clear").lower()
        
        # Clean HUD color scheme
        if "rain" in weather_condition:
            bg_color = (12, 18, 25)  # Dark blue-gray
            accent_color = (30, 50, 70)
        elif "cloud" in weather_condition:
            bg_color = (18, 18, 22)  # Dark gray
            accent_color = (40, 40, 50)
        else:
            bg_color = (15, 20, 28)  # Dark blue
            accent_color = (35, 45, 60)
        
        # Solid background
        arcade.draw_rect_filled(
            arcade.rect.XYWH(self.width/2, self.height/2, self.width, self.height),
            bg_color
        )
        
        # Subtle grid overlay for HUD feel
        self._draw_minimal_grid(accent_color)

    def _draw_minimal_grid(self, accent_color):
        """Draw minimal HUD-style grid"""
        grid_size = 80
        alpha = 15  # Very subtle
        
        # Only draw major grid lines
        for x in range(0, self.width + grid_size, grid_size):
            arcade.draw_line(
                x, 0, x, self.height,
                (*accent_color, alpha), 1
            )
        
        for y in range(0, self.height + grid_size, grid_size):
            arcade.draw_line(
                0, y, self.width, y,
                (*accent_color, alpha), 1
            )
        
        # Add corner accents for modern HUD look
        corner_size = 20
        corner_color = (*accent_color, 80)
        
        # Top-left corner
        arcade.draw_line(0, self.height, corner_size, self.height, corner_color, 2)
        arcade.draw_line(0, self.height, 0, self.height - corner_size, corner_color, 2)
        
        # Top-right corner
        arcade.draw_line(self.width - corner_size, self.height, self.width, self.height, corner_color, 2)
        arcade.draw_line(self.width, self.height, self.width, self.height - corner_size, corner_color, 2)
        
        # Bottom-left corner
        arcade.draw_line(0, 0, corner_size, 0, corner_color, 2)
        arcade.draw_line(0, 0, 0, corner_size, corner_color, 2)
        
        # Bottom-right corner
        arcade.draw_line(self.width - corner_size, 0, self.width, 0, corner_color, 2)
        arcade.draw_line(self.width, 0, self.width, corner_size, corner_color, 2)

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
        
        # Draw modern animated background
        self._draw_dynamic_background()

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
        # Update background timer for minimal effects
        self.background_time += delta_time
        
        # Update race playback
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
