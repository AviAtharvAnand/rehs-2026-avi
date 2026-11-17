import cv2
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from roboflow import Roboflow
import json
from threading import Lock
import time

# Roboflow model setup
rf = Roboflow(api_key="325u9WybFoWDBZlnQsFW")
project = rf.workspace().project("thermal_whale_detection-onnjf")
model = project.version(3).model

# Shared trial number file and lock
TRIAL_FILE = "trial_num.json"
trial_lock = Lock()

# Initialize trial_num if not present
def initialize_trial_file():
    if not os.path.exists(TRIAL_FILE):
        with open(TRIAL_FILE, 'w') as f:
            json.dump({"trial_num": 0}, f)

# Get the current trial number
def get_trial_num():
    with trial_lock:
        with open(TRIAL_FILE, 'r') as f:
            data = json.load(f)
        return data["trial_num"]

# Increment the trial number
# def increment_trial_num():
#     with trial_lock:
#         with open(TRIAL_FILE, 'r') as f:
#             data = json.load(f)
#         data["trial_num"] += 1
#         with open(TRIAL_FILE, 'w') as f:
#             json.dump(data, f)
#         return data["trial_num"]

# Authenticate Google Drive
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    if gauth.credentials is None or gauth.access_token_expired:
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)

# Upload file to Google Drive
def upload_to_drive(file_path, drive, folder_id=None):
    metadata = {'title': file_path}
    if folder_id:
        metadata['parents'] = [{'id': folder_id}]  # Specify the folder ID
    file_drive = drive.CreateFile(metadata)
    file_drive.SetContentFile(file_path)
    file_drive.Upload()
    print(f"File uploaded to Google Drive with ID: {file_drive['id']}")
    file_drive = None
    os.remove(file_path)

# Detect spouts in thermal images
def record_video(duration=5, fps=20):
    """
    Records a video for a given duration, crops the top thermal view,
    and returns it as a list of frames.

    Args:
        duration (int): Duration of the video recording in seconds.
        fps (int): Frames per second for the recording.

    Returns:
        list: A list of captured frames (each frame is a NumPy array).
    """
    cap = cv2.VideoCapture(1)  # 2 assumes the thermal camera index

    if not cap.isOpened():
        raise Exception("Could not open video device")

    frame_interval = 1 / fps
    start_time = time.time()
    video_frames = []

    print("Recording started...")
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if ret:
            # Crop the top half of the frame to get the thermal view
            height, width, _ = frame.shape
            cropped_frame = frame[:height // 2, :]  # Crop top half

            video_frames.append(cropped_frame)

            # Show the cropped view during recording
            cv2.imshow('Recording (Cropped View)', cropped_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):  # Break on 'q' key press
                break
        else:
            print("Frame capture failed.")
            break
        time.sleep(frame_interval)

    cap.release()
    cv2.destroyAllWindows()
    print(f"Recording finished: {len(video_frames)} frames captured.")

    return video_frames

# Detect whales in images
def detect_whales(frames, folder_id):
    results = []
    for i, frame in enumerate(frames):
        trial_num = get_trial_num()
        temp_filename = f"frame_{i}_trial_{trial_num}.jpg"
        cv2.imwrite(temp_filename, frame)

        # Run detection using Roboflow model
        prediction = model.predict(temp_filename, confidence=0, overlap=30)
        prediction_data = prediction.json()

        if any(detection['class'] == "Whale" for detection in prediction_data.get("predictions", [])):
            detected_path = f"image_frame_{i}_trial_{trial_num}_detected.jpg"
            prediction.save(detected_path)
            print(f"Whale detected and saved to: {detected_path}")

            # Upload to Google Drive
            drive = authenticate_drive()
            upload_to_drive(detected_path, drive, folder_id)
            results.append(prediction_data)
 

    return results

    # increment_trial_num()
initialize_trial_file()
folder_id = "1KnzxtghxDoT7JvvKlt1hbIc9Oh3caNsF"
while(True):
    # Example video recording replaced with static images for testing
    frames = record_video()
    detect_whales(frames, folder_id)