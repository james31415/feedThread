#!/usr/bin/env python3
import re
import os

import yaml

CONF_FILE = 'feeds.conf'

def getPodcastOrder():
    playlistOrder = []
    with open(CONF_FILE) as inFile:
        playlistOrder = yaml.load(inFile)

    return playlistOrder["Playlist"]

def getPlaylist(podcastDir, podcastOrder):
    playlistFiles = []
    for title in podcastOrder:
        for (dirpath, dirnames, filenames) in os.walk(os.path.join(podcastDir, title)):
            for f in sorted(filenames):
                playlistFiles.append(os.path.join(title, f))
    return playlistFiles

def writePlaylist(podcastDir, playlistData, playlistFile):
    with open(os.path.join(podcastDir, playlistFile), "w") as outFile:
        for f in playlistData:
            print(f, file=outFile)

if __name__ == "__main__":
    podcastDir = "Podcasts"
    playlistFile = "playlist.m3u"

    podcastOrder = getPodcastOrder()
    playlistData = getPlaylist(podcastDir, podcastOrder)
    writePlaylist(podcastDir, playlistData, playlistFile)
