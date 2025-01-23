echo -e "\e[32mStarting setup for slack-Lambda-button for Linux (pipx)...\e[39m"

if command -v pipx &>/dev/null; then
  echo 'pipx is installed, continuing'
else
  echo 'pipx is not installed, exiting...'
  exit 1
fi

pipx install requests
pipx install google-api-python-client google-auth-httplib2 google-auth-oauthlib
pipx install boto3
pipx install pillow

sudo apt-get install -y python3-dev libasound2-dev
pipx install simpleaudio

echo -e "\e[32mAll done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"
