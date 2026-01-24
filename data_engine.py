"""
F1 INSIGHT HUB - Data Engine
FastF1 data fetching, telemetry processing, and ML data preparation
"""

import os
import sys
import fastf1
import fastf1.plotting
from multiprocessing import Pool, cpu_count
import numpy as np
import json
import pickle
from datetime import timedelta
import pandas as pd

from config import (
    FPS,
    DT,
    CACHE_DIR,
    FASTF1_CACHE_DIR,
    COMPUTED_DATA_DIR,
    get_tyre_compound_int,
    format_time,
)


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================


def enable_cache():
    """Enable and configure FastF1 cache"""
    if not os.path.exists(FASTF1_CACHE_DIR):
        os.makedirs(FASTF1_CACHE_DIR)
    if not os.path.exists(COMPUTED_DATA_DIR):
        os.makedirs(COMPUTED_DATA_DIR)

    fastf1.Cache.enable_cache(FASTF1_CACHE_DIR)
    print(f"Cache enabled at: {FASTF1_CACHE_DIR}")


# ============================================================================
# SESSION LOADING
# ============================================================================


def load_session(year, round_number, session_type="R"):
    """
    Load a FastF1 session

    Args:
        year: Season year
        round_number: Round number in calendar
        session_type: 'R' (Race), 'Q' (Qualifying), 'S' (Sprint), 'SQ' (Sprint Qualifying)

    Returns:
        FastF1 Session object
    """
    session_map = {
        "R": "Race",
        "Q": "Qualifying",
        "S": "Sprint",
        "SQ": "Sprint Qualifying",
    }

    session_name = session_map.get(session_type, "Race")

    try:
        session = fastf1.get_session(year, round_number, session_name)
        session.load()
        return session
    except Exception as e:
        print(f"Error loading session: {e}")
        return None


def get_race_weekends_by_year(year):
    """
    Get all race weekends for a given year

    Args:
        year: Season year

    Returns:
        List of race weekend dictionaries
    """
    try:
        schedule = fastf1.get_event_schedule(year)
        events = []

        for idx, event in schedule.iterrows():
            event_type = "conventional"
            if (
                event.get("EventFormat") == "sprint"
                or event.get("EventFormat") == "sprint_shootout"
            ):
                event_type = "sprint"

            events.append(
                {
                    "round_number": event["RoundNumber"],
                    "event_name": event["EventName"],
                    "country": event.get("Country", "N/A"),
                    "location": event.get("Location", "N/A"),
                    "date": event["EventDate"].strftime("%Y-%m-%d")
                    if pd.notna(event["EventDate"])
                    else "TBA",
                    "type": event_type,
                }
            )

        return events
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []


def list_rounds(year):
    """Print all rounds for a given year"""
    events = get_race_weekends_by_year(year)
    print(f"\n=== {year} F1 Season ===")
    for event in events:
        print(f"Round {event['round_number']}: {event['event_name']} ({event['date']})")


def list_sprints(year):
    """Print all sprint rounds for a given year"""
    events = get_race_weekends_by_year(year)
    sprint_events = [e for e in events if e["type"] == "sprint"]
    print(f"\n=== {year} F1 Sprint Rounds ===")
    for event in sprint_events:
        print(f"Round {event['round_number']}: {event['event_name']} ({event['date']})")


def get_circuit_rotation(session):
    """
    Determine circuit rotation angle for better visualization

    Args:
        session: FastF1 Session object

    Returns:
        Rotation angle in degrees
    """
    circuit_name = session.event.get("Location", "")

    rotations = {
        "Monaco": 90,
        "Silverstone": 0,
        "Spa-Francorchamps": 45,
        "Monza": 0,
        "Suzuka": 30,
        "Bahrain": 0,
        "Jeddah": 270,
        "Melbourne": 180,
        "Imola": 45,
        "Miami": 0,
        "Barcelona": 315,
        "Austria": 45,
        "Budapest": 0,
        "Zandvoort": 180,
        "Singapore": 90,
        "Austin": 0,
        "Mexico City": 270,
        "São Paulo": 225,
        "Las Vegas": 45,
        "Abu Dhabi": 180,
    }

    return rotations.get(circuit_name, 0)


