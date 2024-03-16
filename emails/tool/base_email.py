from abc import ABC, abstractmethod
from typing import List

from tool.google_api_wrapper import GoogleApiWrapper
from tool.spreadsheet import Spreadsheet


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

        successful_rows = self.wrapper.send_emails(
            subject=subject,
            cc=cc,
            email_template_name=email_template_name,
            rows=filtered_rows,
            render_content=self.render_content,
            get_email=self.get_email
        )

        self.on_send(successful_rows)

        print('All emails sent where possible')
        print(f'Successfully sent to {", ".join([str(r.index) for r in successful_rows])}')


