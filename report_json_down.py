#!/usr/bin/env python3

import os
import sys
import json
import datetime
import requests
from pathlib import Path
from PIL import Image
import piexif
from dotenv import load_dotenv

load_dotenv()

STORAGE_PATH = os.getenv("KIDSNOTE_STORAGE_PATH")
if not STORAGE_PATH:
    print("Error: KIDSNOTE_STORAGE_PATH is not set.")
    sys.exit(1)

def convert_to_degrees(value):
    degrees = int(value)
    minutes = int((value - degrees) * 60)
    seconds = (value - degrees - minutes / 60) * 3600
    return ((degrees, 1), (minutes, 1), (int(seconds * 100), 100))

def add_exif_data(image_path, title, content, location_str=None):
    try:
        img = Image.open(image_path)
        if 'exif' in img.info:
            exif_dict = piexif.load(img.info['exif'])
        else:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        if location_str:
            try:
                latitude, longitude = map(float, location_str.split(','))
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitudeRef] = 'N' if latitude >= 0 else 'S'
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitudeRef] = 'E' if longitude >= 0 else 'W'
                exif_dict['GPS'][piexif.GPSIFD.GPSLatitude] = convert_to_degrees(abs(latitude))
                exif_dict['GPS'][piexif.GPSIFD.GPSLongitude] = convert_to_degrees(abs(longitude))
            except Exception as e:
                print(f"Invalid location format '{location_str}': {e}")

        comment = f"Title: {title}\nContent: {content}"
        encoded_comment = b'ASCII\x00\x00\x00' + comment.encode('utf-8')
        exif_dict['Exif'][piexif.ExifIFD.UserComment] = encoded_comment

        exif_bytes = piexif.dump(exif_dict)
        img.save(image_path, exif=exif_bytes)
        img.close()
    except Exception as e:
        print(f"EXIF error for {image_path}: {e}")

def get_creation_datetime(image_path):
    try:
        img = Image.open(image_path)
        exif_bytes = img.info.get('exif')
        if not exif_bytes:
            return None
        exif_dict = piexif.load(exif_bytes)
        dt_bytes = exif_dict['Exif'].get(piexif.ExifIFD.DateTimeOriginal)
        if not dt_bytes:
            return None
        dt_str = dt_bytes.decode('utf-8')  # e.g. "2025:07:12 14:32:45"
        dt = datetime.datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
        return dt
    except Exception:
        return None

with open("report.json", "r", encoding='utf-8') as file:
    data = json.load(file)

# Group reports by date
reports_by_date = {}
for report in data['results']:
    date = datetime.datetime.strptime(report['created'], "%Y-%m-%dT%H:%M:%S.%fZ").date()
    reports_by_date.setdefault(date, []).append(report)

for date, reports in sorted(reports_by_date.items()):
    folder = Path(STORAGE_PATH).expanduser() / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}"
    folder.mkdir(parents=True, exist_ok=True)

    for report_index, report in enumerate(reports, start=1):
        desc_path = folder / f"report-{report_index}-description.txt"
        if desc_path.exists():
            print(f"'{desc_path.name}' exists")
            continue

        with open(desc_path, "w", encoding='utf-8') as f:
            f.write(f"Title: {report['class_name']}-{report['child_name']}\n")
            f.write(f"Weather: {report['weather']}\n")
            f.write(f"Content: {report['content']}\n")

        if report.get('attached_video'):
            try:
                r = requests.get(report['attached_video'])
                r.raise_for_status()
                with open(folder / f"V_{report_index}.MP4", "wb") as f:
                    f.write(r.content)
            except requests.RequestException as e:
                print(f"Video download failed: {e}")

        for img_index, image in enumerate(report.get('attached_images', []), start=1):
            try:
                r = requests.get(image['original'])
                r.raise_for_status()
                temp_path = folder / f"temp_{report_index}_{img_index}.jpg"
                with open(temp_path, "wb") as f:
                    f.write(r.content)

                add_exif_data(temp_path, report['child_name'], report['content'], report.get('location'))

                dt = get_creation_datetime(temp_path)
                if dt:
                    date_str = dt.strftime("%Y-%m-%d_%H-%M")
                else:
                    date_str = date.strftime("%Y-%m-%d")

                final_name = f"P{report_index}_{date_str}.jpg"
                final_path = folder / final_name

                temp_path.rename(final_path)

            except requests.RequestException as e:
                print(f"Image download failed: {e}")

    print(f"Report {report_index} (ID: {report['id']}) saved in '{folder}'")

print("All reports have been processed.")

