#!/usr/bin/env python3

"""
Makes interfacing with Google Sheets a bit easier.

Author:
Nikki Hess (nkhess@umich.edu)
"""

import os
import json
import time
from pathlib import Path
from typing import List, TextIO#, Tuple
import traceback

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# The only scope we need is drive.file so we can create files and interact with those files
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
cache = {
	"spreadsheets": {
		"id": {
			"contents": {},
			"contents_expiry": 123456,
			"regions": {
				"A1:A1": {"contents": ["test"], "expiry": 123456}
			},
			"first_empty_row": {"index": 0, "expiry": 123456},
			"empty": {"value": False, "expiry": 123456}
		}
	}
}
cache_cooldown = 1500

def open_config() -> TextIO:
	"""
	Opens the config/google.json file. Creates one if it doesn't exist.

	Returns:
		config_file (TextIO): the config file that we opened
	"""

	config_dir = "config"

	# make sure we have a config directory first (we should...)
	if not os.path.exists(config_dir):
		Path(config_dir).mkdir(parents=True, exist_ok=True)

	# if there's no google.json, create one and tell the user
	config_path = f"{config_dir}/google.json"
	if not os.path.exists(config_path):
		with open(config_path, "w", encoding="utf8") as config_file:
			config_contents = {
				"title": "Your Title Here",
				"id": ""
			}

			json.dump(config_contents, config_file)
		print("""config/google.json did not exist, one has been created for you. Please at least fill out the \"title\" field before running again. 
			  To use an existing spreadsheet, put the \"id\" field in as well from the Google Sheets URL.""")

		exit(1)
	else:
		config_file = open(config_path, "r+", encoding="utf8")
		config_data = json.load(config_file)

		# make sure all required fields are present
		required_fields = ["title", "id"]
		missing_fields = [field for field in required_fields if field not in config_data]

		if missing_fields:
			print(f"Config file is missing the following fields: {missing_fields}")

			# add missing fields
			for field in missing_fields:
				config_data[field] = "" if field == "id" else "Your Title Here"

			# writeback
			config_file.seek(0)
			json.dump(config_data, config_file)
			config_file.truncate()

			print("The missing fields have been added with default values.")
			exit(1)

		# note to self: DON'T FORGET TO SEEK ;-;
		config_file.seek(0)

		return config_file

def do_oauth_flow() -> Credentials:
	"""
	Log a user in and return the credentials needed

	Args:
		creds (Credentials): OAuth2 user credentials
	"""

	creds = None

	if os.path.exists("config/token.json"):
		try:
			creds = Credentials.from_authorized_user_file("config/token.json", SCOPES)
		except (ValueError, json.JSONDecodeError):
			pass # just don't get creds
	
	# If there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			creds.refresh(Request())
		else:
			flow = InstalledAppFlow.from_client_secrets_file(
				"config/credentials.json", SCOPES
			)
			creds = flow.run_local_server(port=0)
		# Save the credentials for the next run
		with open("config/token.json", "w", encoding="utf8") as token:
			token.write(creds.to_json())

	return creds

def create_spreadsheet(sheets_service, name: str = "Test") -> dict:
	"""
	Create a new spreadsheet by name, returns the created spreadsheet

	Args:
		sheets_service: the Google Sheets service to be used
		name (str): the name of the spreadsheet to be created

	Returns:
		spreadsheet (dict): the created spreadsheet
	"""

	# Properties to create a spreadsheet with
	spreadsheet = {
		"properties": {
			"title": name
		}
	}

	# Call the API to create our new spreadsheet
	spreadsheet = (
		sheets_service
		.spreadsheets()
		.create(body=spreadsheet, fields="spreadsheetId")
		.execute()
	)

	return spreadsheet

def get_spreadsheet(sheets_service, drive_service, spreadsheet_id: str) -> dict:
	"""
	Gets a spreadsheet by id

	Args:
		sheets_service: the Google Sheets service to be used
		drive_service: the Google Drive service to be used
		spreadsheet_id (str): the spreadsheet id to access

	Returns:
		spreadsheet (dict): the retrieved spreadsheet, if any
	"""

	spreadsheet = None

	try:
		response = (
			drive_service
			.files()
			.get(fileId=spreadsheet_id, fields="trashed")
		).execute()
	except (HttpError):
		print(f"Invalid spreadsheet id {spreadsheet_id}. Make sure you typed it correctly!")
		exit(1)

	cached_spreadsheet = cache.get("spreadsheets", {}).get(spreadsheet_id, None)
	cached_contents = cached_spreadsheet.get("contents") if cached_spreadsheet else None
	contents_expiry = cached_spreadsheet.get("contents_expiry") if cached_spreadsheet else None

	if not response["trashed"]:
		if cached_contents is not None and contents_expiry > time.time():
			print(f"Spreadsheet {spreadsheet_id} found in cache. Retrieving...")
			spreadsheet = cache["spreadsheets"][spreadsheet_id]["contents"]
		else:
			spreadsheet = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
			print(f"Got existing spreadsheet with ID: {spreadsheet_id}")
			print(f"Caching spreadsheet...")

            # we need to make sure the structure exists first by setting a default
			cached_spreadsheet = cache.setdefault("spreadsheets", {}).setdefault(spreadsheet_id, {})
			cached_spreadsheet["contents"] = spreadsheet
			cached_spreadsheet["contents_expiry"] = time.time() + cache_cooldown
	else:
		print("Spreadsheet was trashed. We'll have to create a new one.")

	return spreadsheet

