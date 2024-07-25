"""
The TKinter GUI module for Slack-Lambda-Button.

Written by:
Nikki Hess - nkhess@umich.edu
"""

from tkinter import *
from tkinter import ttk
import tkinter.font as tkFont

MAIZE = "#FFCB05"
BLUE = "#00274C"

def display_gui(fullscreen: bool = True):
    """
    Displays the TKinter GUI
    
    Params:
    fullscreen: bool = True -> whether to start the app in full screen
    """

    root = Tk()

    # set display attributes/config
    root.attributes("-fullscreen", fullscreen)
    root.configure(bg=BLUE)
    root.title("Slack Lambda Button")

    # set up a grid
    root.grid()

    # bind keys
    root.bind("<Escape>", lambda event: root.destroy())

    # load Montserrat, a U of M standard font
    montserrat = tkFont.Font(family="Montserrat", size=16)

    # configure style
    style = ttk.Style()
    style.configure("Escape.TLabel", foreground=MAIZE, background=BLUE, font=montserrat)

    # set up the actual items in the display
    ttk.Label(root, text="Press escape to exit", style="Escape.TLabel").grid(column=0, row=0)
    
    # run
    root.mainloop()

if __name__ == "__main__":
    display_gui()