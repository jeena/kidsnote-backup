#!/usr/bin/env python3

#thanks to goodhobak from https://www.clien.net/
#requre: requests Pillow piexif
#use:
#1. get json from api in webpage
#2. save json
import json
from pathlib import Path
import os
import requests
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import datetime
import piexif
from xml.etree import ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

STORAGE_PATH = os.getenv("KIDSNOTE_STORAGE_PATH")

if not STORAGE_PATH:
    print("Error: KIDSNOTE_STORAGE_PATH is not set.")
    sys.exit(1)

def convert_to_degrees(value):
    """Convert decimal coordinate to degrees, minutes, and seconds tuple."""
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = (value - degrees - minutes / 60) * 3600
    seconds_numerator = int(seconds * 100)
    seconds_denominator = 100

    return ((degrees, 1), (minutes, 1), (seconds_numerator, seconds_denominator))

def add_exif_data(image_path, title, content, location):
    # Load the image
    img = Image.open(image_path)

    # Check if the image has 'exif' data
    if 'exif' in img.info:
        exif_dict = piexif.load(img.info['exif'])
    else:
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}


    # GPS coordinates
    latitude, longitude = map(float, location.split(','))
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'N' if latitude >= 0 else 'S'
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'E' if longitude >= 0 else 'W'
    exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = convert_to_degrees(abs(latitude))
    exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = convert_to_degrees(abs(longitude))

    # User comment
    user_comment = f"Title: {title}\nContent: {content}"
    encoded_comment = user_comment.encode('utf-8')
    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = encoded_comment

    # Convert EXIF data to bytes and save the image
    exif_bytes = piexif.dump(exif_dict)
    img.save(image_path, exif=exif_bytes)

    # Close the image
    img.close()

def create_xmp_data(title, content, location):
    xmp_template = f"""
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
        <rdf:Description rdf:about=""
            xmlns:dc="http://purl.org/dc/elements/1.1/">
            <dc:title>{title}</dc:title>
            <dc:description>{content}</dc:description>
            <dc:location>{location}</dc:location>
        </rdf:Description>
    </rdf:RDF>
    """
    return xmp_template

def add_xmp_data(image_path, title, content, location):
    # Open the image
    img = Image.open(image_path)
    
    xmp_data = create_xmp_data(title, content, location)
    xmp_bytes = xmp_data.encode('utf-8')

    # Check if the image has existing metadata and append XMP data
    if "APP1" in img.info:
        existing_metadata = img.info["APP1"]
        new_metadata = existing_metadata + b'\n' + xmp_bytes
    else:
        new_metadata = xmp_bytes


    # Save the image with new metadata
    img.save(image_path, "jpeg", exif=new_metadata)

    # Close the image
    img.close()

# 파일 읽기
with open("report.json", "r", encoding='utf-8') as file:
    data = json.load(file)

# 앨범 처리
for report in data['results']:
    # 폴더 생성
    date = datetime.datetime.strptime(report['created'], "%Y-%m-%dT%H:%M:%S.%fZ")
    date_str = date.date()
    folder_name = Path(STORAGE_PATH).expanduser() / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"
    folder_name.mkdir(parents=True, exist_ok=True)

    # 앨범 설명 저장
    description_path = os.path.join(folder_name, "report-description.txt")
    if os.path.exists(description_path):
        print (f"'{date_str}' exists");
        continue
    with open(os.path.join(description_path), "w", encoding='utf-8') as file:
        file.write(f"Title: {report['class_name']}-{report['child_name']}\n")
        file.write(f"Weather: {report['weather']}\n")
        file.write(f"Content: {report['content']}\n")

    # 비디오 처리
    if report['attached_video']:
        video_url = report['attached_video']
        video_response = requests.get(video_url)
        video_path = os.path.join(folder_name, f"V_{report['id']}.MP4")
        with open(video_path, "wb") as file:
            file.write(video_response.content)

    # 이미지 처리
    for index, image in enumerate(report['attached_images'], start=1):
        image_url = image['original']
        image_response = requests.get(image_url)
        image_path = os.path.join(folder_name, f"P_{date_str}-{index}.jpg")
        with open(image_path, "wb") as file:
            file.write(image_response.content)
        try:
            # EXIF 데이터 추가
            add_exif_data(image_path, report['child_name'], report['content'], "55.55555, 555.5555")
            # XMP 데이터 추가
            #add_xmp_data(image_path, report['child_name'], report['content'], "55.5555, 555.555555")
        except:
            print(f"'{folder_name}' : exif error")
    print(f"Report '{folder_name}' processed.")

print("All reports have been processed.")
