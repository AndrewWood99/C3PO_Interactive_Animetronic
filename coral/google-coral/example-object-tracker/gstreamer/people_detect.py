# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
A demo which runs object detection on camera frames using GStreamer.
It also provides support for Object Tracker.

Run default object detection:
python3 detect.py

Choose different camera and input encoding
python3 detect.py --videosrc /dev/video1 --videofmt jpeg

Choose an Object Tracker. Example : To run sort tracker
python3 detect.py --tracker sort

TEST_DATA=../all_models

Run coco model:
python3 detect.py \
  --model ${TEST_DATA}/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite \
  --labels ${TEST_DATA}/coco_labels.txt
"""
import argparse
import collections
import common
import gstreamer
import numpy as np
import os
import re
import svgwrite
import time
import serial
import pygame
import random
from mutagen.mp3 import MP3
from tracker import ObjectTracker

pygame.mixer.init()
pygame.mixer.music.set_volume(1)
pygame.mixer.music.load("Startup.mp3")
pygame.mixer.music.play()

played_sound_bits = []

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=0.1)
ser.reset_input_buffer()




Object = collections.namedtuple('Object', ['id', 'score', 'bbox'])


def load_labels(path):
    p = re.compile(r'\s*(\d+)(.+)')
    with open(path, 'r', encoding='utf-8') as f:
        lines = (p.match(line).groups() for line in f.readlines())
        return {int(num): text.strip() for num, text in lines}


def shadow_text(dwg, x, y, text, font_size=20):
    dwg.add(dwg.text(text, insert=(x+1, y+1), fill='black', font_size=font_size))
    dwg.add(dwg.text(text, insert=(x, y), fill='white', font_size=font_size))


def generate_svg(src_size, inference_size, inference_box, objs, labels, text_lines, trdata, trackerFlag):
    dwg = svgwrite.Drawing('', size=src_size)
    src_w, src_h = src_size
    inf_w, inf_h = inference_size
    box_x, box_y, box_w, box_h = inference_box
    scale_x, scale_y = src_w / box_w, src_h / box_h
    
    dwg.add(dwg.line(start=(0, 250), end=(src_w, 250),
                                 stroke='yellow', stroke_width='2'))
    dwg.add(dwg.line(start=(0, 400), end=(src_w, 400),
                                 stroke='blue', stroke_width='2'))

    for y, line in enumerate(text_lines, start=1):
        shadow_text(dwg, 10, y*20, line)
    if trackerFlag and (np.array(trdata)).size:
        for td in trdata:
            x0, y0, x1, y1, trackID = td[0].item(), td[1].item(
            ), td[2].item(), td[3].item(), td[4].item()
            overlap = 0
            for ob in objs:
                dx0, dy0, dx1, dy1 = ob.bbox.xmin.item(), ob.bbox.ymin.item(
                ), ob.bbox.xmax.item(), ob.bbox.ymax.item()
                area = (min(dx1, x1)-max(dx0, x0))*(min(dy1, y1)-max(dy0, y0))
                if (area > overlap):
                    overlap = area
                    obj = ob
            if obj.id == 0:
                # Relative coordinates.
                x, y, w, h = x0, y0, x1 - x0, y1 - y0
                # Absolute coordinates, input tensor space.
                x, y, w, h = int(x * inf_w), int(y *
                                                 inf_h), int(w * inf_w), int(h * inf_h)
                # Subtract boxing offset.
                x, y = x - box_x, y - box_y
                # Scale to source coordinate space.
                x, y, w, h = x * scale_x, y * scale_y, w * scale_x, h * scale_y
                percent = int(100 * obj.score)
                label = '{}% {} ID:{}'.format(
                    percent, labels.get(obj.id, obj.id), int(trackID))
                shadow_text(dwg, x, y - 5, label)
                dwg.add(dwg.rect(insert=(x, y), size=(w, h),
                                fill='none', stroke='red', stroke_width='2'))
                dwg.add(dwg.line(start=(x + w/2, y), end=(x + w/2, y + h),
                                 stroke='red', stroke_width='2'))
                
                                 
                
                
                
                #Send Message to Arduino
                message = "ID: {} Position: {} Base: {}\n".format(str(int(trackID)).zfill(10), str(int(x + w/2)).zfill(4), str(int(y + h)).zfill(4))
                ser.write(bytes(message, 'utf-8'))
                
                
                
    else:
        for obj in objs:
            if obj.id == 0:
                x0, y0, x1, y1 = list(obj.bbox)
                # Relative coordinates.
                x, y, w, h = x0, y0, x1 - x0, y1 - y0
                # Absolute coordinates, input tensor space.
                x, y, w, h = int(x * inf_w), int(y *
                                                 inf_h), int(w * inf_w), int(h * inf_h)
                # Subtract boxing offset.
                x, y = x - box_x, y - box_y
                # Scale to source coordinate space.
                x, y, w, h = x * scale_x, y * scale_y, w * scale_x, h * scale_y
                percent = int(100 * obj.score)
                label = '{}% {}'.format(percent, labels.get(obj.id, obj.id))
                shadow_text(dwg, x, y - 5, label)
                dwg.add(dwg.rect(insert=(x, y), size=(w, h),
                                 fill='none', stroke='red', stroke_width='2'))
    return dwg.tostring()


class BBox(collections.namedtuple('BBox', ['xmin', 'ymin', 'xmax', 'ymax'])):
    """Bounding box.
    Represents a rectangle which sides are either vertical or horizontal, parallel
    to the x or y axis.
    """
    __slots__ = ()


def get_output(interpreter, score_threshold, top_k, image_scale=1.0):
    """Returns list of detected objects."""
    boxes = common.output_tensor(interpreter, 0)
    category_ids = common.output_tensor(interpreter, 1)
    scores = common.output_tensor(interpreter, 2)

    def make(i):
        ymin, xmin, ymax, xmax = boxes[i]
        return Object(
            id=int(category_ids[i]),
            score=scores[i],
            bbox=BBox(xmin=np.maximum(0.0, xmin),
                      ymin=np.maximum(0.0, ymin),
                      xmax=np.minimum(1.0, xmax),
                      ymax=np.minimum(1.0, ymax)))
    return [make(i) for i in range(top_k) if scores[i] >= score_threshold]


def main():
    
    
    time.sleep(0.01)
    
    default_model_dir = '../models'
    default_model = 'mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite'
    default_labels = 'coco_labels.txt'
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='.tflite model path',
                        default=os.path.join(default_model_dir, default_model))
    parser.add_argument('--labels', help='label file path',
                        default=os.path.join(default_model_dir, default_labels))
    parser.add_argument('--top_k', type=int, default=3,
                        help='number of categories with highest score to display')
    parser.add_argument('--threshold', type=float, default=0.1,
                        help='classifier score threshold')
    parser.add_argument('--videosrc', help='Which video source to use. ',
                        default='/dev/video0')
    parser.add_argument('--videofmt', help='Input video format.',
                        default='raw',
                        choices=['raw', 'h264', 'jpeg'])
    parser.add_argument('--tracker', help='Name of the Object Tracker To be used.',
                        default=None,
                        choices=[None, 'sort'])
    args = parser.parse_args()

    print('Loading {} with {} labels.'.format(args.model, args.labels))
    interpreter = common.make_interpreter(args.model)
    interpreter.allocate_tensors()
    labels = load_labels(args.labels)

    w, h, _ = common.input_image_size(interpreter)
    inference_size = (w, h)
    # Average fps over last 30 frames.
    fps_counter = common.avg_fps_counter(30)
    
    


    def user_callback(input_tensor, src_size, inference_box, mot_tracker):
        
        global played_sound_bits
        
        line = ser.readline().decode('utf-8').rstrip()
        if line != "":
            print(line)
        if line[0:9] == "Greet ONE":
            played_sound_bits = []
            sound_bit = random.choice(os.listdir("Greet_ONE"))
            pygame.mixer.music.load("Greet_ONE/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Greet_ONE/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:15] == "Call out to ONE":
            sound_bit = random.choice(os.listdir("Call_out_to_ONE"))
            pygame.mixer.music.load("Call_out_to_ONE/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Call_out_to_ONE/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:8] == "Continue":
            sound_bit = random.choice(os.listdir("Conversation_ONE"))
            checks = 0
            while sound_bit in played_sound_bits:
                sound_bit = random.choice(os.listdir("Conversation_ONE"))
                checks = checks + 1
                if checks > 100:
                    break
            played_sound_bits.append(sound_bit)
            pygame.mixer.music.load("Conversation_ONE/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Conversation_ONE/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:27] == "Call out to many to join ME":
            sound_bit = random.choice(os.listdir("Call_out_to_Many_ME"))
            pygame.mixer.music.load("Call_out_to_Many_ME/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Call_out_to_Many_ME/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:27] == "Call out to many to join us":
            sound_bit = random.choice(os.listdir("Call_out_to_Many_US"))
            pygame.mixer.music.load("Call_out_to_Many_US/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Call_out_to_Many_US/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:6] == "Its Ok":
            sound_bit = random.choice(os.listdir("Come_Closer_ONE"))
            pygame.mixer.music.load("Come_Closer_ONE/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Come_Closer_ONE/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:18] == "Converse with Many":
            sound_bit = random.choice(os.listdir("Conversation_MANY"))
            checks = 0
            while sound_bit in played_sound_bits:
                sound_bit = random.choice(os.listdir("Conversation_MANY"))
                checks = checks + 1
                if checks > 100:
                    break
            played_sound_bits.append(sound_bit)
            pygame.mixer.music.load("Conversation_MANY/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Conversation_MANY/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:10] == "Greet this":
            played_sound_bits = []
            sound_bit = random.choice(os.listdir("Greet_MANY"))
            pygame.mixer.music.load("Greet_MANY/" + sound_bit)
            pygame.mixer.music.play()
            message = "length: {}\n".format(MP3("Greet_MANY/" + sound_bit).info.length)
            ser.write(bytes(message, 'utf-8'))
        if line[0:16] == "Is anyone there?":
            #sound_bit = random.choice(os.listdir("IDLE"))
            #pygame.mixer.music.load("IDLE/" + sound_bit)
            #pygame.mixer.music.play()
            #message = "length: {}\n".format(MP3("IDLE/" + sound_bit).info.length)
            message = "length: 0\n"
            ser.write(bytes(message, 'utf-8'))
        
        
        
        
        nonlocal fps_counter
        start_time = time.monotonic()
        common.set_input(interpreter, input_tensor)
        interpreter.invoke()
        # For larger input image sizes, use the edgetpu.classification.engine for better performance
        objs = get_output(interpreter, args.threshold, args.top_k)
        end_time = time.monotonic()
        detections = []  # np.array([])
        for n in range(0, len(objs)):
            element = []  # np.array([])
            element.append(objs[n].bbox.xmin)
            element.append(objs[n].bbox.ymin)
            element.append(objs[n].bbox.xmax)
            element.append(objs[n].bbox.ymax)
            element.append(objs[n].score)  # print('element= ',element)
            detections.append(element)  # print('dets: ',dets)
        # convert to numpy array #      print('npdets: ',dets)
        detections = np.array(detections)
        trdata = []
        trackerFlag = False
        if detections.any():
            if mot_tracker != None:
                trdata = mot_tracker.update(detections)
                trackerFlag = True
            text_lines = [
                'Inference: {:.2f} ms'.format((end_time - start_time) * 1000),
                'FPS: {} fps'.format(round(next(fps_counter))), ]
        if len(objs) != 0:
            return generate_svg(src_size, inference_size, inference_box, objs, labels, text_lines, trdata, trackerFlag)

    result = gstreamer.run_pipeline(user_callback,
                                    src_size=(640, 480),
                                    appsink_size=inference_size,
                                    trackerName=args.tracker,
                                    videosrc=args.videosrc,
                                    videofmt=args.videofmt)
    
    


if __name__ == '__main__':
    main()
