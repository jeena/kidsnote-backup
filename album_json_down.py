#!/usr/bin/env python3

#thanks to goodhobak from https://www.clien.net/
#requre: requests Pillow piexif
#use:
#1. get json from api in webpage
#2. save json
#commit : 파일의 생성일, 수정일 수정
import json
import os
import requests
from PIL import Image
import piexif
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from datetime import datetime
import os
import pywintypes, win32file, win32con

def convert_to_degrees(value):
    """Convert decimal coordinate to degrees, minutes, and seconds tuple."""
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = (value - degrees - minutes / 60) * 3600
    seconds_numerator = int(seconds * 100)
    seconds_denominator = 100

    return ((degrees, 1), (minutes, 1), (seconds_numerator, seconds_denominator))

def add_exif_data(image_path, title, content, modified_time):
    # Load the image
    img = Image.open(image_path)

    # Check if the image has existing EXIF data
    if 'exif' in img.info:
        exif_dict = piexif.load(img.info['exif'])
    else:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

    # Prepare the formatted time
    formatted_time = modified_time.strftime("%Y:%m:%d %H:%M:%S")

    # Check if DateTimeOriginal exists and if it matches the intended value
    existing_date_time_original = exif_dict['Exif'].get(piexif.ExifIFD.DateTimeOriginal, None)
    if existing_date_time_original and existing_date_time_original != formatted_time:
        #print(f"Skipping {image_path}: DateTimeOriginal does not match the intended value.")
        img.close()  # Close the image and skip further processing
        return

    # Update the datetime fields
    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = formatted_time
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = formatted_time
    exif_dict['0th'][piexif.ImageIFD.DateTime] = formatted_time

    # User comment
    user_comment = f"Title: {title}\nContent: {content}"
    encoded_comment = user_comment.encode('utf-8')
    exif_dict['0th'].setdefault(piexif.ImageIFD.ImageDescription, encoded_comment)

    # Convert EXIF data to bytes and save the image
    exif_bytes = piexif.dump(exif_dict)
    img.save(image_path, exif=exif_bytes)

    # Close the image
    img.close()


def add_xmp_data(image_path, title, content, modified_time):
    # Open the image
    img = Image.open(image_path)

    # Create XMP data
    xmp_template = f"""
    <x:xmpmeta xmlns:x="adobe:ns:meta/">
     <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
      <rdf:Description rdf:about=""
        xmlns:dc="http://purl.org/dc/elements/1.1/"
        xmlns:xmp="http://ns.adobe.com/xap/1.0/">
       <dc:title>{title}</dc:title>
       <dc:description>{content}</dc:description>
       <xmp:ModifyDate>{modified_time.strftime("%Y-%m-%dT%H:%M:%S")}</xmp:ModifyDate>
       <xmp:CreateDate>{modified_time.strftime("%Y-%m-%dT%H:%M:%S")}</xmp:CreateDate>
      </rdf:Description>
     </rdf:RDF>
    </x:xmpmeta>
    """
    xmp_data = bytes(xmp_template, 'utf-8')

    # Check if the image has existing XMP data and append the new data
    if "APP1" in img.info and b'http://ns.adobe.com/xap/1.0/' in img.info["APP1"]:
        existing_xmp_index = img.info["APP1"].find(b'http://ns.adobe.com/xap/1.0/')
        if existing_xmp_index != -1:
            # Extract existing XMP data and create a combined XMP
            existing_xmp_data = img.info["APP1"][existing_xmp_index:]
            combined_xmp_data = existing_xmp_data.strip(b' ') + b' ' + xmp_data
        else:
            combined_xmp_data = xmp_data
    else:
        combined_xmp_data = xmp_data

    # Save the image with new metadata
    img.save(image_path, "jpeg", exif=img.info.get('exif'), xmp=combined_xmp_data)

    # Close the image
    img.close()

def change_file_times(filename, created_time, modified_time):
    ctime = pywintypes.Time(created_time)
    mtime = pywintypes.Time(modified_time)

    handle = win32file.CreateFile(filename, win32con.GENERIC_WRITE, 0, None, win32con.OPEN_EXISTING, 0, None)
    win32file.SetFileTime(handle, ctime, None, mtime)
    handle.Close()

    
# 파일 읽기
with open("album.json", "r", encoding='utf-8') as file:
    data = json.load(file)

# 앨범 처리
for album in data['results']:
    # 폴더 생성
    date_str = album['created'][:10]  # "YYYY-MM-DD"
    month_str = album['created'][:7]  # "YYYY-MM"
        
    folder_name = f"Album\Album-{month_str}\{date_str}"
    os.makedirs(folder_name, exist_ok=True)

    # 앨범 설명 저장
    description_path = os.path.join(folder_name, "album-description.txt")
    if os.path.exists(description_path):
        #print (f"'{date_str}' is exist");
        continue
        
    created_time_utc = datetime.strptime(album['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
    modified_time_utc = datetime.strptime(album['modified'], "%Y-%m-%dT%H:%M:%S.%fZ")

    # Add 9 hours to convert UTC to Seoul time (UTC+09:00)
    seoul_offset = timedelta(hours=9)
    created_time = created_time_utc + seoul_offset
    modified_time = modified_time_utc + seoul_offset

    file = open(os.path.join(description_path), "w", encoding='utf-8')
    file.write(f"Title: {album['title']}\n")
    file.write(f"Content: {album['content']}\n")
    file.write(f"json: {album}\n")
    file.close()
    # Change times
    change_file_times(description_path, created_time, modified_time)

    # 비디오 처리
    if album['attached_video']:
        video_url = album['attached_video']
        video_response = requests.get(video_url)
        video_path = os.path.join(folder_name, f"KidsNote_Vidio_{album['id']}.MP4")
        file =  open(video_path, "wb");
        file.write(video_response.content)
        file.close();
        # Change times
        change_file_times(video_path, created_time, modified_time)

    # 이미지 처리
    for index, image in enumerate(album['attached_images'], start=1):
        image_url = image['original']
        image_response = requests.get(image_url)
        image_path = os.path.join(folder_name, f"KidsNote_Photo_{date_str}-{index}.jpg")
        file = open(image_path, "wb")
        file.write(image_response.content)
        file.close();
        # Change times
        change_file_times(image_path, created_time, modified_time)

        # EXIF 데이터 추가
        try:
            add_exif_data(image_path, album['title'], album['content'], modified_time)
            add_xmp_data(image_path, album['title'], album['content'], modified_time)
        except Exception as e:
            print(f"EXIF error for '{folder_name}': {e}")
    
    print(f"Album '{folder_name}' processed.")

print("All albums have been processed.")
