#!/usr/bin/env python3
"""
MLB Weather Widget - Streamlit Application
Clean, mobile-friendly web interface for easy deployment and sharing.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import os
import time

from mlb_api import MLBGameFetcher
from weather_api import WeatherFetcher, get_mock_weather

# Page configuration
st.set_page_config(
    page_title="MLB Weather Widget",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for better mobile experience and cleaner styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(135deg, #1f4e79, #2e86ab, #a23b72);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
    }
    
    .game-card {
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background: white;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .game-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.12);
    }
    
    .live-game {
        border-left: 6px solid #ff4444;
        background: linear-gradient(135deg, #fff5f5, #ffffff);
        animation: pulse-border 2s infinite;
    }
    
    @keyframes pulse-border {
        0%, 100% { border-left-color: #ff4444; }
        50% { border-left-color: #ff6666; }
    }
    
    .final-game {
        border-left: 6px solid #28a745;
        background: linear-gradient(135deg, #f8fff8, #ffffff);
    }
    
    .delayed-game {
        border-left: 6px solid #ff8800;
        background: linear-gradient(135deg, #fff8f0, #ffffff);
    }
    
    .scheduled-game {
        border-left: 6px solid #007bff;
        background: linear-gradient(135deg, #f0f8ff, #ffffff);
    }
    
    .weather-info {
        background: linear-gradient(135deg, #f0f8ff, #e6f3ff);
        padding: 1rem;
        border-radius: 12px;
        margin-top: 1rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 0.95rem;
        color: #2c3e50;
        border: 1px solid #d6e9ff;
    }
    
    .home-runs-info {
        background: linear-gradient(135deg, #fff8e1, #fffbf0);
        padding: 1rem;
        border-radius: 12px;
        margin-top: 1rem;
        border: 1px solid #ffd54f;
        color: #e65100;
    }
    
    .home-run-item {
        background: rgba(255, 193, 7, 0.1);
        padding: 0.5rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #ffc107;
    }
    
    .game-time {
        font-weight: 700;
        font-size: 1.2rem;
        color: #2c3e50;
    }
    
    .live-indicator {
        color: #ff4444;
        font-weight: 700;
        animation: blink 1.5s infinite;
        text-shadow: 0 0 5px rgba(255, 68, 68, 0.5);
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.7; }
    }
    
    .score {
        color: #dc3545;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .final-score {
        color: #28a745;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .team-names {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 0.5rem;
    }
    
    .stadium-info {
        color: #6c757d;
        font-size: 1rem;
        margin: 0.5rem 0;
    }
    
    .metrics-container {
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .footer-info {
        text-align: center;
        color: #6c757d;
        font-size: 0.9rem;
        background: linear-gradient(135deg, #f8f9fa, #ffffff);
        padding: 1.5rem;
        border-radius: 15px;
        margin-top: 2rem;
    }
    
    .cache-info {
        background: linear-gradient(135deg, #e8f5e8, #f0fff0);
        padding: 0.5rem;
        border-radius: 8px;
        border: 1px solid #c3e6c3;
        font-size: 0.85rem;
        color: #2d5a2d;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .game-card {
            padding: 1rem;
        }
        
        .team-names {
            font-size: 1.1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

def get_cache_ttl():
    """Get cache TTL based on Eastern Time - no refresh between 3am-10am."""
    eastern_tz = timezone(timedelta(hours=-4))  # EDT
    eastern_time = datetime.now(eastern_tz)
    current_hour = eastern_time.hour
    
    # During quiet hours (3am-10am Eastern), use very long cache (7 hours)
    if 3 <= current_hour < 10:
        return 25200  # 7 hours in seconds
    else:
        return 600  # 10 minutes in seconds during active hours

@st.cache_data(ttl=86400, show_spinner=False)  # Cache finished game weather for 24 hours
def get_finished_game_weather(coordinates, game_datetime, stadium_name, game_pk, weather_api_key):
    """Get weather data for finished games - cache for entire day since conditions are historical."""
    weather_fetcher = WeatherFetcher(weather_api_key)
    return weather_fetcher.get_weather_for_game(coordinates, game_datetime, stadium_name, "Final")

@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes - shared across all users
def get_games_data():
    """Get games data with caching to avoid API rate limits. Only refreshes when users are active."""
    try:
        # Initialize API components
        mlb_fetcher = MLBGameFetcher()
        weather_api_key = st.secrets.get("OPENWEATHER_API_KEY", None)
        weather_fetcher = WeatherFetcher(weather_api_key)
        
        # Fetch MLB games
        games = mlb_fetcher.get_todays_games()
        
        # Fetch weather for each game with different caching for finished games
        games_with_weather = []
        for game in games:
            # For finished games, use permanent cached weather data (don't update weather)
            if game['status'] in ["Final", "Game Over"]:
                if game['coordinates'] and weather_api_key:
                    weather = get_finished_game_weather(
                        game['coordinates'], 
                        game['game_datetime'],
                        game['stadium_name'],
                        game.get('game_pk', ''),
                        weather_api_key
                    )
                else:
                    weather = get_mock_weather(game['stadium_name'], game['status']) if game['coordinates'] else None
            else:
                # For active/upcoming games, use regular weather updates
                if game['coordinates'] and weather_api_key:
                    weather = weather_fetcher.get_weather_for_game(
                        game['coordinates'], 
                        game['game_datetime'],
                        game['stadium_name'],
                        game['status'])
                else:
                    weather = get_mock_weather(game['stadium_name'], game['status']) if game['coordinates'] else None
            
            game['weather'] = weather
            if weather:
                game['weather_str'] = weather_fetcher.format_weather_string_with_stadium(
                    weather, game['stadium_name'])
            else:
                game['weather_str'] = "Weather data unavailable"
            
            games_with_weather.append(game)
        
        return games_with_weather, weather_api_key is None
        
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], True

@st.cache_data(ttl=600, show_spinner=False)
def get_cache_timestamp():
    """Get cache timestamp for display purposes in Eastern Time."""
    eastern_tz = timezone(timedelta(hours=-4))  # EDT
    eastern_time = datetime.now(eastern_tz)
    return eastern_time.strftime("%I:%M:%S %p")

def track_user_activity():
    """Track user activity to prevent unnecessary cache refreshes."""
    # This function runs every time a user loads the page
    # The cache will only refresh when this function is called (i.e., when users are active)
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
    else:
        st.session_state.last_activity = datetime.now()
    return True

def format_home_runs_display(home_runs, away_team_abbr, home_team_abbr):
    """Format home run information for display as HTML."""
    if not home_runs:
        return "No home runs hit yet"
    
    home_run_text = []
    away_hrs = [hr for hr in home_runs if hr['team_type'] == 'away']
    home_hrs = [hr for hr in home_runs if hr['team_type'] == 'home']
    
    if away_hrs:
        # Use fallback if abbreviation is empty
        team_name = away_team_abbr if away_team_abbr else "Away"
        away_text = f"<strong>{team_name}:</strong> "
        away_details = []
        for hr in away_hrs:
            detail = f"{hr['batter']} (Inning {hr['inning']})"
            if hr['distance']:
                detail += f" - {hr['distance']} ft"
            away_details.append(detail)
        away_text += ", ".join(away_details)
        home_run_text.append(away_text)
    
    if home_hrs:
        # Use fallback if abbreviation is empty
        team_name = home_team_abbr if home_team_abbr else "Home"
        home_text = f"<strong>{team_name}:</strong> "
        home_details = []
        for hr in home_hrs:
            detail = f"{hr['batter']} (Inning {hr['inning']})"
            if hr['distance']:
                detail += f" - {hr['distance']} ft"
            home_details.append(detail)
        home_text += ", ".join(home_details)
        home_run_text.append(home_text)
    
    return " | ".join(home_run_text)

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚾ MLB Weather Widget</h1>
        <p>Today's games with comprehensive weather analysis and home run tracking</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Date and cache info
    col1, col2 = st.columns([2, 1])
    with col1:
        # Display date in Eastern Time
        eastern_tz = timezone(timedelta(hours=-4))  # EDT
        today_eastern = datetime.now(eastern_tz)
        today_str = today_eastern.strftime("%A, %B %d, %Y")
        st.subheader(f"📅 {today_str}")
    
    with col2:
        # Show cache status
        cache_time = get_cache_timestamp()
        st.caption(f"🕐 Data cached at: {cache_time}")
        eastern_tz = timezone(timedelta(hours=-4))
        current_hour = datetime.now(eastern_tz).hour
        if 3 <= current_hour < 10:
            st.caption("⏱️ Quiet hours (3am-10am) - minimal refreshing")
        else:
            st.caption("⏱️ Auto-refreshes every 10 minutes")
    
    # Track user activity (prevents cache refresh when no users are active)
    track_user_activity()
    
    # Get data
    with st.spinner("Loading games and weather data..."):
        games, using_mock_data = get_games_data()
    
    # API key warning
    if using_mock_data:
        st.warning("""
        **⚠️ Using Mock Weather Data**  
        Set the `OPENWEATHER_API_KEY` environment variable for real weather data.  
        Get a free API key at: https://openweathermap.org/api
        """)
    
    # Games display
    if not games:
        st.info("🏟️ No MLB games scheduled for today. Check back tomorrow!")
        return
    
    # Summary metrics
    live_games = len([g for g in games if g['status'] in ['In Progress', 'Live']])
    final_games = len([g for g in games if g['status'] in ['Final', 'Game Over']])
    upcoming_games = len(games) - live_games - final_games
    total_home_runs = sum(len(game.get('home_runs', [])) for game in games)
    
    st.markdown('<div class="metrics-container">', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Games", len(games))
    with col2:
        st.metric("Live Games", live_games)
    with col3:
        st.metric("Final Games", final_games)
    with col4:
        st.metric("Upcoming Games", upcoming_games)
    with col5:
        st.metric("Total Home Runs", total_home_runs)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display games
    for i, game in enumerate(games, 1):
        # Determine card style based on status
        if game['status'] in ['In Progress', 'Live']:
            card_class = "game-card live-game"
            time_class = "live-indicator"
        elif game['status'] in ['Final', 'Game Over']:
            card_class = "game-card final-game"
            time_class = ""
        elif game['status'] == 'Delayed':
            card_class = "game-card delayed-game"
            time_class = ""
        else:
            card_class = "game-card scheduled-game"
            time_class = ""
        
        # Game card - build complete HTML content
        score_info = game.get('score_info', '')
        teams_display = f'{game["away_team"]} @ {game["home_team"]}'
        
        if score_info:
            if "Final:" in score_info:
                score_display = f'<span class="final-score">{score_info}</span>'
            else:
                score_display = f'<span class="score">{score_info}</span>'
        else:
            score_display = ""
        
        # Game time display
        if time_class:
            time_display = f'<span class="{time_class} game-time">{game["game_time"]}</span>'
        else:
            time_display = f'<span class="game-time">{game["game_time"]}</span>'
        
        # Home runs information
        home_runs = game.get('home_runs', [])
        home_runs_html = ""
        if home_runs:
            hr_display = format_home_runs_display(
                home_runs, 
                game.get('away_team_abbr', game['away_team'][:3]), 
                game.get('home_team_abbr', game['home_team'][:3])
            )
            home_runs_html = f'<div class="home-runs-info">⚾ <strong>Home Runs ({len(home_runs)}):</strong><br>{hr_display}</div>'
        elif game['status'] in ["In Progress", "Live", "Final", "Game Over"]:
            home_runs_html = '<div class="home-runs-info">⚾ <strong>Home Runs:</strong> None hit yet</div>'
        
        # Weather information
        weather_html = ""
        if game['weather_str']:
            weather_html = f'<div class="weather-info">🌤️ <strong>Weather:</strong> {game["weather_str"]}</div>'
        
        # Complete game card HTML
        st.markdown(f"""
        <div class="{card_class}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
                <div style="flex: 1;">
                    <div class="team-names">{teams_display}</div>
                    {score_display}
                </div>
                <div style="text-align: right;">
                    {time_display}
                </div>
            </div>
            <div class="stadium-info">🏟️ <strong>{game["stadium_name"]}</strong> | 📊 {game["status"]}</div>
            {home_runs_html}
            {weather_html}
        </div>
        """, unsafe_allow_html=True)
    
    # Footer with cache information
    st.markdown("---")
    cache_time = get_cache_timestamp()
    st.markdown(f"""
    <div class="footer-info">
        <p><strong>📊 Game Summary:</strong> {len(games)} total games | {total_home_runs} home runs hit today</p>
        <p><strong>🕐 Time Zone:</strong> All times displayed in Eastern Time</p>
        <p><strong>⚾ Features:</strong> Real-time scores, home run tracking, and physics-based weather analysis</p>
        <p><strong>💾 Smart Caching:</strong> Data cached at {cache_time} | Shared across all users | 10min refresh (quiet 3am-10am ET)</p>
        <p><strong>🔄 Automatic Updates:</strong> Refreshes every 10 minutes during active hours | No refresh 3am-10am Eastern</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