# ============================================================================
# TELEMETRY PROCESSING (Multi-threaded)
# ============================================================================


def _process_single_driver(args):
    """
    Process telemetry data for a single driver (must be top-level for multiprocessing)

    Args:
        args: Tuple of (driver_no, session, driver_code)

    Returns:
        Dictionary with processed driver data or None
    """
    driver_no, session, driver_code = args

    print(f"Processing telemetry for driver: {driver_code}")

    laps_driver = session.laps.pick_drivers(driver_no)
    if laps_driver.empty:
        return None

    driver_max_lap = laps_driver.LapNumber.max() if not laps_driver.empty else 0

    # Initialize data arrays
    t_all = []
    x_all = []
    y_all = []
    race_dist_all = []
    rel_dist_all = []
    lap_numbers = []
    tyre_compounds = []
    speed_all = []
    gear_all = []
    drs_all = []
    throttle_all = []
    brake_all = []

    total_dist_so_far = 0.0

    # Iterate through laps in order
    for _, lap in laps_driver.iterlaps():
        lap_tel = lap.get_telemetry()
        lap_number = lap.LapNumber
        tyre_compound_as_int = get_tyre_compound_int(lap.Compound)

        if lap_tel.empty:
            continue

        # Extract telemetry arrays
        t_lap = lap_tel["SessionTime"].dt.total_seconds().to_numpy()
        x_lap = lap_tel["X"].to_numpy()
        y_lap = lap_tel["Y"].to_numpy()
        d_lap = lap_tel["Distance"].to_numpy()
        rd_lap = lap_tel["RelativeDistance"].to_numpy()
        speed_kph_lap = lap_tel["Speed"].to_numpy()
        gear_lap = lap_tel["nGear"].to_numpy()
        drs_lap = lap_tel["DRS"].to_numpy()
        throttle_lap = lap_tel["Throttle"].to_numpy()
        brake_lap = lap_tel["Brake"].to_numpy().astype(float)

        # Calculate cumulative race distance
        race_d_lap = total_dist_so_far + d_lap

        # Append to collection arrays
        t_all.append(t_lap)
        x_all.append(x_lap)
        y_all.append(y_lap)
        race_dist_all.append(race_d_lap)
        rel_dist_all.append(rd_lap)
        lap_numbers.append(np.full_like(t_lap, lap_number))
        tyre_compounds.append(np.full_like(t_lap, tyre_compound_as_int))
        speed_all.append(speed_kph_lap)
        gear_all.append(gear_lap)
        drs_all.append(drs_lap)
        throttle_all.append(throttle_lap)
        brake_all.append(brake_lap)

        # Update total distance for next lap
        if len(d_lap) > 0:
            total_dist_so_far += d_lap[-1]  # Last distance value of the lap

    if not t_all:
        return None

    # Concatenate all arrays
    all_arrays = [
        t_all,
        x_all,
        y_all,
        race_dist_all,
        rel_dist_all,
        lap_numbers,
        tyre_compounds,
        speed_all,
        gear_all,
        drs_all,
    ]

    (
        t_all,
        x_all,
        y_all,
        race_dist_all,
        rel_dist_all,
        lap_numbers,
        tyre_compounds,
        speed_all,
        gear_all,
        drs_all,
    ) = [np.concatenate(arr) for arr in all_arrays]

    # Sort all arrays by time
    order = np.argsort(t_all)
    all_data = [
        t_all,
        x_all,
        y_all,
        race_dist_all,
        rel_dist_all,
        lap_numbers,
        tyre_compounds,
        speed_all,
        gear_all,
        drs_all,
    ]

    (
        t_all,
        x_all,
        y_all,
        race_dist_all,
        rel_dist_all,
        lap_numbers,
        tyre_compounds,
        speed_all,
        gear_all,
        drs_all,
    ) = [arr[order] for arr in all_data]

    throttle_all = np.concatenate(throttle_all)[order]
    brake_all = np.concatenate(brake_all)[order]

    print(f"Completed telemetry for driver: {driver_code}")

    return {
        "code": driver_code,
        "data": {
            "t": t_all,
            "x": x_all,
            "y": y_all,
            "dist": race_dist_all,
            "rel_dist": rel_dist_all,
            "lap": lap_numbers,
            "tyre": tyre_compounds,
            "speed": speed_all,
            "gear": gear_all,
            "drs": drs_all,
            "throttle": throttle_all,
            "brake": brake_all,
        },
        "t_min": t_all.min(),
        "t_max": t_all.max(),
        "max_lap": driver_max_lap,
    }


