import os
import json

# Change the current working directory to the location of the script
os.chdir('G:/Mi unidad/RUN TO LIVE/RAMON-BOT')

# Debug: print the current working directory
print("Current working directory:", os.getcwd())

# Use a relative path to the JSON file
json_file_path = 'data.json'

# Check if the file exists before attempting to open
if not os.path.exists(json_file_path):
    raise FileNotFoundError(f"The file {json_file_path} does not exist in the current directory.")

# Open the file safely using a relative path
with open(json_file_path, 'r') as file:
    personal_emails = json.load(file)

# Print loaded content for debugging
print(personal_emails)
