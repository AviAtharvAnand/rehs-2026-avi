import sounddevice as sd
import numpy as np
from scipy.signal import spectrogram
import matplotlib.pyplot as plt
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from roboflow import Roboflow
import os

rf = Roboflow(api_key="IXOa2eeOXSz0SMP69Tcy")
project = rf.workspace().project("findwhalesound")
model = project.version(3).model

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


def record_and_make_spectrogram():
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
    output_file = f"spectrogram.png"
    plt.savefig(output_file, bbox_inches="tight", pad_inches=0)
    plt.close()  # Close the plot to free resources
    print(f"Spectrogram saved as {output_file}.")
    return output_file

def detect_whale_sound(spectrogram, output, i):
    prediction = model.predict(output_file, confidence=40, overlap=30)
    prediction_data = prediction.json()
    if any(detection['class'] == "whale-sound" for detection in prediction_data.get("predictions", [])):
        name = f'sound{i}.jpg'
        detected_path = os.path.join(output, name)
        prediction.save(detected_path)
        print(f"Whale detected and annotated saved to '{detected_path}'")
        drive = authenticate_drive()
        upload_to_drive(name, drive, folder_id)

folder_id = "1KnzxtghxDoT7JvvKlt1hbIc9Oh3caNsF"
i = 0
while(True):
    output_file = record_and_make_spectrogram()
    detect_whale_sound(output_file, r"C:\Users\athar\OneDrive\Avi\Python", i)
    i += 1
