@echo off
echo Preparing package for slack-Lambda-button for AWS deployment...

cd /d "%~dp0"
echo Current working directory: %cd%

:: Install Python Requests library
pip install --target ./package --upgrade requests

:: Install Google Sheets/Docs libraries
pip install --target ./package --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

:: Install boto3
pip install --target ./package --upgrade boto3

:: Copy config over to package, if it exists
copy config ./package/config

echo All done!
pause
