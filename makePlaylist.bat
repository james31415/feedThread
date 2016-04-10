@echo off
call activate FeedThread
echo Let's make a playlist
python makePlaylist.py
echo Done!
call deactivate
pause

