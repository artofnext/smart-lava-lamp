import time

def _last_sunday(year, month):
    """Return the day of month (25..31) for the last Sunday in March or October (0=Sun)."""
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    y = year if month >= 3 else year - 1
    # Sakamoto algorithm for 31st of month: returns 0=Sunday, 1=Monday...
    dow = (y + y // 4 - y // 100 + y // 400 + t[month - 1] + 31) % 7
    return 31 - dow

def is_dst_london(year, month, day, hour):
    """Return True if UTC time is within British Summer Time (BST / WEST)."""
    if month < 3 or month > 10:
        return False
    if 3 < month < 10:
        return True

    if month == 3:
        sun = _last_sunday(year, 3)
        if day < sun:
            return False
        if day > sun:
            return True
        return hour >= 1

    if month == 10:
        sun = _last_sunday(year, 10)
        if day < sun:
            return True
        if day > sun:
            return False
        return hour < 1

    return False

def get_local_time(tz_dst=True):
    """Return (year, month, mday, hour, minute, second, wday) in local London/Lisbon time."""
    now_utc = time.time()
    tm = time.localtime(now_utc)
    offset_hours = 0
    if tz_dst and is_dst_london(tm[0], tm[1], tm[2], tm[3]):
        offset_hours = 1

    if offset_hours:
        tm = time.localtime(now_utc + offset_hours * 3600)
    return tm
