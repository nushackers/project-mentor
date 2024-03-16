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

from tool.spreadsheet import Spreadsheet

class GoogleApiWrapper:
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/script.send_mail'
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

    def get_spreadsheet(self, spreadsheet_id: str, sheet_name: str, sheet_range: str):
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

            return Spreadsheet(spreadsheet_id, sheet_name, sheet_range, values)
        except errors.HttpError as err:
            print(err)

    def update_spreadsheet_values(self, spreadsheet_id: str, data: List[tuple]):
        try:
            service = build('sheets', 'v4', credentials=self.creds)

            rows_update = []
            for (range_name, value) in data:
                rows_update.append({
                    'range': range_name,
                    'values': [[value]]
                })

            body = {
                'valueInputOption': 'USER_ENTERED',
                'data': rows_update
            }

            (service
                .spreadsheets()
                .values()
                .batchUpdate(spreadsheetId=spreadsheet_id, body=body)
                .execute())
        except errors.HttpError as err:
            print(err)

    def send_emails(
            self,
            subject: str,
            cc: List[str],
            email_template_name: str,
            mailer_deployment_id: str,
            spreadsheet: Spreadsheet,
            render_content: Callable[[Spreadsheet.Row], dict],
            get_email: Callable[[Spreadsheet.Row], str],
            filter_fn: Callable[[Spreadsheet.Row], bool] = lambda s: True,
            on_send: Callable[[List[Spreadsheet.Row]], None] = lambda s: None):
        template_loader = FileSystemLoader(searchpath='templates/')
        template_env = Environment(loader=template_loader)
        template = template_env.get_template(email_template_name)

        successful_rows = []

        for row in spreadsheet.rows:
            if not filter_fn(row):
                # Skip if filter condition not met
                continue

            output = template.render(render_content(row)).replace('\n', '<br/>')
            try:
                service = build('script', 'v1', credentials=self.creds)
                request = {
                    'function': 'sendMail',
                    'parameters': [get_email(row), subject, output, ','.join(cc)]
                }
                response = service.scripts().run(scriptId=mailer_deployment_id, body=request).execute()
                if 'error' in response:
                    print(f"Row {row.index} failed because {response['error']['details'][0]['errorMessage']}")
                else:
                    # Successful
                    successful_rows.append(row)
            except errors.HttpError as err:
                print(err)

        on_send(successful_rows)

        print('All emails sent where possible')
        print(f'Successfully sent to {", ".join([str(r.index) for r in successful_rows])}')



