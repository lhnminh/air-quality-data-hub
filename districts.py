from typing import TypedDict


class District(TypedDict):
    name: str
    latitude: float
    longitude: float
    map_x: str
    map_y: str


# Representative coordinates for the first Hanoi pilot districts. They are used
# for regional model lookups, not as a claim that a physical sensor is present.
DISTRICTS: list[District] = [
    {"name": "Tay Ho", "latitude": 21.070, "longitude": 105.818, "map_x": "30%", "map_y": "18%"},
    {"name": "Long Bien", "latitude": 21.045, "longitude": 105.892, "map_x": "76%", "map_y": "43%"},
    {"name": "Ba Dinh", "latitude": 21.035, "longitude": 105.815, "map_x": "36%", "map_y": "44%"},
    {"name": "Cau Giay", "latitude": 21.035, "longitude": 105.793, "map_x": "17%", "map_y": "49%"},
    {"name": "Hoan Kiem", "latitude": 21.028, "longitude": 105.854, "map_x": "60%", "map_y": "55%"},
    {"name": "Dong Da", "latitude": 21.018, "longitude": 105.830, "map_x": "38%", "map_y": "64%"},
    {"name": "Hai Ba Trung", "latitude": 21.005, "longitude": 105.855, "map_x": "61%", "map_y": "72%"},
    {"name": "Thanh Xuan", "latitude": 20.995, "longitude": 105.813, "map_x": "30%", "map_y": "82%"},
]
