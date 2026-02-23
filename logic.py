from datetime import datetime

def calculate_billable_hours(start_str, end_str, lunch_mins):
    """Calculates hours from AM/PM strings and subtracts lunch."""
    fmt = "%I:%M %p"
    try:
        s = datetime.strptime(start_str, fmt)
        e = datetime.strptime(end_str, fmt)
        # Handle cases where shift crosses midnight
        diff = (e - s).total_seconds() / 3600
        if diff < 0: diff += 24 
        
        return round(diff - (float(lunch_mins) / 60), 2)
    except Exception:
        return 0.0