"""
MLB API module for fetching game data.
Uses the free MLB Stats API.
"""

import requests
import json
from datetime import datetime, timezone, timedelta
from stadium_coords import get_stadium_coordinates

class MLBGameFetcher:
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
    
    def get_todays_games(self):
        """
        Fetch today's MLB games.
        Returns list of game dictionaries with relevant information.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{self.base_url}/schedule?sportId=1&date={today}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            if 'dates' in data and len(data['dates']) > 0:
                for game_data in data['dates'][0].get('games', []):
                    game_info = self._parse_game_data(game_data)
                    if game_info:
                        games.append(game_info)
            
            return games
            
        except requests.RequestException as e:
            print(f"Error fetching MLB data: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"Error parsing MLB data: {e}")
            return []
    
    def _parse_game_data(self, game_data):
        """
        Parse individual game data from MLB API response.
        """
        try:
            # Extract basic game info
            away_team = game_data['teams']['away']['team']['name']
            home_team = game_data['teams']['home']['team']['name']
            
            # Get game status first
            status = game_data.get('status', {}).get('detailedState', 'Scheduled')
            
            # Get game time and convert to Eastern Time
            game_datetime = game_data.get('gameDate', '')
            if game_datetime:
                # Convert from UTC to Eastern Time (UTC-5 in winter, UTC-4 in summer)
                dt_utc = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
                # Simple Eastern Time conversion (assumes EDT in summer)
                dt_eastern = dt_utc - timedelta(hours=4)  # EDT offset
                
                # Format time display based on game status
                if status in ["In Progress", "Live"]:
                    # For games in progress, show "LIVE"
                    game_time = "LIVE"
                elif status in ["Final", "Game Over"]:
                    # For finished games, show "FINAL"
                    game_time = "FINAL"
                elif status in ["Delayed"]:
                    # For delayed games, show original time with status
                    original_time = dt_eastern.strftime("%I:%M %p").lstrip('0')
                    game_time = f"{original_time} (Delayed)"
                elif status in ["Postponed"]:
                    game_time = "POSTPONED"
                else:
                    # For scheduled games, show the Eastern start time
                    game_time = dt_eastern.strftime("%I:%M %p").lstrip('0')
            else:
                game_time = "TBD"
            
            # Get score and inning information for live games
            score_info = ""
            if status in ["In Progress", "Live"]:
                try:
                    away_score = game_data['teams']['away'].get('score', 0)
                    home_score = game_data['teams']['home'].get('score', 0)
                    
                    # Get inning information
                    linescore = game_data.get('linescore', {})
                    current_inning = linescore.get('currentInning', 1)
                    inning_state = linescore.get('inningState', 'Top')  # Top, Middle, Bottom
                    
                    if inning_state == "Middle":
                        inning_display = f"Mid {current_inning}"
                    else:
                        inning_display = f"{inning_state} {current_inning}"
                    
                    score_info = f" - {away_score}-{home_score}, {inning_display}"
                except (KeyError, TypeError):
                    # If score data is not available
                    pass
            
            # Get venue information
            venue = game_data.get('venue', {})
            stadium_name = venue.get('name', 'Unknown Stadium')
            
            # Get coordinates for weather lookup
            coordinates = get_stadium_coordinates(stadium_name)
            
            return {
                'away_team': away_team,
                'home_team': home_team,
                'game_time': game_time,
                'stadium_name': stadium_name,
                'coordinates': coordinates,
                'status': status,
                'game_datetime': game_datetime,
                'score_info': score_info
            }
            
        except KeyError as e:
            print(f"Error parsing game data: missing key {e}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing game data: {e}")
            return None

def test_mlb_api():
    """
    Test function to verify MLB API is working.
    """
    fetcher = MLBGameFetcher()
    games = fetcher.get_todays_games()
    
    print(f"Found {len(games)} games today:")
    for game in games:
        print(f"  {game['game_time']}: {game['away_team']} @ {game['home_team']}")
        print(f"    Stadium: {game['stadium_name']}")
        print(f"    Coordinates: {game['coordinates']}")
        print(f"    Status: {game['status']}")
        print()

if __name__ == "__main__":
    test_mlb_api()
