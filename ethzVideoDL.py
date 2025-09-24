import xml.etree.ElementTree as ET
from datetime import datetime
import os
import requests
import concurrent.futures
import argparse
from enum import Enum, unique

# Parse the script arguments
parser = argparse.ArgumentParser()
parser.add_argument("-r", "--rss", type=str, help='Enter the RSS link of the lecture: Open the lecture in your browser, find it under Share->RSS.')
parser.add_argument("-p", "--path", type=str, help='Put in the absolute path of the directory in which the videos will be saved')
#parser.add_argument("-q", "--quality", type=str, help='Pass the quality as LOW, MEDIUM or HIGH')
parser.add_argument("-y", action='store_true', help='Proceeds to the download without asking')
parser.add_argument("-all", action='store_true', help='Downloads all file formats and not just .mp4')
args = parser.parse_args()

#print(args)

print()

# Get the URL
url = args.rss
if not args.rss:
    url = input("Enter the RSS link of the desired videos\nOpen the lecture in your browser, find it under Share->RSS: ")

if url.startswith("http:"):
    url = "https" + url[4:]
if url.startswith("video."):
    url = "https://" + url

def invalidURL():
    print("Invalid URL.")
    print("It should start with 'https://video.ethz.ch/~rss/series/' and end in a random looking string.")
    print("Go to the lecture on the website and click on Share>RSS.")
    exit()

# check if the input URL is valid
if not url.startswith("https://video.ethz.ch/~rss/series/"):
    invalidURL()

# Navigate to the URL and extract the RSS XML data
xml_data = requests.get(url).content

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
    if os.path.isfile(os.path.join(folder, file_name)):
        downloaded_files.add(file_name)


# Loop through all the items in the feed and create a list of download tasks
download_tasks = []
notMP4 = 0
items = tree.findall('.//item')
for item in items:
    # Get the URL of the file
    mp4_url = item.find('enclosure').attrib['url']

    if not args.all and not mp4_url.endswith(".mp4"):
        notMP4 += 1
        continue

    # Get the publication date of the item
    pub_date_str = item.find('pubDate').text
    pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")

    # Create the filename
    filename = pub_date.strftime("%Y-%m-%d--%H-%M--id_") + mp4_url.split('/')[-2] + "." + mp4_url.split(".")[-1]
    
    # Add the download task to the list if the file has not been downloaded yet
    if filename not in downloaded_files:
        download_tasks.append((mp4_url, filename))

print('Found ' + str(len(download_tasks)) + ' new Recordings and ' + str(len(items)-len(download_tasks)-notMP4) + " already downloaded.")
if notMP4 and not args.all:
    print(str(notMP4)+' non mp4 file' + ('s were' if notMP4 != 1 else ' was') + ' ignored. (Look at the -all option if you want to download all filetypes.)')

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
