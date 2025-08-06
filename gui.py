#!/usr/bin/env python3

"""
The TKinter GUI module for Slack-Lambda-Button.

Author:
Nikki Hess - nkhess@umich.edu
"""

import time

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont

import threading # for sqs polling

from PIL import Image, ImageTk

import simpleaudio as sa

import slack
import aws
import sheets

MAIZE = "#FFCB05"
BLUE = "#00274C"
PRESS_START = None # for long button presses

pending_message_ids = [] # pending messages from this device specifically
message_to_channel = {} # maps message ids to channel ids
frames = []

LOGGING_SHEETS_SERVICE, LOGGING_SPREADSHEET_ID = None, None
CONFIG_SHEETS_SERVICE, CONFIG_SPREADSHEET_ID = None, None

INTERACT_SOUND = sa.WaveObject.from_wave_file("audio/send.wav")
RECEIVE_SOUND = sa.WaveObject.from_wave_file("audio/receive.wav")
RATELIMIT_SOUND = sa.WaveObject.from_wave_file("audio/ratelimit.wav")
RESOLVED_SOUND = sa.WaveObject.from_wave_file("audio/resolved.wav")

def preload_frames(root: tk.Tk):
    """
    Preloads and caches images.
    
    Args:
        root (tk.Tk): The root window.
    """
    frame_count = 149

    with Image.open("images/custom-animation-fix.gif") as gif:
        for i in range(frame_count):
            gif.seek(i)
            frames.append(load_and_scale_image(root, gif.copy()))

    # frames.append(load_and_scale_image(root, Image.open("images/stacked-white-smaller.png")))


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

    if actual["width"] == base["width"] and actual["height"] == base["height"]:
        return ImageTk.PhotoImage(img)

    scale = min(actual["width"] / base["width"], actual["height"] / base["height"])
    new_size = (int(scale * img.width), int(scale * img.height))

    resized_image = img.resize(new_size, Image.Resampling.LANCZOS)
    photo_image = ImageTk.PhotoImage(resized_image)

    return photo_image

def display_main(frame: tk.Frame, style: ttk.Style) -> None:
    """
    Displays the main (idle) screen for the user

    Args:
        frame (tk.Frame): the frame we're working with
        style (ttk.Style): the style manager for our window
    """

    def load_contents():
        oswald_96 = tkFont.Font(family="Oswald", size=scale_font(frame, 96), weight="bold")
        oswald_80 = tkFont.Font(family="Oswald", size=scale_font(frame, 80), weight="bold")

        style.configure("NeedHelp.TLabel", foreground=MAIZE, background=BLUE, font=oswald_96)
        style.configure("Instructions.TLabel", foreground=MAIZE, background=BLUE, font=oswald_80)

        dude_img_label = ttk.Label(frame, image=frames[0], background=BLUE)

        frame_count = len(frames)

        def update(index: int) -> None:
            current_frame = frames[index]
            index += 1

            if index != frame_count:
                dude_img_label.configure(image=current_frame)
                frame.after(20, update, index)

        dude_img_label.place(relx=0.5, rely=0.34, anchor="center")

        update(0)

        instruction_label = ttk.Label(frame, text="Tap the screen!",
                                    style="Instructions.TLabel")
        instruction_label.place(relx=0.5, rely=0.71+.06, anchor="center")

        # help label has to be rendered after img to be seen (layering)
        help_label = ttk.Label(frame, text="Need help?", style="NeedHelp.TLabel")
        help_label.place(relx=0.5, rely=0.57+.06, anchor="center")

    load_contents()

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
    current_time = time.time()

    message_id, channel_id = slack.handle_interaction(slack.lambda_client, do_post,
            (current_time - PRESS_START) if PRESS_START is not None else 0)

    if message_id != "statusCode":
        # clear display
        for widget in frame.winfo_children():
            widget.place_forget()

        # clear left click binding
        root.unbind("<ButtonPress-1>")
        root.unbind("<ButtonRelease-1>")
        display_post_interaction(root, frame, style, do_post)

        pending_message_ids.append(message_id)
        message_to_channel[message_id] = channel_id

        play_obj = INTERACT_SOUND.play()
        play_obj.wait_done()
    else:
        ratelimit_label = ttk.Label(frame, text="Rate limit applied. Please wait before tapping again.", style="Escape.TLabel")
        ratelimit_label.place(relx=0.5, rely=0.99, anchor="s")

        RATELIMIT_SOUND.play()

        root.after(3 * 1000, fade_label, root,
                ratelimit_label, hex_to_rgb(MAIZE), hex_to_rgb(BLUE), 0, 1500)

