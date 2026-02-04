import fastf1
import pandas as pd

schedule_2024 = fastf1.get_event_schedule(2024)

# Check what columns exist
print("Columns in schedule:", schedule_2024.columns.tolist())

# Show first 5 events with EventFormat
print("\nFirst 5 events with EventFormat:")
print(schedule_2024[['RoundNumber', 'EventName', 'EventFormat']].head())

# Count sprint events
if 'EventFormat' in schedule_2024.columns:
    sprint_count = (schedule_2024['EventFormat'] == 'sprint').sum()
    print(f"\nTotal Sprint events: {sprint_count}")
    
    # Show unique EventFormats
    print("Unique EventFormats:", schedule_2024['EventFormat'].unique())
