import cv2
import pytesseract
import pandas as pd
import numpy as np
import argparse
import time
from datetime import datetime
from datetime import date
import os
import glob
import re

print("main program starting..")


def order_points(pts):
    # Step 1: Find centre of object
    center = np.mean(pts)

    # Step 2: Move coordinate system to centre of object
    shifted = pts - center

    # Step #3: Find angles subtended from centroid to each corner point
    theta = np.arctan2(shifted[:, 0], shifted[:, 1])

    # Step #4: Return vertices ordered by theta
    ind = np.argsort(theta)
    return pts[ind]


def getContours(img, orig):  # Change - pass the original image too
    biggest = np.array([])
    maxArea = 0
    imgContour = orig.copy()  # Make a copy of the original image to return
    contours, hierarchy = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    index = None
    for i, cnt in enumerate(contours):  # Change - also provide index
        area = cv2.contourArea(cnt)
        if (area > 5000.0) & (area < 20000.0):
            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt,0.02*peri, True)
            if area > maxArea and len(approx) == 4:
                biggest = approx
                maxArea = area
                index = i  # Also save index to contour

    warped = None  # Stores the warped license plate image
    if index is not None: # Draw the biggest contour on the image
        cv2.drawContours(imgContour, contours, index, (255, 0, 0), 3)

        src = np.squeeze(biggest).astype(np.float32) # Source points
        height = 160 #image.shape[0]
        width = 360 #image.shape[1]
        # Destination points
        dst = np.float32([[0, 0], [0, height - 1], [width - 1, 0], [width - 1, height - 1]])

        # Order the points correctly
        biggest = order_points(src)
        dst = order_points(dst)

        # Get the perspective transform
        M = cv2.getPerspectiveTransform(src, dst)

        # Warp the image
        img_shape = (width, height)
        warped = cv2.warpPerspective(orig, M, (img_shape), flags=cv2.INTER_LINEAR)

    return biggest, imgContour, warped  # Change - also return drawn image


def process(image):
    kernel = np.ones((3,3))
    imgGray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    imgBlur = cv2.GaussianBlur(imgGray,(5,5),1)
    imgCanny = cv2.Canny(imgBlur,150,200)
    imgDial = cv2.dilate(imgCanny,kernel,iterations=2)
    imgThres = cv2.erode(imgDial,kernel,iterations=2)
    biggest, imgContour, warped = getContours(imgThres, image)  # Change

    return biggest, imgContour, warped

def video_processor(vid_capture, df):
    frame_rate = 30

    #initialize state variables
    prev = 0
    frame_no = 0
    state = 1 #initial state, no car visible
    text = ''
    direction = ''

    while vid_capture.isOpened():
        time_elapsed = time.time() - prev
        # Capture each frame of webcam video
        ret, image = vid_capture.read()

        if time_elapsed > 1.0 / frame_rate:
            prev = time.time()

            corners, contour, warped = process(image)

            #cv2.imshow("contour", contour)

            # if warped image is not null
            if (type(warped) != type(None)):
                print(f'upperleft corner: {corners[0]}')
                cv2.imshow("warped original", warped)

                # convert the image to txt using pytesseract
                config = "-l eng --oem 1 --psm 7"
                text = pytesseract.image_to_string(warped, config=config)
                print(f'detected text:{text}, length:{len(text)}')
                text = pattern.sub('', text) #keep alphanumeric characters only

            print(f"frame #{frame_no}")


            #implement state machine here:
            if state==1: #no car plate visible
                #check string length
                if (len(text)>= 6):
                    frame_begin = frame_no #save the frame number
                    corner_x = corners[0][0] #save the x coordinate of the upper left corner
                    print(f'plate found at frame#{frame_no}')
                    plate_no = text #save text as plate number
                    text = '' #reset text variable
                    state = 2 #move to state 2

            elif state==2: 
                if (len(text)>= 6):
                    frame_begin = frame_no
                    print(f'corners: {corners}')
                    if len(corners) > 0:
                        delta_x = corners[0][0] - corner_x

                    if delta_x > 0:
                        direction = 'EXITING'
                        print('moving left to right')
                    else:
                        direction = 'ENTERING'
                        print('moving right to left')

                    #check if car is resident or visitor
                    if len(rdf[rdf.Plate == plate_no])==0:
                        car_type = 'VISITOR'
                    else:
                        car_type = 'RESIDENT'

                frame_elapsed = frame_no - frame_begin
                text = ''
                if frame_elapsed > 10:
                    #append this car to the dataframe
                    df = df.append({'DateTime':datetime.now(), 'Plate':plate_no, 'Direction':direction, 'Type': car_type,'Source': source}, ignore_index=True)
                    #next state = 1
                    state = 1


            frame_no += 1    
            print(f'state={state}')

        # output.write(frame)
        # Close and break the loop after pressing "ESC" key
        if cv2.waitKey(1) == 27:
            break

        if source != "webcam":
            if vid_capture.get(cv2.CAP_PROP_POS_FRAMES) == vid_capture.get(cv2.CAP_PROP_FRAME_COUNT) :
                # If the number of captured frames is equal to the total number of frames,
                # we stop
                break

    # close the already opened camera
    vid_capture.release()
    # close the already opened file
    # output.release()
    # close the window and de-allocate any associated memory usage
    cv2.destroyAllWindows()
    return df


#PROGRAM START HERE
ap = argparse.ArgumentParser()
ap.add_argument(
    "-v",
    "--videofolder",
    type=str,
    default="",
    help="video folder to load from",
)
args = vars(ap.parse_args())

#Load residents' plate list
rdf = pd.read_excel('residents.xlsx')

#initialize data frame to store detected plates
df = pd.DataFrame(columns=['DateTime', 'Plate', 'Direction', 'Type', 'Source',])
#Regular expression for stripping out non-alphanumeric characters
pattern = re.compile('[\W_]+')


if args["videofolder"] == "":
    # Capture video from webcam
    vid_cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    vid_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    vid_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    source = 'webcam'
    video_processor(vid_cap)
else:
    all_files = glob.glob(os.path.join(f'{args["videofolder"]}/*.mp4'))
    for filename in all_files:
        print(filename)

        # Create a VideoCapture object and read from input file
        # If the input is the camera, pass 0 instead of the video file name
        vid_cap = cv2.VideoCapture(filename)
        source = os.path.basename(filename)
        # Check if camera opened successfully
        if vid_cap.isOpened() == False:
            print(f'Error opening {filename}')
            continue
        
        #process the opened video file
        df = video_processor(vid_cap, df)



today = str.replace(f'data-{datetime.now()}',':', '_')

df.to_excel(f'{today}.xlsx')