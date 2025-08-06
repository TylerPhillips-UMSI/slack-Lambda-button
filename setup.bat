@echo off
echo Starting setup for slack-Lambda-button for Windows...

pip install --upgrade requests
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install --upgrade boto3
pip install --upgrade pillow
pip install --upgrade simpleaudio

echo All done! You may now run slack-Lambda-button via "python gui.py"
pause
