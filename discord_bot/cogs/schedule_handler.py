import re

def parse_time_range(time_range):
    """
    Parse a time range string (e.g., "6-8pm") into 24-hour time intervals.
    """
    match = re.match(r"(\d+)-(\d+)(am|pm)", time_range)
    if not match:
        raise ValueError("Invalid time range format")
    
    start_hour = int(match.group(1))
    end_hour = int(match.group(2))
    period = match.group(3)

    if period == "pm" and start_hour != 12:
        start_hour += 12
    if period == "pm" and end_hour != 12:
        end_hour += 12
    
    return start_hour, end_hour

def add_availability(user_id, availability_str, availability_data):
    """
    Add a player's availability to the data store.
    
    Example input: "Monday 6-8pm, Tuesday 7-9pm"
    """
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    user_availability = []
    
    for entry in availability_str.split(","):
        entry = entry.strip()
        day_match = next((day for day in days if day in entry), None)
        
        if not day_match:
            raise ValueError(f"Invalid day in entry: {entry}")
        
        time_range_match = re.search(r"\d+-\d+(am|pm)", entry)
        if not time_range_match:
            raise ValueError(f"Invalid time range in entry: {entry}")
        
        time_range = time_range_match.group()
        start_hour, end_hour = parse_time_range(time_range)
        
        user_availability.append((day_match, start_hour, end_hour))
    
    availability_data[user_id] = user_availability

def find_common_times(availability_data):
    """
    Find common available times across all players.
    
    Returns a list of common time slots (e.g., ["Monday 6-8pm"]).
    """
    from collections import defaultdict

    # Group availabilities by day
    daily_availability = defaultdict(list)
    
    for user_id, availabilities in availability_data.items():
        for day, start_hour, end_hour in availabilities:
            daily_availability[day].append((start_hour, end_hour))
    
    # Find overlapping intervals for each day
    common_times = []
    
    for day, intervals in daily_availability.items():
        intervals.sort()  # Sort by start time
        
        merged_intervals = []
        current_start, current_end = intervals[0]
        
        for start, end in intervals[1:]:
            if start <= current_end:  # Overlapping interval
                current_end = max(current_end, end)
            else:  # Non-overlapping interval
                merged_intervals.append((current_start, current_end))
                current_start, current_end = start, end
        
        merged_intervals.append((current_start, current_end))  # Add the last interval
        
        # Add merged intervals to common times
        for start, end in merged_intervals:
            common_times.append(f"{day} {start}-{end}h")
    
    return common_times
