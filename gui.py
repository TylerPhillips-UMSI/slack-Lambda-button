"""
The TKinter GUI module for Slack-Lambda-Button.

Written by:
Nikki Hess - nkhess@umich.edu
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

import lambda_function as lf

MAIZE = "#FFCB05"
BLUE = "#00274C"

def display_gui(fullscreen: bool = True) -> None:
    """
    Displays the TKinter GUI
    
    Params:
    fullscreen: bool = True -> whether to start the app in full screen
    """
    escape_display_period_ms = 5000

    # make a window
    root = tk.Tk()

    # set display attributes/config
    root.attributes("-fullscreen", fullscreen)
    root.configure(bg=BLUE)
    root.title("Slack Lambda Button")

    display_frame = tk.Frame(root, bg=BLUE)
    display_frame.pack(fill=tk.BOTH, expand=True)

    # load oswald, a U of M standard font
    oswald_32 = tkFont.Font(family="Oswald", size=32)

    # configure style
    style = ttk.Style()
    style.configure("Escape.TLabel", foreground=MAIZE, background=BLUE, font=oswald_32)

    # bind keys
    root.bind("<Escape>", lambda event: root.destroy())
    root.bind("<Button-1>", lambda event: handle_interaction(root, display_frame, style, do_post=False))

    # set up the actual items in the display
    escape_label = ttk.Label(display_frame, text="Press escape to exit", style="Escape.TLabel")
    escape_label.place(relx=0.99, rely=0.99, anchor="se")

    display_main(display_frame, style)

    # Fade the escape label out
    root.after(escape_display_period_ms, fade_label, root, 
               escape_label, hex_to_rgb(MAIZE), hex_to_rgb(BLUE), 0, 1500)

    # run
    root.mainloop()

def display_main(root: tk.Frame, style: ttk.Style) -> None:
    """
    Displays the main (idle) screen for the user

    Params:
    root: tk.Tk -> the root window
    style: ttk.Style -> the style manager for our window
    """

    oswald_48 = tkFont.Font(family="Oswald", size=48)
    oswald_64 = tkFont.Font(family="Oswald", size=64)
    
    style.configure("NeedHelp.TLabel", foreground=MAIZE, background=BLUE, font=oswald_64)
    style.configure("Instructions.TLabel", foreground=MAIZE, background=BLUE, font=oswald_48)

    dude_img = tk.PhotoImage(file='images/duderstadt-logo.png')
    dude_img_label = ttk.Label(root, image=dude_img, background=BLUE)
    dude_img_label.image = dude_img # keep a reference so it's still in memory
    dude_img_label.place(relx=0.5, rely=0.4, anchor="center")

    # HELP LABEL HAS TO BE RENDERED AFTER IMG TO BE SEEN
    help_label = ttk.Label(root, text="Need help?", style="NeedHelp.TLabel")
    help_label.place(relx=0.5, rely=0.6, anchor="center")

    instruction_label = ttk.Label(root, text="Tap the screen or press a button!", style="Instructions.TLabel")
    instruction_label.place(relx=0.5, rely=0.7, anchor="center")

def handle_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool = True) -> None:
    """
    Handles the Lambda function and switching to the post-interaction display

    Params:
    root: tk.Tk -> the root window
    frame: tk.Frame -> the frame that we're putting widgets in
    style: ttk.Style -> the style class we're working with
    do_post: bool = True -> whether or not to post to the Slack channel
    """

    # clear display
    for widget in frame.winfo_children():
        widget.place_forget()

    display_post_interaction(root, frame, style)

    # post to Slack/console
    # NEEDS a 20ms delay in order to load the next screen consistently
    root.after(20, lambda: lf.handle_interaction(do_post))

def display_post_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style) -> None:
    """
    Displays the post interaction instructions

    Params:
    root: tk.Tk -> the root window
    frame: tk.Frame -> the frame
    style: ttk.Style -> the style manager for our window
    """

    oswald_96 = tkFont.Font(family="Oswald", size=96)
    oswald_80 = tkFont.Font(family="Oswald", size=80)

    style.configure("Received.TLabel", foreground=MAIZE, background=BLUE, font=oswald_96)
    style.configure("Waiting.TLabel", foreground=MAIZE, background=BLUE, font=oswald_80)

    received_label = ttk.Label(frame, text="Help is on the way!", style="Received.TLabel")
    received_label.place(relx=0.5, rely=0.40, anchor="center")

    waiting_label = ttk.Label(frame, text="Updates will be provided on this screen.", style="Waiting.TLabel")
    waiting_label.place(relx=0.5, rely=0.60, anchor="center")

    root.update_idletasks() # gets stuff to load all at once

    three_min = 3 * 60 * 1000 # minutes * seconds * ms

    root.after(three_min, lambda: revert_to_main(frame, style))

def revert_to_main(frame: tk.Frame, style: ttk.Style) -> None:
    """
    Reverts from another frame to the main display

    Params:
    frame: tk.Frame -> the frame we're working with
    style: ttk.Style -> the style we'd like to hold onto
    """

    for widget in frame.winfo_children():
        widget.place_forget()

    display_main(frame, style)

def hex_to_rgb(hex_: str) -> tuple:
    """
    Converts a hex string (#000000) to an RGB tuple ((0, 0, 0))

    Params:
    hex_: str -> the hex string to convert

    Returns:
    The tuple our hex converts to
    """

    hex_ = hex_.lstrip("#")
    return tuple(int(hex_[i:i+2], 16) for i in (0, 2, 4))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def interpolate(start_color: tuple, end_color: tuple, time: int) -> tuple:
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
def fade_label(root: tk.Tk, label: ttk.Label, start_color: tuple, end_color: tuple, current_step: int,
               fade_duration_ms: int) -> None:
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
    display_gui(fullscreen = True)