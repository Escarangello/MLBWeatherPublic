"""
Weather API module for fetching weather data.
Uses OpenWeatherMap's One Call API 3.0.
"""

import requests
import json
from datetime import datetime, timezone, timedelta

class WeatherFetcher:
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/3.0"
    
    def get_weather_for_game(self, coordinates, game_datetime, stadium_name=None, game_status="Scheduled"):
        """
        Get weather forecast for a specific location and time.
        
        Args:
            coordinates: (lat, lon) tuple
            game_datetime: ISO datetime string of the game
            stadium_name: Name of the stadium for wind direction calculation
            game_status: Current game status to determine timing
            
        Returns:
            Dictionary with weather information or None if error
        """
        if not coordinates or not self.api_key:
            return None
            
        lat, lon = coordinates
        
        try:
            # Use One Call API 3.0 for comprehensive weather data
            url = f"{self.base_url}/onecall"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'imperial',  # Fahrenheit
                'exclude': 'minutely,alerts'  # Exclude unnecessary data
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            # Handle specific HTTP errors
            if response.status_code == 401:
                print(f"Weather API Error 401: Invalid API key or subscription issue.")
                return None
            elif response.status_code == 429:
                print(f"Weather API Error 429: Rate limit exceeded.")
                return None
            
            response.raise_for_status()
            data = response.json()
            
            return self._parse_onecall_data(data, game_datetime, stadium_name, game_status)
            
        except requests.RequestException as e:
            print(f"Error fetching weather data: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing weather data: {e}")
            return None
    
    def _parse_onecall_data(self, data, game_datetime, stadium_name=None, game_status="Scheduled"):
        """
        Parse weather data from One Call API 3.0 response.
        Try to find the best weather data for game time.
        """
        try:
            # Determine if we should use current weather or forecast
            weather_data = self._get_appropriate_weather_data(data, game_datetime, game_status)
            
            if not weather_data:
                return None
            
            weather = weather_data.get('weather', [{}])[0]
            
            # Get wind data
            wind_speed = weather_data.get('wind_speed', 0)
            wind_deg = weather_data.get('wind_deg', 0)
            
            # Calculate wind direction relative to ballpark
            wind_direction_text = self._get_wind_direction_for_stadium(wind_deg, stadium_name)
            
            # Get precipitation data
            rain = weather_data.get('rain', {}).get('1h', 0) if 'rain' in weather_data else 0
            snow = weather_data.get('snow', {}).get('1h', 0) if 'snow' in weather_data else 0
            
            # Get precipitation probability
            precip_chance = weather_data.get('pop', 0) * 100 if 'pop' in weather_data else 0
            if precip_chance == 0 and (rain > 0 or snow > 0):
                # Fallback calculation
                precip_chance = min(100, max(20, (rain + snow) * 10))
            
            return {
                'temperature': round(weather_data.get('temp', 0)),
                'feels_like': round(weather_data.get('feels_like', 0)),
                'humidity': weather_data.get('humidity', 0),
                'description': weather.get('description', 'Unknown').title(),
                'main_condition': weather.get('main', 'Unknown'),
                'wind_speed': round(wind_speed),
                'wind_direction': wind_deg,
                'wind_direction_text': wind_direction_text,
                'precipitation_chance': round(precip_chance),
                'rain_mm': rain,
                'snow_mm': snow,
                'pressure': weather_data.get('pressure'),  # Atmospheric pressure (hPa)
                'visibility': weather_data.get('visibility'),  # Visibility in meters
                'uv_index': weather_data.get('uvi'),  # UV index
                'dew_point': round(weather_data.get('dew_point', 0)) if weather_data.get('dew_point') else None,
                'weather_time': self._get_weather_time_description(game_datetime, game_status)
            }
            
        except Exception as e:
            print(f"Error parsing One Call weather data: {e}")
            return None
    
    def _get_appropriate_weather_data(self, data, game_datetime, game_status):
        """
        Get the appropriate weather data based on game status and timing.
        """
        try:
            # Parse game datetime
            if game_datetime:
                game_dt = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
            else:
                game_dt = None
            
            current_dt = datetime.now(timezone.utc)
            
            # Determine which weather data to use based on game status
            if game_status in ["In Progress", "Live", "Final", "Game Over"]:
                # Game is in progress or finished - use current weather
                return data.get('current', {})
            elif game_dt and game_dt > current_dt:
                # Game hasn't started - try to find forecast for game time
                hours_until_game = (game_dt - current_dt).total_seconds() / 3600
                
                if hours_until_game <= 48 and 'hourly' in data:
                    # Find the closest hourly forecast to game time
                    hourly_data = data['hourly']
                    best_forecast = None
                    min_time_diff = float('inf')
                    
                    for hour_data in hourly_data:
                        forecast_dt = datetime.fromtimestamp(hour_data['dt'], tz=timezone.utc)
                        time_diff = abs((forecast_dt - game_dt).total_seconds())
                        
                        if time_diff < min_time_diff:
                            min_time_diff = time_diff
                            best_forecast = hour_data
                    
                    if best_forecast:
                        return best_forecast
                
                # Fallback to current weather if no suitable forecast found
                return data.get('current', {})
            else:
                # Default to current weather
                return data.get('current', {})
                
        except Exception as e:
            print(f"Error determining appropriate weather data: {e}")
            return data.get('current', {})
    
    def _get_wind_direction_for_stadium(self, wind_deg, stadium_name):
        """
        Calculate wind direction relative to the ballpark layout.
        """
        if not stadium_name or wind_deg is None:
            return self._degrees_to_cardinal(wind_deg) if wind_deg is not None else "Unknown"
        
        # Import here to avoid circular imports
        from stadium_coords import get_stadium_orientation
        
        # Get stadium orientation (default to 90 degrees if not found)
        stadium_bearing = get_stadium_orientation(stadium_name)
        if stadium_bearing is None:
            stadium_bearing = 90  # Default east orientation
        
        # Calculate relative wind direction
        # Wind direction is "from" direction, so we need to adjust
        relative_angle = (wind_deg - stadium_bearing + 360) % 360
        
        # Determine wind direction relative to field
        if 337.5 <= relative_angle or relative_angle < 22.5:
            return "out to center field"
        elif 22.5 <= relative_angle < 67.5:
            return "out to right field"
        elif 67.5 <= relative_angle < 112.5:
            return "out to right field foul territory"
        elif 112.5 <= relative_angle < 157.5:
            return "in from right field"
        elif 157.5 <= relative_angle < 202.5:
            return "in from center field"
        elif 202.5 <= relative_angle < 247.5:
            return "in from left field"
        elif 247.5 <= relative_angle < 292.5:
            return "out to left field foul territory"
        elif 292.5 <= relative_angle < 337.5:
            return "out to left field"
        else:
            return self._degrees_to_cardinal(wind_deg)
    
    def _degrees_to_cardinal(self, degrees):
        """Convert wind degrees to cardinal direction."""
        if degrees is None:
            return "Unknown"
        
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return f"from {directions[index]}"
    
    def _calculate_home_run_factor(self, weather_data, stadium_name=None):
        """
        Calculate home run carry distance difference from standard conditions.
        Uses density altitude and wind vector analysis for accuracy.
        
        Standard conditions: 70°F, sea level, 50% humidity, no wind
        
        Returns:
            Dictionary with carry distance difference and description
        """
        if not weather_data:
            return None
        
        # Get stadium elevation for station pressure calculation
        stadium_elevations = {
            'Coors Field': 5200,  # feet
            'Chase Field': 1100,
            'Kauffman Stadium': 750,
            'Globe Life Field': 550,
            'Minute Maid Park': 50,
            'Tropicana Field': 10,
            # Most other stadiums are near sea level (0-200 ft)
        }
        
        elevation = stadium_elevations.get(stadium_name, 0)
        
        # Standard baseline conditions (sea level)
        STANDARD_TEMP = 70  # °F
        STANDARD_PRESSURE_SL = 29.92  # inHg at sea level
        STANDARD_HUMIDITY = 50  # %
        
        # Get current conditions
        temp_f = weather_data.get('temperature', STANDARD_TEMP)
        pressure_hpa = weather_data.get('pressure')
        humidity = weather_data.get('humidity', STANDARD_HUMIDITY)
        wind_speed = weather_data.get('wind_speed', 0)
        wind_direction_text = weather_data.get('wind_direction_text', '')
        
        # Calculate actual station pressure from elevation and conditions
        # Weather APIs typically provide altimeter pressure (sea-level corrected), not station pressure
        if elevation > 500:  # For significant elevation, calculate true station pressure
            # Standard atmosphere model for station pressure at elevation
            station_pressure_inhg = STANDARD_PRESSURE_SL * (1 - 0.0000068756 * elevation) ** 5.2559
            
            # Adjust for temperature deviation from standard (59°F at sea level)
            standard_temp_at_elevation = 59 - (elevation * 0.00356)  # Standard lapse rate
            temp_correction = (temp_f + 459.67) / (standard_temp_at_elevation + 459.67)
            station_pressure_inhg = station_pressure_inhg * temp_correction
        else:
            # For low elevation stadiums, use the provided pressure (likely close to station pressure)
            if pressure_hpa:
                station_pressure_inhg = pressure_hpa * 0.02953
            else:
                station_pressure_inhg = STANDARD_PRESSURE_SL
        
        # Use stadium-specific approach for high altitude vs sea level
        if stadium_name == 'Coors Field':
            # Fixed altitude baseline for Coors Field on neutral days: +22 ft
            altitude_baseline = 22.0
            
            # Add temperature effect: +2.5 ft per 10°F above 70°F
            temp_effect = ((temp_f - STANDARD_TEMP) / 10.0) * 2.5
            
            # Add humidity effect: +1.2 ft per 10% above 50% (humid air less dense)
            humidity_effect = ((humidity - STANDARD_HUMIDITY) / 10.0) * 1.2
            
            # Wind effect
            wind_effect = self._calculate_wind_vector_effect(wind_speed, wind_direction_text, stadium_name)
            
            # Humidor effect
            humidor_effect = self._calculate_humidor_effect(temp_f, humidity)
            
            total_carry_difference = altitude_baseline + temp_effect + humidity_effect + wind_effect + humidor_effect
            
        elif stadium_name == 'Chase Field':
            # Moderate altitude baseline for Chase Field: +4 ft
            altitude_baseline = 4.0
            temp_effect = ((temp_f - STANDARD_TEMP) / 10.0) * 2.5
            humidity_effect = ((humidity - STANDARD_HUMIDITY) / 10.0) * 1.2
            wind_effect = self._calculate_wind_vector_effect(wind_speed, wind_direction_text, stadium_name)
            humidor_effect = self._calculate_humidor_effect(temp_f, humidity)
            total_carry_difference = altitude_baseline + temp_effect + humidity_effect + wind_effect + humidor_effect
            
        else:
            # Sea level stadiums - use weather effects only
            temp_effect = ((temp_f - STANDARD_TEMP) / 10.0) * 2.5
            humidity_effect = ((humidity - STANDARD_HUMIDITY) / 10.0) * 1.2
            
            # For sea level, use simple pressure effect
            if pressure_hpa:
                pressure_inhg = pressure_hpa * 0.02953
                pressure_effect = (STANDARD_PRESSURE_SL - pressure_inhg) * 5.0  # Conservative pressure effect
            else:
                pressure_effect = 0
            
            wind_effect = self._calculate_wind_vector_effect(wind_speed, wind_direction_text, stadium_name)
            humidor_effect = self._calculate_humidor_effect(temp_f, humidity)
            
            total_carry_difference = temp_effect + humidity_effect + pressure_effect + wind_effect + humidor_effect
        
        # Create description
        if total_carry_difference >= 20:
            description = "Excellent home run conditions"
        elif total_carry_difference >= 10:
            description = "Good home run conditions"
        elif total_carry_difference >= 4:
            description = "Slightly favorable for home runs"
        elif total_carry_difference >= -4:
            description = "Average home run conditions"
        elif total_carry_difference >= -10:
            description = "Slightly unfavorable for home runs"
        elif total_carry_difference >= -20:
            description = "Poor home run conditions"
        else:
            description = "Very poor home run conditions"
        
        return {
            'carry_difference': round(total_carry_difference, 1),
            'description': description,
            'temp_effect': round(temp_effect, 1) if 'temp_effect' in locals() else 0,
            'humidity_effect': round(humidity_effect, 1) if 'humidity_effect' in locals() else 0,
            'wind_effect': round(wind_effect, 1),
            'humidor_effect': round(humidor_effect, 1),
            'altitude_baseline': round(altitude_baseline, 1) if 'altitude_baseline' in locals() else 0,
            'station_pressure': round(station_pressure_inhg, 2)
        }
    
    def _calculate_wind_vector_effect(self, wind_speed, wind_direction_text, stadium_name):
        """
        Calculate wind effect using vector analysis for typical home run trajectories.
        """
        if wind_speed < 4:  # Treat light winds as negligible
            return 0
        
        # Typical home run spray patterns (degrees from center field)
        # Most HRs are pulled: LH batters to LF (-30°), RH batters to RF (+30°)
        # Use average of typical spray angles
        
        wind_effect = 0
        
        if 'out to center' in wind_direction_text.lower():
            # Direct tailwind - full effect
            wind_effect = wind_speed * 2.0
        elif 'in from center' in wind_direction_text.lower():
            # Direct headwind - full negative effect
            wind_effect = wind_speed * -1.8
        elif 'out to left' in wind_direction_text.lower() or 'out to right' in wind_direction_text.lower():
            # Quartering tailwind - partial effect (75%)
            wind_effect = wind_speed * 1.5
        elif 'in from left' in wind_direction_text.lower() or 'in from right' in wind_direction_text.lower():
            # Quartering headwind - partial negative effect (75%)
            wind_effect = wind_speed * -1.3
        elif 'foul territory' in wind_direction_text.lower():
            # Cross wind - minimal effect (25%)
            wind_effect = wind_speed * 0.25
        
        # Reduce effect for very light winds
        if wind_speed < 8:
            wind_effect *= 0.7  # 70% effect for light winds
        
        return wind_effect
    
    def _calculate_humidor_effect(self, temp_f, humidity):
        """
        Calculate humidor effect on ball properties.
        Temperature and humidity affect ball elasticity and seam height.
        """
        # Standard humidor conditions: 70°F, 50% RH
        temp_diff = temp_f - 70
        humidity_diff = humidity - 50
        
        # Temperature effect on ball elasticity (~0.3 ft per 10°F)
        temp_ball_effect = (temp_diff / 10.0) * 0.3
        
        # Humidity effect on ball properties (~0.2 ft per 10% RH)
        # Higher humidity = softer ball = less carry
        humidity_ball_effect = -(humidity_diff / 10.0) * 0.2
        
        return temp_ball_effect + humidity_ball_effect
    
    def _get_weather_time_description(self, game_datetime, game_status):
        """
        Get a description of when the weather data applies.
        """
        if game_status in ["In Progress", "Live"]:
            return "current conditions"
        elif game_status in ["Final", "Game Over"]:
            return "conditions during game"
        else:
            try:
                if game_datetime:
                    game_dt = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
                    return f"forecast for game time ({game_dt.strftime('%I:%M %p')})"
                else:
                    return "forecast for game time"
            except:
                return "forecast for game time"
    
    def format_weather_string(self, weather_data):
        """
        Format weather data into a readable string with baseball-relevant parameters.
        """
        if not weather_data:
            return "Weather data unavailable"
        
        temp = weather_data['temperature']
        feels_like = weather_data.get('feels_like', temp)
        condition = weather_data['description']
        precip = weather_data['precipitation_chance']
        wind = weather_data['wind_speed']
        wind_dir = weather_data.get('wind_direction_text', 'unknown direction')
        humidity = weather_data.get('humidity', 0)
        dew_point = weather_data.get('dew_point')
        
        # Build weather string with baseball-relevant info
        weather_parts = []
        
        # Temperature (with feels like if significantly different)
        if abs(temp - feels_like) > 3:
            weather_parts.append(f"{temp}°F (feels {feels_like}°F)")
        else:
            weather_parts.append(f"{temp}°F")
        
        # Condition
        weather_parts.append(condition)
        
        # Precipitation
        if precip > 0:
            weather_parts.append(f"{precip}% rain")
        
        # Humidity and dew point (important for ball flight and comfort)
        if dew_point:
            # Add dew point context for baseball conditions
            if dew_point >= 70:
                humidity_desc = f"{humidity}% humidity (oppressive, dew point {dew_point}°F)"
            elif dew_point >= 65:
                humidity_desc = f"{humidity}% humidity (uncomfortable, dew point {dew_point}°F)"
            elif dew_point >= 60:
                humidity_desc = f"{humidity}% humidity (sticky, dew point {dew_point}°F)"
            elif dew_point >= 55:
                humidity_desc = f"{humidity}% humidity (comfortable, dew point {dew_point}°F)"
            else:
                humidity_desc = f"{humidity}% humidity (dry, dew point {dew_point}°F)"
            weather_parts.append(humidity_desc)
        else:
            weather_parts.append(f"{humidity}% humidity")
        
        # Wind (critical for baseball) with impact assessment
        if wind >= 15:
            wind_impact = " (strong, affects fly balls significantly)"
        elif wind >= 10:
            wind_impact = " (moderate, noticeable effect on ball flight)"
        elif wind >= 5:
            wind_impact = " (light breeze)"
        else:
            wind_impact = " (calm)"
        weather_parts.append(f"{wind} mph winds {wind_dir}{wind_impact}")
        
        # Add pressure info if available (affects ball flight)
        pressure = weather_data.get('pressure')
        if pressure:
            # Convert hPa to inHg for US audience
            pressure_inhg = pressure * 0.02953
            # Add context for baseball (higher pressure = less ball carry)
            if pressure_inhg > 30.20:
                pressure_desc = f"{pressure_inhg:.2f} inHg (high pressure, less ball carry)"
            elif pressure_inhg < 29.80:
                pressure_desc = f"{pressure_inhg:.2f} inHg (low pressure, more ball carry)"
            else:
                pressure_desc = f"{pressure_inhg:.2f} inHg"
            weather_parts.append(pressure_desc)
        
        # Visibility removed - doesn't affect ball carry
        
        # Add UV index if significant (day games)
        uv_index = weather_data.get('uv_index')
        if uv_index and uv_index >= 6:
            if uv_index >= 11:
                uv_desc = f"UV index {uv_index} (extreme)"
            elif uv_index >= 8:
                uv_desc = f"UV index {uv_index} (very high)"
            elif uv_index >= 6:
                uv_desc = f"UV index {uv_index} (high)"
            weather_parts.append(uv_desc)
        
        return ", ".join(weather_parts)
    
    def format_weather_string_with_stadium(self, weather_data, stadium_name=None):
        """
        Format weather data with stadium-specific home run factor.
        """
        if not weather_data:
            return "Weather data unavailable"
        
        # Get base weather string
        base_weather = self.format_weather_string(weather_data)
        
        # Add home run factor with stadium context
        hr_factor = self._calculate_home_run_factor(weather_data, stadium_name)
        if hr_factor:
            carry_diff = hr_factor['carry_difference']
            if carry_diff > 0:
                hr_desc = f"Home runs carry +{carry_diff} ft ({hr_factor['description'].lower()})"
            elif carry_diff < 0:
                hr_desc = f"Home runs carry {carry_diff} ft ({hr_factor['description'].lower()})"
            else:
                hr_desc = f"Average home run conditions"
            
            # Also show calculated station pressure for high altitude stadiums
            if stadium_name in ['Coors Field', 'Chase Field'] and hr_factor.get('station_pressure'):
                station_p = hr_factor['station_pressure']
                hr_desc += f" (station pressure: {station_p} inHg)"
            
            return f"{base_weather}, {hr_desc}"
        
        return base_weather

