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
            away_team_abbr = game_data['teams']['away']['team'].get('abbreviation', '')
            home_team_abbr = game_data['teams']['home']['team'].get('abbreviation', '')
            game_pk = game_data.get('gamePk')
            
            # Get game status first
            status = game_data.get('status', {}).get('detailedState', 'Scheduled')
            
            # Get game time and convert to Eastern Time
            game_datetime = game_data.get('gameDate', '')
            if game_datetime:
                # Convert from UTC to Eastern Time (EDT is UTC-4, EST is UTC-5)
                dt_utc = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
                # Convert to Eastern Time (currently EDT in August)
                dt_eastern = dt_utc.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-4)))
                
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
            
            # Get score and inning information for live and final games
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
            elif status in ["Final", "Game Over"]:
                try:
                    away_score = game_data['teams']['away'].get('score', 0)
                    home_score = game_data['teams']['home'].get('score', 0)
                    score_info = f" - Final: {away_score}-{home_score}"
                except (KeyError, TypeError):
                    pass
            
            # Get venue information
            venue = game_data.get('venue', {})
            stadium_name = venue.get('name', 'Unknown Stadium')
            
            # Get coordinates for weather lookup
            coordinates = get_stadium_coordinates(stadium_name)
            
            # Get home run information if available
            home_runs_info = []
            if game_pk and status in ["In Progress", "Live", "Final", "Game Over"]:
                home_runs_info = self._get_home_runs_for_game(game_pk)
            
            return {
                'away_team': away_team,
                'home_team': home_team,
                'away_team_abbr': away_team_abbr,
                'home_team_abbr': home_team_abbr,
                'game_time': game_time,
                'stadium_name': stadium_name,
                'coordinates': coordinates,
                'status': status,
                'game_datetime': game_datetime,
                'score_info': score_info,
                'home_runs': home_runs_info,
                'game_pk': game_pk
            }
            
        except KeyError as e:
            print(f"Error parsing game data: missing key {e}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing game data: {e}")
            return None
    
    def _get_home_runs_for_game(self, game_pk):
        """
        Fetch home run data for a specific game.
        """
        try:
            url = f"{self.base_url}/game/{game_pk}/playByPlay"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            home_runs = []
            plays = data.get('allPlays', [])
            
            for play in plays:
                result = play.get('result', {})
                if result.get('eventType') == 'home_run':
                    # Get batter info
                    batter = play.get('matchup', {}).get('batter', {})
                    batter_name = batter.get('fullName', 'Unknown')
                    
                    # Get team info
                    batting_team = play.get('about', {}).get('halfInning', '')
                    if batting_team == 'top':
                        team_type = 'away'
                    else:
                        team_type = 'home'
                    
                    # Get inning
                    inning = play.get('about', {}).get('inning', 0)
                    
                    # Get description for distance if available
                    description = result.get('description', '')
                    distance = None
                    if 'feet' in description:
                        # Try to extract distance from description
                        import re
                        distance_match = re.search(r'(\d+)\s*feet', description)
                        if distance_match:
                            distance = int(distance_match.group(1))
                    
                    home_runs.append({
                        'batter': batter_name,
                        'team_type': team_type,
                        'inning': inning,
                        'description': description,
                        'distance': distance
                    })
            
            return home_runs
            
        except Exception as e:
            print(f"Error fetching home run data for game {game_pk}: {e}")
            return []

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
        if game.get('home_runs'):
            print(f"    Home runs: {len(game['home_runs'])}")
        print()

if __name__ == "__main__":
    test_mlb_api()
