# -*- coding: utf-8 -*-
"""
Created on Fri Jun 04 17:37:05 2010

@author: Owner
"""

import os
import datetime
import re
import urllib
import urllib2
import Queue as queue
import threading
import hashlib
import collections
import msvcrt
import feedparser

#podcast_directory = "D:\Owner\Music\Audio Files\Podcasts" 
log_file = "feeds.log"
list_file = "feeds.list"
number_of_threads = 4
formats = "mp3|wma|aa|ogg|flac"
global_timeout = 60

thread_data = collections.defaultdict(dict)
thread_finished = {}
can_quit = threading.Event()
want_to_quit = threading.Event()

feeds = queue.Queue(0)
urls = queue.Queue(0)

def fail_url(name, e):
    if hasattr(e, 'reason'):
        print("[{0}] Failed: {1}".format(name,
            e.reason))
    elif hasattr(e, 'code'):
        print("[{0}] Failed: {1}".format(name,
            e.code))

def get_urls():
    my_thread = threading.current_thread()
    my_id = my_thread.ident
    thread_data[my_id]['url'] = ''

    while not want_to_quit.is_set() and not urls.empty():
        name, feed = urls.get()

        my_thread.name = "u{0}".format(name)
        thread_data[my_id]['url'] = feed
        try:
            rssfile = feedparser.parse(
                    urllib2.urlopen(feed, None, global_timeout))
        except urllib2.URLError as e:
            print(feed)
            fail_url(name, e)
            continue

        try:
            tname = rssfile['feed'].get('title') or name
            name = re.sub("[^\w-]"," ", tname).rstrip()
        except KeyError:
            name = hashlib.sha224(feed.encode()).hexdigest()

        dirname = os.path.join("Podcasts", name)
        
        print("Getting entries for {0}".format(name))
        for entry in rssfile.entries:
            if want_to_quit.is_set():
                break
            try:
                entrytime = datetime.datetime(
                    *(entry.updated_parsed[0:6])).toordinal()
            except:
                continue

            try:
                if loggedfeeds[dirname] >= entrytime:
                    continue
            except KeyError:
                loggedfeeds[dirname] = (datetime.date.today() -
                        datetime.timedelta(weeks=1)).toordinal()

            try:
                enclosures = entry.enclosures
            except AttributeError:
                continue
            for enclosure in enclosures:
                try:
                    resource = urllib2.urlopen(urllib.quote(enclosure.href, '/:'), None,
                            global_timeout)
                except urllib2.URLError as e:
                    print(enclosure.href)
                    fail_url(my_thread.name, e)
                    continue

                url = resource.geturl()
                try:
                    filename = urllib.unquote(re.search('.*/([^/]*\.(?:'+formats+'))',
                            url).group(1))
                except AttributeError:
                    continue
                print("Storing {0} for {1} ({2})".format(filename, name, datetime.datetime(
                    *(entry.updated_parsed[0:6]))))
                feeds.put((name, url, dirname, filename, entrytime))

def feed_thread():
    my_thread = threading.current_thread()
    my_id = my_thread.ident
    thread_data[my_id]['reading'] = 0
    thread_data[my_id]['size'] = -1
    thread_finished[my_id] = threading.Event()

    def reporthook(block_count, block_size, total_size):
        thread_data[my_id]['reading'] = block_count * block_size
        thread_data[my_id]['size'] = total_size
    
    while not want_to_quit.is_set() and not (urls.empty() and feeds.empty()):
        if feeds.empty():
            continue

        try:
            name, url, dirname, filename, entrytime = feeds.get(False)
        except:
            continue
        my_thread.name = "f{0}".format(name)

        temptime = loggedfeeds[dirname]

        if not os.path.exists(os.path.join(dirname, filename)):
            if not os.path.exists(dirname):
                os.mkdir(dirname)

            print("[{0}] Downloading: {1}".format(my_thread.name,
                    filename))

            try:
                urllib.urlretrieve(url, filename=os.path.join(dirname, filename), reporthook=reporthook)
            except urllib.ContentTooShortError:
                os.remove(os.path.join(dirname, filename))
        else:
            print("[{0}] {1} exists.".format(my_thread.name, 
                    filename))

        loggedfeeds[dirname] = max(temptime, entrytime)
        urls.task_done()
        print("[{0}] Done".format(my_thread.name))

    thread_finished[my_id].set()
    print("[{0}] Finished.".format(my_thread.name)) 

    if False not in map(lambda x: x.is_set(), thread_finished.values()):
        print("Really quitting.")
        can_quit.set()

def check_key():
    while True:
        key = msvcrt.getch()
        if key.lower() == b'q':
            print("Quitting early.")
            want_to_quit.set()
        else:
            print("{0} items in feeds".format(feeds.qsize()))
            print("{0} items in urls".format(urls.qsize()))
            print("want_to_quit: {0}".format(want_to_quit.is_set()))
            print("can_quit: {0}".format(can_quit.is_set()))
            print("feeds.empty(): {0}".format(feeds.empty()))
            print("urls.empty(): {0}".format(urls.empty()))

            active_threads = threading.enumerate()
            print("{0} active threads:".format(len(active_threads)))
            for active in active_threads:
                active_dict = thread_data[active.ident]
                if len(active_dict) == 0:
                    print("\t{0}".format(active.name))

                elif 'size' in active_dict:
                    if active_dict['size'] != -1:
                        print("\t{0}: {1}% [{2} / {3}]".format(active.name,
                            round(active_dict['reading'] * 100.0 / active_dict['size'], 1),
                            active_dict['reading'], active_dict['size']))
                    else:
                        print("\t{0}: {1} read".format(active.name, active_dict['reading']))

                elif 'url' in active_dict:
                    print("\t{0}: {1}".format(active.name, active_dict['url']))

            print("\n")


if os.path.exists(log_file):
    with open(log_file) as feedlog:
        loggedfeeds = {feed: int(lastdate) for feed,lastdate in
                [lines.split(',') for lines in feedlog]}

with open(list_file) as feedlist:
    for lines in feedlist:
        if lines[0] == "#":
            name = lines[2:].strip()
            continue

        urls.put((name, lines.strip()))

print("Starting threads.")

for i in range(number_of_threads):
    t = threading.Thread(target=feed_thread)
    t.name = 'ItemGet{0}'.format(i)
    t.start()

    t = threading.Thread(target=get_urls)
    t.name = 'GetUrls{0}'.format(i)
    t.start()

t = threading.Thread(target=check_key)
t.name = 'Input'
t.daemon = True
t.start()

can_quit.wait()

print("Cleaning up.")

with open(log_file, "w") as feedlog:
    for key, value in loggedfeeds.items():
        feedlog.write("{0},{1}\n".format(key,value))
