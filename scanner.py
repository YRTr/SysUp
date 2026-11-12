import platform
import psutil
import cpuinfo
import GPUtil

def get_size_gb(bytes_val):
    """Convert bytes to gigabytes."""
    return round(bytes_val / (1024 ** 3), 2)

def get_gpu_info():
    """Retrieve GPU models and VRAM details."""
    gpus = []
    try:
        nvidia_gpus = GPUtil.getGPUs()
        for gpu in nvidia_gpus:
            gpus.append({
                "name": gpu.name,
                "vram_total_gb": round(gpu.memoryTotal / 1024, 2),
                "vram_free_gb": round(gpu.memoryFree / 1024, 2),
                "driver": gpu.driver
            })
    except Exception:
        pass

    # Fallback if no NVIDIA GPU is detected
    if not gpus:
        gpus.append({
            "name": "Integrated / Non-NVIDIA GPU",
            "vram_total_gb": 0.0,
            "vram_free_gb": 0.0,
            "driver": "N/A"
        })
    return gpus

def scan_system_specs():
    """Scan and return complete hardware specifications."""
    # CPU Information
    cpu_data = cpuinfo.get_cpu_info()
    cpu_specs = {
        "brand": cpu_data.get("brand_raw", platform.processor()),
        "arch": platform.machine(),
        "physical_cores": psutil.cpu_count(logical=False),
        "logical_cores": psutil.cpu_count(logical=True),
        "max_freq_mhz": psutil.cpu_freq().max if psutil.cpu_freq() else "N/A"
    }

    # RAM Information
    virtual_mem = psutil.virtual_memory()
    ram_specs = {
        "total_gb": get_size_gb(virtual_mem.total),
        "available_gb": get_size_gb(virtual_mem.available)
    }

    # Storage Information (Primary Partition)
    disk_usage = psutil.disk_usage('/')
    storage_specs = {
        "total_gb": get_size_gb(disk_usage.total),
        "free_gb": get_size_gb(disk_usage.free)
    }

    # Compile full hardware profile
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu_specs,
        "ram": ram_specs,
        "storage": storage_specs,
        "gpus": get_gpu_info()
    }

if __name__ == "__main__":
    import json
    specs = scan_system_specs()
    print(json.dumps(specs, indent=4))