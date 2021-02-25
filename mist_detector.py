#!/usr/bin/python3

"""
    Mist_Meter
    Detects whether it is foggy or not, based on webcam images
    Copyright (C) 2021 Paul Schouten aka bosgnoom

    Grab image from webcam,
    run analysis:
    1. Brightness: detect day/night
    2. Variation in image: detect mist 

    Brightness:
    - Calculate averaged brightness of ROI
    - Above threshold: DAY, proceed
    - Below threshold: NIGHT, stop

    Variation:
    - Calculate Laplacian variation of ROI
    - Above threshold: SHARP image: no fog
    - Below threshold: BLURRED image: foggy

    Inputs:
    - Threshold values (BRIGHTNESS and VARIATION)
    - (via Signal messaging service?)

    Outputs:
    - Message to user (via Signal?)
    - Both brightness and variation to INFLUX db, to follow values, to set threshold values

    2021-02-02: 
    - Start of program

    2021-02-13:
    - Integration with signal: push image when fog is detected
    - Integration with google sheet: push values to remote database

    2021-02-20:
    - All settings into config.ini
    - Remove identities and passwords from this file
    - Push to github
    
"""

import logging
import cv2
from influxdb import InfluxDBClient
import configparser
import requests
import time
from pydbus import SystemBus
import argparse
import csv
from sklearn import svm


# Logging, normal logging is CRITICAL
LOGLEVEL = logging.CRITICAL
logging.basicConfig(level=LOGLEVEL)
logging.debug('OpenCV version: {}'.format(cv2.__version__))

# Import constants from configfile
config = configparser.ConfigParser()
config.read('/home/pi/mist_detector/config.ini')

IMAGE = config['IMAGE']['image']
OUTPUT = config['IMAGE']['output']
FOGFOLDER = config['IMAGE']['fogfolder']

ROI_X1 = int(config['IMAGE']['roi_x1'])
ROI_Y1 = int(config['IMAGE']['roi_y1'])
ROI_X2 = int(config['IMAGE']['roi_x2'])
ROI_Y2 = int(config['IMAGE']['roi_y2'])

THRESH_BLUR = int(config['THRESHOLD']['blur'])
THRESH_BRIGHT = int(config['THRESHOLD']['brightness'])

GOOGLE_SHEET_URL = config['GOOGLE']['url']

INFLUX_HOST = config['INFLUX']['host']
INFLUX_PORT = int(config['INFLUX']['port'])
INFLUX_USER = config['INFLUX']['user']
INFLUX_PASS = config['INFLUX']['password']

SIGNAL_USERS = config.items('SIGNAL')


def calculate_fog_values(file_name):
    logging.debug('Getting image: {}'.format(file_name))
    image = cv2.imread(file_name)
    logging.debug('Image size: {}'.format(image.shape))

    logging.debug('Checking image size, resize needed?')
    if image.shape != (720, 1280, 3):
        logging.debug('Resizing image')
        image = cv2.resize(image, (1280, 720), interpolation=cv2.INTER_CUBIC)

    logging.debug('Selecting ROI')
    roi = image[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]
    logging.debug('ROI size: {}'.format(roi.shape))
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(OUTPUT, gray)

    logging.debug('Calculating ROI image properties')
    brightness, stdev = cv2.meanStdDev(gray)
    logging.debug('Brightness: {}'.format(brightness))
    logging.debug('Stdev: {}'.format(stdev))

    blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    logging.debug('Blur value: {}'.format(blur))

    # Flatten and return values of brightness, stdev and blur
    return (brightness[0][0], stdev[0][0], blur)


def output_to_influx(brightness, stdev, blur, mist, prob):
    # Push to local influxdb. User credentials from config.ini
    client = InfluxDBClient(host=INFLUX_HOST, port=INFLUX_PORT,
                            username=INFLUX_USER, password=INFLUX_PASS)
    client.switch_database('mist_meter')

    data = ["{} brightness={},stdev={},blur={},mist={},probability={}".format(
        "Aeneas",
        brightness,
        stdev,
        blur,
        mist,
        prob)]

    client.write_points(data, database="mist_meter", protocol="line")