# Mock weather data for testing when API key is not available
def get_mock_weather(stadium_name=None, game_status="Scheduled"):
    """
    Return mock weather data for testing purposes with comprehensive baseball-relevant parameters.
    """
    # Create a WeatherFetcher instance to use its methods
    fetcher = WeatherFetcher()
    wind_deg = 180
    wind_direction_text = fetcher._get_wind_direction_for_stadium(wind_deg, stadium_name)
    weather_time = fetcher._get_weather_time_description(None, game_status)
    
    # Use realistic conditions for different stadiums
    if stadium_name == 'Coors Field':
        # Realistic Coors conditions
        temp = 87
        humidity = 18
        pressure = 845  # hPa (realistic for 5200 ft)
        dew_point = 39
        wind_speed = 7
    else:
        # Standard conditions for other stadiums
        temp = 75
        humidity = 65
        pressure = 1013.25
        dew_point = 58
        wind_speed = 8
    
    return {
        'temperature': temp,
        'feels_like': temp + 3,
        'humidity': humidity,
        'description': 'Partly Cloudy',
        'main_condition': 'Clouds',
        'wind_speed': wind_speed,
        'wind_direction': wind_deg,
        'wind_direction_text': wind_direction_text,
        'precipitation_chance': 20,
        'rain_mm': 0,
        'snow_mm': 0,
        'pressure': pressure,
        'visibility': 10000,  # 6.2 miles in meters
        'uv_index': 6,
        'dew_point': dew_point,
        'weather_time': weather_time
    }

def test_weather_api():
    """
    Test function to verify weather API is working.
    """
    # Test with mock data since we don't have an API key yet
    weather_data = get_mock_weather()
    fetcher = WeatherFetcher()
    weather_string = fetcher.format_weather_string(weather_data)
    print(f"Sample weather: {weather_string}")

if __name__ == "__main__":
    test_weather_api()
