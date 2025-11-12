import smtplib

# Informasi akun Gmail
sender_email = "fullstackoverflow401@gmail.com"
app_password = "jjwa pgrt zcek kudv"  # Gunakan app password yang benar
recipient_email = "revaldianggars@gmail.com"

try:
    # Menghubungkan ke server Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        # Login ke akun Gmail menggunakan app password
        server.login(sender_email, app_password)
        
        # Mengirim email
        subject = "Test Email"
        body = "This is a test email sent from Python!"
        message = f"Subject: {subject}\n\n{body}"
        
        server.sendmail(sender_email, recipient_email, message)
        print("Email sent successfully!")
except smtplib.SMTPAuthenticationError as e:
    print(f"Authentication Error: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
