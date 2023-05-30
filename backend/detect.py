import numpy as np
import sys
from scenedetect.backends.opencv import VideoStream
from scenedetect import SceneManager
from scenedetect.detectors.adaptive_detector import AdaptiveDetector
from typing import Tuple, Optional, Union
from scenedetect.frame_timecode import FrameTimecode
from numpy import ndarray


frameRate = 30
width = 480
height = 270
num_channel = 3
num_pix_per_frame = width * height * num_channel


def readVideo(fn):
    imgs = np.fromfile(fn, dtype=np.ubyte).reshape(-1, height, width, num_channel)
    return imgs

videoFn = sys.argv[1]
videoMp4 = sys.argv[2]
imgs = readVideo(videoFn)


class MyVideo(VideoStream):
    def __init__(self, start=0, end=imgs.shape[0]):
        self._path = ""
        self.imgs = imgs
        self.start = start
        self.end = end
        self.pos = start

    @property
    def BACKEND_NAME(self) -> str:
        return "RGB"

    @property
    def name(self) -> Union[bytes, str]:
        return "rgb"

    @property
    def path(self) -> Union[bytes, str]:
        return self._path

    @property
    def is_seekable(self) -> bool:
        return True

    @property
    def frame_rate(self) -> float:
        return 30.0

    @property
    def duration(self) -> Optional[FrameTimecode]:
        return FrameTimecode(timecode=self.end, fps=self.frame_rate)

    @property
    def frame_size(self) -> Tuple[int, int]:
        return (width, height)

    @property
    def aspect_ratio(self) -> float:
        return 1

    @property
    def position(self) -> FrameTimecode:

        x = self.pos

        if self.pos > 0:
            x = self.pos - 1

        return FrameTimecode(timecode=x, fps=self.frame_rate)

    @property
    def position_ms(self) -> float:

        return self.pos * 1000 / self.frame_rate

    @property
    def frame_number(self) -> int:
        return self.pos

    def read(self, decode: bool = True, advance: bool = True) -> Union[ndarray, bool]:

        if self.pos >= self.duration.frame_num:
            return False

        img = self.imgs[self.pos]
        if advance:
            self.pos += 1
        return img

    def reset(self) -> None:
        self.pos = self.start

    def seek(self, target: Union[FrameTimecode, float, int]) -> None:
        self.pos = target


def detectScene():
    video = MyVideo()
    manager = SceneManager()
    manager.add_detector(AdaptiveDetector(adaptive_threshold=8, min_scene_len=300))
    manager.detect_scenes(video, show_progress=True)
    scene_list = manager.get_scene_list()
    file = open('scene.txt', 'w')
    for i, scene in enumerate(scene_list):
        print('Scene %2d: Start %s / Frame %4d, End %s / Frame %4d' % (
            i + 1,
            scene[0].get_timecode(), scene[0].get_frames(),
            scene[1].get_timecode(), scene[1].get_frames()))
        file.write(str(scene[0].get_frames())+" "+str(scene[1].get_frames())+"\n")
    file.close()

if __name__ == '__main__':
    import time
    t1 = time.time()
    # for scene detection
    detectScene()

    # # for shot detection
    import detect_shot
    detect_shot.main(videoMp4)

    # for sub-shot detection
    import transnetv2
    with open("shot.txt", "r") as input:
        file = open("subshot.txt","w")
        file.close()
        for line in input:
            param = line.strip().split(' ')
            start_frame = int(param[0])
            end_frame = int(param[1])
            if end_frame-start_frame<250:
                continue
            transnetv2.main(videoMp4, start_frame, end_frame)
    t2 = time.time()
    print(t2-t1)
