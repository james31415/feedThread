import sys
import collections
import urllib.request
import os
import feedparser
import re
import time

import yaml

feed_conf = "feeds.conf"
feed_url = sys.argv[1]
if feed_url[0:4] == "feed":
    feed_url = feed_url[5:]

def cleanTitle(dirty_title):
    return re.sub("[^\w-]", " ", dirty_title).strip()

feed_title = cleanTitle(feedparser.parse(urllib.request.urlopen(feed_url)).feed.title)

Present = False
list_of_feeds = yaml.load(open(feed_conf, "r"))
for feed in list_of_feeds:
    if feed["Feed"]["URL"] == feed_url:
        Present = True

if not Present:
    list_of_feeds.append({"Feed": { "Name": feed_title, "URL": feed_url } })

yaml.dump(list_of_feeds, open(feed_conf, "w"), default_flow_style=False)
