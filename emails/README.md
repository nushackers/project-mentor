# Emails

Handles mass emailing from Google Sheets. Use this on top of any existing scripts to read from
Google Sheets and send bulk emails.

## Set up

To use these scripts, you have to first setup a Google project, follow the "Set up your
environment" steps in [this page](https://developers.google.com/apps-script/api/quickstart/python#set_up_your_environment).

Copy the `credentials.json` file to this sub-folder. It has been explicitly set to be ignored by
Git so ensure that you have copied the exact file.

Navigate to this sub-folder:

```bash
cd scripts/
```

Then, start the environment:

```bash
source venv/bin/activate
```

Run the installation scripts:

```bash
pip install -r requirements.txt
```

Once done, create a new Google AppScript project with your NUS Hackers email and add a script with
the following function:

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

Use [this as reference.](https://developers.google.com/apps-script/api/how-tos/execute#general_procedure)

## Usage

Create a new script and use the `EmailUtility` class to access Google Sheets data and send emails.

```bash
touch email_script.py
python email_script.py
```

For a sample file, see `mentor_interview_tracking_script.py`.