def display_post_interaction(root: tk.Tk, frame: tk.Frame, style: ttk.Style, do_post: bool) -> None:
    """
    Displays the post interaction instructions

    Args:
        root (tk.Tk): the root window
        frame (tk.Frame): the frame
        style (ttk.Style): the style manager for our window
        do_post (bool): whether to post to Slack
    """

    base_timeout = 180

    # countdown
    timeout = base_timeout

    oswald_96 = tkFont.Font(family="Oswald", size=scale_font(root, 96), weight="bold")
    oswald_80 = tkFont.Font(family="Oswald", size=scale_font(root, 80), weight="bold")
    oswald_36 = tkFont.Font(family="Oswald", size=scale_font(root, 36), weight="bold")
    monospace = tkFont.Font(family="Ubuntu Mono", size=scale_font(root, 36), weight="bold")

    # make a BG frame so nothing else shows through
    background_frame = tk.Frame(frame, bg=BLUE)
    background_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

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

    def update_text_widget():
        text_widget.config(state=tk.NORMAL) # enable editing

        text_widget.delete("1.0", tk.END)

        text_widget.insert(tk.END, f"{' ' if timeout < 100 else ''}", "countdown")
        text_widget.insert(tk.END, "Request times out in ", "timeout")
        text_widget.insert(tk.END, f"{timeout}", "countdown")
        text_widget.insert(tk.END, " seconds", "timeout")

        text_widget.config(state=tk.DISABLED) # disable editing

    # Initial update
    update_text_widget()

    polling_thread = threading.Thread(target=aws.poll_sqs,
                                      args=[aws.SQS_CLIENT, slack.BUTTON_CONFIG["device_id"]],
                                      daemon=True)
    polling_thread.start()

    # this helps determine whether we've received a reply later
    reply_received = False

    # do a timeout countdown
    def countdown():
        nonlocal timeout, reply_received
        nonlocal root, frame, style, do_post

        # decrement seconds left and set the label's text
        timeout -= 1
        update_text_widget()

        # if we have a message from SQS, make sure it's ours and then use it
        if aws.LATEST_MESSAGE:
            ts = aws.LATEST_MESSAGE["ts"]
            reply_author = aws.LATEST_MESSAGE["reply_author"]
            reply_text = aws.LATEST_MESSAGE["reply_text"]

            if ts in pending_message_ids:
                # if no resolving reaction/emoji, display message
                if not "white_check_mark" in reply_text and not "+1" in reply_text:
                    received_label.configure(text="")
                    waiting_label.configure(text=f"From {reply_author}\n" + reply_text)
                    waiting_label.place_configure(rely=0.5)

                    aws.LATEST_MESSAGE = None

                    # bump the timer up if necessary
                    if timeout <= base_timeout // 3 + 1:
                        timeout = base_timeout // 3 + 1

                    # make sure the system knows we replied but
                    # still allow for multi-replies
                    reply_received = True

                    # if we've received a reply mark it replied
                    message_id = pending_message_ids[0]
                    channel_id = message_to_channel[message_id]
                    aws.mark_message_replied(slack.lambda_client, message_id, channel_id, True)

                    play_obj = RECEIVE_SOUND.play()
                    play_obj.wait_done()
                # else revert to main and cancel this countdown
                else:
                    sheets_button_config = slack.get_config(CONFIG_SHEETS_SERVICE,
                                                            CONFIG_SPREADSHEET_ID,
                                                            slack.BUTTON_CONFIG["device_id"])
                    sheets.add_row(LOGGING_SHEETS_SERVICE, LOGGING_SPREADSHEET_ID,
                                    [
                                    slack.get_datetime(),
                                    sheets_button_config[3], # gets location
                                    "Resolved"
                                    ]
                                )

                    revert_to_main(root, frame, style, do_post)
                    RESOLVED_SOUND.play()
                    aws.LATEST_MESSAGE = None

        if timeout <= 0:
            revert_to_main(root, frame, style, do_post)

            sheets_button_config = slack.get_config(CONFIG_SHEETS_SERVICE,
                                                    CONFIG_SPREADSHEET_ID,
                                                    slack.BUTTON_CONFIG["device_id"])
            sheets.add_row(LOGGING_SHEETS_SERVICE, LOGGING_SPREADSHEET_ID,
                            [
                            slack.get_datetime(),
                            sheets_button_config[3], # gets location
                            "Replied" if reply_received else "Timed Out"
                            ]
                          )

            # if we have a pending message or haven't received a reply,
            # we need to time out
            if len(pending_message_ids) > 0 and not reply_received:
                message_id = pending_message_ids[0]
                channel_id = message_to_channel[message_id]

                aws.mark_message_timed_out(slack.lambda_client, message_id, channel_id, True)

        # schedule countdown until seconds_left is 1
        if timeout > 0:
            root.after(1000, countdown)
        else:
            aws.STOP_THREAD = True
            return

    root.after(1000, countdown)

    received_label = tk.Label(frame,
                            text="Help is on the way!",
                            font=oswald_96,
                            fg=MAIZE,
                            bg=BLUE,
                            anchor="center",
                            justify="center"
                            )
    received_label.place(relx=0.5, rely=0.40, anchor="center")

    waiting_label = tk.Label(frame,
                            text="Updates will be provided on this screen.",
                            font=oswald_80,
                            fg=MAIZE,
                            bg=BLUE,
                            anchor="center",
                            justify="center"
                            )
    waiting_label.configure(wraplength=root.winfo_screenwidth())
    waiting_label.place(relx=0.5, rely=0.60, anchor="center")

    root.update_idletasks() # gets stuff to load all at once

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
        widget.destroy()

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
def interpolate(start_color: tuple, end_color: tuple, time_: int) -> tuple:
    """
    Interpolates between two colors based on time

    Args:
        start_color (tuple): the color to start with
        end_color (tuple): the color to end with
        time_ (int): the amount of time that has passed

    Returns:
        An interpolated tuple somewhere between our two colors
    """
    return tuple(int(a + (b - a) * time_) for a, b in zip(start_color, end_color))

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

    time_ = (1.0 / fps) * current_step
    current_step += 1

    new_color = interpolate(start_color, end_color, time_)
    label.configure(foreground=f"#{new_color[0]:02x}{new_color[1]:02x}{new_color[2]:02x}")

    if current_step <= fps:
        frame.after(fade_duration_ms // fps, fade_label, frame,
                   label, start_color, end_color, current_step,
                   fade_duration_ms)

def setup_logging():
    """
    Runs the sheets function to set up logging,
    then sets the globals LOGGING_SHEETS_SERVICE + SPREADSHEET_ID
    """
    global LOGGING_SHEETS_SERVICE, LOGGING_SPREADSHEET_ID, CONFIG_SHEETS_SERVICE
    global CONFIG_SPREADSHEET_ID

    _, sheets_service, _, _, spreadsheet_id = sheets.setup_sheets("google_logging")
    LOGGING_SHEETS_SERVICE = sheets_service
    LOGGING_SPREADSHEET_ID = spreadsheet_id

    _, sheets_service, _, _, spreadsheet_id = sheets.setup_sheets("google_config")
    CONFIG_SHEETS_SERVICE = sheets_service
    CONFIG_SPREADSHEET_ID = spreadsheet_id

def display_gui() -> None:
    """
    Displays the TKinter GUI. Essentially the main function
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

    preload_frames(root)

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

if __name__ == "__main__":
    setup_logging()

    display_gui()
