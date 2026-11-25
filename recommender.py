from scanner import scan_system_specs
from geo_pricing import (
    get_user_location,
    calculate_localized_budget,
    calculate_power_and_opex
)

# Workload target matrix with current-gen hardware, wattage, and daily duty cycles
WORKLOAD_PROFILES = {
    "fullstack_dev": {
        "title": "Full-Stack & Containerized Development (MERN, Docker, Local DBs)",
        "tier": "prosumer",
        "min_specs": {"cpu_cores": 8, "ram_gb": 32, "vram_gb": 0, "storage_gb": 1000},
        "duty_cycle_hours": 10,
        "pc_build": {
            "cpu": "AMD Ryzen 7 9700X / Intel Core Ultra 7 265K",
            "gpu": "Integrated or RTX 4060 8GB",
            "ram": "32GB DDR5-6000MHz",
            "storage": "1TB PCIe 4.0 NVMe SSD",
            "avg_watts": 100,
            "usd_range": (950, 1250)
        },
        "laptop_option": {
            "models": "MacBook Air M3 (24GB/1TB) / Lenovo ThinkPad E16 Gen 3 / ASUS Zenbook 14 Core Ultra",
            "specs": "24-32GB Unified/DDR5 RAM, 1TB NVMe, 8+ Core CPU",
            "avg_watts": 45,
            "usd_range": (1150, 1500)
        }
    },
    "gaming_aaa": {
        "title": "High-Refresh 1440p / 4K AAA Gaming",
        "tier": "prosumer",
        "min_specs": {"cpu_cores": 8, "ram_gb": 32, "vram_gb": 16, "storage_gb": 2000},
        "duty_cycle_hours": 5,
        "pc_build": {
            "cpu": "AMD Ryzen 7 9800X3D",
            "gpu": "NVIDIA RTX 4070 Ti Super 16GB / RTX 5070 Ti 16GB",
            "ram": "32GB DDR5-6000MHz CL30",
            "storage": "2TB PCIe 4.0 NVMe SSD",
            "avg_watts": 450,
            "usd_range": (1750, 2250)
        },
        "laptop_option": {
            "models": "ASUS ROG Zephyrus G16 / Lenovo Legion Pro 7i",
            "specs": "Core Ultra 9 / Ryzen 9, Mobile RTX 4080 12GB, 32GB RAM, 2TB SSD",
            "avg_watts": 190,
            "usd_range": (2300, 2850)
        }
    },
    "ai_local_finetuning": {
        "title": "Local AI Image Generation, LoRA Fine-Tuning & LLM Quantized Inference",
        "tier": "workstation",
        "min_specs": {"cpu_cores": 12, "ram_gb": 64, "vram_gb": 16, "storage_gb": 2000},
        "duty_cycle_hours": 12,
        "pc_build": {
            "cpu": "AMD Ryzen 9 9900X (12-Core / 24-Thread)",
            "gpu": "NVIDIA RTX 4070 Ti Super 16GB / RTX 5090 32GB (for heavy batch LoRA)",
            "ram": "64GB DDR5-6000MHz",
            "storage": "2TB PCIe 4.0 NVMe SSD (High TBW for model checkpoints)",
            "avg_watts": 650,
            "usd_range": (2000, 3800)
        },
        "laptop_option": {
            "models": "MacBook Pro 16 M4 Max (64GB Unified Memory) / MSI Titan 18 HX (RTX 4090 16GB)",
            "specs": "64GB Unified Memory architecture or 175W TGP Mobile GPU, 64GB RAM, 2TB NVMe",
            "avg_watts": 140,
            "usd_range": (3400, 4400)
        }
    },
    "enterprise_ai_datacenter": {
        "title": "Foundation Model Training (70B+ Params) / High-Density Crypto Node Cluster",
        "tier": "datacenter",
        "min_specs": {"cpu_cores": 64, "ram_gb": 512, "vram_gb": 384, "storage_gb": 15000},
        "duty_cycle_hours": 24,
        "datacenter_rack": {
            "compute_nodes": "2x 4U GPU Servers (Dual AMD EPYC 9354 32-Core per node)",
            "gpu_cluster": "4x NVIDIA RTX PRO 6000 Blackwell (96GB GDDR7 ECC each) or 8x HGX B200 (180GB HBM3e via NVLink)",
            "memory": "512GB - 1TB DDR5 ECC Registered RAM",
            "storage_san": "15.36TB Enterprise U.3 NVMe RAID Array (Scratch) + 40TB NAS",
            "networking_power": "42U Rack, 100GbE Mellanox InfiniBand Switch, Dual 3-Phase PDU + 10kVA Online UPS, Dedicated Precision Cooling",
            "avg_watts": 9500,
            "usd_range": (65000, 250000)
        }
    }
}


