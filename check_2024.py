from data_engine import get_race_weekends_by_year, enable_cache
enable_cache()
events_2024 = get_race_weekends_by_year(2024)
sprint_events = [e for e in events_2024 if 'sprint' in e['type'].lower()]
print(f'2024 Sprint Events: {len(sprint_events)}')
for e in sprint_events[:5]:
    print(f'  Round {e["round_number"]}: {e["event_name"]}')
