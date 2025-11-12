import smtplib

sender_email = "your_email@gmail.com"
app_password = "your_app_password"
recipient_email = "candidate_email@example.com"

try:
    # Hubungkan ke server SMTP Gmail
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        # Login ke akun Gmail menggunakan App Password
        server.login(sender_email, app_password)
        
        # Isi email
        subject = "Interview Invitation"
        body = f"""
        Dear Candidate,

        We are pleased to invite you to an interview session. Below are the details:
        
        Zoom Meeting Link: {meeting_link}
        Date and Time: January 15, 2025, 10:00 AM (Jakarta Time)
        Duration: 30 minutes
        
        Best regards,
        Recruitment Team
        """

        message = f"Subject: {subject}\n\n{body}"
        server.sendmail(sender_email, recipient_email, message)
        print("Email sent successfully!")
except Exception as e:
    print(f"An error occurred: {e}")
