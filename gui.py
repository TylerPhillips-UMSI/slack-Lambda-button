#!/usr/bin/env python3

"""
The TKinter GUI module for Slack-Lambda-Button.

Author:
Nikki Hess - nkhess@umich.edu
"""

# import sys
import time

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

from PIL import Image, ImageTk

import slack
import aws

MAIZE = "#FFCB05"
BLUE = "#00274C"
PRESS_START = None # for long button presses

pending_message_ids = [] # pending messages from this device specifically

def bind_presses(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    A simple function to bind or rebind button press-release events for TKinter

    Args:
        root (tk.Tk): the root window
        frame (tk.Frame): the frame we're currently working with
        style (ttk.Style): the style manager for our window
        do_post (bool): whether to post to Slack
    """

    # sets the press_start time to be used to determine press length
    def set_press_start():
        global PRESS_START
        PRESS_START = time.time()

    root.bind("<ButtonPress-1>", lambda event: set_press_start())
    root.bind("<ButtonRelease-1>", lambda event:
              handle_interaction(root, frame, style, do_post))

def scale_font(root: tk.Tk, base_size: int) -> int:
    """
    Scales a font based on the size of the window

    Args:
        root (tk.Tk): the root window
        base_size (int): the size of the text at 1080p

    Returns:
        int: the scaled font's size
    """
    base = {"width": 1920, "height": 1080}
    actual = {"width": root.winfo_screenwidth(), "height": root.winfo_screenheight()}

    calculated_scale = min(actual["width"] / base["width"], actual["height"] / base["height"])

    return int(calculated_scale * base_size)

def load_and_scale_image(root: tk.Tk, img: Image.Image) -> ImageTk.PhotoImage:
    """
    Uses PIL to rescale an image based on the size of the window

    Args:
        root (tk.Tk): the root window
        image_path (str): the image to load and scale

    Returns:
        ImageTk.PhotoImage: the scaled PhotoImage for TKinter
    """

    base = {"width": 1920, "height": 1080}
    actual = {"width": root.winfo_screenwidth(), "height": root.winfo_screenheight()}

    scale = min(actual["width"] / base["width"], actual["height"] / base["height"])
    new_size = (int(scale * img.width), int(scale * img.height))

    resized_image = img.resize(new_size, Image.Resampling.LANCZOS)
    photo_image = ImageTk.PhotoImage(resized_image)

    return photo_image

def display_main(root: tk.Frame, style: ttk.Style) -> None:
    """
    Displays the main (idle) screen for the user

    Args:
        root (tk.Tk): the root window
        style (ttk.Style): the style manager for our window
    """

    def load_contents():
        oswald_96 = tkFont.Font(family="Oswald", size=scale_font(root, 96), weight="bold")
        oswald_80 = tkFont.Font(family="Oswald", size=scale_font(root, 80), weight="bold")

        style.configure("NeedHelp.TLabel", foreground=MAIZE, background=BLUE, font=oswald_96)
        style.configure("Instructions.TLabel", foreground=MAIZE, background=BLUE, font=oswald_80)

        # KEEP THIS CODE IN CASE WE NEED TO GO BACK TO A STATIC IMAGE!
        # dude_img = load_and_scale_image(root, "images/duderstadt-logo.png")
        # dude_img_label = ttk.Label(root, image=dude_img, background=BLUE)
        # dude_img_label.image = dude_img # keep a reference so it's still in memory
        # dude_img_label.place(relx=0.5, rely=0.37, anchor="center")

        frame_count = 136
        frames = []

        with Image.open("images/DuderstadtAnimatedLogoTrans.gif") as gif:
            for i in range(frame_count):
                gif.seek(i)
                frames.append(load_and_scale_image(root, gif.copy()))

        dude_img_label = ttk.Label(root, image=frames[0], background=BLUE)

        def update(index: int) -> None:
            frame = frames[index]
            index += 1

            if index != frame_count:
                dude_img_label.configure(image=frame)
                root.after(20, update, index)

        dude_img_label.place(relx=0.5, rely=0.36, anchor="center")

        update(0)

        instruction_label = ttk.Label(root, text="Tap the screen!",
                                    style="Instructions.TLabel")
        instruction_label.place(relx=0.5, rely=0.71, anchor="center")

        # help label has to be rendered after img to be seen (layering)
        help_label = ttk.Label(root, text="Need help?", style="NeedHelp.TLabel")
        help_label.place(relx=0.5, rely=0.57, anchor="center")

    root.after(20, load_contents) # add delay to make gif not affect countdown?

def handle_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style,
                       do_post: bool) -> None:
    """
    Handles the Lambda function and switching to the post-interaction display

    Args:
        root (tk.Tk): the root window
        frame (tk.Frame): the frame that we're putting widgets in
        style (ttk.Style): the style manager for our window
        do_post (bool): whether or not to post to the Slack channel
    """

    # clear display
    for widget in frame.winfo_children():
        widget.place_forget()

    # clear left click binding
    root.unbind("<ButtonPress-1>")
    root.unbind("<ButtonRelease-1>")

    display_post_interaction(root, frame, style, do_post)

    current_time = time.time()

    def post():
        global pending_message_ids
        message_id = slack.handle_interaction(slack.aws_client, do_post,
               (current_time - PRESS_START) if PRESS_START is not None else 0)

        pending_message_ids.append(message_id)

    # post to Slack/console
    # NEEDS a 20ms delay in order to load the next screen consistently
    root.after(20, post)

def display_post_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    Displays the post interaction instructions

    Args:
        root (tk.Tk): the root window
        frame (tk.Frame): the frame
        style (ttk.Style): the style manager for our window
        do_post (bool): whether to post to Slack
    """

    # countdown
    countdown_length_sec = 180

    oswald_96 = tkFont.Font(family="Oswald", size=scale_font(root, 96), weight="bold")
    oswald_80 = tkFont.Font(family="Oswald", size=scale_font(root, 80), weight="bold")
    oswald_36 = tkFont.Font(family="Oswald", size=scale_font(root, 36), weight="bold")
    monospace = tkFont.Font(family="Ubuntu Mono", size=scale_font(root, 36), weight="bold")

    # create a text widget to display the countdown and timeout
    text_widget = tk.Text(frame, background=BLUE, foreground=MAIZE, bd=0,
                          highlightthickness=0, selectbackground=BLUE)
    text_widget.place(relx=0.996, rely=0.99, anchor="se", relheight=0.07, relwidth=0.355)

    # configure tags for different fonts
    text_widget.tag_configure("timeout", font=oswald_36, foreground=MAIZE)
    text_widget.tag_configure("countdown", font=monospace, foreground=MAIZE)

    # configure tag for right justification
    text_widget.tag_configure("right", justify="right")
    text_widget.tag_add("right", "1.0", "end")

    seconds_left = countdown_length_sec

    def update_text_widget():
        text_widget.config(state=tk.NORMAL) # enable editing

        text_widget.delete("1.0", tk.END)

        text_widget.insert(tk.END, f"{' ' if seconds_left < 100 else ''}", "countdown")
        text_widget.insert(tk.END, "Request times out in ", "timeout")
        text_widget.insert(tk.END, f"{seconds_left}", "countdown")
        text_widget.insert(tk.END, " seconds", "timeout")

        text_widget.config(state=tk.DISABLED) # disable editing

    # Initial update
    update_text_widget()

    # do a timeout countdown
    def countdown():
        nonlocal seconds_left # allows us to access seconds_left in here

        # decrement seconds left and set the label's text
        seconds_left -= 1
        update_text_widget()

        # schedule countdown until seconds_left is 1
        if seconds_left > 0:
            root.after(1000, countdown)
        else:
            # text_widget.place_forget()
            pass

    root.after(1000, countdown)

    style.configure("Received.TLabel", foreground=MAIZE, background=BLUE, font=oswald_96)
    style.configure("Waiting.TLabel", foreground=MAIZE, background=BLUE, font=oswald_80)

    received_label = ttk.Label(frame, text="Help is on the way!", style="Received.TLabel")
    received_label.place(relx=0.5, rely=0.40, anchor="center")

    waiting_label = ttk.Label(frame, text="Updates will be provided on this screen.",
                              style="Waiting.TLabel")
    waiting_label.place(relx=0.5, rely=0.60, anchor="center")

    # if we have a message from SQS, make sure it's ours and then use it
    if aws.latest_message:
        split = aws.latest_message.split()
        
        # split[0] should be a timestamp
        if split[0] in pending_message_ids:
            received_label.configure(text=split[1])

            aws.latest_message = None

    root.update_idletasks() # gets stuff to load all at once

    three_min = countdown_length_sec * 1000 # seconds * ms

    def after_3_min():
        nonlocal root, frame, style, do_post

        revert_to_main(root, frame, style, do_post)
        # aws.mark_message_timed_out(slack.aws_client, message_id, channel_id)

    after_id = root.after(three_min, after_3_min) # to be used for cancelling when a checkmark is received

def revert_to_main(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    Reverts from another frame to the main display

    Args:
        root (tk.Tk): the root window we're working with
        frame (tk.Frame): the frame we're working with
        style (ttk.Style): the style we'd like to hold onto
        do_post (bool): whether to post to Slack
    """

    for widget in frame.winfo_children():
        widget.place_forget()

    # restore left click bindings
    bind_presses(root, frame, style, do_post)

    display_main(frame, style)

def hex_to_rgb(hex_str: str) -> tuple:
    """
    Converts a hex string (#000000) to an RGB tuple ((0, 0, 0))

    Args:
        hex_str (str): the hex string to convert

    Returns:
        tuple: what our hex converts to
    """

    hex_str = hex_str.lstrip("#")
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def interpolate(start_color: tuple, end_color: tuple, t: int) -> tuple:
    """
    Interpolates between two colors based on time

    Args:
        start_color (tuple): the color to start with
        end_color (tuple): the color to end with
        t (int): the amount of time that has passed

    Returns:
        An interpolated tuple somewhere between our two colors
    """
    return tuple(int(a + (b - a) * t) for a, b in zip(start_color, end_color))

# https://stackoverflow.com/questions/57337718/smooth-transition-in-tkinter
def fade_label(frame: tk.Tk, label: ttk.Label, start_color: tuple, end_color: tuple,
               current_step: int, fade_duration_ms: int) -> None:
    """
    A recursive function that fades a label from one color to another

    Args:
        root (tk.Tk): the root of the window
        label (ttk.Label): the label to fade
        start_color (tuple): the start color, as an RGB tuple
        end_color (tuple): the end color, as an RGB tuple
        current_step (int): for recursion, tells the function how much we've faded
        fade_duration_ms (int): the length of time to fade for, in MS
    """

    # set a framerate for the fade
    fps = 60

    t = (1.0 / fps) * current_step
    current_step += 1

    new_color = interpolate(start_color, end_color, t)
    label.configure(foreground=f"#{new_color[0]:02x}{new_color[1]:02x}{new_color[2]:02x}")

    if current_step <= fps:
        frame.after(fade_duration_ms // fps, fade_label, frame,
                   label, start_color, end_color, current_step,
                   fade_duration_ms)

def display_gui() -> None:
    """
    Displays the TKinter GUI
    """
    escape_display_period_ms = 5000
    do_post = True

    # make a window
    root = tk.Tk()
    root.config(cursor="none")

    root.attributes("-fullscreen", True)
    root.configure(bg=BLUE)
    root.title("Slack Lambda Button")

    display_frame = tk.Frame(root, bg=BLUE)
    display_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

    # configure style
    style = ttk.Style()

    # bind keys/buttons
    root.bind("<Escape>", lambda event: root.destroy())
    bind_presses(root, display_frame, style, do_post)

    # if is_raspberry_pi:
    #     setup_gpio(root, display_frame, style, do_post)

    display_main(display_frame, style)

    # load oswald, a U of M standard font
    oswald_42 = tkFont.Font(family="Oswald", size=scale_font(root, 42), weight="bold")

    style.configure("Escape.TLabel", foreground=MAIZE, background=BLUE, font=oswald_42)

    # set up the actual items in the display
    escape_label = ttk.Label(display_frame, text="Press escape to exit", style="Escape.TLabel")
    escape_label.place(relx=0.99, rely=0.99, anchor="se")

    # Fade the escape label out
    root.after(escape_display_period_ms, fade_label, root,
               escape_label, hex_to_rgb(MAIZE), hex_to_rgb(BLUE), 0, 1500)

    # run
    root.mainloop()

    # if is_raspberry_pi:
    #     try:
    #         GPIO.cleanup() # finally, clean everything up
    #     except Exception:
    #         pass # okay, don't clean everything up

if __name__ == "__main__":
    display_gui()
