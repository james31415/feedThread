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
import socket
import multiprocessing
import Queue
import hashlib
import msvcrt
import time
import feedparser

log_file = "feeds.log"
list_file = "feeds.list"
number_of_threads = 4
formats = "mp3|wma|aa|ogg|flac"
global_timeout = 60
socket.setdefaulttimeout(global_timeout)

today = datetime.date.today().toordinal()

def fail_url(name, e):
    if hasattr(e, 'reason'):
        print("[{0}] Failed (reason): {1}".format(name,
            e.reason))
    elif hasattr(e, 'code'):
        print("[{0}] Failed (code): {1}".format(name,
            e.code))

def get_urls(statuses, loggedfeeds, can_quit, want_to_quit, hard_quit, feeds, urls):
    def update_statuses(thread_data):
        return("[{0}] {1}".format(thread_data['name'], thread_data['url']))

    thread_data = dict()
    my_thread = multiprocessing.current_process()
    my_id = my_thread.pid
    statuses[my_id] = "[{0}]".format(my_thread.name)
    print("[{0}] Started.".format(my_id))
    thread_data['url'] = ''

    while not (want_to_quit.is_set() or urls.empty() or hard_quit.is_set()):
        name, feed, days_back = urls.get()

        cont = False

        my_thread.name = "u{0}".format(name)
        thread_data['name'] = my_thread.name
        thread_data['url'] = feed
        statuses[my_id] = update_statuses(thread_data)
        try:
            rssfile = feedparser.parse(
                    urllib2.urlopen(urllib.quote(feed, safe="%/:=&?~#+!$,;'@()*[]"), None, global_timeout))
        except urllib2.URLError as e:
            print(feed)
            fail_url(name, e)
            urls.task_done()
            continue

        try:
            tname = rssfile['feed'].get('title') or name
            name = re.sub("[^\w-]"," ", tname).rstrip()
        except KeyError:
            name = hashlib.sha224(feed.encode()).hexdigest()

        dirname = os.path.join("Podcasts", name)

        print("Getting entries for {0}".format(name))
        for entry in rssfile.entries:
            if cont:
                break

            if want_to_quit.is_set() or hard_quit.is_set():
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
                loggedfeeds[dirname] = max([datetime.datetime(*(ent.updated_parsed[0:6])).toordinal() for ent in rssfile.entries if ent.updated_parsed is not None])-2
                if loggedfeeds[dirname] >= entrytime:
                    continue

            if abs(entrytime - today) > days_back:
                loggedfeeds[dirname] = max(entrytime, loggedfeeds[dirname])
                continue

            try:
                enclosures = entry.enclosures
            except AttributeError:
                continue
            for enclosure in enclosures:
                try:
                    resource = urllib2.urlopen(urllib.quote(enclosure.href, safe="%/:=&?~#+!$,;'@()*[]"), None, global_timeout)
                except urllib2.URLError as e:
                    print(enclosure.href)
                    fail_url(my_thread.name, e)
                    cont = True
                    break

                url = resource.geturl()
                try:
                    filename = urllib.unquote(re.search('.*/([^/]*\.(?:'+formats+'))',
                            url).group(1))
                except AttributeError:
                    continue
                print("Storing {0} for {1}".format(filename, name))
                feeds.put((name, url, dirname, filename, entrytime))
        urls.task_done()

    if not (want_to_quit.is_set() or hard_quit.is_set()):
        urls.join()
        feeds.join()

    can_quit.set()


