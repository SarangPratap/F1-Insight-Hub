#!/usr/bin/env python3
"""Find rounds with Sprint sessions"""

from data_engine import get_race_weekends_by_year, enable_cache

enable_cache()

print("=" * 60)
print("Finding Rounds with SPRINT sessions in 2025")
print("=" * 60)

events = get_race_weekends_by_year(2025)

sprint_events = [e for e in events if e['type'] == 'sprint']
conventional_events = [e for e in events if e['type'] == 'conventional']

print(f"\nTOTAL EVENTS: {len(events)}")
print(f"Sprint Events: {len(sprint_events)}")
print(f"Conventional Events: {len(conventional_events)}")

print("\n📍 SPRINT EVENTS:")
for event in sprint_events:
    print(f"   Round {event['round_number']}: {event['event_name']}")

print("\n📍 CONVENTIONAL EVENTS (First 5):")
for event in conventional_events[:5]:
    print(f"   Round {event['round_number']}: {event['event_name']}")

print("\n" + "=" * 60)
