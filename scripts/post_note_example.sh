#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
SUBMITTED_AT="$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")"

curl -X POST "${API_URL}/note" \
  -H 'Content-Type: application/json' \
  -d "{
    \"title\": \"Delaunay Triangulation\",
    \"content\": \"Delaunay triangulation maximizes the minimum angle of all the angles of the triangles in the triangulation.\",
    \"tags\": [\"geometry\", \"computational-geometry\"],
    \"images\": [],
    \"type\": \"concept\",
    \"status\": \"draft\",
    \"related\": [\"voronoi-diagram\"],
    \"submitted_at\": \"${SUBMITTED_AT}\"
  }"

echo
