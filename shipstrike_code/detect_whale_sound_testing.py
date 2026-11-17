import sounddevice as sd
import numpy as np
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from roboflow import Roboflow
import os
import json
from threading import Lock

# Roboflow model setup
rf = Roboflow(api_key="IXOa2eeOXSz0SMP69Tcy")
project = rf.workspace().project("findwhalesound")
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

# # Increment the trial number
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

def record_and_make_spectrogram():
    trial_num = get_trial_num()
    spectrogram_file = f"spectrogram_trial_{trial_num}.png"
    # Record audio
    duration = 5  # seconds
    fs = 44100  # Sampling frequency
    print("Recording...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    audio = audio.flatten()
    print("Recording finished.")

    # Compute Spectrogram
    frequencies, times, Sxx = spectrogram(audio, fs, nperseg=2048)

    # Convert to decibels
    Sxx_db = 10 * np.log10(Sxx + 1e-10)

    # Plot Spectrogram
    plt.figure(figsize=(10, 6))
    plt.style.use('dark_background')
    plt.pcolormesh(times, frequencies, Sxx_db, shading='gouraud', cmap='plasma')
    plt.axis('off')  # Turn off axes for a cleaner look
    output_file = spectrogram_file
    plt.savefig(output_file, bbox_inches="tight", pad_inches=0)
    plt.close()  # Close the plot to free resources
    print(f"Spectrogram saved as {output_file}.")
    return output_file

def detect_whale_sound(spectrogram, output, folder_id):
    prediction = model.predict(spectrogram, confidence=100, overlap=30)
    prediction_data = prediction.json()
    if any(detection['class'] == "whale-sound" for detection in prediction_data.get("predictions", [])):
        name = spectrogram
        detected_path = os.path.join(output, name)
        prediction.save(detected_path)
        print(f"Whale detected and annotated saved to '{detected_path}'")
        drive = authenticate_drive()
        upload_to_drive(name, drive, folder_id)
    else:
        os.remove(spectrogram)


# Record and process sound to detect whale calls
def record_and_detect_sound(folder_id):
    trial_num = get_trial_num()
    spectrogram_file = f"spectrogram_trial_{trial_num}.png"

    # Record audio
    duration = 5  # seconds
    fs = 44100  # Sampling frequency
    print("Recording audio...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='float32')
    sd.wait()
    print("Recording finished.")

    # Compute spectrogram
    frequencies, times, Sxx = spectrogram(audio.flatten(), fs, nperseg=2048)
    Sxx_db = 10 * np.log10(Sxx + 1e-10)

    # Plot spectrogram
    plt.figure(figsize=(10, 6))
    plt.style.use('dark_background')
    plt.pcolormesh(times, frequencies, Sxx_db, shading='gouraud', cmap='plasma')
    plt.axis('off')
    plt.savefig(spectrogram_file, bbox_inches="tight", pad_inches=0)
    plt.close()

    # Detect whale sounds using Roboflow model
    prediction = model.predict(spectrogram_file, confidence=40, overlap=30)
    prediction_data = prediction.json()

    if any(detection['class'] == "whale-sound" for detection in prediction_data.get("predictions", [])):
        detected_file = f"spectrogram_trial_{trial_num}_detected.png"
        os.rename(spectrogram_file, detected_file)
        print(f"Whale sound detected and saved to: {detected_file}")

        # Upload to Google Drive
        drive = authenticate_drive()
        upload_to_drive(detected_file, drive, folder_id)
    else:
        os.remove(spectrogram_file)

    # increment_trial_num()

initialize_trial_file()
folder_id = "1KnzxtghxDoT7JvvKlt1hbIc9Oh3caNsF"
while(True):
    output_file = record_and_make_spectrogram()
    detect_whale_sound(output_file, r"C:\Users\athar\OneDrive\Avi\Python", folder_id)