# Precision byte weights and task overhead multipliers for dynamic VRAM estimation
PRECISION_BYTES = {
    "fp16": 2.0,   # BF16 / FP16
    "int8": 1.0,   # FP8 / INT8
    "int4": 0.5    # 4-bit QLoRA / GGUF
}

TASK_OVERHEAD = {
    "inference": 1.25,     # Model weights + KV cache + runtime buffers
    "lora_finetune": 1.75, # Weights + LoRA adapters + activations + gradients
    "full_train": 4.5      # Weights + full gradients + AdamW optimizer states
}

def estimate_ai_vram_gb(model_params_b, precision="int4", task="lora_finetune"):
    """
    Calculate estimated VRAM (GB) required for an AI model workload.
    Formula: Params (B) * Bytes_per_Param * Task_Overhead_Multiplier
    """
    bytes_per_param = PRECISION_BYTES.get(precision.lower(), 0.5)
    overhead = TASK_OVERHEAD.get(task.lower(), 1.25)
    return round(model_params_b * bytes_per_param * overhead, 1)

def analyze_bottlenecks(current_specs, target_min):
    """Compare current scanned specs against workload minimum thresholds."""
    bottlenecks = []
    deficits = {
        "cpu_short": False,
        "ram_deficit_gb": 0,
        "vram_deficit_gb": 0,
        "storage_deficit_gb": 0,
        "slow_hdd": False
    }

    curr_cores = current_specs["cpu"].get("physical_cores") or 4
    curr_ram = current_specs["ram"].get("total_gb", 0)
    curr_storage = current_specs["storage"].get("total_gb", 0)
    media_type = current_specs["storage"]. get("media_type", "")
    curr_vram = max([gpu.get("vram_total_gb", 0) for gpu in current_specs.get("gpus", [])], default=0)

    if curr_cores < target_min["cpu_cores"]:
        deficits["cpu_short"] = True
        bottlenecks.append(
            f"CPU Cores: Have {curr_cores} physical cores, need at least {target_min['cpu_cores']}."
        )
    if curr_ram < target_min["ram_gb"]:
        ram_gap = round(target_min["ram_gb"] - curr_ram, 1)
        deficits["ram_deficit_gb"] = ram_gap
        bottlenecks.append(
            f"System RAM: Have {curr_ram} GB, need {target_min['ram_gb']} GB (short by {ram_gap} GB)."
        )
    if curr_vram < target_min["vram_gb"]:
        vram_gap = round(target_min["vram_gb"] - curr_vram, 1)
        deficits["vram_deficit_gb"] = vram_gap
        bottlenecks.append(
            f"GPU VRAM: Have {curr_vram} GB dedicated VRAM, need {target_min['vram_gb']} GB for CUDA/tensor workloads."
        )
    if curr_storage < target_min["storage_gb"]:
        storage_gap = round(target_min["storage_gb"] - curr_storage, 1)
        deficits["storage_deficits_gb"] = storage_gap
        bottlenecks.append(
            f"Storage Capacity: Primary drive is {curr_storage} GB, recommended is {target_min['storage_gb']} GB+ NVMe."
        )
    if "HDD" in media_type.upper():
        deficits["slow_hdd"] = True
        bottlenecks.append(
            f"Storage Speed: Detected rotational drive ({media_type}). Upgrade to PCIe 4.0 NVMe SSD to avoid I/O bottlenecks."
        )

    return bottlenecks, deficits


