import requests

# Regional hardware tax, import duty, and distributor markup multipliers
# Baseline = 1.0 (US MSRP before local state tax)
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

def format_local_Currency(amount, currency_code):
    """Format numbers cleanly (using Indian numbering system for INR, standard elsewhere)."""
    symbol = CURRENCY_SYMBOLS.get(currency_code, f"{currency_code} ")
    rounded_amt = round(amount, -2) if amount > 1000 else round(amount, 2)
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
        "formatted_budget": f"{format_local_Currency(local_min, currency_code)} - {format_local_Currency(local_max, currency_code)}"
    }

if __name__ == "__main__":
    import json

    # Test 1: Detect location and price a $1,800 - $2,200 high-end workstation
    user_loc = get_user_location()
    budget_estimate = calculate_localized_budget(1800, 2200, user_loc)
    print(json.dumps(budget_estimate, indent=4))