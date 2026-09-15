#!/bin/sh
set -e

CERT="/etc/letsencrypt/live/${CHATBOT_DOMAIN}/fullchain.pem"
if [ -f "$CERT" ]; then
    TMPL=/etc/nginx/templates/https.conf.template
else
    TMPL=/etc/nginx/templates/http.conf.template
fi

# Replace only our two variables; leave nginx's own $host, $uri etc. untouched
envsubst '${CHATBOT_DOMAIN} ${MAIL_DOMAIN}' < "$TMPL" > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
