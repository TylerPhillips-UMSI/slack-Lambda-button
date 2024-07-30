"""
The TKinter GUI module for Slack-Lambda-Button.

Written by:
Nikki Hess - nkhess@umich.edu
"""

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

import sys
import time

import lambda_function as lf

MAIZE = "#FFCB05"
BLUE = "#00274C"
PRESS_START = None # for long button presses

is_raspberry_pi = not sys.platform.startswith("win32")

if is_raspberry_pi:
    import RPi.GPIO as GPIO # for Argon interactions

def setup_gpio(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool = True) -> None:
    """
    Sets up GPIO event listeners for the Argon case's 4 buttons

    Params:
    root: tk.Tk -> the root window
    frame: tk.Frame -> the frame that we're putting widgets in
    style: ttk.Style -> the style class we're working with
    do_post: bool = True -> whether or not to post to the Slack channel
    """
    
    button_1 = 16
    button_2 = 20
    button_3 = 21
    button_4 = 22

    # initial GPIO setup
    GPIO.setmode(GPIO.BCM)

    # add pull-up resistory to make readings more stable
    GPIO.setup(button_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(button_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(button_3, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(button_4, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def handle_gpio_event(channel):
        """
        Handles GPIO events for falling and rising edges.

        Params:
        channel: int -> the GPIO channel that triggered the event
        """
        global PRESS_START
        if GPIO.input(channel) == GPIO.LOW:
            # Falling edge
            PRESS_START = time.time()
        else:
            # Rising edge
            handle_interaction(root, frame, style, do_post)

    # Add event detection for both edges
    for button in [button_1, button_2, button_3, button_4]:
        GPIO.add_event_detect(button, GPIO.BOTH, callback=handle_gpio_event, bouncetime=200)

def bind_presses(root: tk.Frame, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    A simple function to bind or rebind button press-release events for TKinter
    """

    # sets the press_start time to be used to determine press length
    def set_press_start():
        global PRESS_START
        PRESS_START = time.time()

    root.bind("<ButtonPress-1>", lambda event: set_press_start())
    root.bind("<ButtonRelease-1>", lambda event:
              handle_interaction(root, frame, style, do_post=do_post))

def display_main(root: tk.Frame, style: ttk.Style) -> None:
    """
    Displays the main (idle) screen for the user

    Params:
    root: tk.Tk -> the root window
    style: ttk.Style -> the style manager for our window
    """

    oswald_48 = tkFont.Font(family="Oswald", size=48, weight="bold")
    oswald_64 = tkFont.Font(family="Oswald", size=64, weight="bold")

    style.configure("NeedHelp.TLabel", foreground=MAIZE, background=BLUE, font=oswald_64)
    style.configure("Instructions.TLabel", foreground=MAIZE, background=BLUE, font=oswald_48)

    dude_img = tk.PhotoImage(file="images/duderstadt-logo.png")
    dude_img_label = ttk.Label(root, image=dude_img, background=BLUE)
    dude_img_label.image = dude_img # keep a reference so it's still in memory
    dude_img_label.place(relx=0.5, rely=0.4, anchor="center")

    # HELP LABEL HAS TO BE RENDERED AFTER IMG TO BE SEEN
    help_label = ttk.Label(root, text="Need help?", style="NeedHelp.TLabel")
    help_label.place(relx=0.5, rely=0.6, anchor="center")

    instruction_label = ttk.Label(root, text="Tap the screen or press a button!",
                                  style="Instructions.TLabel")
    instruction_label.place(relx=0.5, rely=0.7, anchor="center")

def handle_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style,
                       do_post: bool = True) -> None:
    """
    Handles the Lambda function and switching to the post-interaction display

    Params:
    root: tk.Tk -> the root window
    frame: tk.Frame -> the frame that we're putting widgets in
    style: ttk.Style -> the style class we're working with
    do_post: bool = True -> whether or not to post to the Slack channel
    """
    global PRESS_START

    # clear display
    for widget in frame.winfo_children():
        widget.place_forget()

    # clear left click binding
    root.unbind("<ButtonPress-1>")
    root.unbind("<ButtonRelease-1>")

    display_post_interaction(root, frame, style, do_post)

    current_time = time.time()

    # post to Slack/console
    # NEEDS a 20ms delay in order to load the next screen consistently
    root.after(20, lambda:
               lf.handle_interaction(do_post,
               (current_time - PRESS_START) if PRESS_START is not None else 0))

def display_post_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    Displays the post interaction instructions

    Params:
    root: tk.Tk -> the root window
    frame: tk.Frame -> the frame
    style: ttk.Style -> the style manager for our window
    do_post: bool -> whether to post to Slack
    """

    # Countdown
    countdown_length_sec = 180

    oswald_96 = tkFont.Font(family="Oswald", size=96, weight="bold")
    oswald_80 = tkFont.Font(family="Oswald", size=80, weight="bold")

    style.configure("Received.TLabel", foreground=MAIZE, background=BLUE, font=oswald_96)
    style.configure("Waiting.TLabel", foreground=MAIZE, background=BLUE, font=oswald_80)

    received_label = ttk.Label(frame, text="Help is on the way!", style="Received.TLabel")
    received_label.place(relx=0.5, rely=0.40, anchor="center")

    waiting_label = ttk.Label(frame, text="Updates will be provided on this screen.",
                              style="Waiting.TLabel")
    waiting_label.place(relx=0.5, rely=0.60, anchor="center")

    root.update_idletasks() # gets stuff to load all at once

    three_min = countdown_length_sec * 1000 # seconds * ms
    root.after(three_min, lambda: revert_to_main(root, frame, style, do_post))

    oswald_32 = tkFont.Font(family="Oswald", size=32, weight="bold")
    style.configure("Timeout.TLabel", foreground=MAIZE, background=BLUE, font=oswald_32)

    seconds_left = countdown_length_sec
    timeout_label = ttk.Label(frame, text=f"Request times out in {seconds_left} seconds",
                              style="Timeout.TLabel")
    timeout_label.place(relx=0.99, rely=0.99, anchor="se")

    # do a timeout countdown
    def countdown():
        nonlocal seconds_left # allows us to access seconds_left in here

        # clear the label and decrement seconds_left
        timeout_label.place_forget()
        seconds_left -= 1

        # update and place the label
        timeout_label.configure(text=f"Request times out in {seconds_left} seconds")
        timeout_label.place(relx=0.99, rely=0.99, anchor="se")

        # schedule countdown until seconds_left is 1
        if seconds_left > 0:
            root.after(1000, countdown)
        else:
            timeout_label.place_forget()

    root.after(1000, countdown)

def revert_to_main(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    Reverts from another frame to the main display

    Params:
    root: tk.Tk -> the root window we're working with
    frame: tk.Frame -> the frame we're working with
    style: ttk.Style -> the style we'd like to hold onto
    do_post: bool -> whether to post to Slack
    """

    for widget in frame.winfo_children():
        widget.place_forget()

    # restore left click bindings
    bind_presses(root, frame, style, do_post)

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
def interpolate(start_color: tuple, end_color: tuple, t: int) -> tuple:
    """
    Interpolates between two colors based on time

    Params:
    start_color: tuple -> the color to start with
    end_color: tuple -> the color to end with
    t: int -> the amount of time that has passed

    Returns:
    An interpolated tuple somewhere between our two colors
    """
    return tuple(int(a + (b - a) * t) for a, b in zip(start_color, end_color))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def fade_label(root: tk.Tk, label: ttk.Label, start_color: tuple, end_color: tuple,
               current_step: int, fade_duration_ms: int) -> None:
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
    label.configure(foreground=f"#{new_color[0]:02x}{new_color[1]:02x}{new_color[2]:02x}")

    if current_step <= fps:
        root.after(fade_duration_ms // fps, fade_label, root,
                   label, start_color, end_color, current_step,
                   fade_duration_ms)

def display_gui(fullscreen: bool = True) -> None:
    """
    Displays the TKinter GUI
    
    Params:
    fullscreen: bool = True -> whether to start the app in full screen
    """
    escape_display_period_ms = 5000
    do_post = False

    # make a window
    root = tk.Tk()
    # root.iconbitmap("images/lambda.ico")

    # set display attributes/config
    # NEED to delay this to ensure consistent behavior
    # if you don't, it may not go fullscreen
    root.after(300, lambda: root.attributes("-fullscreen", fullscreen))
    root.configure(bg=BLUE)
    root.title("Slack Lambda Button")

    display_frame = tk.Frame(root, bg=BLUE)
    display_frame.pack(fill=tk.BOTH, expand=True)

    # load oswald, a U of M standard font
    oswald_32 = tkFont.Font(family="Oswald", size=32, weight="bold")

    # configure style
    style = ttk.Style()
    style.configure("Escape.TLabel", foreground=MAIZE, background=BLUE, font=oswald_32)

    # bind keys/buttons
    root.bind("<Escape>", lambda event: root.destroy())
    bind_presses(root, display_frame, style, do_post)

    if is_raspberry_pi:
        setup_gpio(root, display_frame, style, do_post=do_post)

    # set up the actual items in the display
    escape_label = ttk.Label(display_frame, text="Press escape to exit", style="Escape.TLabel")
    escape_label.place(relx=0.99, rely=0.99, anchor="se")

    display_main(display_frame, style)

    # Fade the escape label out
    root.after(escape_display_period_ms, fade_label, root,
               escape_label, hex_to_rgb(MAIZE), hex_to_rgb(BLUE), 0, 1500)

    # run
    root.mainloop()

    if is_raspberry_pi:
        try:
            GPIO.cleanup() # finally, clean everything up
        except GPIO.error:
            pass

if __name__ == "__main__":
    display_gui(fullscreen = True)
