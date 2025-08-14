"""
Stadium coordinates mapping for MLB teams.
Maps stadium names to their latitude and longitude coordinates.
"""

# Stadium coordinates and orientations for MLB teams
# Coordinates are (latitude, longitude)
# Orientations are the bearing from home plate to center field in degrees
STADIUM_COORDINATES = {
    # American League
    "Fenway Park": (42.3467, -71.0972),  # Boston Red Sox
    "Yankee Stadium": (40.8296, -73.9262),  # New York Yankees
    "Tropicana Field": (27.7682, -82.6534),  # Tampa Bay Rays
    "Rogers Centre": (43.6414, -79.3894),  # Toronto Blue Jays
    "Oriole Park at Camden Yards": (39.2838, -76.6217),  # Baltimore Orioles
    
    "Progressive Field": (41.4962, -81.6852),  # Cleveland Guardians
    "Comerica Park": (42.3390, -83.0485),  # Detroit Tigers
    "Guaranteed Rate Field": (41.8300, -87.6338),  # Chicago White Sox
    "Kauffman Stadium": (39.0517, -94.4803),  # Kansas City Royals
    "Target Field": (44.9817, -93.2776),  # Minnesota Twins
    
    "Minute Maid Park": (29.7570, -95.3551),  # Houston Astros
    "Angel Stadium": (33.8003, -117.8827),  # Los Angeles Angels
    "Oakland Coliseum": (37.7516, -122.2005),  # Oakland Athletics
    "T-Mobile Park": (47.5914, -122.3326),  # Seattle Mariners
    "Globe Life Field": (32.7473, -97.0814),  # Texas Rangers
    
    # National League
    "Truist Park": (33.8906, -84.4677),  # Atlanta Braves
    "loanDepot park": (25.7781, -80.2197),  # Miami Marlins
    "Citi Field": (40.7571, -73.8458),  # New York Mets
    "Citizens Bank Park": (39.9061, -75.1665),  # Philadelphia Phillies
    "Nationals Park": (38.8730, -77.0074),  # Washington Nationals
    
    "Wrigley Field": (41.9484, -87.6553),  # Chicago Cubs
    "Great American Ball Park": (39.0974, -84.5061),  # Cincinnati Reds
    "American Family Field": (43.0280, -87.9712),  # Milwaukee Brewers
    "PNC Park": (40.4469, -80.0057),  # Pittsburgh Pirates
    "Busch Stadium": (38.6226, -90.1928),  # St. Louis Cardinals
    
    "Chase Field": (33.4453, -112.0667),  # Arizona Diamondbacks
    "Coors Field": (39.7559, -104.9942),  # Colorado Rockies
    "Dodger Stadium": (34.0739, -118.2400),  # Los Angeles Dodgers
    "Petco Park": (32.7073, -117.1566),  # San Diego Padres
    "Oracle Park": (37.7786, -122.3893),  # San Francisco Giants
}

# Stadium orientations (home plate to center field bearing in degrees)
# These are more accurate orientations based on actual ballpark layouts
STADIUM_ORIENTATIONS = {
    # American League
    "Fenway Park": 65,  # ENE (Green Monster creates unique layout)
    "Yankee Stadium": 95,  # E-ESE
    "Tropicana Field": 90,  # E (indoor, standard orientation)
    "Rogers Centre": 90,  # E (indoor, standard orientation)
    "Oriole Park at Camden Yards": 70,  # ENE
    
    "Progressive Field": 80,  # E-ENE
    "Comerica Park": 85,  # E-ENE
    "Guaranteed Rate Field": 90,  # E
    "Kauffman Stadium": 90,  # E
    "Target Field": 105,  # ESE
    
    "Minute Maid Park": 105,  # ESE (left field wall creates unique angles)
    "Angel Stadium": 90,  # E
    "Oakland Coliseum": 90,  # E
    "T-Mobile Park": 90,  # E
    "Globe Life Field": 90,  # E
    
    # National League
    "Truist Park": 90,  # E
    "loanDepot park": 90,  # E
    "Citi Field": 90,  # E
    "Citizens Bank Park": 90,  # E
    "Nationals Park": 90,  # E
    
    "Wrigley Field": 90,  # E (classic orientation)
    "Great American Ball Park": 90,  # E
    "American Family Field": 90,  # E
    "PNC Park": 85,  # E-ENE (river creates slight angle)
    "Busch Stadium": 90,  # E
    
    "Chase Field": 90,  # E (indoor, standard orientation)
    "Coors Field": 90,  # E
    "Dodger Stadium": 90,  # E
    "Petco Park": 90,  # E
    "Oracle Park": 225,  # SW (unique orientation due to bay location)
}

def get_stadium_coordinates(stadium_name):
    """
    Get coordinates for a stadium name.
    Returns (lat, lon) tuple or None if not found.
    """
    return STADIUM_COORDINATES.get(stadium_name)

def get_stadium_orientation(stadium_name):
    """
    Get orientation (home plate to center field bearing) for a stadium.
    Returns bearing in degrees or None if not found.
    """
    return STADIUM_ORIENTATIONS.get(stadium_name)

def get_all_stadiums():
    """
    Get all stadium names.
    """
    return list(STADIUM_COORDINATES.keys())
