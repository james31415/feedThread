import sys
import collections
import urllib.request
import os
import feedparser
import re
import time
import sys

import requests
import yaml

feed_conf = "feeds.conf"
USER_AGENT = 'FeedThread/1.0 (https://github.com/james31415/feedthread)'
HEADERS = {'User-Agent': USER_AGENT}

feed_url = sys.argv[1]
if feed_url[0:4] == "feed":
    feed_url = feed_url[5:]

def cleanTitle(dirty_title):
    return re.sub("[^\w-]", " ", dirty_title).strip()

try:
    r = requests.get(feed_url, headers = HEADERS)
except requests.ConnectionError as e:
    print("Feed {} failed: {}".format(name, e.response))
    sys.exit(1)

feed_title = cleanTitle(feedparser.parse(r.text).feed.title)

Present = False
list_of_feeds = yaml.load(open(feed_conf, "r"))
for feed in list_of_feeds["Feeds"]:
    if feed["URL"] == feed_url:
        Present = True

if not Present:
    list_of_feeds["Feeds"].append({ "Name": feed_title, "URL": feed_url })
    list_of_feeds["Playlist"].append(feed_title)

yaml.dump(list_of_feeds, open(feed_conf, "w"), default_flow_style=False)
