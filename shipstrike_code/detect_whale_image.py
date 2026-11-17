import cv2
import os
import time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from roboflow import Roboflow
rf = Roboflow(api_key="IXOa2eeOXSz0SMP69Tcy")
project = rf.workspace().project("avi-w-normalimage")
model = project.version(2).model

def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")  # Load saved credentials
    if gauth.credentials is None or gauth.access_token_expired:  # If no credentials or expired
        gauth.LocalWebserverAuth()  # Open browser for authentication
        gauth.SaveCredentialsFile("mycreds.txt")  # Save credentials for next time
    return GoogleDrive(gauth)


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

def record_video(duration=5, fps=20):
    """
    Records a video for a given duration and returns it as a list of frames.

    Args:
        duration (int): Duration of the video recording in seconds.
        fps (int): Frames per second for the recording.

    Returns:
        list: A list of captured frames (each frame is a NumPy array).
    """
    cap = cv2.VideoCapture(0)  # 0 is usually the default camera

    if not cap.isOpened():
        raise Exception("Could not open video device")

    frame_interval = 1 / fps
    start_time = time.time()
    video_frames = []

    print("Recording started...")
    while time.time() - start_time < duration:
        ret, frame = cap.read()
        if ret:
            video_frames.append(frame)
            cv2.imshow('Recording...', frame)
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

def detect_whales(frames, folder_id):
    """
    Processes frames with the Roboflow model and uploads annotated images of detected whales to Google Drive.

    Args:
        frames (list): List of frames (NumPy arrays).
        drive (GoogleDrive): Authenticated GoogleDrive instance.
        folder_id (str): Google Drive folder ID.

    Returns:
        list: Results from the Roboflow model for each frame where a whale is detected.
    """

    results = []
    for i, frame in enumerate(frames):
        temp_filename = f"frame_{i}.jpg"
        cv2.imwrite(temp_filename, frame)

        prediction = model.predict(temp_filename, confidence=40, overlap=30)
        prediction_data = prediction.json()

        if any(detection['class'] == "Whale" for detection in prediction_data.get("predictions", [])):
            detected_path = f"image_frame_{i}_detected.jpg"
            prediction.save(detected_path)
            print(f"Whale detected and annotated saved to '{detected_path}'")
            drive = authenticate_drive()
            upload_to_drive(detected_path, drive, folder_id)
            results.append(prediction_data)

        os.remove(temp_filename)

    return results

# Authenticate once

folder_id = '1KnzxtghxDoT7JvvKlt1hbIc9Oh3caNsF'

# Record and process
while(True):
    frames = record_video()
    detect_whales(frames, folder_id)
