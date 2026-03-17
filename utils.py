def format_hours(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m}m"