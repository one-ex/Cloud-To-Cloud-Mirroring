def format_bytes(size):
    if size is None:
        return "Tidak diketahui"
    power = 1024
    n = 0
    power_labels = {0: '', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power and n < len(power_labels) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}B"

def format_time(seconds):
    """Format seconds into human readable time (days, hours, minutes, seconds)"""
    if seconds is None or seconds < 0:
        return "0s"
    
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    time_parts = []
    if days > 0:
        time_parts.append(f"{days}d")
    if hours > 0:
        time_parts.append(f"{hours}h")
    if minutes > 0:
        time_parts.append(f"{minutes}m")
    if secs > 0 or not time_parts:
        time_parts.append(f"{secs}s")
    
    return "".join(time_parts)

def format_speed(bytes_per_second):
    """Format bytes per second into human readable speed"""
    if bytes_per_second is None or bytes_per_second <= 0:
        return "0 B/s"
    
    power = 1024
    n = 0
    power_labels = {0: 'B/s', 1: 'KB/s', 2: 'MB/s', 3: 'GB/s', 4: 'TB/s'}
    while bytes_per_second > power and n < len(power_labels) - 1:
        bytes_per_second /= power
        n += 1
    return f"{bytes_per_second:.2f} {power_labels[n]}"

def calculate_eta(current_bytes, total_bytes, bytes_per_second):
    """Calculate estimated time remaining"""
    if not total_bytes or not bytes_per_second or bytes_per_second <= 0:
        return None
    
    remaining_bytes = total_bytes - current_bytes
    if remaining_bytes <= 0:
        return 0
    
    eta_seconds = remaining_bytes / bytes_per_second
    return eta_seconds
