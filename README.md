# Tasks lists
## Completed 
- [x] UI Design
- [x] Shot 
- [x] Subshot 
- [x] Scene 
- [x] Add video indexes to UI 
- [x] Add audio indexes to UI

## In Progess
- [ ] Presentation slides

# Setup
1. Install Python (tested with 3.10)
2. Setup a venv and activate it

```
python -m venv venv_path
```

Windows:

```
./venv_path/Scripts/activate
```

3. Install ffmpeg

LINUX
```
apt-get install ffmpeg
```

WINDOWS

Follow this install tutorial [here](https://phoenixnap.com/kb/ffmpeg-windows)

4. Install required packages

```
python -m pip install -r requirements.txt
```

5. If there is an issue with rendering the video player with PyQt, you may need to additionally install K-Lite Codec Basic for Windows [here](https://codecguide.com/download_kl.htm)

5. If UI could be rendered but video is not played, please double check if you put the full path of mp4/wav/rgb files in the command line argument.

# Backend

`python detect.py /path/to/video.rgb /path/to/video.mp4`

This will generate 3 files: scene.txt, shot.txt and subshot.txt. 

# Running the Media Player
`python run_videoplayer_v2.py [path_to_rgbfile] [path_to_wavfile]`

This will generate an .mp4 file and then run the backend to generate scene, shot and subshot segmentation.

Then it will generate a video player with indexed labels.