def is_spreadsheet_empty(sheets_service, spreadsheet_id: str) -> bool:
	"""
	Returns whether a given spreadsheet (by ID) is empty.
	For our purposes, this just means that A1 and B1 are empty

	Args:
		sheets_service: the Google Sheets service we're using
		spreadsheet_id (str): the spreadsheet to check for emptiness
	"""

	cached_spreadsheet = cache.get("spreadsheets", {}).get(spreadsheet_id, None)
	cached_emptiness = cached_spreadsheet.get("emptiness", {}).get("value") if cached_spreadsheet else None
	emptiness_expiry = cached_spreadsheet.get("emptiness", {}).get("expiry") if cached_spreadsheet else None

	if cached_emptiness is not None and emptiness_expiry > time.time():
		print(f"Cached value found for spreadsheet emptiness: {cached_emptiness}")
		return cached_emptiness
	else:
		try:
			result = (
				sheets_service.spreadsheets()
				.values().get(
					spreadsheetId=spreadsheet_id,
					range="A1:B1"
				).execute()
			)

			values = result.get("values", [])
			empty = (len(values) == 0)

			emptiness_dict = cache.setdefault("spreadsheets", {}).setdefault(spreadsheet_id, {}).setdefault("emptiness", {})
			emptiness_dict["value"] = empty
			emptiness_dict["expiry"] = time.time() + cache_cooldown
			print(f"Spreadsheet {spreadsheet_id} {'is' if empty else 'is not'} empty")

			return empty
		except HttpError as e:
			traceback.format_exc(e)

def find_first_empty_row(sheets_service, spreadsheet_id: str) -> int:
	"""
	Gets the last row of a given spreadsheet

	Args:
		sheets_service: the Google Sheets service to be used
		spreadsheet_id (str): the spreadsheet id to access

	Returns:
	first_empty_row (int): the first empty row in the spreadsheet
	"""

	cached_spreadsheet = cache.get("spreadsheets", {}).get(spreadsheet_id, None)
	cached_index = cached_spreadsheet.get("first_empty_row", {}).get("index") if cached_spreadsheet else None
	index_expiry = cached_spreadsheet.get("first_empty_row", {}).get("expiry") if cached_spreadsheet else None

	if cached_index is not None and index_expiry > time.time():
		last_row = cached_index

		print(f"Cached value found for spreadsheet {spreadsheet_id} first empty row: {last_row}")
	else:
		range_ = "A:A"

		result = (
			sheets_service.spreadsheets()
			.values()
			.get(
				spreadsheetId=spreadsheet_id,
				range=range_
			)
			.execute()
		)

		values = result.get("values", [])
		last_row = len(values) + 1

		index_dict = cache.setdefault("spreadsheets", {}).setdefault(spreadsheet_id, {}).setdefault("first_empty_row", {})
		index_dict["index"] = last_row
		index_dict["expiry"] = time.time() + cache_cooldown

		print(f"First empty row for spreadsheet {spreadsheet_id} is {last_row}")

	return last_row # Return the number of non-empty rows
		
def add_row(sheets_service, spreadsheet_id: str, cells: List[str]):
	"""
	Adds a row at the first empty position on the spreadsheet

	Args:
		sheets_service: the Google Sheets service to be used
		spreadsheet_id (str): the id of the spreadsheet we're operating on
		cells (list): a list of cell contents to set

	Returns:
		result: the result of the execution
	"""

	next_row = find_first_empty_row(sheets_service, spreadsheet_id)

	final_letter = len(cells) - 1
	final_letter += ord('A')
	final_letter = chr(final_letter) # 1 = A, 2 = B, etc.

	values = [
		cells
	]

	body = {"values": values}

	result = (
		sheets_service.spreadsheets()
		.values()
		.update(
			spreadsheetId=spreadsheet_id,
			range=f"A{next_row}:{final_letter}{next_row}",
			valueInputOption="USER_ENTERED",
			body=body
		)
		.execute()
	)

	print(f"{result.get('updatedCells')} cells added in row {next_row}: {cells}")
	return result

