echo -e "\e[32mStarting setup for slack-Lambda-button for Linux...\e[39m"

pip install --upgrade --break-system-packages requests
pip install --upgrade --break-system-packages google-api-python-client google-auth-httplib2 google-auth-oauthlib
pip install --upgrade --break-system-packages boto3
pip install --upgrade --break-system-packages pillow
sudo apt-get install -y python3-dev libasound2-dev
pip install --upgrade --break-system-packages simpleaudio

echo -e "\e[32mAll done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"
