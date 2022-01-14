#!/usr/bin/python3

"""
    Mist_Tester

    Grab image from images
    Analyse fog values
    Write onto canvas

    BUGGY

    NEEDS CLEANUP! AS DIRECTORIES AND TELEPHONE NUMBERS ARE IN HERE
"""

from imutils import paths
import cv2
import mist_detector
from pydbus import SystemBus


# send message
bus = SystemBus()
signal = bus.get('org.asamk.Signal')


for i, image in enumerate(paths.list_images('afstellen_cam/')):
    brightness, stdev, blur = mist_detector.calculate_fog_values(image)

    img = cv2.imread(image)
    img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_CUBIC)

    img = cv2.rectangle(
        img,
        (mist_detector.ROI_X1, mist_detector.ROI_Y1),
        (mist_detector.ROI_X2, mist_detector.ROI_Y2),
        (255, 0, 0),
        1
    )

    cv2.putText(
        img,
        'Blur: {:.0f} Brightness: {:.0f}'.format(blur, brightness),
        (50, 150),
        cv2.FONT_HERSHEY_TRIPLEX,
        1,
        (0, 0, 255),
        2)

    cv2.imwrite('/var/www/html/img/{}.jpg'.format(i), img)

    signal.sendMessage("Biep biep dit is de mist miep",
                       ['/var/www/html/img/{}.jpg'.format(i)],
                       ['+316xxxxx'])
