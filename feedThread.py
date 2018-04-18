#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import hashlib
import os
import re
import urllib.parse
import sys

import feedparser
import requests

CHUNK_SIZE = 1024 * 1024
FORMATS = 'mp3|wma|aa|ogg|flac'
USER_AGENT = 'FeedThread/1.0 (https://github.com/james31415/feedthread)'
HEADERS = {'User-Agent': USER_AGENT}

todaysDate = datetime.now()

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
        filename = os.path.join(dirname, urllib.parse.unquote(re.search('.*/([^/]*\.(?:'+FORMATS+'))', url).group(1)))
    except AttributeError:
        print("Couldn't find {} in {}. Is the feed valid?".format(FORMATS, url))
        return False

    if not os.path.exists(filename):
        print('Downloading {} from {}'.format(filename, url))

        downloaded_size = 0
        with open(filename, 'wb') as fd:
            for chunk in r.iter_content(CHUNK_SIZE):
                downloaded_size += fd.write(chunk)

                if total_size > 0:
                    print("{:6.2f}%".format((downloaded_size / total_size) * 100), end='\r')

        print('Downloaded {}'.format(filename))
    else:
        print("{} exists".format(filename))

    return True

if __name__ == '__main__':
    LOG_FILE = 'feeds.log'
    LIST_FILE = 'feeds.list'
    PODCAST_DIRECTORY = 'Podcasts'

    loggedfeeds = {}
    feeds = []
    casts = []

    if not os.path.exists(PODCAST_DIRECTORY):
        os.mkdir(PODCAST_DIRECTORY)

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE) as feedlog:
            loggedfeeds.update({feed: datetime.strptime(lastdate, "%Y-%m-%dT%H:%M:%S") for feed, lastdate in
                [lines.strip().split(',') for lines in feedlog]})

    days_back = 7
    with open(LIST_FILE) as feedlist:
        for lines in feedlist:
            if lines[0] == '#':
                name = lines[2:].strip()
                days_back = 7
                continue
            elif lines[0] == "!":
                days_back = int(lines[1:].strip())
                continue

            feeds.append((name, lines.strip(), days_back))

    for name, feed, days_back in feeds:
        try:
            r = requests.get(feed, headers = HEADERS)
        except requests.ConnectionError as e:
            print("Feed {} failed: {}".format(name, e.response))

        if r.status_code != requests.codes.ok:
            print('{} failed with {} code'.format(name, r.status_code))
            continue

        rssfile = feedparser.parse(r.text)

        try:
            tname = rssfile['feed'].get('title') or name
            name = re.sub('[^\w-]', ' ', tname).strip()
        except KeyError:
            name = hashlib.sha224(feed.encode()).hexdigest()

        dirname = os.path.join(PODCAST_DIRECTORY, name)

        print('Getting entries for {}'.format(name))
        for entry in rssfile.entries:
            try:
                entrytime = datetime(*(entry.updated_parsed[0:6]))
            except:
                print('Could not parse date for {}'.format(name))
                continue

            try:
                if loggedfeeds[dirname] >= entrytime:
                    continue
            except KeyError:
                loggedfeeds[dirname] = max([datetime(*(ent.updated_parsed[0:6])) for ent in rssfile.entries if ent.updated_parsed is not None])-timedelta(days=2)
                if loggedfeeds[dirname] >= entrytime:
                    continue

            if abs(entrytime - todaysDate) > timedelta(days=days_back):
                loggedfeeds[dirname] = max(entrytime, loggedfeeds[dirname])
                continue

            try:
                enclosures = entry.enclosures
            except AttributeError:
                continue

            for enclosure in enclosures:
                if not os.path.exists(dirname):
                    os.mkdir(dirname)

                casts.append((enclosure.href, dirname, entrytime))

    for url, dirname, entrytime in casts:
        if download_url(url, dirname):
            loggedfeeds[dirname] = max(loggedfeeds[dirname], entrytime)

    print('Cleaning up.')

    with open(LOG_FILE, 'w') as feedlog:
        for key, value in list(loggedfeeds.items()):
            feedlog.write("{0},{1}\n".format(key,value.isoformat()))