# ... continuing from Part 1 ...


def get_race_telemetry(session, session_type="R", force_refresh=False):
    """
    Get processed race telemetry for all drivers with frame-by-frame data

    Args:
        session: FastF1 Session object
        session_type: 'R' or 'S'
        force_refresh: Force recomputation even if cached

    Returns:
        Dictionary with frames, driver colors, track statuses, and metadata
    """
    # Check for cached data
    cache_filename = f"{COMPUTED_DATA_DIR}/race_{session.event['EventName'].replace(' ', '_')}_{session.event['RoundNumber']}_{session_type}.pkl"

    if os.path.exists(cache_filename) and not force_refresh:
        print(f"Loading cached telemetry from: {cache_filename}")
        with open(cache_filename, "rb") as f:
            return pickle.load(f)

    print("Computing race telemetry...")

    drivers = session.drivers
    driver_codes = {}
    for driver_no in drivers:
        try:
            driver_info = session.get_driver(driver_no)
            driver_codes[driver_no] = driver_info["Abbreviation"]
        except:
            driver_codes[driver_no] = str(driver_no)

    # Process all drivers in parallel
    driver_data = {}
    global_t_min = None
    global_t_max = None
    max_lap_number = 0

    print(f"Processing {len(drivers)} drivers in parallel...")
    driver_args = [
        (driver_no, session, driver_codes[driver_no]) for driver_no in drivers
    ]

    num_processes = min(cpu_count(), len(drivers))

    with Pool(processes=num_processes) as pool:
        results = pool.map(_process_single_driver, driver_args)

    # Process results
    for result in results:
        if result is None:
            continue

        code = result["code"]
        driver_data[code] = result["data"]

        t_min = result["t_min"]
        t_max = result["t_max"]
        max_lap_number = max(max_lap_number, result["max_lap"])

        global_t_min = t_min if global_t_min is None else min(global_t_min, t_min)
        global_t_max = t_max if global_t_max is None else max(global_t_max, t_max)

    if global_t_min is None or global_t_max is None:
        print("Error: No valid telemetry data found")
        return None

    print(f"Time range: {global_t_min:.2f}s to {global_t_max:.2f}s")
    print(f"Max laps: {max_lap_number}")

    # Create unified timeline
    n_frames = int((global_t_max - global_t_min) / DT) + 1
    timeline = np.linspace(global_t_min, global_t_max, n_frames)

    print(f"Resampling to {n_frames} frames at {FPS} FPS...")

    # Resample all driver data to unified timeline
    resampled_data = {}
    for code, data in driver_data.items():
        t_sorted = data["t"]
        order = np.argsort(t_sorted)
        t_sorted = t_sorted[order]

        arrays_to_resample = [
            data["x"][order],
            data["y"][order],
            data["dist"][order],
            data["rel_dist"][order],
            data["lap"][order],
            data["tyre"][order],
            data["speed"][order],
            data["gear"][order],
            data["drs"][order],
            data["throttle"][order],
            data["brake"][order],
        ]

        resampled = [np.interp(timeline, t_sorted, arr) for arr in arrays_to_resample]
        (
            x_r,
            y_r,
            dist_r,
            rel_dist_r,
            lap_r,
            tyre_r,
            speed_r,
            gear_r,
            drs_r,
            throttle_r,
            brake_r,
        ) = resampled

        resampled_data[code] = {
            "t": timeline,
            "x": x_r,
            "y": y_r,
            "dist": dist_r,
            "rel_dist": rel_dist_r,
            "lap": lap_r,
            "tyre": tyre_r,
            "speed": speed_r,
            "gear": gear_r,
            "drs": drs_r,
            "throttle": throttle_r,
            "brake": brake_r,
        }

    # Get driver colors
    driver_colors = {}
    for code in resampled_data.keys():
        try:
            color = fastf1.plotting.get_driver_color(code, session)
            # Convert hex to RGB tuple
            color = color.lstrip("#")
            driver_colors[code] = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
        except:
            driver_colors[code] = (255, 255, 255)

    # Extract weather data if available
    weather_resampled = None
    try:
        weather = session.weather_data
        if weather is not None and not weather.empty:
            weather_t = weather["Time"].dt.total_seconds().to_numpy()
            weather_resampled = {
                "rainfall": np.interp(
                    timeline, weather_t, weather["Rainfall"].to_numpy()
                ),
                "track_temp": np.interp(
                    timeline, weather_t, weather["TrackTemp"].to_numpy()
                ),
                "air_temp": np.interp(
                    timeline, weather_t, weather["AirTemp"].to_numpy()
                ),
                "humidity": np.interp(
                    timeline, weather_t, weather["Humidity"].to_numpy()
                ),
                "pressure": np.interp(
                    timeline, weather_t, weather["Pressure"].to_numpy()
                ),
                "wind_speed": np.interp(
                    timeline, weather_t, weather["WindSpeed"].to_numpy()
                ),
            }
            if "WindDirection" in weather.columns:
                weather_resampled["wind_direction"] = np.interp(
                    timeline, weather_t, weather["WindDirection"].to_numpy()
                )
    except Exception as e:
        print(f"Weather data not available: {e}")

    # Extract track status events
    track_statuses = []
    try:
        status_data = session.track_status
        if status_data is not None and not status_data.empty:
            for _, row in status_data.iterrows():
                track_statuses.append(
                    {
                        "status": row["Status"],
                        "start_time": row["Time"].total_seconds()
                        if pd.notna(row["Time"])
                        else 0,
                        "message": row.get("Message", ""),
                    }
                )
    except Exception as e:
        print(f"Track status not available: {e}")

    # Build frames
    frames = []
    print("Building frames...")

    for i, t in enumerate(timeline):
        # Sort drivers by race distance (position)
        cars = []
        for code, data in resampled_data.items():
            cars.append(
                {
                    "code": code,
                    "x": data["x"][i],
                    "y": data["y"][i],
                    "dist": data["dist"][i],
                    "rel_dist": data["rel_dist"][i],
                    "lap": int(data["lap"][i]),
                    "tyre": int(data["tyre"][i]),
                    "speed": data["speed"][i],
                    "gear": int(data["gear"][i]),
                    "drs": int(data["drs"][i]),
                    "throttle": data["throttle"][i],
                    "brake": data["brake"][i],
                }
            )

        cars.sort(key=lambda c: -c["dist"])

        frame_data = {}
        for idx, car in enumerate(cars):
            code = car["code"]
            position = idx + 1

            frame_data[code] = {
                "x": car["x"],
                "y": car["y"],
                "dist": car["dist"],
                "lap": car["lap"],
                "rel_dist": round(car["rel_dist"], 4),
                "tyre": car["tyre"],
                "position": position,
                "speed": car["speed"],
                "gear": car["gear"],
                "drs": car["drs"],
                "throttle": car["throttle"],
                "brake": car["brake"],
            }

        weather_snapshot = {}
        if weather_resampled:
            try:
                weather_snapshot = {
                    "rainfall": float(weather_resampled["rainfall"][i]),
                    "track_temp": float(weather_resampled["track_temp"][i]),
                    "air_temp": float(weather_resampled["air_temp"][i]),
                    "humidity": float(weather_resampled["humidity"][i]),
                    "pressure": float(weather_resampled["pressure"][i]),
                    "wind_speed": float(weather_resampled["wind_speed"][i]),
                }
                if "wind_direction" in weather_resampled:
                    weather_snapshot["wind_direction"] = float(
                        weather_resampled["wind_direction"][i]
                    )
            except:
                pass

        frames.append(
            {
                "time": float(t),
                "drivers": frame_data,
                "weather": weather_snapshot if weather_snapshot else None,
            }
        )

    result = {
        "frames": frames,
        "driver_colors": driver_colors,
        "track_statuses": track_statuses,
        "total_laps": int(max_lap_number),
    }

    # Cache the result
    print(f"Caching telemetry to: {cache_filename}")
    with open(cache_filename, "wb") as f:
        pickle.dump(result, f)

    return result


