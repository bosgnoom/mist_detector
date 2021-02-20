#!/usr/bin/python3

"""
    mist_bot

    Very basic bot:
    - wait for Signal message
    - change setting in config.ini based on input

"""

import logging
import configparser
from pydbus import SystemBus
from gi.repository import GLib
import signal


# Logging
LOGLEVEL = logging.DEBUG
#LOGLEVEL = logging.CRITICAL
logging.basicConfig(level=LOGLEVEL)


# Import constants from configfile
config = configparser.ConfigParser()
config.read('/home/pi/mist_detector/config.ini')
IMAGE = config['DEFAULT']['image']
OUTPUT = config['DEFAULT']['output']
ROI_X1 = int(config['DEFAULT']['roi_x1'])
ROI_Y1 = int(config['DEFAULT']['roi_y1'])
ROI_X2 = int(config['DEFAULT']['roi_x2'])
ROI_Y2 = int(config['DEFAULT']['roi_y2'])


# Function to handle control+C
def sigint_handler(sig, frame):
    if sig == signal.SIGINT:
        logging.debug("Exiting")
        loop.quit()
    else:
        raise ValueError("Undefined handler for '{}'".format(sig))


# Function which is called when a message is received
def msgRcv(timestamp, source, groupID, message, attachments):
    """
        Process message
    """
    logging.debug("{} Message: {}:{}:".format(timestamp, source, message))

    if message.upper() == "HELP":
        msg = "SET B xx \nSET T xx"
        global signal_bus
        signal_bus.sendMessage(msg, [], ['+31615511544'])


logging.info("Starting mist_bot")
loop = GLib.MainLoop()

signal.signal(signal.SIGINT, sigint_handler)

bus = SystemBus()
signal_bus = bus.get('org.asamk.Signal')
signal_bus.onMessageReceived = msgRcv
#signal_bus.sendMessage("Miep miep hier is de mist miep", [], ['+31615511544'])

logging.debug("Going into loop...")
loop.run()
