import platform
import subprocess
import json
import psutil
import cpuinfo
import GPUtil

def get_size_gb(bytes_val):
    """Convert bytes to gigabytes."""
    return round(bytes_val / (1024 ** 3), 2)

def detect_form_factor():
    """
    Detect whether the system is a Laptop or Desktop.
    Laptops have battery sensors and restricted upgrade paths (soldered CPU/GPU).
    """
    battery = psutil.sensors_battery()
    if battery is not None:
        return {
            "chassis_type": "Laptop",
            "is_modular_desktop": False,
            "power_plugged": battery.power_plugged
        }
    return {
        "chassis_type": "Desktop / Server",
        "is_modular_desktop": True,
        "power_plugged": True
    }

# Queries OS hardware tables to detect RAM speed (MHz/MT/s) and how many DIMM slots are occupied vs total slots available
def get_detailed_ram_hardware():
    """
    Probe OS-level SMBIOS/WMI tables for RAM speed (MHz) and physical DIMM slot usage.
    """
    os_name = platform.system()
    ram_details = {
        "speed_mhz": "Unknown",
        "slots_used": "Unknown",
        "slots_total": "Unknown",
        "upgrade_advice": "Check motherboard manual for free DIMM slots."
    }

    try:
        if os_name == "Windows":
            # Query physical memory sticks and array capacity via PowerShell
            ps_cmd = (
                "Get-CimInstance Win32_PhysicalMemory | "
                "Select-Object ConfiguredClockSpeed, Capacity | ConvertTo-Json; "
                "Write-Output '---SPLIT---'; "
                "Get-CimInstance Win32_PhysicalMemoryArray | "
                "Select-Object MemoryDevices | ConvertTo-Json"
            )
            output = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            parts = output.split("---SPLIT---")
            sticks_raw = json.loads(parts[0].strip()) if parts[0].strip() else []
            array_raw = json.loads(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else {}

            sticks = sticks_raw if isinstance(sticks_raw, list) else [sticks_raw]
            slots_used = len(sticks)
            speed = sticks[0].get("ConfiguredClockSpeed", "Unknown") if sticks else "Unknown"
            slots_total = (
                array_raw[0].get("MemoryDevices") if isinstance(array_raw, list)
                else array_raw.get("MemoryDevices", slots_used)
            )

            ram_details["speed_mhz"] = speed
            ram_details["slots_used"] = slots_used
            ram_details["slots_total"] = slots_total

        elif os_name == "Darwin":  # macOS
            output = subprocess.check_output(
                ["system_profiler", "SPMemoryDataType", "-json"],
                text=True, stderr=subprocess.DEVNULL, timeout=5
            )
            data = json.loads(output).get("SPMemoryDataType", [{}])[0]
            ram_details["speed_mhz"] = data.get("dimm_speed", "Unified Memory")
            ram_details["slots_used"] = 1
            ram_details["slots_total"] = 1
            ram_details["upgrade_advice"] = "Apple Unified Memory is soldered and cannot be upgraded post-purchase."

        elif os_name == "Linux":
            # Non-root fallback check; populates if dmidecode permissions allow
            output = subprocess.check_output(
                ["dmidecode", "-t", "memory"],
                text=True, stderr=subprocess.DEVNULL, timeout=4
            )
            total_slots = output.count("Memory Device")
            empty_slots = output.count("Size: No Module Installed")
            ram_details["slots_total"] = total_slots
            ram_details["slots_used"] = total_slots - empty_slots
    except Exception:
        pass

    # Generate slot-aware upgrade advice
    if isinstance(ram_details["slots_used"], int) and isinstance(ram_details["slots_total"], int):
        free_slots = ram_details["slots_total"] - ram_details["slots_used"]
        if free_slots > 0:
            ram_details["upgrade_advice"] = f"{free_slots} empty RAM slot(s) available for direct drop-in expansion."
        else:
            ram_details["upgrade_advice"] = "All RAM slots occupied. Upgrading requires replacing existing sticks."

    return ram_details

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