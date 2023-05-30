import argparse
import sys
import tempfile
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip, AudioFileClip
from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtWidgets import *
from PyQt5.QtMultimediaWidgets import QVideoWidget
from backend import transnetv2, detect_shot_v2_1, detect_scene_v2_1


def get_scenes_shots_subshots(rgb_filepath, mp4_filepath):
    # saves results as scene.txt, shot.txt, subshot.txt

    # # for shot detection
    detect_shot_v2_1.main(mp4_filepath)

    # for scene detection
    detect_scene_v2_1.main(rgb_filepath)

    # for sub-shot detection
    with open("shot.txt", "r") as input:
        file = open("subshot.txt", "w")
        file.close()
        for line in input:
            param = line.strip().split(' ')
            start_frame = int(param[0])
            end_frame = int(param[1])
            if end_frame - start_frame < 250:
                continue
            transnetv2.main(mp4_filepath, start_frame, end_frame)


def convert_txts_to_timestamps(fps=30):
    scenes = []

    scenes_np = np.loadtxt('scene.txt').astype(np.int)
    shots_np = np.loadtxt('shot.txt').astype(np.int)
    subshots_np = np.loadtxt('subshot.txt').astype(np.int)
    for scene in scenes_np:
        start_scene, end_scene = scene
        new_scene_list = []
        for shot in shots_np:
            start_shot, end_shot = shot
            if start_shot >= start_scene and end_shot <= end_scene:
                timestamp_ms = round((start_shot / fps) * 1000.)
                new_shot_list = [timestamp_ms]
                for subshot in subshots_np:
                    start_subshot, end_subshot = subshot
                    if start_subshot >= start_shot and end_subshot <= end_shot:
                        timestamp_ms = round((start_subshot / fps) * 1000.)
                        new_shot_list.append(timestamp_ms)
                new_scene_list.append(new_shot_list)
        scenes.append(new_scene_list)
    return scenes


# helper utility function for constructing an .mp4 file from .rgb and .wav files
def write_video(rgb_filepath, audio_filepath, width, height, mp4_filepath=None):
    frames = []

    if mp4_filepath is None:
        mp4_filepath = rgb_filepath.replace('.rgb', '.mp4')

    with open(rgb_filepath, "rb") as f:
        video_data = f.read(height * width * 3)
        while (video_data):
            frame = np.frombuffer(video_data, dtype=np.uint8).reshape(height, width, 3)
            frames.append(frame)
            video_data = f.read(height * width * 3)

    clip = ImageSequenceClip(frames, fps=30)

    audio_file = AudioFileClip(audio_filepath)

    final_clip = clip.set_audio(audio_file)

    final_clip.write_videofile(mp4_filepath, codec="libx264")

    return mp4_filepath


# this class specifically for shot and subshot label in table of contents
# designed such that when they are clicked, the label can be easily identified
class ToCLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        QLabel.mousePressEvent(self, event)


