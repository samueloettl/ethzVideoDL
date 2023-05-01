import xml.etree.ElementTree as ET
from datetime import datetime
import os
import requests
import concurrent.futures
import argparse
from enum import Enum, unique

# Parse the script arguments
parser = argparse.ArgumentParser()
parser.add_argument("-u", "--url", type=str, help='Enter the URL of the Lecture: It should start with https://video.ethz.ch/lectures/ and end in the number of the lecture')
parser.add_argument("-p", "--path", type=str, help='Put in the absolute path of the directory in which the videos will be saved')
parser.add_argument("-q", "--quality", type=str, help='Pass the quality as LOW, MEDIUM or HIGH')
args = parser.parse_args()

print(args)

print()


# Get the URL
url = args.url
if not args.url:
    url = input("Enter the URL of the Lecture: ")

if url.startswith("http:"):
    url = "https" + url[4:]
if url.startswith("video."):
    url = "https://" + url

def invalidURL():
    print("Invalid URL.")
    print("It should start with 'https://video.ethz.ch/lectures/' and end in the number of the lecture")
    exit()

# check if the input URL is valid
if not url.startswith("https://video.ethz.ch/lectures/"):
    invalidURL()

# extract the course code semester and year from the URL
parts = url.split("/")
try:
    i = parts.index("lectures")
except ValueError():
    invalidURL()
if len(parts) < i+5:
    invalidURL()
department = parts[i+1]
year = parts[i+2]
semester = parts[i+3]
course_code = parts[i+4]

course_code = course_code.split(".")[0]
# create the RSS feed URL using the extracted course code and semester
url = f"https://video.ethz.ch/lectures/{department}/{year}/{semester}/{course_code}.rss.xml"


@unique
class Quality(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INVALID = "INVALID"

    def __str__(self):
        return f'?quality={self.value}'

    @classmethod
    def from_str(cls, s: str):
        s = s.capitalize()
        if len(s) == 0:
            return cls(Quality.HIGH)
        if s[0] == 'H':
            return cls(Quality.HIGH)
        if s[0] == 'M':
            return cls(Quality.MEDIUM)
        if s[0] == 'L':
            return cls(Quality.LOW)
        return cls(Quality.INVALID)

# Ask the user for desired video quality
while True:
    response = args.quality
    if not args.quality: 
        response = input("Please enter video quality ('HIGH' (default), 'MEDIUM' or 'LOW'): ")
    quality = Quality.from_str(response)
    if not quality == Quality.INVALID:
        break
    else:
        print("Invalid quality. Please enter one of 'HIGH', 'MEDIUM', 'LOW', 'H', 'M' or 'L'.")

url = url + str(quality)


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

# Ask the user for confirmation to download
while len(download_tasks) > 0:
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
