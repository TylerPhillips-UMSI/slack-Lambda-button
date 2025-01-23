echo -e "\e[32mStarting setup for slack-Lambda-button for Linux...\e[39m"

pip install --upgrade requests
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install --upgrade boto3
pip install --upgrade pillow
sudo apt-get install -y python3-dev libasound2-dev
pip install --upgrade simpleaudio

echo -e "\e[32mAll done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"
