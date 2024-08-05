@echo off
echo Starting setup for slack-Lambda-button for AWS deployment...

:: Install Python Requests library
pip install --target ./package --upgrade requests

:: Install Google Sheets/Docs libraries
pip install --target ./package --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

:: Install boto3
pip install --target ./package --upgrade boto3

echo All done!
pause
