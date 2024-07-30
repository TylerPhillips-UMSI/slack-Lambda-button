@echo off
echo Starting setup for slack-Lambda-button for Windows...

:: Install Python Requests library
pip install --upgrade requests

:: Install Google Sheets/Docs libraries
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

echo All done! You may now run slack-Lambda-button via "python gui.py"