def calculate_surgical_upgrade(current_specs, target_min, deficits, location_data):
    """
    Evaluate whether a modular drop-in component upgrade is viable instead of a full rebuild.
    Uses Module 1 form factor, RAM slot availability, and drive media type.
    """
    is_desktop = current_specs.get("form_factor", {}).get("is_modular_desktop", True)
    ram_info = current_specs.get("ram", {})
    slots_used = ram_info.get("slots_used", "Unknown")
    slots_total = ram_info.get("slots_total", "Unknown")
    is_mac_soldered = "Unified" in str(ram_info.get("speed_mhz", ""))

    parts_to_buy = []
    notes = []
    usd_min = 0
    usd_max = 0
    viable = True

    # 1. RAM Drop-In Assessment
    if deficits["ram_deficit_gb"] > 0:
        if is_mac_soldered:
            viable = False
            notes.append("RAM is soldered Unified Memory — a surgical RAM upgrade is impossible.")
        else:
            free_slots = (
                slots_total - slots_used
                if isinstance(slots_used, int) and isinstance(slots_total, int)
                else 0
            )
            if free_slots > 0:
                add_gb = int(target_min["ram_gb"] - current_specs["ram"]["total_gb"])
                parts_to_buy.append(f"Add {add_gb}GB+ matching RAM stick(s) into {free_slots} empty slot(s)")
                usd_min += max(45, int(add_gb * 2.8))
                usd_max += max(75, int(add_gb * 3.8))
            else:
                target_gb = target_min["ram_gb"]
                parts_to_buy.append(f"Replace existing RAM with a full {target_gb}GB kit (all slots occupied)")
                usd_min += int(target_gb * 3.0)
                usd_max += int(target_gb * 4.2)
    # 2. Storage Drop-In Assessment
    if deficits["storage_deficit_gb"] > 0 or deficits["slow_hdd"]:
        drive_size = "2TB" if target_min["storage_gb"] >= 2000 else "1TB"
        parts_to_buy.append(f"{drive_size} PCIe 4.0 NVMe M.2 SSD")
        usd_min += 125 if drive_size == "2TB" else 70
        usd_max += 175 if drive_size == "2TB" else 105

    # 3. GPU Drop-In Assessment
    if deficits["vram_deficit_gb"] > 0:
        req_vram = target_min["vram_gb"]
        if not is_desktop:
            viable = False
            notes.append(
                "Laptop GPU is soldered. Internal GPU swap is impossible — consider an OCuLink/Thunderbolt 4 eGPU enclosure or a full system upgrade."
            )
        else:
            if req_vram <= 16:
                parts_to_buy.append("NVIDIA RTX 5070 Ti 16GB (Drop-In PCIe GPU)")
                usd_min += 750
                usd_max += 950
                notes.append("Verify your desktop PSU is at least 750W ATX 3.0/3.1 before installing.")
            elif req_vram <= 32:
                parts_to_buy.append("NVIDIA RTX 5090 32GB (Drop-In PCIe GPU) + 1000W ATX 3.1 PSU")
                usd_min += 2200
                usd_max += 2800
                notes.append("Requires a 1000W+ ATX 3.1 power supply and high-airflow chassis clearance.")
            else:
                viable = False
                notes.append("Required VRAM exceeds single consumer GPU limits (>32GB).")

    # 4. CPU Assessment
    if deficits["cpu_short"]:
        if not is_desktop:
            viable = False
            notes.append("Laptop CPU is soldered and cannot be upgraded.")
        else:
            parts_to_buy.append(f"{target_min['cpu_cores']}+ Core Desktop CPU (Verify motherboard socket compatibility)")
            usd_min += 300
            usd_max += 480

    if not parts_to_buy and viable:
        return {
            "viable": True,
            "status": "No hardware purchases required — your current machine passes.",
            "parts_list": [],
            "notes": notes,
            "estimated_budget": "0",
            "pricing_details": None
        }

    pricing = calculate_localized_budget(usd_min, usd_max, location_data) if viable else None

    return {
        "viable": viable,
        "status": "Surgical drop-in upgrade recommended!" if viable else "Full system replacement recommended (chassis/hardware limits reached).",
        "chassis_detected": current_specs.get("form_factor", {}).get("chassis_type", "Unknown"),
        "parts_list": parts_to_buy,
        "notes": notes,
        "estimated_budget": pricing["formatted_budget"] if pricing else "N/A (See Full Build / Laptop Options)",
        "pricing_details": pricing
    }

