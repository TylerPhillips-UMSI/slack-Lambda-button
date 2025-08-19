echo -e "\e[32mStarting setup for slack-Lambda-button for Linux...\e[39m"

sudo apt-get install -y python3-dev libasound2-dev
pip install --upgrade -r requirements.txt

echo -e "\e[32mAll done! You may now run slack-Lambda-button via \"python gui.py\"\e[39m"