# main class for the UI interface
class VideoPlayer(QMainWindow):
    def __init__(self, mp4_filepath, scenes):
        super().__init__()
        self.setWindowTitle('Video Player')
        window_width = 720
        window_height = 540
        video_width = 480
        video_height = 270

        self.setGeometry(0, 0, window_width, window_height)

        # create video widget
        video_widget = QVideoWidget()
        video_widget.setMaximumSize(video_width, video_height)
        video_widget.setMinimumSize(video_width, video_height)

        # create media player
        self.media_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        media_content = QMediaContent(QUrl.fromLocalFile(mp4_filepath))
        self.media_player.setMedia(media_content)
        self.media_player.positionChanged.connect(self.video_updated_func)
        self.media_player.setVideoOutput(video_widget)

        # every 200 ms, check position of video
        # do not set value too low, may collide with clicking label click event check
        # if it still collides, then raise interval value
        self.media_player.setNotifyInterval(200)

        # create play pause stop buttons
        self.play_button = QPushButton('Play')
        self.play_button.clicked.connect(self.play_button_func)
        self.play_button.setCheckable(True)
        self.play_button.setChecked(True)
        self.pause_button = QPushButton('Pause')
        self.pause_button.clicked.connect(self.pause_button_func)
        self.pause_button.setCheckable(True)
        self.pause_button.setChecked(False)
        self.stop_button = QPushButton('Stop')
        self.stop_button.clicked.connect(self.stop_button_func)
        self.stop_button.setCheckable(True)
        self.stop_button.setChecked(False)

        # set up horizontal button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)

        # set up vertical layout for video widget and buttons layout
        vid_and_buttons_layout = QVBoxLayout()
        vid_and_buttons_layout.addWidget(video_widget)
        vid_and_buttons_layout.addLayout(button_layout)

        # set up table of contents layout
        self.toc_layout = QGridLayout()
        self.toc_layout.setHorizontalSpacing((window_width - video_width) // 6)  # just an arbitrary number

        # each list in scenes is a scene.
        # within each list are more lists, each of those a shot.
        # within those lists, are timestamps in ms of when the subshot begins (examples for now)
        # labels are shown for subshots only if there is more than 1 subshot for any given shot
        self.rowcol_to_timestamp = dict()

        num_labels_gen = 0
        for scene_idx, scene in enumerate(scenes):
            label = QLabel("Scene {}".format(scene_idx + 1))
            label.setStyleSheet("color: black")
            self.toc_layout.addWidget(label, num_labels_gen, 0, Qt.Alignment())
            num_labels_gen += 1

            for shot_idx, shot in enumerate(scene):
                label = ToCLabel("Shot {}".format(shot_idx + 1))
                label.setStyleSheet("color: black")
                label.setCursor(Qt.PointingHandCursor)
                label.clicked.connect(self.label_click_func)
                self.toc_layout.addWidget(label, num_labels_gen, 1, Qt.Alignment())
                self.rowcol_to_timestamp[(num_labels_gen, 1)] = shot[0]
                num_labels_gen += 1

                if len(shot) > 1:
                    for subshot_idx, subshot in enumerate(shot):
                        label = ToCLabel("Subshot {}".format(subshot_idx + 1))
                        label.setStyleSheet("color: black")
                        label.setCursor(Qt.PointingHandCursor)
                        label.clicked.connect(self.label_click_func)
                        self.toc_layout.addWidget(label, num_labels_gen, 2, Qt.Alignment())
                        self.rowcol_to_timestamp[(num_labels_gen, 2)] = subshot
                        num_labels_gen += 1

        # starting on scene1,shot1
        self.curr_shot = self.toc_layout.itemAtPosition(1, 1).widget()
        self.curr_shot.setStyleSheet("color: red")

        # set layout of table of contents widget
        toc_widget = QWidget()
        toc_widget.setLayout(self.toc_layout)

        # create scrollbar widget for table of contents widget
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(window_height)
        scroll.setFixedWidth(window_width - video_width)
        scroll.setWidget(toc_widget)

        # set up central widget layout
        master_layout = QHBoxLayout()
        master_layout.addWidget(scroll)
        master_layout.addLayout(vid_and_buttons_layout)

        # set the layout of the central widget
        main_widget = QWidget()
        main_widget.setLayout(master_layout)
        self.setCentralWidget(main_widget)

        self.media_player.play()

    def video_updated_func(self, position):
        curr_shot_idx = self.toc_layout.indexOf(self.curr_shot)
        if curr_shot_idx == self.toc_layout.count() - 1:
            return
        row, col, _, _ = self.toc_layout.getItemPosition(curr_shot_idx + 1)
        if col == 0:  # scene label, so skip
            row, col, _, _ = self.toc_layout.getItemPosition(curr_shot_idx + 2)
        timestamp_ms = self.rowcol_to_timestamp[(row, col)]
        if position > timestamp_ms:
            self.curr_shot.setStyleSheet("color: black")
            next_shot_label = self.toc_layout.itemAtPosition(row, col).widget()
            next_shot_label.setStyleSheet("color: red")
            self.curr_shot = next_shot_label

    def play_button_func(self):
        # if button pressed at the end of .mp4 video, then pyqt restarts the video
        if self.media_player.mediaStatus() == QMediaPlayer.EndOfMedia:
            self.curr_shot.setStyleSheet("color: black")
            self.curr_shot = self.toc_layout.itemAtPosition(1, 1).widget()
            self.curr_shot.setStyleSheet("color: red")
        self.media_player.play()
        self.stop_button.setChecked(False)
        self.play_button.setChecked(True)
        self.pause_button.setChecked(False)

    def pause_button_func(self):
        # if button pressed at the end of .mp4 video, then pyqt restarts the video
        if self.media_player.mediaStatus() == QMediaPlayer.EndOfMedia:
            self.curr_shot.setStyleSheet("color: black")
            self.curr_shot = self.toc_layout.itemAtPosition(1, 1).widget()
            self.curr_shot.setStyleSheet("color: red")
        self.media_player.pause()
        self.stop_button.setChecked(False)
        self.play_button.setChecked(False)
        self.pause_button.setChecked(True)

    def stop_button_func(self):
        curr_shot_idx = self.toc_layout.indexOf(self.curr_shot)
        row, col, _, _ = self.toc_layout.getItemPosition(curr_shot_idx)
        timestamp_ms = self.rowcol_to_timestamp[(row, col)]
        self.media_player.setPosition(timestamp_ms)
        self.media_player.pause()
        self.stop_button.setChecked(True)
        self.play_button.setChecked(False)
        self.pause_button.setChecked(False)

    def label_click_func(self):
        label = self.sender()
        self.curr_shot.setStyleSheet("color: black")
        label.setStyleSheet("color: red")
        row, col, _, _ = self.toc_layout.getItemPosition(self.toc_layout.indexOf(label))
        timestamp_ms = self.rowcol_to_timestamp[(row, col)]
        self.media_player.setPosition(timestamp_ms)
        self.curr_shot = label
        self.stop_button.setChecked(False)
        self.play_button.setChecked(True)
        self.pause_button.setChecked(False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rgbfile')
    parser.add_argument('wavfile')
    parser.add_argument('--width', default=480)
    parser.add_argument('--height', default=270)
    parser.add_argument('--mp4file', help='Optionally, Skip generating a .mp4 if it already exists in this path')
    args = parser.parse_args()

    if not args.mp4file:
        mp4_filepath = write_video(args.rgbfile, args.wavfile, args.width, args.height)
    else:
        mp4_filepath = args.mp4file

    get_scenes_shots_subshots(args.rgbfile, mp4_filepath)  # saves results as scene.txt, shot.txt, subshot.txt
    scenes = convert_txts_to_timestamps()

    app = QApplication(sys.argv)
    player = VideoPlayer(mp4_filepath, scenes)
    player.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()