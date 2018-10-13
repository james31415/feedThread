#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import hashlib
import os
import re
import urllib.parse
import sys
from enum import Enum

import feedparser
import requests
import yaml

class FetchStyle(Enum):
    Latest = 1
    InOrder = 2

CHUNK_SIZE = 1024 * 1024
FORMATS = 'mp3|wma|aa|ogg|flac'
USER_AGENT = 'FeedThread/1.0 (https://github.com/james31415/feedthread)'
HEADERS = {'User-Agent': USER_AGENT}

todaysDate = datetime.now()

def first_date(entries, order = FetchStyle.Latest):
    if order == FetchStyle.Latest:
        return max([datetime(*(ent.updated_parsed[0:6])) for ent in entries if ent.updated_parsed is not None])
    else:
        return min([datetime(*(ent.updated_parsed[0:6])) for ent in entries if ent.updated_parsed is not None])

def get_entrytime(entry):
    try:
        return datetime(*(entry.updated_parsed[0:6]))
    except:
        return None

def download_url(url, dirname):
    try:
        r = requests.get(url, stream=True, headers = HEADERS)
    except:
        print("Unexpected error:", sys.exc_info()[0])
        return False

    try:
        total_size = int(r.headers['Content-Length'])
    except KeyError:
        print(r.headers)
        total_size = 0

    try:
        base_name = urllib.parse.unquote_plus(re.search('.*/([^/]*\.(?:'+FORMATS+'))', url).group(1))
        base_name = re.sub('[^\w\-\.]', '_', base_name).strip()
        filename = os.path.join(dirname, base_name)
    except AttributeError:
        print("Couldn't find {} in {}. Is the feed valid?".format(FORMATS, url))
        r.close()
        return False

    if not os.path.exists(dirname):
        os.mkdir(dirname)

    if os.path.exists(filename):
        print("{} exists".format(filename))
        r.close()
        return True

    print('Downloading {} from {}'.format(filename, url))

    downloaded_size = 0
    with open(filename, 'wb') as fd:
        for chunk in r.iter_content(CHUNK_SIZE):
            downloaded_size += fd.write(chunk)

            if total_size > 0:
                print("{:6.2f}%".format((downloaded_size / total_size) * 100), end='\r')

    print('Downloaded {}'.format(filename))

    return True

if __name__ == '__main__':
    CONF_FILE = 'feeds.conf'
    PODCAST_DIRECTORY = 'Podcasts'

    feeds = []
    casts = []

    if not os.path.exists(PODCAST_DIRECTORY):
        os.mkdir(PODCAST_DIRECTORY)

    if os.path.exists(CONF_FILE):
        with open(CONF_FILE) as confFile:
            feeds = yaml.load(confFile)

    for index, feed in enumerate(feeds["Feeds"]):
        name = feed["Name"]
        url = feed["URL"]
        fetch_style = feed.get("FetchStyle", FetchStyle.Latest)
        number_to_save = feed.get("NumberToSave", 2)

        try:
            r = requests.get(url, headers = HEADERS)
        except requests.exceptions.RequestException as e:
            print("Feed {} failed: {}".format(name, e))
            continue

        if r.status_code != requests.codes.ok:
            print('{} failed with {} code'.format(name, r.status_code))
            continue

        rssfile = feedparser.parse(r.text)

        try:
            tname = rssfile['feed'].get('title') or name
            name = re.sub('[^\w-]', ' ', tname).strip()
        except KeyError:
            name = hashlib.sha224(url.encode()).hexdigest()

        dirname = os.path.join(PODCAST_DIRECTORY, name)

        number_existing = 0
        if os.path.exists(dirname):
            number_existing = len(os.listdir(dirname))

        number_remaining = number_to_save - number_existing

        if number_remaining <= 0:
            continue

        if feed.get("Date") is None:
            feed["Date"] = first_date(rssfile.entries, fetch_style)-timedelta(days=2)

        print('Getting entries for {}'.format(name))
        entries = filter(get_entrytime, rssfile.entries)
        entries = sorted(entries, key = lambda x: get_entrytime(x))
        entries = list(filter(lambda x: get_entrytime(x) > feed["Date"], entries))
        entries_to_get = entries[:number_remaining]

        for entry in entries_to_get:
            try:
                enclosures = entry.enclosures
            except AttributeError:
                continue

            entrytime = get_entrytime(entry)

            for enclosure in enclosures:
                casts.append((index, enclosure.href, dirname, entrytime))

    for index, url, dirname, entrytime in casts:
        if download_url(url, dirname):
            feeds["Feeds"][index]["Date"] = max(feeds["Feeds"][index]["Date"], entrytime)

    print('Cleaning up.')

    with open(CONF_FILE, 'w') as confFile:
        yaml.dump(feeds, confFile, default_flow_style=False)
