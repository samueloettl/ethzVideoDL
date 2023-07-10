import xml.etree.ElementTree as ET
from datetime import datetime
import os
import requests
import concurrent.futures
import argparse
from enum import Enum, unique

# Parse the script arguments
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--rss", type=str, help='Enter the RSS link of the lecture: You can get it by opening the lecture in your browser and opening "Media"')
parser.add_argument("-p", "--path", type=str, help='Put in the absolute path of the directory in which the videos will be saved')
#parser.add_argument("-q", "--quality", type=str, help='Pass the quality as LOW, MEDIUM or HIGH')
parser.add_argument("-y", action='store_true', help='Proceeds to the download without asking')
args = parser.parse_args()

#print(args)

print()

# Get the URL
url = args.rss
if not args.rss:
    url = input("Enter the RSS link of the desired videos: ")

if url.startswith("http:"):
    url = "https" + url[4:]
if url.startswith("video."):
    url = "https://" + url

def invalidURL():
    print("Invalid URL.")
    print("It should start with 'https://video.ethz.ch/lectures/' and end in the quality of the lecture")
    exit()

# check if the input URL is valid
if not url.startswith("https://video.ethz.ch/") or not (url.endswith("&quality=LOW") or url.endswith("&quality=MEDIUM") or url.endswith("&quality=HIGH")):
    invalidURL()

# Navigate to the URL and extract the RSS XML data
xml_data = requests.get(url, headers={'User-Agent': 'Custom'}).content

# Parse the RSS feed
tree = ET.fromstring(xml_data)

# Get the title of the feed
title = tree.find('.//title').text.strip()

description = tree.find('.//description').text.strip().split("<")[0]

print()
print('***********************************************')
print()
print('Found Lecture')
print(title)
print()
print('Description:')
print(description)
print()
print('***********************************************')
print()


# Set default folder path to the execution directory of the script
default_path = os.path.join(os.getcwd(), title.replace(' ', '_'))

# Ask user to input folder path
folder = args.path
if not args.path:
    folder = input(f"Enter folder in which to save the videos ({default_path}): ")

# Use default path if user doesn't input anything
if not folder:
    folder = default_path
    if not os.path.exists(folder):
        os.makedirs(folder)

# Check if folder path exists
if not os.path.exists(folder):
    create_folder = input("Folder path does not exist. Do you want to create it? (y/n): ")
    if create_folder.lower() == 'y':
        os.makedirs(folder)
    else:
        print("Exiting script.")
        exit()


# Get list of already downloaded Files
downloaded_files = set()
for file_name in os.listdir(folder):
    if not file_name.endswith('.mp4'):
        continue
    if os.path.isfile(os.path.join(folder, file_name)):
        downloaded_files.add(file_name)


# Loop through all the items in the feed and create a list of download tasks
download_tasks = []
items = tree.findall('.//item')
for item in items:
    # Get the URL of the mp4 file
    mp4_url = item.find('enclosure').attrib['url']

    # Get the publication date of the item
    pub_date_str = item.find('pubDate').text
    pub_date = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%MZ")

    # Create the filename
    filename = pub_date.strftime("%Y-%m-%d--%H-%M--id_") + mp4_url.split('/')[-2] + ".mp4"
    
    # Add the download task to the list if the file has not been downloaded yet
    if filename not in downloaded_files:
        download_tasks.append((mp4_url, filename))

print('Found ' + str(len(download_tasks)) + ' new Recordings and ' + str(len(items)-len(download_tasks)) + ' already downloaded.')

# Ask the user for confirmation to download, skip if -y was supplied
while not args.y and len(download_tasks) > 0:
    response = input("Do you want to proceed? (y/n): ")
    if response.lower() == 'y':
        print("Proceeding...")
        break
    elif response.lower() == 'n':
        print("Aborting...")
        exit()
    else:
        print("Invalid response. Please enter 'y' or 'n'.")

# Download the mp4 files in parallel using multiple threads
def download_task(task):
    mp4_url, filename = task
    path_to_file = os.path.join(folder, filename)
    print(f'Downloading {filename}')
    with requests.get(mp4_url, stream=True) as r:
        r.raise_for_status()
        with open(path_to_file+".part", 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    os.rename(path_to_file+".part", path_to_file)
    print(f'Downloaded {filename}')

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(download_task, download_tasks)

print(f"Downloaded {len(download_tasks)} new files to folder {folder}.")
