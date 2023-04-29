import xml.etree.ElementTree as ET
from datetime import datetime
import os
import requests
import concurrent.futures

# Ask the user for the URL
print()
url = input("Enter the URL of the Lecture: ")

if url.endswith('.html'):
    url = url[:-5] + '.rss.xml?quality=HIGH'
elif url.endswith('/'):
    url = url + 'rss.xml?quality=HIGH'
elif '.rss.xml' in url:
    url = url
else:
    url = url + '.rss.xml?quality=HIGH'

# Navigate to the URL and extract the RSS XML data
xml_data = requests.get(url, headers={'User-Agent': 'Custom'}).content

# Parse the RSS feed
tree = ET.fromstring(xml_data)

# Get the title of the feed
title = tree.find('.//title').text.strip().replace(' ', '_')

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

# Create the directory for the files
if not os.path.exists(title):
    os.makedirs(title)

folder = os.path.join(title)
downloaded_file = os.path.join(title, ".downloaded_files.txt")
with open(downloaded_file, "w") as f:
    for file_name in os.listdir(folder):
        if not file_name.endswith('.mp4'):
            continue
        if os.path.isfile(os.path.join(folder, file_name)):
            f.write(file_name + "\n")

# Read the list of already downloaded files
with open(downloaded_file, 'r') as f:
    downloaded_files = set(line.strip() for line in f)

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
    filename = pub_date.strftime("%Y-%m-%d--%H-%M") + ".mp4"
    
    # Add the download task to the list if the file has not been downloaded yet
    if filename not in downloaded_files:
        download_tasks.append((mp4_url, filename))

print('Found ' + str(len(download_tasks)) + ' new Recordings and ' + str(len(items)-len(download_tasks)) + ' already downloaded.')

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
    print(f'Downloading {filename}')
    with open(filename, 'wb') as f:
        response = requests.get(mp4_url)
        f.write(response.content)
    print(f'Downloaded {filename}')

    # Add the downloaded file to the list
    with open(downloaded_file, 'a') as f:
        f.write(filename + '\n')

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    executor.map(download_task, download_tasks)

print(f"Downloaded {len(download_tasks)} new files to folder {title}.")
