import cv2
import os

def crop_top_view(input_file, output_file):
    cap = cv2.VideoCapture(input_file)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Use MP4 codec for better compatibility
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height // 2))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        cropped_frame = frame[:height // 2, :]
        out.write(cropped_frame)
        cv2.imshow("Cropped View", cropped_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()

def record_video(camera_index, output_file):
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"Error: Camera with index {camera_index} could not be accessed.")
        return None

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Use MP4 codec for better compatibility
    fourcc = cv2.VideoWriter_fourcc(*'MP4V')
    out = cv2.VideoWriter(output_file, fourcc, fps, (width, height))

    print("Recording started. Press 'q' to stop recording.")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        cv2.imshow('Recording', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):  # Break the loop on pressing "q"
            print("Recording stopped.")
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    return output_file

if __name__ == "__main__":
    camera_index = 1
    raw_output_file = "raw_output.mp4"
    cropped_output_file = "cropped_output.mp4"

    # Record the video
    recorded_file = record_video(camera_index, raw_output_file)

    # Process the video (crop it) and stop
    if recorded_file:
        crop_top_view(recorded_file, cropped_output_file)
        print(f"Cropped video saved to {cropped_output_file}")

        # Delete the raw video file
        if os.path.exists(raw_output_file):
            os.remove(raw_output_file)
            print(f"Deleted raw video file: {raw_output_file}")

    print("Video download complete. Exiting program...")
