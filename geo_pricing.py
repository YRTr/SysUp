import requests

# Regional hardware tax, import duty, and distributor markup multipliers
REGIONAL_HARDWARE_MULTIPLIERS = {
    "US": 1.08,  # Avg state sales tax
    "IN": 1.18,  # 18% GST + import duties on high-end components
    "GB": 1.20,  # 20% VAT
    "DE": 1.19,  # 19% VAT (EU baseline)
    "CA": 1.13,  # HST
    "AU": 1.10,  # 10% GST
    "BR": 1.60,  # Heavy import tariffs on electronics
    "DEFAULT": 1.15
}

# Average residential/commercial electricity cost in USC per kWh
REGIONAL_ELECTRICITY_USD_KWH = {
    "US": 0.16,
    "IN": 0.09,  # ~₹7.5 - ₹8.5 per unit (kWh) commercial/high-slab average
    "GB": 0.34,
    "DE": 0.38,
    "CA": 0.13,
    "AU": 0.25,
    "BR": 0.17,
    "DEFAULT": 0.18
}


CURRENCY_SYMBOLS = {
    "USD": "$",
    "INR": "₹",
    "GBP": "£",
    "EUR": "€",
    "CAD": "CA$",
    "AUD": "A$",
    "BRL": "R$",
    "JPY": "¥"
}

def get_user_location():
    """Detect user location and currency via IP geolocation."""
    try:
        # ipapi.co provides free JSON geolocation including currency code
        response = requests.get("https://ipapi.co/json/", timeout=5)
        response.raise_for_status()
        data = response.json()

        return {
            "ip": data.get("ip", "Unknown"),
            "city": data.get("city", "Unknown"),
            "region": data.get("region", "Unknown"),
            "country_name": data.get("country_name", "United States"),
            "country_code": data.get("country_code", "US"),
            "currency": data.get("currency", "USD")
        }
    except Exception:
        # Fallback to US/USD if offline or rate-limited
        return {
            "ip": "127.0.0.1",
            "city": "Fallback",
            "region": "N/A",
            "country_name": "United States",
            "country_code": "US",
            "currency": "USD"
        }

def get_exchange_rate(target_currency="USD"):
    """Fetch live exchange rate from USD to the target currency."""
    if target_currency == "USD":
        return 1.0

    try:
        # Free open exchange rate API (no API key required)
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        rates = response.json().get("rates", {})
        return rates.get(target_currency, 1.0)
    except Exception:
        # Hardcoded fallback rates if offline
        fallback_rates = {
            "INR": 84.5,
            "EUR": 0.92,
            "GBP": 0.79,
            "CAD": 1.38,
            "AUD": 1.52
        }
        return fallback_rates.get(target_currency, 1.0)

def _format_indian_grouping(number_int):
    """Format an integer using the Indian Lakh/Crore comma system (e.g., 12,34,567)."""
    s = str(abs(int(number_int)))
    if len(s) <= 3:
        return s
    last_three = s[-3:]
    remaining = s[:-3]
    groups = []
    while remaining:
        groups.append(remaining[-2:])
        remaining = remaining[:-2]
    return ",".join(reversed(groups)) + "," + last_three

def format_local_currency(amount, currency_code, round_hundreds=True):
    """Format numbers cleanly (using Indian numbering system for INR, standard elsewhere)."""
    symbol = CURRENCY_SYMBOLS.get(currency_code, f"{currency_code} ")
    rounded_amt = round(amount, -2) if (round_hundreds and amount > 1000) else round(amount, 2)

    if currency_code == "INR":
        return f"{symbol}{_format_indian_grouping(rounded_amt)}"
    return f"{symbol}{int(rounded_amt):,}"

