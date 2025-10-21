#!/usr/bin/env bash
set -euo pipefail

FASTAPI_URL="http://localhost:8000"
#API_SVC="osm-fastapi"
#DB_SVC="osm-postgis"


#ROAD_EP="$FASTAPI_URL/osm/roads/polygon"
#AMENITY_EP="$FASTAPI_URL/osm/amenity/polygon"

#MAX_RETRIES=20
#RETRY_DELAY=10

#ROAD_POLYGON='{
 # "type": "Polygon",
  #"coordinates": [
   # [
    #          [-73.9870, 40.7600],
     #         [-73.9870, 40.7600],
      #        [-73.9870, 40.7600],
       #       [-73.9870, 40.7600],
       #       [-73.9870, 40.7600]
    #]
  #]
#}'

echo "Clean up services"
docker compose down

# Bring up services
echo "🚀 Starting services..."
echo
#docker compose up -d --build

docker compose up -d && \
until curl -sf http://localhost:8000/docs > /dev/null; do sleep 2; done

echo
echo ""
echo

echo "The data base is initially empty "
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache;"
echo

echo
echo -e "Now we will ask for amenity data in a particular region. If data is returned, it will be written to the database \n
and we should have a nonzero count returned."
echo

curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://localhost:8000/osm/amenity/polygon"   -H "accept: application/json"   -H "Content-Type: application/json"   -d '{
        "type": "Polygon",
        "coordinates": [
          [
          [-115.157891, 36.155421],
          [-115.121709, 36.155421],
          [-115.121709, 36.184379],
          [-115.157891, 36.184379],
          [-115.157891, 36.155421]

          ]
        ]
      }'

echo
echo "Now get the total entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache;"
echo
echo "Next ask for the total amenity entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='amenity';"
echo
echo "Now the total number of road entries (we expect zero, since we haven't requested that type of data yet)"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='highway';"
echo

echo
echo "Now request road data from a different area"
echo

curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://localhost:8000/osm/roads/polygon"   -H "accept: application/json"   -H "Content-Type: application/json"   -d '{
          "type": "Polygon",
          "coordinates": [[
            [-115.280990, 36.105152],
            [-115.279788, 36.121655],
            [-115.296182, 36.111462],
            [-115.280990, 36.105152],
            [-115.280990, 36.105152]
          ]]
        }'

echo
echo -e "Count the number of entries in the database now"
echo
echo "Count the total entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache;"
echo "Count the total amenity entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='amenity';"
echo "Count the total road entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='highway';"
echo
echo
echo -e "Next, request the same amenity data from before. Confirm that \n no new entries are actually requested since \n
 since they already exist in the database"
echo

curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://localhost:8000/osm/amenity/polygon"   -H "accept: application/json"   -H "Content-Type: application/json"   -d '{
        "type": "Polygon",
        "coordinates": [
          [
        [-115.157891, 36.155421],
        [-115.121709, 36.155421],
        [-115.121709, 36.184379],
        [-115.157891, 36.184379],
        [-115.157891, 36.155421]
          ]
        ]
      }'

echo "Total entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache;"
echo "Total amenity entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='amenity';"
echo "Total road entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='highway';"
echo
echo

echo
echo "Now request additional amenity objects in a region that overlaps with the prior road region"
echo

curl -X POST "http://localhost:8000/osm/amenity/polygon"   -H "accept: application/json"   -H "Content-Type: application/json"   -d '{
  "type": "Polygon",
  "coordinates": [[
    [-115.286000, 36.112000],
    [-115.270000, 36.123000],
    [-115.290000, 36.125000],
    [-115.286000, 36.112000]
  ]]
}'

echo
echo "There amenity objects will be added to the database, they overlap partially in area with the road data but are a different type of data"
echo "Total database entries:"
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache;"
echo "Total amenity entries in the data base (should have increased)"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='amenity';"
echo "Total road entries in the data base"
echo
docker exec -it osm-postgis psql -U postgres -d osm -c "SELECT COUNT(*) FROM public.osm_cache WHERE query_key='highway';"
echo


echo
echo "✅ Done."
