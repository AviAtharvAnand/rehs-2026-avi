import cv2
import os

def split_video_into_frames(video_path, output_folder):
    # Check if the video file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' does not exist.")
        return

    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Capture the video
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    frame_count = 0

    # Read frames from the video
    while True:
        ret, frame = cap.read()

        if not ret:
            break  # Break if no frames are left to read

        # Save the frame as an image file
        frame_file = os.path.join(output_folder, f"test6_{frame_count:04d}.jpg")
        cv2.imwrite(frame_file, frame)

        print(f"Saved: {frame_file}")
        frame_count += 1

    # Release the video capture
    cap.release()
    print(f"Finished! Extracted {frame_count} frames to '{output_folder}'.")

# Input video path
video_path = "whale-video.mp4"  # Replace with the path to your video file

# Output folder path
output_folder = "training"  # Replace with your desired output folder

# Call the function
split_video_into_frames(video_path, output_folder)