def generate_recommendation(goal_key, current_specs=None, location_data=None):
    """
    Generate full upgrade path, surgical delta kit, localized CapEx, and monthly OpEx.
    Optional `ai_params`: {"model_params_b": 70, "precision": "fp16", "task": "lora_finetune"}
    """
    if goal_key not in WORKLOAD_PROFILES:
        raise ValueError(f"Unknown workload goal. Choose from: {list(WORKLOAD_PROFILES.keys())}")

    if not current_specs:
        current_specs = scan_system_specs()
    if not location_data:
        location_data = get_user_location()

    # Copy baseline profile so dynamic overrides don't mutate the global dict
    profile = WORKLOAD_PROFILES[goal_key]
    target_min = dict(profile["min_specs"])
    active_tier = profile["tier"]
    dynamic_ai_summary = None

    report = {
        "selected_goal": profile["title"],
        "workload_tier": profile["tier"],
        "system_passed": meets_requirements,
        "detected_bottlenecks": bottlenecks if not meets_requirements else [
            "Your current system meets or exceeds all baseline requirements!"],
        "location_detected": f"{location_data['city']}, {location_data['country_name']} ({location_data['currency']})",
        "recommendations": {}
    }

    # Route 1: Extreme Workload -> Recommend Small Data Center Setup
    if profile["tier"] == "datacenter":
        dc = profile["datacenter_rack"]
        dc_budget = calculate_localized_budget(dc["usd_range"][0], dc["usd_range"][1], location_data)

        report["recommendations"]["warning"] = (
            "Consumer desktops and laptops cannot handle this workload efficiently due to PCIe lane, "
            "memory bandwidth, and thermal limits. A dedicated small data center / server rack is required."
        )
        report["recommendations"]["small_datacenter_blueprint"] = {
            "compute_nodes": dc["compute_nodes"],
            "gpu_cluster": dc["gpu_cluster"],
            "memory": dc["memory"],
            "storage_san": dc["storage_san"],
            "infrastructure": dc["networking_power"],
            "estimated_budget": dc_budget["formatted_budget"],
            "pricing_details": dc_budget
        }

    # Route 2: Standard / Workstation Workload -> Recommend PC + Laptop paths
    else:
        pc = profile["pc_build"]
        laptop = profile["laptop_option"]

        pc_budget = calculate_localized_budget(pc["usd_range"][0], pc["usd_range"][1], location_data)
        laptop_budget = calculate_localized_budget(laptop["usd_range"][0], laptop["usd_range"][1], location_data)

        report["recommendations"]["desktop_pc_upgrade"] = {
            "cpu": pc["cpu"],
            "gpu": pc["gpu"],
            "ram": pc["ram"],
            "storage": pc["storage"],
            "estimated_budget": pc_budget["formatted_budget"],
            "pricing_details": pc_budget
        }
        report["recommendations"]["laptop_alternative"] = {
            "recommended_models": laptop["models"],
            "target_specs": laptop["specs"],
            "estimated_budget": laptop_budget["formatted_budget"],
            "pricing_details": laptop_budget
        }

    return report

if __name__ == "__main__":
    import json

    # Scan local machine and location once
    my_specs = scan_system_specs()
    my_loc = get_user_location()

    print("--- TEST 1: Local AI Fine-Tuning Check ---")
    ai_report = generate_recommendation("ai_local_finetuning", my_specs, my_loc)
    print(json.dumps(ai_report, indent=4))

    print("\n--- TEST 2: Enterprise Data Center Trigger ---")
    dc_report = generate_recommendation("enterprise_ai_datacenter", my_specs, my_loc)
    print(json.dumps(dc_report, indent=4))