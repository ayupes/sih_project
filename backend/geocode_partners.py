# Run this ONCE to fill in latitude/longitude on partners.csv.
# It is not part of the live app - it's a one-time data prep script.
#
# BEFORE RUNNING: this geocodes whatever addresses are currently in
# partners.csv. If those addresses haven't been checked against the
# official government PDF yet, this will still work - it just means
# the coordinates are only as good as the addresses are. Re-run this
# script any time an address gets corrected; it's cheap and safe to
# run more than once.

import requests
import pandas as pd
import time

df = pd.read_csv("partners.csv")

for i, row in df.iterrows():
    if pd.notna(row.get("latitude")):
        continue  # already geocoded, skip it

    query = f"{row['address']}, {row['state']}, India"
    resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "json", "limit": 1},
        headers={"User-Agent": "SaarthiAI-Hackathon-Prototype"},
    )
    results = resp.json()
    if results:
        df.at[i, "latitude"] = results[0]["lat"]
        df.at[i, "longitude"] = results[0]["lon"]
        print(f"OK   {row['partner_name']}")
    else:
        print(f"MISS {row['partner_name']} - address not found, left blank")

    time.sleep(1)  # Nominatim's usage policy: max 1 request/second

df.to_csv("partners.csv", index=False)
print("\nDone - partners.csv updated in place.")
