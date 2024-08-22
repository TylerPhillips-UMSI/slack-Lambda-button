echo -e "\e[32mStarting setup for slack-Lambda-button for Linux...\e[39m"

# Install Python Requests library
pip install --upgrade requests

# Install Google Sheets/Docs libraries
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib

# Install boto3
pip install --upgrade boto3

# Install PIL
pip install --upgrade pillow

echo -e "\e[All done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"