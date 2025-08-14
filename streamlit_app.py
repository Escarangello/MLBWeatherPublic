#!/usr/bin/env python3
"""
MLB Weather Widget - Streamlit Application
Clean, mobile-friendly web interface for easy deployment and sharing.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
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

# Custom CSS for better mobile experience
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #1f4e79, #2e86ab);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .game-card {
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        background: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .live-game {
        border-left: 5px solid #ff4444;
        background: #fff5f5;
    }
    
    .final-game {
        border-left: 5px solid #888;
        background: #f8f8f8;
    }
    
    .delayed-game {
        border-left: 5px solid #ff8800;
        background: #fff8f0;
    }
    
    .weather-info {
        background: #f0f8ff;
        padding: 0.8rem;
        border-radius: 8px;
        margin-top: 0.5rem;
        font-family: monospace;
        font-size: 0.9rem;
        color: #333 !important;
    }
    
    .game-time {
        font-weight: bold;
        font-size: 1.1rem;
    }
    
    .live-indicator {
        color: #ff4444;
        font-weight: bold;
        animation: blink 1.5s infinite;
    }
    
    @keyframes blink {
        0%, 50% { opacity: 1; }
        51%, 100% { opacity: 0.7; }
    }
    
    .score {
        color: #ff4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_games_data():
    """Get games data with caching to avoid API rate limits."""
    try:
        # Initialize API components
        mlb_fetcher = MLBGameFetcher()
        weather_api_key = st.secrets.get("OPENWEATHER_API_KEY", None)
        weather_fetcher = WeatherFetcher(weather_api_key)
        
        # Fetch MLB games
        games = mlb_fetcher.get_todays_games()
        
        # Fetch weather for each game
        games_with_weather = []
        for game in games:
            if game['coordinates'] and weather_api_key:
                weather = weather_fetcher.get_weather_for_game(
                    game['coordinates'], 
                    game['game_datetime'],
                    game['stadium_name'],
                    game['status'])
            else:
                # Use mock weather data if no API key or coordinates
                weather = get_mock_weather(
                    game['stadium_name'], 
                    game['status']) if game['coordinates'] else None
            
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

def main():
    """Main Streamlit application."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>⚾ MLB Weather Widget</h1>
        <p>Today's games with comprehensive weather analysis and home run factors</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Date and refresh
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        today_str = datetime.now().strftime("%A, %B %d, %Y")
        st.subheader(f"📅 {today_str}")
    
    with col3:
        if st.button("🔄 Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
    
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
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Games", len(games))
    with col2:
        st.metric("Live Games", live_games)
    with col3:
        st.metric("Final Games", final_games)
    with col4:
        st.metric("Upcoming Games", upcoming_games)
    
    st.markdown("---")
    
    # Display games
    for i, game in enumerate(games, 1):
        # Determine card style based on status
        if game['status'] in ['In Progress', 'Live']:
            card_class = "live-game"
            time_class = "live-indicator"
        elif game['status'] in ['Final', 'Game Over']:
            card_class = "final-game"
            time_class = ""
        elif game['status'] == 'Delayed':
            card_class = "delayed-game"
            time_class = ""
        else:
            card_class = "game-card"
            time_class = ""
        
        # Game card
        with st.container():
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # Game header
            col1, col2 = st.columns([3, 1])
            with col1:
                score_info = game.get('score_info', '')
                teams_display = f"**{game['away_team']}** @ **{game['home_team']}**"
                if score_info:
                    teams_display += f" <span class='score'>{score_info}</span>"
                st.markdown(teams_display, unsafe_allow_html=True)
            
            with col2:
                if time_class:
                    st.markdown(f"<span class='{time_class} game-time'>{game['game_time']}</span>", 
                               unsafe_allow_html=True)
                else:
                    st.markdown(f"<span class='game-time'>{game['game_time']}</span>", 
                               unsafe_allow_html=True)
            
            # Stadium and status
            st.markdown(f"🏟️ **{game['stadium_name']}** | 📊 {game['status']}")
            
            # Weather information
            if game['weather_str']:
                st.markdown(f"""
                <div class="weather-info">
                    🌤️ {game['weather_str']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Weather data unavailable")
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("")  # Spacing
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>📊 Total games: {len(games)} | 🕐 All times in Eastern Time</p>
        <p>⚾ Enhanced with wind direction relative to ballparks and physics-based home run factors</p>
        <p>🔄 Data updates when you click refresh</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
