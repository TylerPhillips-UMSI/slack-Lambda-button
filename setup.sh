echo -e "\e[32mStarting setup for slack-Lambda-button...\e[39m"

# Python Requests library
pip install --upgrade requests

# Google Sheets/Docs stuff
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# boto3
pip install --upgrade boto3

# force upgrade to lgpio, which doesn't error out for this project
sudo apt remove python3-rpi.gpio
sudo apt update
sudo apt install python3-rpi-lgpio

echo -e "\e[All done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"