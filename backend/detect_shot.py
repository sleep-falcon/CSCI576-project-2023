import cv2
import numpy
import math


def MSE(mat1, mat2):
    dim = mat1.shape
    pixels = dim[0] * dim[1]
    diff = mat1.astype(numpy.int64) - mat2.astype(numpy.int64)
    abs = numpy.abs(diff)
    return (numpy.sum(abs) / float(pixels))

def prepare_scores(cap):
    frameNum = 0
    scoreTotal = 0
    scoreList = []
    frames = []
    timeList = []
    while (True):
        ret, frame = cap.read()
        if frame is None:
            break
        frameNum += 1
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue, sat, lum = cv2.split(hsv)
        if frameNum == 1:
            prevHue, prevSat, prevLum = hue, sat, lum 
            frames.append(frame)
            continue
        delta_hue = MSE(hue, prevHue)
        delta_sat = MSE(sat, prevSat)
        delta_lum = MSE(lum, prevLum)
        score = (delta_hue + delta_sat + delta_lum) / 3
        scoreTotal += score
        scoreList.append(score)
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)/1000
        timeList.append(timestamp)
        frames.append(frame)
    avg = scoreTotal/(frameNum - 1)
    var = 0
    for i in range(frameNum - 1):
        var += (avg - scoreList[i]) * (avg - scoreList[i])
    sd = math.sqrt(var / (frameNum - 1))
    return sd, frames, timeList

def split_frames(sd, frames, start, end):
    cutList = []
    frameNum = start
    outputFrameCount = 0
    prevHue, prevSat, prevLum = None, None, None
    frameList = []
    cut = False
    for i in range(start, end):
        frame = frames[i]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hue, sat, lum = cv2.split(hsv)
        if frameNum == start:
            prevHue, prevSat, prevLum = hue, sat, lum
            frameNum += 1
            continue
        delta_hue = MSE(hue, prevHue)
        delta_sat = MSE(sat, prevSat)
        delta_lum = MSE(lum, prevLum)
        score = (delta_hue + delta_sat + delta_lum) / 3
        if (score > sd + 2.5 and cut == False):
            cut = True
            changeH, changeS, changeL = prevHue, prevSat, prevLum
            frameList.append([frame, score, frameNum])
        elif cut == True and len(frameList) < 15:
            delta_hue1 = MSE(hue, changeH)
            delta_sat1 = MSE(sat, changeS)
            delta_lum1 = MSE(lum, changeL)
            score1 = (delta_hue1 + delta_sat1 + delta_lum1) / 3
            frameList.append([frame, score1, frameNum])
        elif cut == True and len(frameList) == 15:
            maxFrame = None
            maxScore = -1
            maxFrameNum = -1
            totalScore = 0
            countFive = 0
            maxStamp = 0
            for arr in frameList:
                totalScore += arr[1]
                if arr[1] > maxScore:
                    maxScore = arr[1]
                    if (countFive < 5):
                        maxFrame = arr[0]
                        maxFrameNum = arr[2]
                        countFive += 1
            #cv2.imshow("Captured", maxFrame)
            cutList.append(maxFrameNum)
            outputFrameCount += 1
            cut = False
            changeH, changeS, changeL = None, None, None
            frameList = []
        frameNum += 1
        prevHue, prevSat, prevLum = hue, sat, lum
        #cv2.imshow("Frame", frame)
        #key = cv2.waitKey(1) & 0xFF
    return cutList

def frames_range(cuts, time_list, start_frame, end_frame):
    l = len(cuts)
    tuples = []
    time_arr = []
    count = 0
    prev_cut = 0
    if l == 0:
        tuples.append([start_frame, end_frame])
        time_arr.append(time_list[start_frame])
    if l == 1:
        cut = cuts[0]
        tuples.append([start_frame, cut - 1])
        tuples.append([cut, end_frame])
        time_arr.append(time_list[start_frame])
        time_arr.append(time_list[cut])
    else:
        for cut in cuts:
            count += 1
            if (prev_cut != 0 and cut - prev_cut < 30):
                if (count == l):
                    tuples.append([prev_cut, end_frame])
                    time_arr.append(time_list[prev_cut])
                continue
            if (count == 1):
                tuples.append([start_frame, cut - 1])
                time_arr.append(time_list[start_frame])
            elif (count == l):
                tuples.append([prev_cut, cut - 1])
                tuples.append([cut, end_frame])
                time_arr.append(time_list[prev_cut])
                time_arr.append(time_list[cut])
            else:
                tuples.append([prev_cut, cut - 1])
                time_arr.append(time_list[prev_cut])
            prev_cut = cut
    return tuples, time_arr

        

def main(path):
    cap = cv2.VideoCapture(path)
    sd, frames, time_list = prepare_scores(cap)
    output_list = []
    output_time = []
    with open("scene.txt", "r") as input:
        for line in input:
            param = line.strip().split(' ')
            start_frame = int(param[0])
            end_frame = int(param[1])
            arr = split_frames(sd, frames, start_frame, end_frame)
            tuples, time = frames_range(arr, time_list, start_frame, end_frame)
            output_list.append(tuples)
            output_time.append(time)
    input.close()
    with open("shot.txt", "w+") as f:
        for arr in output_list:
            for a in arr:
                f.write(str(a[0]) + " " + str(a[1]) + " ")
                f.write("\n")
    f.close()
