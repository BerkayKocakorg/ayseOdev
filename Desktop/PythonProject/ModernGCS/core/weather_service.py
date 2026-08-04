import threading
import time

# Graceful fallback for requests
try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False
    print("[WARN] requests not installed. Weather service disabled. Install with: pip install requests")


class WeatherService:
    """
    Weather service using Open-Meteo API (free, no API key required).
    
    Features:
    - Current wind speed and direction
    - Temperature
    - Weather condition code
    - Flight safety assessment
    - Auto-refresh every 5 minutes
    """
    
    # Wind safety thresholds (m/s)
    WIND_SAFE = 8.0       # Below 8 m/s is safe
    WIND_CAUTION = 12.0   # 8-12 m/s is caution
    # Above 12 m/s is dangerous
    
    def __init__(self):
        self.data = {
            "temperature": 0.0,       # °C
            "wind_speed": 0.0,        # m/s
            "wind_direction": 0,      # degrees
            "wind_gusts": 0.0,        # m/s
            "weather_code": 0,        # WMO weather code
            "weather_text": "Unknown",
            "humidity": 0,            # %
            "pressure": 0.0,         # hPa
            "flight_safety": "UNKNOWN",  # SAFE / CAUTION / DANGEROUS
            "last_update": None,
            "available": False,
        }
        
        self.lat = 39.92077  # Default: Ankara
        self.lon = 32.85411
        
        self.running = False
        self.thread = None
        self.refresh_interval = 300  # 5 minutes
        
        # Callback for UI updates
        self.on_weather_updated = None
    
    # WMO Weather Codes → Human readable
    _WMO_CODES = {
        0: "Açık", 1: "Çoğunlukla açık", 2: "Parçalı bulutlu", 3: "Kapalı",
        45: "Sisli", 48: "Kırağı sisi",
        51: "Hafif çisenti", 53: "Orta çisenti", 55: "Yoğun çisenti",
        61: "Hafif yağmur", 63: "Orta yağmur", 65: "Şiddetli yağmur",
        66: "Dondurucu hafif yağmur", 67: "Dondurucu şiddetli yağmur",
        71: "Hafif kar", 73: "Orta kar", 75: "Şiddetli kar",
        77: "Kar taneleri",
        80: "Hafif sağanak", 81: "Orta sağanak", 82: "Şiddetli sağanak",
        85: "Hafif kar sağanağı", 86: "Şiddetli kar sağanağı",
        95: "Gök gürültülü fırtına", 96: "Dolu ile fırtına", 99: "Şiddetli dolu fırtınası",
    }
    
    def set_location(self, lat, lon):
        """Update the location for weather queries."""
        if lat != 0.0 and lon != 0.0:
            self.lat = lat
            self.lon = lon
    
    def start(self):
        """Start periodic weather updates."""
        if not _REQUESTS_AVAILABLE:
            return
        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop weather updates."""
        self.running = False
    
    def fetch_now(self):
        """Fetch weather data immediately."""
        if not _REQUESTS_AVAILABLE:
            return False
        return self._fetch_weather()
    
    def _update_loop(self):
        """Background loop: fetch weather every refresh_interval seconds."""
        while self.running:
            self._fetch_weather()
            # Sleep in small increments so we can stop quickly
            for _ in range(int(self.refresh_interval)):
                if not self.running:
                    break
                time.sleep(1)
    
    def _fetch_weather(self):
        """Fetch current weather from Open-Meteo API."""
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast"
                f"?latitude={self.lat}&longitude={self.lon}"
                f"&current=temperature_2m,relative_humidity_2m,weather_code,"
                f"wind_speed_10m,wind_direction_10m,wind_gusts_10m,surface_pressure"
            )
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            current = result.get("current", {})
            
            wind_speed_kmh = current.get("wind_speed_10m", 0)
            wind_speed_ms = wind_speed_kmh / 3.6  # Convert km/h to m/s
            
            wind_gusts_kmh = current.get("wind_gusts_10m", 0)
            wind_gusts_ms = wind_gusts_kmh / 3.6
            
            weather_code = current.get("weather_code", 0)
            
            self.data["temperature"] = current.get("temperature_2m", 0)
            self.data["wind_speed"] = round(wind_speed_ms, 1)
            self.data["wind_direction"] = current.get("wind_direction_10m", 0)
            self.data["wind_gusts"] = round(wind_gusts_ms, 1)
            self.data["weather_code"] = weather_code
            self.data["weather_text"] = self._WMO_CODES.get(weather_code, f"Kod {weather_code}")
            self.data["humidity"] = current.get("relative_humidity_2m", 0)
            self.data["pressure"] = current.get("surface_pressure", 0)
            self.data["last_update"] = time.strftime("%H:%M")
            self.data["available"] = True
            
            # Flight safety assessment
            self.data["flight_safety"] = self._assess_safety(wind_speed_ms, wind_gusts_ms, weather_code)
            
            # Notify UI
            if self.on_weather_updated:
                try:
                    self.on_weather_updated(self.data)
                except Exception:
                    pass
            
            return True
            
        except Exception as e:
            print(f"[WARN] Weather fetch error: {e}")
            self.data["available"] = False
            return False
    
    def _assess_safety(self, wind_speed, wind_gusts, weather_code):
        """Assess flight safety based on weather conditions."""
        # Dangerous weather codes (thunderstorms, heavy precipitation)
        dangerous_codes = {65, 66, 67, 75, 82, 85, 86, 95, 96, 99}
        caution_codes = {51, 53, 55, 61, 63, 71, 73, 80, 81}
        
        if weather_code in dangerous_codes or wind_speed > self.WIND_CAUTION or wind_gusts > 15.0:
            return "DANGEROUS"
        elif weather_code in caution_codes or wind_speed > self.WIND_SAFE or wind_gusts > 10.0:
            return "CAUTION"
        else:
            return "SAFE"
    
    def get_wind_arrow(self):
        """Get wind direction as an arrow character."""
        direction = self.data.get("wind_direction", 0)
        arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
        index = round(direction / 45) % 8
        return arrows[index]
