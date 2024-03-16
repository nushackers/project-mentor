
from typing import List
from tool.google_api_wrapper import GoogleApiWrapper
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

def main():
    spreadsheet_id = '1DCm5GX0DvyNi4W_2PttBHz0Fnsxo5VeakpvIGCEoOr8'
    sheet_name = 'Sheet1'
    sheet_range = 'A1:F3'

    wrapper = GoogleApiWrapper()

    # This is a sample Google Sheet, replace this with whatever code you use
    sheet = wrapper.get_spreadsheet(spreadsheet_id, sheet_name, sheet_range)

    def render_content(row: Spreadsheet.Row):
        return {
            'first_name': row.values['First Name'],
            'last_name': row.values['Last Name'],
            'assigned_interviewer': row.values['Assigned Interviewer'],
            'assigned_interviewer_email': interviewers[row.values['Assigned Interviewer']]['email'],
            'assigned_interviewer_calendly': interviewers[row.values['Assigned Interviewer']]['calendly']
        }

    def on_send(rows: List[Spreadsheet.Row]):
        status_column_letter = sheet.get_header_letter('Status')
        data = []
        for i in range(len(rows)):
            range_name = f'{sheet.sheet_name}!{status_column_letter}{rows[i].index}'
            data.append((range_name, 'Invite Sent'))
        print(data)
        wrapper.update_spreadsheet_values(spreadsheet_id, data)


    # This is using my (Jiahao) personal deployment id, but it should be accessible so long as you
    # are within the NUS Hackers organization
    wrapper.send_emails(
        subject='Test email',
        cc=[],
        email_template_name='sample_email.html',
        mailer_deployment_id='AKfycbwAe_N_JCR3s7KJRLuX30ybhX2N0SNua1FiKDbiHbU',
        spreadsheet=sheet,
        render_content=render_content,
        get_email=lambda row: row.values['Email'],
        filter_fn=lambda row: row.values['Status'] == 'Pending',
        on_send=on_send
    )

if __name__ == '__main__':
    main()