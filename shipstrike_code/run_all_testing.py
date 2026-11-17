import subprocess

# List of files to run
files = ["detect_whale_image_testing.py", "detect_whale_sound_testing.py", "detect_whale_thermal_spout_testing.py", "alarm_testing.py"]

# Store all subprocesses
processes = []
for file in files:
    # Launch each file as a separate process
    print(f"Starting {file}...")
    processes.append(subprocess.Popen(["python", file]))

# Wait for all processes to complete
for process in processes:
    process.wait()

print("All files have completed execution.")
