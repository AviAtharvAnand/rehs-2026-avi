import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from roboflow import Roboflow

# Initialize Roboflow
rf = Roboflow(api_key="IXOa2eeOXSz0SMP69Tcy")
project = rf.workspace().project("avi-w-normalimage")
model = project.version(1).model

# Authenticate Google Drive
def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")  # Load saved credentials
    if gauth.credentials is None or gauth.access_token_expired:  # If no credentials or expired
        gauth.LocalWebserverAuth()  # Open browser for authentication
        gauth.SaveCredentialsFile("mycreds.txt")  # Save credentials for next time
    return GoogleDrive(gauth)

# Upload file to Google Drive
def upload_to_drive(file_path, drive, folder_id=None):
    metadata = {'title': os.path.basename(file_path)}
    if folder_id:
        metadata['parents'] = [{'id': folder_id}]  # Specify the folder ID
    file_drive = drive.CreateFile(metadata)
    file_drive.SetContentFile(file_path)
    file_drive.Upload()
    print(f"File uploaded to Google Drive with ID: {file_drive['id']}")

# Detect whales in an image
def detect_folder(input_folder, drive, folder_id_detected, folder_id_not_detected):
    detected = 0
    not_detected = 0
    for file in os.listdir(input_folder):
        file_path = os.path.join(input_folder, file)
        if os.path.isfile(file_path):
            prediction = model.predict(file_path, confidence=40, overlap=30)
            prediction_data = prediction.json()

            if any(detection['class'] == "Whale" for detection in prediction_data.get("predictions", [])):
                detected_path = f"image_frame_detected.jpg"
                # Save annotated image (if Roboflow supports this)
                prediction.save(detected_path)  # Or generate annotations manually
                print(f"Whale detected and annotated saved to '{detected_path}'")
                upload_to_drive(detected_path, drive, folder_id_detected)
                detected += 1
            else:
                not_detected_path = f"image_frame_not_detected.jpg"
                # Save the non-detected image (you may need to copy the original image here)
                prediction.save(not_detected_path)
                print(f"No Whale detected, annotated saved to '{not_detected_path}'")
                upload_to_drive(not_detected_path, drive, folder_id_not_detected)
                not_detected += 1
    return detected, not_detected



# Specify folder and IDs
drive = authenticate_drive()
answer = detect_folder(r"C:\Users\athar\OneDrive\Avi\tests_for_science_project_2025\images\trial3-not-whale", drive,"1YsD5VKv4_mNDWlmxzE8eNkyMxKl9egar", "18e_wTJYKPqS_vuTNlM8qSpdGi53E6-4X")
print(answer)
