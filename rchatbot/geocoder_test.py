from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="recycle-assistant")

latitude = 37.7749
longitude = -122.4194

result = geolocator.reverse(
    (latitude, longitude),
    exactly_one=True
)

address = result.raw.get("address", {})

state = address.get("state")

county = address.get("county")
if county:
    county = county.replace(" County", "")

city = (
    address.get("city")
    or address.get("town")
    or address.get("village")
)

print("Full address data:", address)
print("State:", state)
print("County:", county)
print("City:", city)