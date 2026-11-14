from scanner import scan_system_specs
from geo_pricing import get_user_location, calculate_localized_budget

# Workload target matrix and hardware recommendations
WORKLOAD_PROFILES = {
    "fullstack_dev": {
        "title": "Full-Stack & Containerized Development (MERN, Docker, Local DBs)",
        "tier": "prosumer",
        "min_specs": {"cpu_cores": 8, "ram_gb": 32, "vram_gb": 0, "storage_gb": 1000},
        "pc_build": {
            "cpu": "AMD Ryzen 7 9700X / Intel Core Ultra 7 265K",
            "gpu": "Integrated or RTX 4060 8GB",
            "ram": "32GB DDR5-6000MHz",
            "storage": "1TB PCIe 4.0 NVMe SSD",
            "usd_range": (950, 1250)
        },
        "laptop_option": {
            "models": "MacBook Air M3 (24GB/1TB) / Lenovo ThinkPad E16 Gen 3 / ASUS Zenbook 14 Core Ultra",
            "specs": "16-24GB Unified/DDR5 RAM, 1TB NVMe, 8+ Core CPU",
            "usd_range": (1100, 1450)
        }
    },
    "gaming_aaa": {
        "title": "High-Refresh 1440p / 4K AAA Gaming",
        "tier": "prosumer",
        "min_specs": {"cpu_cores": 8, "ram_gb": 32, "vram_gb": 16, "storage_gb": 2000},
        "pc_build": {
            "cpu": "AMD Ryzen 7 9800X3D",
            "gpu": "NVIDIA RTX 4070 Ti Super 16GB / RTX 5070 Ti 16GB",
            "ram": "32GB DDR5-6000MHz CL30",
            "storage": "2TB PCIe 4.0 NVMe SSD",
            "usd_range": (1650, 2100)
        },
        "laptop_option": {
            "models": "ASUS ROG Zephyrus G16 / Lenovo Legion Pro 7i",
            "specs": "Core Ultra 9 / Ryzen 9, Mobile RTX 4080 12GB, 32GB RAM, 2TB SSD",
            "usd_range": (2100, 2600)
        }
    },
    "ai_local_finetuning": {
        "title": "Local AI Image Generation, LoRA Fine-Tuning & LLM Quantized Inference",
        "tier": "workstation",
        "min_specs": {"cpu_cores": 12, "ram_gb": 64, "vram_gb": 16, "storage_gb": 2000},
        "pc_build": {
            "cpu": "AMD Ryzen 9 9900X (12-Core / 24-Thread)",
            "gpu": "NVIDIA RTX 4070 Ti Super 16GB / Used RTX 3090 24GB",
            "ram": "64GB DDR5-6000MHz",
            "storage": "2TB PCIe 4.0 NVMe SSD (High TBW for model checkpoints)",
            "usd_range": (1800, 2300)
        },
        "laptop_option": {
            "models": "MacBook Pro 16 M4 Max (64GB Unified Memory) / MSI Titan 18 HX (RTX 4090 16GB)",
            "specs": "Unified Memory architecture or 175W TGP Mobile GPU, 64GB RAM, 2TB SSD",
            "usd_range": (3200, 4000)
        }
    },
    "enterprise_ai_datacenter": {
        "title": "Foundation Model Training (70B+ Params) / High-Density Crypto Node Cluster",
        "tier": "datacenter",
        "min_specs": {"cpu_cores": 64, "ram_gb": 512, "vram_gb": 320, "storage_gb": 15000},
        "datacenter_rack": {
            "compute_nodes": "2x 4U GPU Servers (Dual AMD EPYC 9354 32-Core per node)",
            "gpu_cluster": "4x to 8x NVIDIA H100 (80GB) or RTX 6000 Ada (48GB) via NVLink",
            "memory": "512GB - 1TB DDR5 ECC Registered RAM",
            "storage_san": "15.36TB Enterprise U.3 NVMe RAID Array (Scratch) + 40TB NAS",
            "networking_power": "42U Rack, 100GbE Mellanox InfiniBand Switch, Dual 3-Phase PDU + 10kVA Online UPS, Dedicated Precision Cooling",
            "usd_range": (45000, 115000)
        }
    }
}

def analyze_bottlenecks(current_specs, target_min):
    """Compare current scanned specs against workload minimum thresholds."""
    bottlenecks = []

    curr_cores = current_specs["cpu"].get("physical_cores") or 4
    curr_ram = current_specs["ram"].get("total_gb", 0)
    curr_storage = current_specs["storage"].get("total_gb", 0)
    curr_vram = max([gpu.get("vram_total_gb", 0) for gpu in current_specs.get("gpus", [])], default=0)

    if curr_cores < target_min["cpu_cores"]:
        bottlenecks.append(
            f"CPU Cores: Have {curr_cores} physical cores, need at least {target_min['cpu_cores']}."
        )
    if curr_ram < target_min["ram_gb"]:
        bottlenecks.append(
            f"System RAM: Have {curr_ram} GB, need {target_min['ram_gb']} GB (short by {round(target_min['ram_gb'] - curr_ram, 1)} GB)."
        )
    if curr_vram < target_min["vram_gb"]:
        bottlenecks.append(
            f"GPU VRAM: Have {curr_vram} GB dedicated VRAM, need {target_min['vram_gb']} GB for CUDA/tensor workloads."
        )
    if curr_storage < target_min["storage_gb"]:
        bottlenecks.append(
            f"Storage Capacity: Primary drive is {curr_storage} GB, recommended is {target_min['storage_gb']} GB+ NVMe."
        )

    return bottlenecks

def generate_recommendation(goal_key, current_specs=None, location_data=None):
    """Generate full upgrade path and localized budgets based on user goal."""
    if goal_key not in WORKLOAD_PROFILES:
        raise ValueError(f"Unknown workload goal. Choose from: {list(WORKLOAD_PROFILES.keys())}")

    if not current_specs:
        current_specs = scan_system_specs()
    if not location_data:
        location_data = get_user_location()

    profile = WORKLOAD_PROFILES[goal_key]
    bottlenecks = analyze_bottlenecks(current_specs, profile["min_specs"])
    meets_requirements = len(bottlenecks) == 0

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