def get_region(sheets_service, spreadsheet_id: str, first_row: int = 1, last_row: int = 1,
			   first_letter: str = "A", last_letter: str = "A") -> List[str]:
	"""
	Gets a row in a spreadsheet by index (row_idx)
	
	Params:
		sheets_service: the Google Sheets service we're using
		spreadsheet_id (str): the id of the spreadsheet we're working with
		first_row (int): the first row that we need to get
		last_row (int): the last row that we need to get
		first_letter (str): the first column that we need to get
		last_letter (int): the last column that we need to get
	"""

	if first_row < 1 or last_row < 1 or first_letter < "A" or last_letter < "A":
		raise ValueError("Google Sheets starts at A1!")

	# cache = {
	# 	"spreadsheets": {
	# 		"id": {
	# 			"contents": {},
	# 			"contents_expiry": 123456,
	# 			"regions": {
	# 				"A1:A1": {"contents": ["test"], "expiry": 123456}
	# 			},
	# 			"first_empty_row": {"index": 0, "expiry": 123456},
	# 			"empty": {"value": False, "expiry": 123456}
	# 		}
	# 	}
	# }

	range = f"{first_letter}{first_row}:{last_letter}{last_row}"

	cached_spreadsheet = cache.get("spreadsheets", {}).get(spreadsheet_id, None)
	cached_region = cached_spreadsheet.get("regions", {}).get(range) if cached_spreadsheet else None
	region_expiry = cached_region.get("expiry") if cached_region else None

	if cached_region is not None and region_expiry > time.time():
		print(f"Cached region {range} found in spreadsheet {spreadsheet_id}.")
		return cached_region["contents"]
	else:
		result = (
			sheets_service.spreadsheets()
			.values()
			.get(
				spreadsheetId=spreadsheet_id,
				range=range
			)
			.execute()
		)

		try:
			contents = result["values"]
		except KeyError: # if the region is empty, there's no values
			contents = []
		
		print(f"Contents for region {range} retrieved. Caching...")

		region_dict = cache.setdefault("spreadsheets", {}).setdefault(spreadsheet_id, {}).setdefault("regions", {})
		region_dict = region_dict.setdefault(range, {})
		region_dict["contents"] = contents
		region_dict["expiry"] = time.time() + cache_cooldown

		return contents

def setup_sheets():
	"""
	Sets up a Google Sheet using the configuration provided.

	Returns:
		config_file: the config file that we created or opened
		sheets_service: the Google Sheets service we used
		drive_service: the Google Drive service we used
		spreadsheet: the spreadsheet gotten/created
		spreadsheet_id: the spreadsheet's id, for convenience
	"""

	# Log in using OAuth
	creds = do_oauth_flow()

	config_file = open_config()

	sheets_service = None
	drive_service = None
	spreadsheet = None
	spreadsheet_id = None

	try:
		sheets_service = build("sheets", "v4", credentials=creds)
		drive_service = build("drive", "v3", credentials=creds)

		# If we've already saved this spreadsheet by name, let's grab it
		config_data = json.load(config_file)
		if config_data["id"] != "":
			spreadsheet = get_spreadsheet(sheets_service, drive_service, config_data["id"])
			spreadsheet_id = config_data["id"]

		# At this point, if there is no spreadsheet we need to create one
		if spreadsheet is None:
			spreadsheet = create_spreadsheet(sheets_service, config_data["title"])

			config_data["id"] = spreadsheet.get("spreadsheetId")
			config_file.seek(0)
			json.dump(config_data, config_file)
			config_file.truncate()

			spreadsheet_id = config_data["id"]

			print(f"Created new spreadsheet with ID: {spreadsheet_id}")
	except HttpError as error:
		print(error)
	finally:
		config_file.close()

	return config_file, sheets_service, drive_service, spreadsheet, spreadsheet_id


if __name__ == "__main__":
	_, sheets_service, drive_service, _, spreadsheet_id = setup_sheets()
	get_spreadsheet(sheets_service, drive_service, spreadsheet_id)

	print("")
	empty = is_spreadsheet_empty(sheets_service, spreadsheet_id)
	empty = is_spreadsheet_empty(sheets_service, spreadsheet_id)

	print("")
	first_empty = find_first_empty_row(sheets_service, spreadsheet_id)
	first_empty = find_first_empty_row(sheets_service, spreadsheet_id)

	print("")
	region = get_region(sheets_service, spreadsheet_id)
	region = get_region(sheets_service, spreadsheet_id)