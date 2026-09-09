from typing import Optional, Tuple, Dict
import re

# Comprehensive registry of canonical agricultural coordinates across Indian farming districts
AGRICULTURAL_COORDINATES: Dict[str, Tuple[float, float]] = {
    # Andhra Pradesh
    "guntur": (16.3067, 80.4365),
    "tenali": (16.2435, 80.6400),
    "vijayawada": (16.5062, 80.6480),
    "krishna": (16.1809, 81.1303),
    "prakasam": (15.5057, 80.0499),
    "ongole": (15.5057, 80.0499),
    "kurnool": (15.8281, 78.0373),
    "anantapur": (14.6819, 77.6006),
    "chittoor": (13.2172, 79.1003),
    "kadapa": (14.4673, 78.8242),
    "ysr kadapa": (14.4673, 78.8242),
    "nellore": (14.4426, 79.9865),
    "visakhapatnam": (17.6868, 83.2185),
    "east godavari": (17.0005, 81.8040),
    "west godavari": (16.7107, 81.0952),
    "srikakulam": (18.2949, 83.8938),
    "vizianagaram": (18.1067, 83.3956),
    
    # Telangana
    "warangal": (17.9689, 79.5941),
    "khammam": (17.2473, 80.1514),
    "karimnagar": (18.4386, 79.1288),
    "nizamabad": (18.6725, 78.0941),
    "nalgonda": (17.0575, 79.2684),
    "mahabubnagar": (16.7488, 77.9840),
    "hyderabad": (17.3850, 78.4867),
    
    # Maharashtra
    "pune": (18.5204, 73.8567),
    "nashik": (19.9975, 73.7898),
    "nagpur": (21.1458, 79.0882),
    "solapur": (17.6599, 75.9064),
    "aurangabad": (19.8762, 75.3433),
    "chhatrapati sambhajinagar": (19.8762, 75.3433),
    
    # Karnataka
    "mysuru": (12.2958, 76.6394),
    "dharwad": (15.4589, 75.0078),
    "belagavi": (15.8497, 74.4977),
    "raichur": (16.2120, 77.3439),
    "bengaluru": (12.9716, 77.5946),
    
    # Tamil Nadu
    "coimbatore": (11.0168, 76.9558),
    "madurai": (9.9252, 78.1198),
    "thanjavur": (10.7870, 79.1378),
    
    # North / Central India
    "varanasi": (25.3176, 82.9739),
    "ludhiana": (30.9010, 75.8573),
    "indore": (22.7196, 75.8577),
    "rajkot": (22.3039, 70.8022)
}

def resolve_location_coordinates(
    location: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Resolves geographic coordinates from GPS inputs or agricultural district names.
    Does NOT fabricate random coordinates.
    Returns: (latitude, longitude, canonical_location_name)
    """
    # 1. If GPS coordinates are explicitly provided and valid
    if lat is not None and lon is not None:
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            return float(lat), float(lon), location.strip()

    # 2. Extract tokens from location string (e.g., "Tenali, Guntur, Andhra Pradesh")
    if not location or not location.strip():
        return None, None, "Unknown Location"

    cleaned_location = location.lower().strip()
    tokens = re.split(r"[,/ -]+", cleaned_location)

    # Check for specific mandal/village first (e.g. "tenali")
    for token in tokens:
        if token in AGRICULTURAL_COORDINATES:
            coords = AGRICULTURAL_COORDINATES[token]
            return coords[0], coords[1], token.capitalize()

    # Check if any key is contained within the string
    for key, coords in AGRICULTURAL_COORDINATES.items():
        if key in cleaned_location:
            return coords[0], coords[1], key.capitalize()

    # Coordinates could not be resolved
    return None, None, location.strip()
