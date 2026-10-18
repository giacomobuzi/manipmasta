#!/usr/bin/env bash
# Crea/aggiorna il file password di Mosquitto con gli utenti ManipMasta presi da .env.
# Uso (dalla cartella server/):   ./scripts/create_mqtt_users.sh
# Variabili lette da .env: MQTT_USER/MQTT_PASS (server), MQTT_DEVICE_USER/MQTT_DEVICE_PASS (Arduino),
# MQTT_TOOLS_PASS (facoltativo, utente manipmasta-tools).
# Se una password è vuota ne genera una casuale e la scrive in .env.
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env
[ -f "$ENV_FILE" ] || { echo "Manca $ENV_FILE: copia .env.example in .env e compila API_TOKEN"; exit 1; }

getv() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- ; }
setv() {
  if grep -qE "^$1=" "$ENV_FILE"; then sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
}
rnd() { openssl rand -hex 16 2>/dev/null || head -c 16 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

SRV_USER=$(getv MQTT_USER);         SRV_USER=${SRV_USER:-manipmasta-server}
SRV_PASS=$(getv MQTT_PASS)
DEV_USER=$(getv MQTT_DEVICE_USER);  DEV_USER=${DEV_USER:-manipmasta}
DEV_PASS=$(getv MQTT_DEVICE_PASS)
TOOLS_PASS=$(getv MQTT_TOOLS_PASS)

if [ -z "$SRV_PASS" ]; then SRV_PASS=$(rnd); setv MQTT_PASS "$SRV_PASS"; echo "Generata MQTT_PASS"; fi
if [ -z "$DEV_PASS" ]; then DEV_PASS=$(rnd); setv MQTT_DEVICE_PASS "$DEV_PASS"; echo "Generata MQTT_DEVICE_PASS"; fi

CONF_DIR="$(pwd)/mosquitto/config"
PASSWD="$CONF_DIR/passwd"
rm -f "$PASSWD"
touch "$PASSWD"
chmod 0600 "$PASSWD"

if command -v mosquitto_passwd >/dev/null 2>&1 && [ "${USE_DOCKER:-0}" != "1" ]; then
  mp() { mosquitto_passwd -b "$PASSWD" "$1" "$2"; }
else
  mp() { docker run --rm -v "$CONF_DIR:/mosquitto/config" eclipse-mosquitto:2 \
           mosquitto_passwd -b /mosquitto/config/passwd "$1" "$2"; }
fi

mp "$SRV_USER" "$SRV_PASS"
mp "$DEV_USER" "$DEV_PASS"
[ -n "$TOOLS_PASS" ] && mp manipmasta-tools "$TOOLS_PASS"

# Mosquitto nel container gira come uid 1883: file password leggibile solo da lui
if [ "$(id -u)" = "0" ]; then
  chown 1883:1883 "$PASSWD" "$CONF_DIR/acl"
  chown -R 1883:1883 mosquitto/data mosquitto/log
  chmod 0700 "$PASSWD"
  chmod 0700 "$CONF_DIR/acl"
else
  echo "Nota: eseguire come root (sudo) per impostare proprietario 1883 su passwd/acl/data/log."
fi

echo "Utenti MQTT creati in $PASSWD: $SRV_USER, $DEV_USER${TOOLS_PASS:+, manipmasta-tools}"
echo "Password Arduino da impostare via seriale:  SET mqtt_user $DEV_USER  /  SET mqtt_pass $DEV_PASS  /  SAVE"
echo "Riavvia il broker:  docker compose restart mosquitto"
