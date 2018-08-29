#!/usr/local/bin/python3

import ssl
import sys
import paho.mqtt.client as mqtt

# Script to test MQTT connections. 
#
# This script will run tests connecting to a "local" RabbitMQ node with the rabbitmq_web_mqtt plugin
# enabled and configured. It will also connect to test.mosquitto.org. For the encrypted tests using TLS,
# the CA Cert from the RabbitMQ instance and/or from test.mosquitto.org needs to be in the same directory
# as this script.
#
# This script requires python3 (download: https://www.python.org/downloads/) and the Eclipse MQTT Python
# client library, paho-mqtt (download and install with "pip3 install paho-mqtt").
# 
# My RabbitMQ instance includes the following configuration:
# 
##[
##  {rabbit, [
##     {ssl_listeners, [5671]},
##     {ssl_options, [{cacertfile, "/opt/pivotal/ssl/testca/cacert.pem"},
##                    {certfile,   "/opt/pivotal/ssl/server/cert.pem"},
##                    {keyfile,    "/opt/pivotal/ssl/server/key.pem"},
##                    {verify,     verify_peer},
##                    {fail_if_no_peer_cert,false}
##                   ]}
##   ]},
##   {rabbitmq_mqtt, [
##                    {ssl_listeners,    [8883]},
##                    {tcp_listeners,    [1883]}
##   ]},
##   {rabbitmq_web_mqtt,
##      [{tcp_config, [{port,       15675}]},
##       {ssl_config, [{port,       12345},
##                     {backlog,    1024},
##                     {certfile,   "/opt/pivotal/ssl/server/cert.pem"},
##                     {keyfile,    "/opt/pivotal/ssl/server/key.pem"},
##                     {cacertfile, "/opt/pivotal/ssl/testca/cacert.pem"},
##                     {verify,     verify_none},
##                     {fail_if_no_peer_cert,false}
##                    ]
##      }]
##   }
##].
#
# NOTE: The test.mosquitto.org MQTT over websockets, encrypted currently does not work due to its
# server cert being signed by a different CA Cert than that provided on the site.
#

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("$SYS/#")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

def on_log(client, obj, level, string):
    print(string)

def show_help():
    print("Usage: testmqtt [-ws] [-rmq] [-tls]")
    print("\t-ws:  If provided connect to MQTT over websocket, otherwise plain MQTT")
    print("\t-rmq: If provided connect to my RabbitMQ, otherwise connect to test.mosquitto.org")
    print("\t-tls: If provided connect using TLS")
    print("default: Connect to test.mosquitto.org, plain MQTT, with no TLS")     

ws  = False # Are we using a websocket? If false, this is a plain MQTT connection
rmq = False # Are we connecting to our RabbitMQ? If false, connect to the test server at mosquitto.org
tls = False # Should we use a tls connection? 

if len(sys.argv) > 1:
    for i in range(1,len(sys.argv)):
        if sys.argv[i] == "-ws":
            ws = True
        elif sys.argv[i] == "-rmq":
            rmq = True
        elif sys.argv[i] == "-tls":
            tls = True
        else:
            show_help()
            sys.exit()

# Create the client
if ws:
    client = mqtt.Client(transport="websockets")    # MQTT over websockets Connection
else:
    client = mqtt.Client()                          # MQTT Connection

# Set properties if using our RabbitMQ, else setup for mosquitto.org
cacert = ""
if rmq:
    host = "rmq37c"
    client.username_pw_set(username="phil", password="phil")
    if ws:
        if tls:
            port = 12345
            cacert = "cacert.pem"
        else:
            port = 15675
    else:
        if tls:
            port = 8883
            cacert = "cacert.pem"
        else:
            port = 1883
else:
    host = "test.mosquitto.org"
    if ws:
        if tls:
            port = 8081
            cacert = "mosquitto.org.crt"
        else:
            port = 8080
    else:
        if tls:
            port = 8883
            cacert = "mosquitto.org.crt"
        else:
            port = 1883

client.on_connect = on_connect
client.on_message = on_message
client.on_log     = on_log

# HTTP/1.1 Requires a Host header
headers = {
        "Host": "{0:s}".format(host)
}

if ws:
    client.ws_set_options(path="{}?{}".format("/ws", ""), headers=headers)

if tls:
    client.tls_set(ca_certs=cacert, certfile=None, keyfile=None, cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS, ciphers=None)

print(f'Connecting to {host} on port {port} with CA cert "{cacert}"')

client.connect(host, port, 60)

# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.
client.loop_forever()

