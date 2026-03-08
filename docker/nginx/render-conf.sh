#!/bin/sh
set -eu

SSL_DOMAIN="${SSL_DOMAIN:-example.com}"
CERT_PATH="/etc/letsencrypt/live/${SSL_DOMAIN}/fullchain.pem"

if [ -f "$CERT_PATH" ]; then
  TEMPLATE="/etc/nginx/templates/app.https.conf.template"
else
  TEMPLATE="/etc/nginx/templates/app.http.conf.template"
fi

sed "s|__SERVER_NAME__|${SSL_DOMAIN}|g" "$TEMPLATE" > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
