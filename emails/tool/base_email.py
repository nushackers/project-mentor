from abc import ABC, abstractmethod
from typing import List

from jinja2 import Environment, FileSystemLoader

from tool.google_api_wrapper import GoogleApiWrapper
from tool.spreadsheet import Spreadsheet

class EmailDetails:
    def __init__(self, to: str, subject: str, cc: str, body: str):
        self.to = to
        self.subject = subject
        self.cc = cc
        self.body = body

class BaseEmail(ABC):
    def __init__(self, spreadsheet_id: str, sheet_name: str, sheet_range: str):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.sheet_range = sheet_range
        self.wrapper = GoogleApiWrapper()
        self.sheet = self.wrapper.get_spreadsheet(self.spreadsheet_id, self.sheet_name, self.sheet_range)

    @abstractmethod
    def render_content(self, row: Spreadsheet.Row):
        pass

    @abstractmethod
    def on_send(self, rows: List[Spreadsheet.Row]):
        pass

    @abstractmethod
    def get_email(self, row: Spreadsheet.Row):
        pass

    @abstractmethod
    def filter_fn(self, row: Spreadsheet.Row):
        pass

    def send(self, email_template_name: str, subject: str, cc: List[str] = []):
        filtered_rows = [row for row in self.sheet.rows if self.filter_fn(row)]

        template_loader = FileSystemLoader(searchpath='templates/')
        template_env = Environment(loader=template_loader)
        template = template_env.get_template(email_template_name)

        data = {}
        for row in filtered_rows:
            data[row] = {
                'to': self.get_email(row),
                'subject': subject,
                'cc': ','.join(cc),
                'body': template.render(self.render_content(row)).replace('\n', '<br/>'),
            }
        successful_rows = self.wrapper.send_emails(data)

        self.on_send(successful_rows)

        print('All emails sent where possible')
        print(f'Successfully sent to {", ".join([str(r.index) for r in successful_rows])}')


