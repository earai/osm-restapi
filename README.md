# osm-restapi
Prompt: Create a REST API that has endpoints for different types of data
(roads, POIs, etc.) from OpenStreetMap (OSM), caches the fetched data in a
database, and returns properly formatted geojson to the user. Queries should
check the cached data first before reaching out to OSM. If data exists for
part of a submitted AOI, only fetch the missing data and ensure complete data
capture for the AOI. The endpoints should take as input an Area of Interest
(Polygon) in geojson format.
