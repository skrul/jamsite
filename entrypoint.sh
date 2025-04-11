#!/bin/bash
set -e

# Generate the site
echo "Generating site..."
/venv/bin/jamsite --generate

# Copy the generated files to nginx's html directory
echo "Copying generated files to nginx html directory..."
cp -r /src/dist/* /usr/share/nginx/html/

# Start nginx
echo "Starting nginx..."
exec nginx -g 'daemon off;'
