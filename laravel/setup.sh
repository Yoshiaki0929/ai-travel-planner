#!/bin/bash
# Laravel Travel App — first-time setup

set -e

echo "=== Installing PHP dependencies ==="
composer install --no-dev --optimize-autoloader

echo ""
echo "=== Setting up environment ==="
if [ ! -f .env ]; then
    cp .env.example .env
    php artisan key:generate
    echo "Created .env — please fill in your API keys."
else
    echo ".env already exists, skipping."
fi

echo ""
echo "=== Linking SPA frontend ==="
# Copy the frontend from parent directory into public/
if [ -f ../static/index.html ]; then
    cp ../static/index.html public/index.html
    echo "Copied static/index.html → public/index.html"
else
    echo "WARNING: ../static/index.html not found. Place index.html in laravel/public/ manually."
fi

echo ""
echo "=== Fixing permissions ==="
chmod -R 775 storage bootstrap/cache

echo ""
echo "=== Done! Start the server with: ==="
echo "    php artisan serve --port=8000"
echo ""
echo "Or for production with nginx/Apache, point the document root to laravel/public/"
