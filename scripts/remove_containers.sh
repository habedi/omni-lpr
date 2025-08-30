#!/bin/bash

# This script removes recently exited Docker containers and their associated images.
# It targets containers that have exited within the last hour (3600 seconds).
AGE=3600   # seconds (=1 hour)
now=$(date +%s)

# Collect recent exited container IDs
recent_containers=$(
  docker ps -a -q -f status=exited \
    | while read -r id; do
        created=$(docker inspect --format='{{.Created}}' "$id")
        created_epoch=$(date -d "$created" +%s)
        if [ $((now - created_epoch)) -le $AGE ]; then
          printf '%s\n' "$id"
        fi
      done
)

# Remove containers (if any)
if [ -n "$recent_containers" ]; then
  printf '%s\n' "$recent_containers" | xargs -r docker rm
  # get unique image IDs referenced by those containers and remove them
  printf '%s\n' "$recent_containers" \
    | xargs -r -I {} docker inspect --format='{{.Image}}' {} \
    | sort -u \
    | xargs -r docker image rm
fi

# Alternative: remove dangling images (safely)
docker image prune -f
