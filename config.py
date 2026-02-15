"""
F1 INSIGHT HUB - Configuration & Settings
Shared settings for team colors, track scales, UI themes, and constants
"""

import fastf1.plotting


# ============================================================================
# TELEMETRY & PLAYBACK CONSTANTS
# ============================================================================

# Frames per second for telemetry data
FPS = 25
DT = 1 / FPS  # Delta time per frame

# Available playback speed multipliers
PLAYBACK_SPEEDS = [0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0, 128.0, 256.0]


# ============================================================================
# SCREEN & UI CONSTANTS
# ============================================================================

# Default screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# Screen titles
SCREEN_TITLE_RACE = "F1 Insight Hub - Race Vision"
SCREEN_TITLE_QUALIFYING = "F1 Insight Hub - Qualifying Vision"
SCREEN_TITLE_ANALYTICS = "F1 Insight Hub - Analytics"
SCREEN_TITLE_INTELLIGENCE = "F1 Insight Hub - ML Intelligence"

# UI Layout margins
UI_LEFT_MARGIN = 340
UI_RIGHT_MARGIN = 260
UI_TOP_MARGIN = 40
UI_BOTTOM_MARGIN = 40


# ============================================================================
# TRACK RENDERING CONSTANTS
# ============================================================================

# Default track width in meters
DEFAULT_TRACK_WIDTH = 200

# Track line colors (RGB)
TRACK_COLOR_INNER = (200, 200, 200)
TRACK_COLOR_OUTER = (200, 200, 200)
TRACK_COLOR_CENTER = (255, 255, 255)
TRACK_LINE_WIDTH = 3

# DRS Zone colors
DRS_ZONE_COLOR = (100, 255, 100, 80)  # Light green with transparency


# ============================================================================
# DRIVER & TEAM COLORS
# ============================================================================


def get_driver_color(driver_code, session=None):
    
    try:
        if session:
            # Get color from session data
            color_hex = fastf1.plotting.get_driver_color(driver_code, session)
        else:
            # Use FastF1's default driver colors
            color_hex = fastf1.plotting.DRIVER_COLORS.get(driver_code, "#FFFFFF")

        # Convert hex to RGB
        color_hex = color_hex.lstrip("#")
        return tuple(int(color_hex[i : i + 2], 16) for i in (0, 2, 4))
    except:
        return FALLBACK_DRIVER_COLORS.get(driver_code, (255, 255, 255))


FALLBACK_DRIVER_COLORS = {
    "VER": (30, 65, 255),  
    "PER": (30, 65, 255),  
    "HAM": (0, 210, 190),  
    "RUS": (0, 210, 190),  
    "LEC": (220, 0, 0),  
    "SAI": (220, 0, 0),  
    "NOR": (255, 135, 0),  
    "PIA": (255, 135, 0),  
    "ALO": (0, 120, 80),  
    "STR": (0, 120, 80),  
    "GAS": (70, 155, 255),  
    "OCO": (70, 155, 255),  
    "TSU": (43, 69, 98),  
    "RIC": (43, 69, 98),  
    "BOT": (165, 0, 40),  
    "ZHO": (165, 0, 40),  
    "MAG": (182, 186, 189),  
    "HUL": (182, 186, 189),  
    "ALB": (37, 82, 163),  
    "SAR": (37, 82, 163),  
    "DEV": (255, 200, 0),  
    "LAW": (255, 200, 0),
    "BEA": (255, 200, 0),
}

# Team colors for 2024 season
TEAM_COLORS = {
    "Red Bull Racing": (30, 65, 255),
    "Mercedes": (0, 210, 190),
    "Ferrari": (220, 0, 0),
    "McLaren": (255, 135, 0),
    "Aston Martin": (0, 120, 80),
    "Alpine": (70, 155, 255),
    "AlphaTauri": (43, 69, 98),
    "Alfa Romeo": (165, 0, 40),
    "Haas F1 Team": (182, 186, 189),
    "Williams": (37, 82, 163),
}


# ============================================================================
# TYRE COMPOUND SETTINGS
# ============================================================================

TYRE_COMPOUNDS = {
    "SOFT": 0,
    "MEDIUM": 1,
    "HARD": 2,
    "INTERMEDIATE": 3,
    "WET": 4,
}

TYRE_COLORS = {
    "SOFT": (255, 0, 0),  # Red
    "MEDIUM": (255, 255, 0),  # Yellow
    "HARD": (255, 255, 255),  # White
    "INTERMEDIATE": (0, 255, 0),  # Green
    "WET": (0, 0, 255),  # Blue
}


def get_tyre_compound_int(compound_str):
    """Convert tyre compound string to integer code"""
    return TYRE_COMPOUNDS.get(str(compound_str).upper(), -1)


def get_tyre_compound_str(compound_int):
    """Convert tyre compound integer to string"""
    for name, value in TYRE_COMPOUNDS.items():
        if value == compound_int:
            return name
    return "UNKNOWN"


def get_tyre_color(compound_str):
    """Get RGB color for tyre compound"""
    return TYRE_COLORS.get(str(compound_str).upper(), (128, 128, 128))


# ============================================================================
# TELEMETRY DATA RANGES
# ============================================================================

SPEED_MIN = 0
SPEED_MAX = 380  # km/h

THROTTLE_MIN = 0
THROTTLE_MAX = 100

BRAKE_MIN = 0
BRAKE_MAX = 100

GEAR_MIN = 0
GEAR_MAX = 8

RPM_MIN = 0
RPM_MAX = 15000


# ============================================================================
# UI THEME COLORS
# ============================================================================

# Background colors
BG_COLOR_DARK = (20, 20, 25)
BG_COLOR_LIGHT = (240, 240, 245)

# Text colors
TEXT_COLOR_PRIMARY = (255, 255, 255)
TEXT_COLOR_SECONDARY = (180, 180, 180)
TEXT_COLOR_ACCENT = (225, 6, 0)  # F1 Red

# UI Element colors
UI_COLOR_PANEL = (40, 40, 45, 200)
UI_COLOR_BORDER = (100, 100, 105)
UI_COLOR_HIGHLIGHT = (225, 6, 0)

# Status colors
COLOR_STATUS_GREEN = (0, 255, 0)
COLOR_STATUS_YELLOW = (255, 255, 0)
COLOR_STATUS_RED = (255, 0, 0)
COLOR_STATUS_BLUE = (0, 150, 255)


# ============================================================================
# CACHE SETTINGS
# ============================================================================

CACHE_DIR = "data/cache"
FASTF1_CACHE_DIR = f"{CACHE_DIR}/.fastf1"
COMPUTED_DATA_DIR = f"{CACHE_DIR}/computed"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def format_time(seconds):
    """Convert seconds to MM:SS.mmm format"""
    if seconds is None or seconds < 0:
        return "N/A"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes:02d}:{secs:06.3f}"


def format_speed(speed_kmh):
    """Format speed value"""
    if speed_kmh is None:
        return "---"
    return f"{int(speed_kmh)} km/h"


def format_distance(distance_m):
    """Format distance in meters to km"""
    if distance_m is None:
        return "---"
    return f"{distance_m / 1000:.2f} km"


# ============================================================================
# CIRCUIT-SPECIFIC ROTATIONS
# ============================================================================

CIRCUIT_ROTATIONS = {
    "Monaco": 90,
    "Silverstone": 0,
    "Spa-Francorchamps": 45,
    "Monza": 0,
    "Suzuka": 30,
    # Add more as needed
}


def get_circuit_rotation(circuit_name):
    return CIRCUIT_ROTATIONS.get(circuit_name, 0)
