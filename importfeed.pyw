from __future__ import print_function
import sys
import collections
import urllib.request
import os
import msvcrt
import feedparser
import re
import time

feed_list = "feeds.list"
feed = sys.argv[1]
if feed[0:4] == "feed":
    feed = feed[5:]

def cleanTitle(dirty_title):
    return re.sub("[^\w-]", " ", dirty_title).strip()

feed_title = cleanTitle(feedparser.parse(urllib.request.urlopen(feed)).feed.title)

list_of_feeds = collections.defaultdict(list)
this_feed_title = ""

with open(feed_list) as fl:
    for line in fl:
        if line[0] == '#':
            this_feed_title = line[2:].strip()
        else:
            list_of_feeds[this_feed_title].append(line.strip())

if feed not in list_of_feeds[feed_title]:
    list_of_feeds[feed_title].append(feed)

with open(feed_list, "w") as fl:
    for a in sorted(list_of_feeds.keys()):
        print("# {0}".format(a), file=fl)
        for b in sorted(list_of_feeds[a]):
            print("{0}".format(b), file=fl)
