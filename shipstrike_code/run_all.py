import subprocess

# List of files to run
files = ["detect_whale_image.py", "detect_whale_sound.py", "detect_whale_thermal_spout.py", "alarm.py"]

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
