@echo off
echo Starting setup for slack-Lambda-button for Windows...

pip install --upgrade pip setuptools wheel
pip install --upgrade -r requirements.txt

echo All done! You may now run slack-Lambda-button via "python gui.py"
pause
