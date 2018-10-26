import os.path
import sys
import ntpath
import shutil

if __name__ == "__main__":
    destination = sys.argv[1]

    with open("Podcasts/playlist.m3u", "r") as playlist:
        for i, line in enumerate(playlist):
            source_name = os.path.join("Podcasts", line.strip())
            dest_name = os.path.join(destination, "{:02}-{}".format(i, ntpath.basename(line.strip())))
            print("Copying {} to {}".format(source_name, dest_name))
            shutil.copyfile(source_name, dest_name)
