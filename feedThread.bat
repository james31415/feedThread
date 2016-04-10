@echo off
call activate FeedThread
python feedThread.py
call deactivate
pause