def feed_thread(statuses, loggedfeeds, can_quit, want_to_quit, hard_quit, feeds, urls):
    def update_statuses(thread_data):
        return("[{0}] {1:.1f}% {2}/{3}".format(thread_data['name'], thread_data['reading'] / float(thread_data['size']) * 100, thread_data['reading'], thread_data['size']))

    thread_data = dict()
    my_thread = multiprocessing.current_process()
    my_id = my_thread.pid
    statuses[my_id] = "[{0}]".format(my_thread.name)
    print("[{0}] Started.".format(my_id))
    thread_data['reading'] = 0
    thread_data['size'] = -1

    def reporthook(block_count, block_size, total_size):
        thread_data['reading'] = block_count * block_size
        thread_data['size'] = total_size
        statuses[my_id] = update_statuses(thread_data)
        if hard_quit.is_set():
            raise urllib.ContentTooShortError

    while True:
        print("[{0}] Getting".format(my_thread.name))
        name, url, dirname, filename, entrytime = feeds.get()
        my_thread.name = "f{0}".format(name)
        print("[{0}] Got".format(my_thread.name))
        thread_data['name'] = my_thread.name
        statuses[my_id] = update_statuses(thread_data)

        if not want_to_quit.is_set():
            temptime = loggedfeeds[dirname]

            if not os.path.exists(os.path.join(dirname, filename)):
                if not os.path.exists(dirname):
                    os.mkdir(dirname)

                print("[{0}] Downloading: {1}".format(my_thread.name,
                        filename))

                tries = 0
                max_tries = 5

                while True:
                    try:
                        if tries > 0:
                            if tries <= max_tries:
                                print("[{0}] Trying again: {1}".format(my_thread.name, filename))
                            else:
                                print("[{0}] Failed: {1}".format(my_thread.name, filename))
                                break
                        urllib.urlretrieve(url, filename=os.path.join(dirname, filename), reporthook=reporthook)
                        break
                    except urllib.ContentTooShortError:
                        print("[{0}] Content too short: {1}".format(my_thread.name, filename))
                        os.remove(os.path.join(dirname, filename))
                        feeds.task_done()
                        tries += 1
                    except IOError:
                        print("[{0}] Problem with connection: {1}".format(my_thread.name, filename))
                        os.remove(os.path.join(dirname, filename))
                        feeds.task_done()
                        tries += 1
            else:
                print("[{0}] {1} exists.".format(my_thread.name, 
                        filename))

            loggedfeeds[dirname] = max(temptime, entrytime)
        feeds.task_done()
        print("[{0}] Done".format(my_thread.name))
    print("[{0}] Quitting".format(my_thread.name))

def check_key(statuses, can_quit, want_to_quit, hard_quit, feeds, urls):
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key.lower() == b'q':
                print("Quitting early.")
                want_to_quit.set()
            elif key.lower() == b'h':
                print("Quitting now.")
                hard_quit.set()
                can_quit.set()
            else:
                print("{0} items in feeds".format(feeds.qsize()))
                print("{0} items in urls".format(urls.qsize()))
                print("want_to_quit: {0}".format(want_to_quit.is_set()))
                print("can_quit: {0}".format(can_quit.is_set()))
                print("hard_quit: {0}".format(hard_quit.is_set()))
                print("{0} active threads:".format(len(statuses)))
                for status in statuses.values():
                    print("{0}".format(status))

                print("\n")
        if can_quit.is_set():
            break


if __name__ == "__main__":
    manager = multiprocessing.Manager()
    statuses = manager.dict()
    loggedfeeds = manager.dict()
    can_quit = multiprocessing.Event()
    want_to_quit = multiprocessing.Event()
    hard_quit = multiprocessing.Event()

    feeds = multiprocessing.JoinableQueue(0)
    urls = multiprocessing.JoinableQueue(0)

    if not os.path.exists('Podcasts'):
        os.mkdir('Podcasts')

    if os.path.exists(log_file):
        with open(log_file) as feedlog:
            loggedfeeds.update({feed: int(lastdate) for feed,lastdate in
                    [lines.split(',') for lines in feedlog]})

    days_back = 7
    with open(list_file) as feedlist:
        for lines in feedlist:
            if lines[0] == "#":
                name = lines[2:].strip()
                days_back = 7
                continue
            elif lines[0] == "!":
                days_back = int(lines[1:].strip())
                continue

            urls.put((name, lines.strip(), days_back))

    print("Starting threads.")

    for i in range(number_of_threads):
        t = multiprocessing.Process(target=feed_thread, args=(statuses, loggedfeeds, can_quit, want_to_quit, hard_quit, feeds, urls))
        t.name = 'ItemGet{0}'.format(i)
        t.daemon = True
        t.start()

        t = multiprocessing.Process(target=get_urls, args=(statuses, loggedfeeds, can_quit, want_to_quit, hard_quit, feeds, urls))
        t.name = 'GetUrls{0}'.format(i)
        t.start()

    t = multiprocessing.Process(target=check_key, args=(statuses, can_quit, want_to_quit, hard_quit, feeds, urls))
    t.name = 'Input'
    t.start()

    can_quit.wait()

    if not hard_quit.is_set():
        print("Cleaning up.")

        with open(log_file, "w") as feedlog:
            for key, value in loggedfeeds.items():
                feedlog.write("{0},{1}\n".format(key,value))
