import time
import asyncio
from dst import get_local_time

class Scheduler:
    def __init__(self, config):
        self.config = config
        self.ntp_synced = False
        self.last_ntp_sync = 0

    async def sync_ntp(self):
        try:
            import ntptime
            ntptime.settime()
            self.ntp_synced = True
            self.last_ntp_sync = time.time()
            print("NTP time synced successfully")
        except Exception as e:
            print("NTP sync attempt failed:", e)

    def should_heat(self, ambient_temp, target_temp):
        """Check if any schedule rule requires heating now, including predictive warm-up."""
        if not self.ntp_synced:
            return False, None

        tz_dst = self.config.get("tz_dst", True)
        tm = get_local_time(tz_dst)
        wday = tm[6]  # 0=Monday, 6=Sunday
        cur_min = tm[3] * 60 + tm[4]

        # Calculate warm-up lead time
        heat_rate = float(self.config.get("heat_rate", 0.15)) # deg C / min
        if heat_rate <= 0.01:
            heat_rate = 0.15
        lead_min = 45
        if ambient_temp is not None and target_temp is not None and target_temp > ambient_temp:
            lead_min = int((target_temp - ambient_temp) / heat_rate)
            lead_min = max(0, min(120, lead_min))

        schedules = self.config.get("schedule", [])
        for entry in schedules:
            days = entry.get("days", [])
            if wday not in days:
                continue

            start_s = entry.get("start", "18:00")
            end_s = entry.get("end", "23:00")
            try:
                sh, sm = [int(x) for x in start_s.split(":")]
                eh, em = [int(x) for x in end_s.split(":")]
                start_min = sh * 60 + sm
                end_min = eh * 60 + em

                # Check if current time is in the warm-up window or active heating window
                warmup_start = start_min - lead_min
                if warmup_start <= cur_min < end_min:
                    return True, entry.get("pattern", "calm")
            except Exception:
                continue

        return False, None

