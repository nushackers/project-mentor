"""
Handling bulk emailing from Google Sheets documents.

This works by reading from Google Sheets using the API and parsing the data into a suitable email
format before being passed off to Google App Script to be sent through emails.
"""

import os.path
from typing import Callable, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build
from jinja2 import Environment, FileSystemLoader
from requests import HTTPError

from email_utility.spreadsheet import Spreadsheet

class EmailUtility:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/script.projects'
    ]

    def __init__(self):
        self.creds = self.auth()

    def auth(self):
        # Handle the authentication part with Google
        creds: Credentials | None = None

        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        return creds

    def get_spreadsheet(
            self,
            spreadsheet_id: str,
            sheet_name: str,
            sheet_range: str,
            mapping: dict):
        # Retrieves and parses a Spreadsheet given the ID, name, and range
        try:
            service = build('sheets', 'v4', credentials=self.creds)

            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=f'{sheet_name}!{sheet_range}').execute()
            values = result.get('values', [])

            if not values:
                print('Data not found')
                return

            return Spreadsheet(sheet_range, values, mapping)
        except HTTPError as err:
            print(err)

    def send_emails(
            self,
            subject: str,
            cc: List[str],
            email_template_name: str,
            spreadsheet: Spreadsheet,
            render_content: Callable[[Spreadsheet.Row], dict],
            filter_fn: Callable[[Spreadsheet.Row], bool] = lambda s: True,
            on_send: Callable[[Spreadsheet.Row], None] = lambda s: None):
        """
        Sends the emails in bulk and maintains the emails that fail. Those that fail will have any
        status flag retained, otherwise, all successful updates will have the status flags
        updated.
        """

        template_loader = FileSystemLoader(searchpath='email_templates/')
        template_env = Environment(loader=template_loader)
        template = template_env.get_template(email_template_name)
        for row in spreadsheet.rows:
            output = template.render(render_content(row))
            print(output)