def calculate_localized_budget(base_usd_min, base_usd_max, location_data=None):
    """
    Convert a base USD hardware budget range into localized street prices.
    Includes exchange rate + regional hardware import/tax multiplier.
    """
    if not location_data:
        location_data = get_user_location()

    country_code = location_data["country_code"]
    currency_code = location_data["currency"]

    exchange_rate = get_exchange_rate(currency_code)
    hw_multiplier = REGIONAL_HARDWARE_MULTIPLIERS.get(
        country_code, REGIONAL_HARDWARE_MULTIPLIERS["DEFAULT"]
    )

    # Calculate street price: Base USD * Exchange Rate * Regional Markup
    local_min = base_usd_min * exchange_rate * hw_multiplier
    local_max = base_usd_max * exchange_rate * hw_multiplier

    return {
        "location": f"{location_data['city']}, {location_data['country_name']}",
        "currency": currency_code,
        "exchange_rate_used": round(exchange_rate, 2),
        "regional_tax_multiplier": hw_multiplier,
        "base_usd_range": f"${base_usd_min:,} - ${base_usd_max:,}",
        "estimated_local_min": round(local_min),
        "estimated_local_max": round(local_max),
        "formatted_budget": f"{format_local_currency(local_min, currency_code)} - {format_local_currency(local_max, currency_code)}"
    }


def calculate_power_and_opex(avg_watts, daily_hours=8, is_datacenter=False, location_data=None):
    """
    Calculate monthly electricity OpEx, PUE cooling overhead, and thermal BTU output.
    1 Watt = 3.41214 BTU/hr; 1 Ton of AC cooling = 12,000 BTU/hr.
    """
    if not location_data:
        location_data = get_user_location()

    country_code = location_data["country_code"]
    currency_code = location_data["currency"]
    exchange_rate = get_exchange_rate(currency_code)

    # Power Usage Effectiveness (PUE): Data centers require ~35% extra power for cooling/PDUs
    pue_multiplier = 1.35 if is_datacenter else 1.0
    effective_watts = avg_watts * pue_multiplier

    # Monthly energy usage in kWh (30-day month)
    monthly_kwh = round((effective_watts / 1000.0) * daily_hours * 30, 1)

    # Local electricity cost calculation
    usd_per_kwh = REGIONAL_ELECTRICITY_USD_KWH.get(
        country_code, REGIONAL_ELECTRICITY_USD_KWH["DEFAULT"]
    )
    local_rate_per_kwh = round(usd_per_kwh * exchange_rate, 2)
    monthly_cost_local = monthly_kwh * local_rate_per_kwh

    # Thermal output & cooling requirements
    btu_per_hour = round(avg_watts * 3.41214)
    ac_tons_required = round(btu_per_hour / 12000, 2)

    return {
        "hardware_load_watts": avg_watts,
        "pue_multiplier": pue_multiplier,
        "effective_wall_watts": round(effective_watts),
        "daily_hours_assumed": daily_hours,
        "monthly_kwh": monthly_kwh,
        "local_tariff_per_kwh": f"{CURRENCY_SYMBOLS.get(currency_code, '')}{local_rate_per_kwh}/kWh",
        "estimated_monthly_opex": format_local_currency(monthly_cost_local, currency_code, round_hundreds=False),
        "thermal_output_btu_hr": f"{btu_per_hour:,} BTU/hr",
        "recommended_cooling_tons": f"{ac_tons_required} Ton(s) of AC cooling"
    }

if __name__ == "__main__":
    import json

    user_loc = get_user_location()

    print("--- 1. Workstation CapEx & OpEx (850W Load @ 12 hrs/day) ---")
    ws_capex = calculate_localized_budget(1800, 2300, user_loc)
    ws_opex = calculate_power_and_opex(avg_watts=850, daily_hours=12, is_datacenter=False, location_data=user_loc)
    print(json.dumps({"capex": ws_capex, "opex": ws_opex}, indent=4))

    print("\n--- 2. Small Data Center Rack OpEx (9,500W Load @ 24 hrs/day) ---")
    dc_opex = calculate_power_and_opex(avg_watts=9500, daily_hours=24, is_datacenter=True, location_data=user_loc)
    print(json.dumps(dc_opex, indent=4))