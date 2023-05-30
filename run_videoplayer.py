# Example commands to run:
# python run_videoplayer.py The_Long_Dark_rgb/InputVideo.rgb The_Long_Dark_rgb/InputAudio.wav
# python run_videoplayer.py Ready_Player_One_rgb/InputVideo.rgb Ready_Player_One_rgb/InputAudio.wav
# python run_videoplayer.py The_Great_Gatsby_rgb/InputVideo.rgb The_Great_Gatsby_rgb/InputAudio.wav

import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import argparse
import pyaudio
import wave
import time

class VideoPlayer:
    def __init__(self, video_filepath, audio_filepath):
        self.width = 480
        self.height = 270
        fps = 30
        self.delay = 1000 // fps 
        self.delay_float = 1000./fps

        self.root = tk.Tk()

        self.video_buffer = []
        self.frame_idx = 0
        video = open(video_filepath, "rb")
        video_data = video.read(self.height * self.width * 3)
        while(video_data):
            data2 = np.frombuffer(video_data, dtype=np.uint8).reshape(270, 480, 3)
            photo = ImageTk.PhotoImage(image=Image.fromarray(data2, mode="RGB"))
            # self.video_buffer.append(data2)
            self.video_buffer.append(photo)
            video_data = video.read(self.height * self.width * 3)
        video.close()

        self.root.title('Video Player')
        
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.play = 1
        self.paused = 0
        self.stopped = 0


        right_frame = tk.Frame(self.root)
        right_frame.pack(side=tk.RIGHT)

        # self.video_canvas = tk.Canvas(right_frame, width=self.width, height=self.height)
        # self.video_canvas.pack(side=tk.TOP)

        self.video_label = tk.Label(right_frame)
        self.video_label.pack(side=tk.TOP)

        play_button = tk.Button(right_frame, text='PLAY', command=self.play_pressed)
        play_button.pack(side=tk.LEFT)

        pause_button = tk.Button(right_frame, text='PAUSE', command=self.pause_pressed)
        pause_button.pack(side=tk.RIGHT)

        stop_button = tk.Button(right_frame, text='STOP', command=self.stop_pressed)
        stop_button.pack(side=tk.BOTTOM)

        # TODO feel free to change below scene structure if it doesnt align with whatever scene detection method we use.
        # each list in scenes is a scene.
        # within each list are more lists, each list a shot.
        # within those lists, would be tuples indicating frame of video and frame of audio. (only examples for now)
        # labels are shown for subshots only if there is more than 1 subshot for any given shot
        scenes = [[[(1,2)],
                   [(2,3)]],
                  [[(3,4), (8,9)],
                   [(4,5), (5,6), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1), (1,1)]]] 
        self.label_idx_to_frames = []

        left_frame = tk.Frame(self.root)
        left_frame.pack(side=tk.LEFT)

        toc_canvas = tk.Canvas(left_frame, width=self.width//2, height=self.height*2)
        toc_canvas.pack(side=tk.LEFT, fill=tk.BOTH)
        
        scrollbar = tk.Scrollbar(left_frame, orient=tk.VERTICAL, command=toc_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.BOTH)
        toc_canvas.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=toc_canvas.yview)

        self.previous_label = None

        def on_click(event):
            label_idx = toc_canvas.find_closest(toc_canvas.canvasx(event.x), toc_canvas.canvasy(event.y))[0]

            if self.previous_label:
                toc_canvas.itemconfigure(self.previous_label, fill='red')
            
            # tkinter canvas starts indexing labels from 1
            # so subtract 1 to get correct tuple
            audio_frame, video_frame = self.label_idx_to_frames[label_idx-1]
            toc_canvas.itemconfigure(label_idx, fill='blue')            

            self.previous_label = label_idx


        scene_x = 20
        shot_x = 90
        subshot_x = 160
        num_labels_gen = 0 
        for scene_idx, scene in enumerate(scenes):
            label = 'Scene {}'.format(scene_idx+1)
            y = 30 + num_labels_gen * 30
            toc_canvas.create_text(scene_x, y, text=label, anchor='w', fill='black')
            num_labels_gen += 1
            self.label_idx_to_frames.append(())

            for shot_idx, shot in enumerate(scene):
                label = 'Shot {}'.format(shot_idx+1)
                y = 30 + num_labels_gen * 30
                toc_canvas.create_text(shot_x, y, text=label, tags=('label',), anchor='w', fill='red')
                num_labels_gen += 1
                self.label_idx_to_frames.append((shot[0]))

                if len(shot) > 1:
                    for subshot_idx, subshot in enumerate(shot):
                        label = 'Subshot {}'.format(subshot_idx+1)
                        y = 30 + num_labels_gen * 30
                        toc_canvas.create_text(subshot_x, y, text=label, tags=('label',), anchor='w', fill='red')
                        num_labels_gen += 1
                        self.label_idx_to_frames.append(subshot)
        toc_canvas.configure(scrollregion=(0,0,self.width//2, num_labels_gen * 30 + 30))
        toc_canvas.tag_bind('label', '<Button-1>', on_click)

        with wave.open(audio_filepath,"rb") as audf:
            audio_params = dict((audf.getparams()._asdict()))
            self.audio = audf.readframes(audio_params['nframes'])

        self.pyaud = pyaudio.PyAudio()
        self.curr_aud_frame = 0

        def callback(in_data, frame_count, time_info, status):
            frame_start = self.curr_aud_frame*4
            frame_end = frame_start + (frame_count*4)
            data = self.audio[frame_start:frame_end]
            self.curr_aud_frame += frame_count
            return (data, pyaudio.paContinue)
        
        self.audio_stream = self.pyaud.open(format = self.pyaud.get_format_from_width(audio_params['sampwidth']),  # 2
                channels = audio_params['nchannels'],  # 2
                rate = audio_params['framerate'],  ## 44.1 khz
                output = True,
                stream_callback=callback)
        
        self.last_update_time = time.time()
    

    def run(self):
        self.update()
        self.root.mainloop()

    def close(self):
        self.play = 0
        self.audio_stream.close()
        self.pyaud.terminate()
        self.root.destroy()

    def play_pressed(self):
        self.play = 1
        self.paused = 0
        self.stopped = 0
        self.audio_stream.start_stream()

    def pause_pressed(self):
        self.play = 0
        self.paused = 1
        self.stopped = 0
        self.audio_stream.stop_stream()

    def stop_pressed(self):
        self.play = 0
        self.paused = 0
        self.stopped = 1
        self.audio_stream.stop_stream()
        # TODO eventually we want the player to reset to the beginning of the shot its on
        # here i am just resetting back to the beginning
        self.curr_aud_frame = 0
        self.frame_idx = 0
        
    # TODO figure out the right amount of time to delay in order to closely mimic fps of video
    def update(self):
        start_time = time.time()
        if self.play:
            # self.photo = ImageTk.PhotoImage(image=Image.fromarray(self.video_buffer[self.frame_idx], mode="RGB"))
            # self.video_canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
            # self.video_label.config(image=self.photo)
            # self.video_label.image=self.photo
            self.video_label.config(image=self.video_buffer[self.frame_idx])
            self.video_label.image=self.video_buffer[self.frame_idx]
            self.frame_idx += 1
        updated_time = time.time()
        # process_time_ms_float = ((updated_time - self.last_update_time) * 1000.)
        process_time_ms_float = (updated_time - start_time) * 1000.
        # print(start_time, updated_time, process_time_ms_float)
        # time_since_update = (updated_time - self.last_update_time) // 1_000_000 # gives ms
        time_to_wait = round(self.delay_float - process_time_ms_float)
       
        # self.last_update_time = updated_time
        delay = max(time_to_wait, 0)
        # self.root.after(33, self.update)
        self.root.after(30, self.update)
        # self.root.after(1000//15, self.update)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('rgbfile')
    parser.add_argument('wavfile')
    args = parser.parse_args()

    player = VideoPlayer(args.rgbfile, args.wavfile)
    player.run()

if __name__ == '__main__':
    main()
