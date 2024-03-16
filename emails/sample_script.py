
from email_utility.email_utility import EmailUtility
from email_utility.spreadsheet import Spreadsheet

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
    email_utility = EmailUtility()

    mapping = {
        'First Name': 'first_name',
        'Last Name': 'last_name',
        'Telegram': 'telegram',
        'Email': 'email',
        'Assigned Interviewer': 'assigned_interviewer',
        'Status': 'status',
    }
    sheet = email_utility.get_spreadsheet(
        '1DCm5GX0DvyNi4W_2PttBHz0Fnsxo5VeakpvIGCEoOr8',
        'Sheet1',
        'A1:F3',
        mapping)

    def render_content(row: Spreadsheet.Row):
        print(row.values)
        return {
            'first_name': row.values['First Name'],
            'last_name': row.values['Last Name'],
            'assigned_interviewer': row.values['Assigned Interviewer'],
            'assigned_interviewer_email': interviewers[row.values['Assigned Interviewer']]['email'],
            'assigned_interviewer_calendly': interviewers[row.values['Assigned Interviewer']]['calendly']
        }

    email_utility.send_emails(
        'Test email',
        ['woojiahao1234@gmail.com'],
        'sample_email.html',
        sheet,
        render_content,
        lambda row: row.values['status'] == 'Pending',
    )

if __name__ == '__main__':
    main()