# ============================================================================
# QUALIFYING SESSION DATA
# ============================================================================


def get_quali_telemetry(session, session_type="Q"):
    """
    Get qualifying session results and telemetry

    Args:
        session: FastF1 Session object
        session_type: 'Q' or 'SQ'

    Returns:
        Dictionary with qualifying results and lap data
    """
    results = []

    for driver in session.drivers:
        driver_laps = session.laps.pick_drivers(driver)
        if driver_laps.empty:
            continue

        driver_info = session.get_driver(driver)
        driver_code = driver_info["Abbreviation"]

        # Get best lap times from each segment
        q1_time = None
        q2_time = None
        q3_time = None

        q1_laps = driver_laps[driver_laps["Q1"].notna()]
        if not q1_laps.empty:
            q1_time = q1_laps["LapTime"].min()

        q2_laps = driver_laps[driver_laps["Q2"].notna()]
        if not q2_laps.empty:
            q2_time = q2_laps["LapTime"].min()

        q3_laps = driver_laps[driver_laps["Q3"].notna()]
        if not q3_laps.empty:
            q3_time = q3_laps["LapTime"].min()

        # Get overall best lap
        best_lap = driver_laps.pick_fastest()

        results.append(
            {
                "driver": driver_code,
                "q1": q1_time.total_seconds() if q1_time else None,
                "q2": q2_time.total_seconds() if q2_time else None,
                "q3": q3_time.total_seconds() if q3_time else None,
                "best": best_lap["LapTime"].total_seconds()
                if best_lap is not None and pd.notna(best_lap["LapTime"])
                else None,
                "position": best_lap["Position"] if best_lap is not None else None,
            }
        )

    # Sort by best lap time
    results.sort(key=lambda x: (x["best"] is None, x["best"]))

    return {"results": results, "session_type": session_type}


# ============================================================================
# ML DATA PREPARATION (Placeholder for future ML modules)
# ============================================================================


def prepare_ml_features(session):
    """
    Prepare features for machine learning models

    Args:
        session: FastF1 Session object

    Returns:
        DataFrame with ML features
    """
    # Placeholder - to be implemented in Intelligence Module
    pass


def calculate_driver_performance_scores(session):
    """
    Calculate performance scores for drivers

    Args:
        session: FastF1 Session object

    Returns:
        Dictionary with driver scores
    """
    # Placeholder - to be implemented in Intelligence Module
    pass


if __name__ == "__main__":
    # Test the data engine
    enable_cache()
    print("Data Engine initialized")

    # Example usage
    if len(sys.argv) > 2:
        year = int(sys.argv[1])
        round_num = int(sys.argv[2])

        session = load_session(year, round_num, "R")
        if session:
            print(f"Loaded: {session.event['EventName']}")
            telemetry = get_race_telemetry(session)
            print(f"Generated {len(telemetry['frames'])} frames")
