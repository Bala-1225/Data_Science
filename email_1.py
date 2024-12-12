import imaplib
import email
from email import message_from_bytes
import json
from datetime import datetime
import openai
import smtplib
from email.mime.text import MIMEText

openai_api_key = openai.api_key = "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"

# Monitoring Class
class Monitoring:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password

    def monitor_and_notify(self, timestamps, intern_name, recipient_email):
        """Monitors timestamps and sends notification emails."""
        for timestamp in timestamps:
            try:
                # Convert the timestamp to a datetime object
                timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")

                # Check if time exceeds 7:00 PM
                if timestamp_obj.hour >= 19:  # 7 PM in 24-hour format
                    print(f"Notification triggered: {intern_name} didn’t submit the report.")
                    self.send_notification_email(intern_name, recipient_email)
                    return
            except Exception as e:
                print(f"Error processing timestamp {timestamp}: {e}")

    def send_notification_email(self, intern_name, recipient_email):
        """Sends an email notification using the ChatGPT-generated context."""
        try:
            # Generate the email context dynamically
            email_content = self.generate_email_context(intern_name)

            msg = MIMEText(email_content, "plain")
            msg["Subject"] = f"Intern Report Missing: {intern_name}"
            msg["From"] = self.sender_email
            msg["To"] = recipient_email

            # Send the email
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
                print(f"Notification email sent to {recipient_email}.")
        except Exception as e:
            print(f"Error sending notification email: {e}")

    def generate_email_context(self, intern_name):
        """Generates email context dynamically using ChatGPT."""
        openai.api_key = "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"  # Replace with your OpenAI API key

        prompt = f"""
        Write a polite email notification indicating that {intern_name} did not submit their daily report by the required time of 7 PM.
        Request them to provide the report as soon as possible and emphasize the importance of timely reporting.
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating email content: {e}")
            return "Error generating email content."

# Reply Handler Class
class ReplyHandler:
    def __init__(self, smtp_server, smtp_port, sender_email, sender_password, openai_api_key):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.openai_api_key = openai_api_key

    def check_and_reply(self, original_email_subject, original_message_id, recipient_email):
        """Checks if a reply was sent to the triggered email and notifies if no reply was received."""
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(self.sender_email, self.sender_password)
            mail.select("inbox")

            # Search for emails with the same subject
            status, messages = mail.search(None, f'SUBJECT "Re: {original_email_subject}"')

            if status != "OK" or not messages[0]:
                print("No reply received for the triggered email.")
                email_content = self.generate_email_content("no_reply", original_email_subject)
                self.send_notification_email(email_content, recipient_email)
            else:
                # Check if the reply is for the correct message by verifying the 'In-Reply-To' header
                is_reply_for_triggered_email = False
                for msg_id in messages[0].split():
                    status, data = mail.fetch(msg_id, '(RFC822)')
                    if status == "OK":
                        email_message = message_from_bytes(data[0][1])
                        in_reply_to = email_message.get("In-Reply-To")
                        if in_reply_to and in_reply_to == original_message_id:
                            is_reply_for_triggered_email = True
                            break

                if is_reply_for_triggered_email:
                    print("Reply has been received for the triggered email.")
                else:
                    print("Received a reply, but it is not for the triggered email.")
                    email_content = self.generate_email_content("incorrect_reply", original_email_subject)
                    self.send_notification_email(email_content, recipient_email)

            mail.logout()
        except Exception as e:
            print(f"Error checking for replies: {e}")

    def generate_email_content(self, issue_type, original_email_subject):
        """Generates dynamic email content using OpenAI based on the issue type."""
        openai.api_key = self.openai_api_key

        if issue_type == "no_reply":
            prompt = f"""
            Write a polite email to notify that no reply was received for the email with the subject "{original_email_subject}". 
            Politely ask the recipient to follow up and emphasize the importance of the reply.
            """
        elif issue_type == "incorrect_reply":
            prompt = f"""
            Write a polite email to notify that a reply was received, but it was not in response to the email with the subject "{original_email_subject}". 
            Politely request the recipient to respond to the correct email and remind them of the importance of timely and accurate responses.
            """

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error generating email content: {e}")
            return "Error generating email content."

    def send_notification_email(self, email_content, recipient_email):
        """Sends a notification email with dynamically generated content."""
        try:
            msg = MIMEText(email_content, "plain")
            msg["Subject"] = "No Reply Notification"
            msg["From"] = self.sender_email
            msg["To"] = recipient_email

            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient_email, msg.as_string())
                print(f"Notification email sent to {recipient_email}.")
        except Exception as e:
            print(f"Error sending notification email: {e}")

# Email Adapter Class
class EmailAdapter:
    def __init__(self, email_user, app_password, mailbox="inbox"):
        self.email_user = email_user
        self.app_password = app_password
        self.mailbox = mailbox

    def extract(self, search_criteria='ALL'):
        """Extracts unread emails and returns them as JSON."""
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(self.email_user, self.app_password)
        mail.select(self.mailbox)
        print(f"Searching for emails with criteria: {search_criteria}")

        status, messages = mail.search(None, search_criteria)
        if status != 'OK':
            print("Error searching emails:", messages)
            mail.logout()
            return []

        email_data = []
        for msg_id in messages[0].split():
            print(f"Fetching email ID: {msg_id}")
            status, data = mail.fetch(msg_id, '(RFC822)')
            if status != 'OK':
                print(f"Error fetching email ID {msg_id}.")
                continue
            email_message = message_from_bytes(data[0][1])
            email_content = self._extract_email_data(email_message)
            if email_content:
                email_data.append(email_content)

        mail.logout()
        return email_data

    def _extract_email_data(self, message):
        """Extracts relevant headers and body from an email message."""
        data = {
            header.lower(): message[header] for header in ['Subject', 'From', 'To', 'Date'] if message[header]
        }
        body = self._get_email_body(message)
        if body:
            data['body'] = body

        # Add email's sent timestamp instead of extraction time
        try:
            data['sent_timestamp'] = datetime.strptime(message['Date'], "%a, %d %b %Y %H:%M:%S %z").strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"Error parsing email date: {e}")
            data['sent_timestamp'] = None

        print(f"Extracted data: {data}")
        return data

    def _get_email_body(self, message):
        """Extracts the plain text body from an email message."""
        try:
            if message.is_multipart():
                for part in message.walk():
                    if part.get_content_type() == 'text/plain' and not part.get("Content-Disposition"):
                        return self._decode_body(part.get_payload(decode=True))
            else:
                return self._decode_body(message.get_payload(decode=True))
        except Exception as e:
            print(f"Error extracting body: {e}")
            return "Error extracting body."

    def _decode_body(self, payload):
        """Decodes the email body to a readable format."""
        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return payload.decode('iso-8859-1', errors='ignore')

    def extract_timestamps(self, email_data):
        """Extracts timestamps from email data."""
        timestamps = [email.get('sent_timestamp') for email in email_data]
        return timestamps

# Main function that runs the script
def main():
    email_user = "b8860157@gmail.com"
    app_password = "wymr aicj ybtq xtnj"  # Application-specific password
    openai_api_key = "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"  # Replace with your OpenAI API key

    # Create EmailAdapter instance
    adapter = EmailAdapter(email_user, app_password)
    extracted_data = adapter.extract()

    if extracted_data:
        print("Extracted Data in JSON format:")
        print(json.dumps(extracted_data, indent=4))

        # Extract and display timestamps
        timestamps = adapter.extract_timestamps(extracted_data)
        print("\nExtraction Timestamps:")
        print(json.dumps(timestamps, indent=4))

        # Monitor and notify if necessary
        monitoring = Monitoring(
            smtp_server="smtp.gmail.com",
            smtp_port=465,
            sender_email="b8860157@gmail.com",
            sender_password="wymr aicj ybtq xtnj"
        )
        monitoring.monitor_and_notify(timestamps, "Intern Name", "balajimsd098@gmail.com")

        # Check for reply and notify if none
        reply_handler = ReplyHandler(
            smtp_server="smtp.gmail.com",
            smtp_port=465,
            sender_email="b8860157@gmail.com",
            sender_password="wymr aicj ybtq xtnj",
            openai_api_key="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"  # Pass the OpenAI API key here
        )
        reply_handler.check_and_reply("Intern Report Missing: balaji", "original_message_id_here", "balajimsd098@gmail.com")

    else:
        print("No data extracted.")

if __name__ == "__main__":
    main()