from email_utility.email_utility import EmailUtility

def main():
    email_utility = EmailUtility(
        '1KafDSbnhJWD06_p3opd6GRpNBdMU8A_ObrEXYpCE9S4',
        'Mentor Interview Tracker!A1:F105',
        'mentor_interview_tracker.html'
    )
    mapping = {
        'First Name': 'first_name',
        'Last Name': 'last_name',
        'Telegram': 'telegram',
        'Email': 'email',
        'Assigned Interviewer': 'assigned_interviewer',
        'Status': 'status',
    }
    sheet = email_utility.get_spreadsheet(mapping)
    email_utility.send_emails()

if __name__ == '__main__':
    main()