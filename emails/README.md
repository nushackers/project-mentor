# Emails

Bulk send email using your personal email account and reading from a Google Sheets

## How this works

- Reading data: Google Sheets API
- Sending emails: Google AppScript + MailApp API
- Updating values: Google Sheets API
- Email templating: Jinja2

## Set up

To use these scripts, you have to first setup a Google project, follow the "Set up your
environment" steps in [this page](https://developers.google.com/apps-script/api/quickstart/python#set_up_your_environment).

Copy the `credentials.json` file to this sub-folder. It has been explicitly set to be ignored by
Git so ensure that you have copied the exact file.

Once done, create a new Google AppScript project and add the following function:

```gs
function sendMail(to, subject, htmlBody, cc) {
  MailApp.sendEmail({
    to: to,
    subject: subject,
    htmlBody: htmlBody,
    cc: cc
  });
}
```

Then, setup the script as a deployment using
[this as reference.](https://developers.google.com/apps-script/api/how-tos/execute#general_procedure)

Then to setup the project.

Navigate to this sub-folder:

```bash
cd emails/
```

Add your deployment key for AppScript by copying `.env.example` to `.env`:

```env
MAILER_DEPLOYMENT_KEY=
```

Then, start the environment:

```bash
source venv/bin/activate
```

Run the installation scripts:

```bash
pip install -r requirements.txt
```

## Usage

Create a Python script and initialize a class that extends `BaseEmail`. Implement the functions for:

- `get_email` - retrieves the target email
- `render_content` - specifies the fields and values to be rendered by Jinja in the email
- `on_send` - action to be performed on all successfully sent rows
- `filter_fn` - filters the rows to send an email for

Create a corresponding HTML template in `templates/` where any variables to be injected is wrapped with `{{ }}`:

```html
Hi {{ first_name }} {{ last_name }},

On behalf of NUS Hackers and the Student Life Office, thank you for your application to be a mentor for Project Mentor AY23/24. Project Mentor hopes to enrich the lives of the freshmen of the School of Computing (SoC) by pairing them with mentors to help them navigate their first year in SoC

We would like to arrange a quick <strong>15 minute</strong> chat with you between <u>1 August to 10 August</u> to get to know you and understand your priorities and goals as a mentor. It is not a formal session so don't worry about having the right answers, just be yourself!

<strong>Interview details</strong>
Interviewer: {{ assigned_interviewer }} ({{ assigned_interviewer_email }})
Book your session: {{ assigned_interviewer_calendly }}

If you have any questions, feel free to reach out to mentorship2023@nushackers.org

Once again, thank you for your interest in being a mentor and we are excited to meet you!

Regards,
Jiahao
NUS Hackers Coreteam
```

Then, initialize the class and call `send(email_template_path, subject, cc=[])`:

```python
spreadsheet_id = ''
sheet_name = ''
sheet_range = ''
SampleEmail(spreadsheet_id, sheet_name, sheet_range).send('sample_email.html', 'This is a test')
```

Sample implementation:

```python
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
```