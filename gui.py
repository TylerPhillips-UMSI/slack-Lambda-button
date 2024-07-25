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
    global MAIZE, BLUE

    escape_display_period_ms = 5000

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
    montserrat = tkFont.Font(family="Montserrat", size=20)

    # configure style
    style = ttk.Style()
    style.configure("Escape.TLabel", foreground=MAIZE, background=BLUE, font=montserrat)

    # set up the actual items in the display
    escape_label = ttk.Label(root, text="Press escape to exit", style="Escape.TLabel")
    escape_label.grid(column=0, row=0)

    # Fade the escape label out
    root.after(escape_display_period_ms, fade_label, root, 
               escape_label, hex_to_rgb(MAIZE), hex_to_rgb(BLUE), 0, 1500)

    # run
    root.mainloop()

def hex_to_rgb(hex: str) -> tuple:
    """
    Converts a hex string (#000000) to an RGB tuple ((0, 0, 0))

    Params:
    hex: str -> the hex string to convert

    Returns:
    The tuple our hex converts to
    """

    hex = hex.lstrip("#")
    return tuple(int(hex[i:i+2], 16) for i in (0, 2, 4))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def interpolate(start_color: tuple, end_color: tuple, time: int):
    """
    Interpolates between two colors based on time

    Params:
    start_color: tuple -> the color to start with
    end_color: tuple -> the color to end with
    time: int -> the amount of time that has passed

    Returns:
    An interpolated tuple somewhere between our two colors
    """
    return tuple(int(a + (b - a) * time) for a, b in zip(start_color, end_color))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def fade_label(root: Tk, label: ttk.Label, start_color: tuple, end_color: tuple, current_step: int,
               fade_duration_ms: int):
    """
    A recursive function that fades a label from one color to another

    Params:
    root: Tk -> the root of the window
    label: ttk.Label -> the label to fade
    start_color: tuple -> the start color, as an RGB tuple
    end_color: tuple -> the end color, as an RGB tuple
    current_step: int -> for recursion, tells the function how much we've faded
    fade_duration_ms: int -> the length of time to fade for, in MS
    """

    # set a framerate for the fade
    fps = 60

    t = (1.0 / fps) * current_step
    current_step += 1

    new_color = interpolate(start_color, end_color, t)
    label.configure(foreground="#%02x%02x%02x" % new_color)

    if current_step <= fps:
        root.after(fade_duration_ms // fps, fade_label, root,
                   label, start_color, end_color, current_step,
                   fade_duration_ms)

if __name__ == "__main__":
    display_gui(fullscreen = False)