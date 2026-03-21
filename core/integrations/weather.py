# core/integrations/weather.py
# Free weather API — no key needed

import requests
from core.audit.audit_logger import AuditLogger
from core.audit.audit_event import AuditEvent


class WeatherCapability:
    def __init__(self):
        self.audit = AuditLogger()

    def execute(self, *, action: str, query: str = "", **kwargs) -> str:
        try:
            city = query.strip()
            if not city:
                return "[ERROR] City name required."

            # Geocode city name to lat/lon
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
            geo_res = requests.get(geo_url, timeout=10).json()

            if not geo_res.get("results"):
                return f"[ERROR] City '{city}' not found."

            loc = geo_res["results"][0]
            lat, lon = loc["latitude"], loc["longitude"]
            name = loc["name"]
            country = loc.get("country", "")

            if action == "current":
                return self._current(lat, lon, name, country)
            elif action == "forecast":
                return self._forecast(lat, lon, name, country)
            else:
                return f"[ERROR] Unknown action: {action}"

        except Exception as e:
            return f"[ERROR] Weather error: {e}"

    def _current(self, lat, lon, name, country) -> str:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,"
            f"wind_speed_10m,weather_code,apparent_temperature"
            f"&timezone=auto"
        )
        data = requests.get(url, timeout=10).json()
        curr = data["current"]

        condition = self._weather_code(curr.get("weather_code", 0))

        self.audit.log(AuditEvent(
            phase="plugin", action="weather_current",
            tool_name="weather_current", decision="allowed",
            metadata={"city": name}
        ))

        return (
            f"Weather in {name}, {country}:\n"
            f"Condition: {condition}\n"
            f"Temperature: {curr['temperature_2m']}°C "
            f"(feels like {curr['apparent_temperature']}°C)\n"
            f"Humidity: {curr['relative_humidity_2m']}%\n"
            f"Wind: {curr['wind_speed_10m']} km/h"
        )

    def _forecast(self, lat, lon, name, country) -> str:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
            f"&timezone=auto&forecast_days=3"
        )
        data = requests.get(url, timeout=10).json()
        daily = data["daily"]

        lines = [f"3-day forecast for {name}, {country}:"]
        for i in range(3):
            condition = self._weather_code(daily["weather_code"][i])
            lines.append(
                f"{daily['time'][i]}: {condition} "
                f"{daily['temperature_2m_min'][i]}°C — "
                f"{daily['temperature_2m_max'][i]}°C"
            )

        return "\n".join(lines)

    def _weather_code(self, code: int) -> str:
        codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy",
            3: "Overcast", 45: "Foggy", 48: "Icy fog",
            51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
            61: "Light rain", 63: "Rain", 65: "Heavy rain",
            71: "Light snow", 73: "Snow", 75: "Heavy snow",
            80: "Light showers", 81: "Showers", 82: "Heavy showers",
            95: "Thunderstorm", 99: "Thunderstorm with hail"
        }
        return codes.get(code, f"Code {code}")