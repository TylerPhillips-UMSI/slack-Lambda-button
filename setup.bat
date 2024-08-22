@echo off
echo Starting setup for slack-Lambda-button for Windows...

:: Install Python Requests library
pip install --upgrade requests

:: Install Google Sheets/Docs libraries
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

:: Install boto3
pip install --upgrade boto3

:: Install PIL
pip install --upgrade pillow

:: Install flask
pip install --upgrade flask

echo All done! You may now run slack-Lambda-button via "python gui.py"
pause
