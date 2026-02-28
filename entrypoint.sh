#!/bin/bash
set -e

# Generate the site
echo "Generating site..."
uv run jamsite --generate

# Copy the generated files to nginx's html directory
echo "Copying generated files to nginx html directory..."
cp -r /src/dist/* /usr/share/nginx/html/

# Start the broadcast server in the background
echo "Starting broadcast server..."
uv run python -m jamsite.broadcast &

# Start nginx
echo "Starting nginx..."
exec nginx -g 'daemon off;'
