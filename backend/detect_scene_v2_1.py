import numpy
import numpy as np
import argparse
from PIL import Image
import colorsys

def mean_pixel(mat):
    num_pixels = 9 * 16
    sqr = mat.astype(numpy.int64)**2
    abs = numpy.abs(sqr)
    total = numpy.sum(abs)
    return total / float(num_pixels)

def prepare_scores(video_name):
    height = 270
    width = 480
    scale_height = 9
    scale_width = 16
    scale_factor = 30
    frames = []
    score_arr = []
    rawdata = open(video_name, "rb")
    imgdata = rawdata.read(height * width * 3)
    frame_num = -1

    while imgdata:
        img = Image.new("RGB", (scale_width, scale_height))
        num = 0 
        frame_num += 1
        value = []
        for j in range(0, scale_height):
            for i in range(0, scale_width):
                j_large = j * scale_factor
                i_large = i * scale_factor
                num = 3 * (j_large * width + i_large)
                r = imgdata[num] & 0xff
                num = num + 1
                g = imgdata[num] & 0xff
                num = num + 1
                b = imgdata[num] & 0xff
                num = num + 1
                (h, s, v) = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                h_val = int(h * 7)
                s_val = 1 if s > 0.65 else 0
                v_val = 1 if v > 0.7 else 0
                val = h_val * 2 * 2 + s_val * 2 + v_val
                value.append(val)
                img.putpixel((i, j), (r, g, b))
        frames.append(img)
        score_arr.append(value)
        imgdata = rawdata.read(height * width * 3)
    score_arr = np.array(score_arr)
    return frames, score_arr, frame_num

def split_frames(frames, score_arr, start, end):
    total = 0
    for i in range(start, end + 1):
        total += mean_pixel(score_arr[i])
    avg = total / (end - start + 1)
    return avg

def frames_range(cuts, start_frame, end_frame):
    l = len(cuts)
    res = []
    prev_cut = 0
    if l == 0:
        res.append([start_frame, end_frame])
    if l == 1:
        cut = cuts[0]
        res.append([start_frame, cut])
        res.append([cut, end_frame])
    else:
        for idx, cut in enumerate(cuts):
            if (idx == 0):
                res.append([start_frame, cut])
            elif (idx == l - 1):
                res.append([prev_cut, cut])
                res.append([cut, end_frame])
            else:
                res.append([prev_cut, cut])
            prev_cut = cut
    return res

def read_shots(frames, score_arr, filename):
    avg_list = []
    start_frames = []
    with open(filename, "r") as input:
        for line in input:
            param = line.strip().split(' ')
            start_frame = int(param[0])
            end_frame = int(param[1])
            avg = split_frames(frames, score_arr, start_frame, end_frame)
            avg_list.append(avg)
            start_frames.append(start_frame)
    input.close()
    return start_frames, avg_list

def find_max_diff(avg_list):
    max_diff = 0
    l = len(avg_list)
    for i in range(l):
        if (i != 0):
            diff = abs(avg_list[i] - avg_list[i - 1])
            if (max_diff < diff):
                max_diff = diff
    return max_diff

def find_avg_diff(avg_list):
    total = 0
    l = len(avg_list)
    for i in range(l):
        total += avg_list[i]
    return total / l
    
def group_scenes(avg_list, max_diff, threshold):
    prev_avg = 0
    res = []
    count = 0
    l = len(avg_list)
    for i in range(l):
        if (i != 0):
            diff = abs(avg_list[i] - prev_avg)
            if (diff > max_diff * threshold):
                res.append(i)
                prev_avg = avg_list[i]
                count = 1
            else:
                prev_avg = (prev_avg * count + avg_list[i]) / (count + 1)
                count += 1
        else:
            prev_avg = avg_list[i]
            count = 1
    return res

def get_scene_num(start_frames, break_index):
    selected_scenes = []
    for i in break_index:
        selected_scenes.append(start_frames[i])
    return selected_scenes

def output_scene(output_list):
    with open("scene.txt", "w+") as f:
        for tuple in output_list:
            f.write(str(tuple[0]) + " " + str(tuple[1]) + " ")
            f.write("\n")
    f.close()


def main(path):
    filename = "shot.txt"
    frames, score_arr, frame_num = prepare_scores(path)
    start_frames, avg_list = read_shots(frames, score_arr, filename)
    #max_diff =  find_max_diff(avg_list)
    avg_diff = find_avg_diff(avg_list)
    threshold = 1
    break_index = group_scenes(avg_list, avg_diff, threshold)
    #print(break_index)
    selected_scenes = get_scene_num(start_frames, break_index)
    output_list = frames_range(selected_scenes, 0, frame_num)
    output_scene(output_list)
