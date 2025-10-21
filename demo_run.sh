#!/usr/bin/env bash
set -euo pipefail

FASTAPI_URL="http://localhost:8000"
API_SVC="osm-fastapi"
DB_SVC="osm-postgis"


ROAD_EP="$FASTAPI_URL/osm/roads/polygon"
AMENITY_EP="$FASTAPI_URL/osm/amenity/polygon"


#Clean up services
docker compose down

# Bring up services
#echo "🚀 Starting services..."
#docker compose up -d --build

docker compose up -d && \
until curl -sf http://localhost:8000/docs > /dev/null; do sleep 2; done && \
curl -X POST "http://localhost:8000/osm/amenity/polygon"   -H "accept: application/json"   -H "Content-Type: application/json"   -d '{
        "type": "Polygon",
        "coordinates": [
          [
            [-73.9885, 40.7585],
            [-73.9855, 40.7585],
            [-73.9855, 40.7605],
            [-73.9885, 40.7605],
            [-73.9885, 40.7585]
          ]
        ]
      }'


#docker exec -it osm-postgis psql -U postgres -d osm -c

echo "✅ Done."
