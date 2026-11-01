def evaluate_pattern(pattern_points, elapsed_minutes, default_temp=50.0):
    """Interpolate target temperature given pattern points [[minute, temp], ...]."""
    if not pattern_points:
        return default_temp
    if len(pattern_points) == 1:
        return float(pattern_points[0][1])

    cycle_len = pattern_points[-1][0]
    if cycle_len <= 0:
        return float(pattern_points[0][1])

    m = elapsed_minutes % cycle_len
    if m == 0 and elapsed_minutes > 0:
        m = cycle_len

    for i in range(len(pattern_points) - 1):
        m0, t0 = pattern_points[i]
        m1, t1 = pattern_points[i + 1]
        if m0 <= m <= m1:
            if m1 == m0:
                return float(t0)
            frac = (m - m0) / (m1 - m0)
            return float(t0 + frac * (t1 - t0))

    return float(pattern_points[-1][1])
