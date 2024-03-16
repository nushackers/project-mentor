from typing import List
from tool.base_email import BaseEmail
from tool.spreadsheet import Spreadsheet

interviewers = {
  "Jiahao": {
    "calendly": "https://calendly.com/woojiahao/project-mentor-ay23-24-mentor-interview",
    "email": "woojiahao@nushackers.org"
  },
  "Mayank": {
    "calendly": "https://calendly.com/keoliyamayank/project-mentor-ay23-24",
    "email": "mayank@nushackers.org"
  },
};

class SampleEmail(BaseEmail):
    def get_email(self, row: Spreadsheet.Row):
        return row.values['Email']

    def filter_fn(self, row: Spreadsheet.Row):
        return row.values['Status'] == 'Pending'

    def on_send(self, rows: List[Spreadsheet.Row]):
        data = self.prepare_update_data('Status', rows, 'Invite Sent')
        self.wrapper.update_spreadsheet_values(self.spreadsheet_id, data)

    def render_content(self, row: Spreadsheet.Row):
        return {
            'first_name': row.values['First Name'],
            'last_name': row.values['Last Name'],
            'assigned_interviewer': row.values['Assigned Interviewer'],
            'assigned_interviewer_email': interviewers[row.values['Assigned Interviewer']]['email'],
            'assigned_interviewer_calendly': interviewers[row.values['Assigned Interviewer']]['calendly']
        }

def main():
    spreadsheet_id = '1DCm5GX0DvyNi4W_2PttBHz0Fnsxo5VeakpvIGCEoOr8'
    sheet_name = 'Sheet1'
    sheet_range = 'A1:F3'
    SampleEmail(spreadsheet_id, sheet_name, sheet_range).send('sample_email.html', 'This is a test')

if __name__ == '__main__':
    main()