def output_to_google_sheets(brightness, blur, mist, probability):
    # Push data to google sheet
    data = {'action': 'mistmeter',
            'blur': blur,
            'brightness': brightness,
            'timestamp': int(time.time()),
            'mist': mist,
            'probability': probability}

    req = requests.post(GOOGLE_SHEET_URL, data=data)

    logging.debug(req.text)

    if req.json()["result"] == "success":
        logging.debug("Request to Google sheet OK")
    else:
        logging.critical("Request to google failed: {}".format(req.text))


def test_threshold(blur, bright):
    # Check for threshold values

    # If brightness > lower limit (outside is light enough) and
    #    blur < upper limit       (low blur = low variation = mist)
    # adapt image,
    # send to receivers
    if (bright >= THRESH_BRIGHT) and (blur <= THRESH_BLUR):
        process_mist_image('Threshold')


def test_svm(blur, brightness):
    # SVM for fog detection, instead of threshold values

    logging.debug('Load known values')
    with open('/home/pi/mist_detector/calibration.csv') as csvfile:
        csvreader = csv.DictReader(csvfile)
        X = []
        Y = []
        for row in csvreader:
            X.append([row['blur'], row['brightness']])
            Y.append(row['mist'])

    logging.debug('Apply SVM')
    clf = svm.SVC(
        kernel='linear',
        gamma='scale',
        probability=True
    )

    logging.debug('Fitting known blur and brightness values into model')
    clf.fit(X, Y)
    mist = clf.predict([[blur, brightness]])[0]
    prob = clf.predict_proba([[blur, brightness]])[0][0]

    logging.debug('Model result: {}'.format(mist))
    logging.debug('Probability: {}'.format(prob))

    logging.debug('Check if probability is OK')
    if (prob < 0.3) or (mist == 1):
        # Probability is too low, send message to user, to alert doubtful result
        if mist == 1:
            process_mist_image('SVM voorspelt mist met waarschijnlijkheid {}...'.format(
                prob), blur, brightness)
        else:
            process_mist_image('SVM voorspelt geen mist met waarschijnlijkheid {}...'.format(
                prob), blur, brightness)

    return mist, prob


def process_mist_image(message, blur, bright):
    # Process image:
    # - Resize if needed,
    # - Draw rectangle around ROI
    # - Embed blur and brightness values
    # Push to signal messaging app

    # Values match foggy situation
    logging.debug("Image matches threshold values, processing image...")

    # Load image
    logging.debug('Loading image: {}'.format(IMAGE))
    image = cv2.imread(IMAGE)

    # Resize to desired value
    logging.debug('Image size: {}'.format(image.shape))
    if image.shape != (720, 1280, 3):
        logging.debug('Resizing image')
        image = cv2.resize(image, (1280, 720),
                           interpolation=cv2.INTER_CUBIC)

    # Draw rectangle around ROI
    image = cv2.rectangle(
        image,
        (ROI_X1, ROI_Y1),
        (ROI_X2, ROI_Y2),
        (255, 0, 0),
        1
    )

    # Embed fog values in image
    cv2.putText(
        image,
        'Blur: {:.0f} Brightness: {:.0f}'.format(blur, bright),
        (50, 150),
        cv2.FONT_HERSHEY_PLAIN,
        2,
        (250, 0, 0),
        2)

    # Save file with fog values
    filename = '{}/{}.png'.format(FOGFOLDER,
                                  time.strftime('%Y-%m-%d_%H%M'))
    logging.debug("Writing to {}".format(filename))
    cv2.imwrite(filename, image)

    # Connect to Signal service via systembus
    # Send image to receivers
    logging.debug("Sending image to receiver")
    bus = SystemBus()
    signal = bus.get('org.asamk.Signal')

    send_list = []
    for name, number in SIGNAL_USERS:
        logging.debug('Adding {} with number {}'.format(name, number))
        send_list.append(number)

    signal.sendMessage(message,
                       [filename],
                       send_list)


def mist_detect():
    brightness, stdev, blur = calculate_fog_values(IMAGE)

    test_threshold(blur, brightness)
    mist, prob = test_svm(blur, brightness)

    output_to_influx(brightness, stdev, blur, mist, prob)
    output_to_google_sheets(brightness, blur, mist, prob)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Calculate fog values from image')
    parser.add_argument('-v', dest='verbose', action='store_true')

    args = parser.parse_args()

    if args.verbose:
        # Verbose means logging.DEBUG here
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

    mist_detect()
