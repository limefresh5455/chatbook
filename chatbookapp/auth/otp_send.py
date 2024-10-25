from rest_framework.response import Response
from rest_framework import status
import random
import smtplib
import re
import dns.resolver
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings

def is_valid_email_format( email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def is_valid_email_domain( email):
    domain = email.split('@')[1]
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout):
        return False

def verify_email_smtp( email):
    domain = email.split('@')[1]
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(mx_records[0].exchange)
        server = smtplib.SMTP()
        server.set_debuglevel(0)
        server.connect(mx_record)
        server.helo(server.local_hostname)
        server.mail('test@example.com')
        code, message = server.rcpt(email)
        server.quit()
        return code == 250
    except Exception:
        return False
######################

def send_otp_email(email: str, otp: int,username:str):
    sender = settings.SENDER_EMAIL_ID
    password = settings.SENDER_EMAIL_ID_PASSWORD

    if not is_valid_email_format(email):
        return "Invalid email format"

    if not is_valid_email_domain(email):
        return "Email domain is not valid"

    if not verify_email_smtp(email):
        return "The email address does not exist"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username=username
    # HTML template (content of the updated artifact)
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chatpdf Account Verification</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding: 20px; background-color: #ffffff;">
                    <h1 style="font-size: 28px; font-weight: bold; margin-bottom: 20px; color: #000000;">Chatpdf Verification</h1>
                    
                    <div style="border-top: 1px solid #e6e6e6; padding-top: 20px;">
                        <h2 style="font-size: 22px; margin-bottom: 10px;">TODAY'S VERIFICATION CODE</h2>
                        
                        <div style="background-color: #f9f9f9; border: 1px solid #e6e6e6; padding: 20px; margin-bottom: 20px;">
                            <p style="font-size: 16px; margin-bottom: 10px;">Hello {username},</p>
                            <p style="font-size: 16px; margin-bottom: 20px;">Thank you for creating your Chatpdf account. To complete your registration, please use the following One-Time Password (OTP):</p>
                            <p style="font-size: 32px; font-weight: bold; color: #0091F7; margin-bottom: 20px; text-align: center;">{otp}</p>
                            <p style="font-size: 14px; color: #666;">This OTP was generated on {current_time} and will expire in 5 minutes.</p>
                        </div>
                        
                        <p style="font-size: 14px; color: #666;">If you did not request this, please ignore this email.</p>
                    </div>
                    
                   
                    
                    <p style="font-size: 12px; color: #666; margin-top: 30px; text-align: center;">
                        © 2024 Chatpdf. All rights reserved.<br>
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Format the HTML content with the OTP and current time
    html_content = html_template.format(otp=otp, current_time=current_time,username=username)

    message = MIMEMultipart('alternative')
    message['From'] = sender
    message['To'] = email
    message['Subject'] = 'Verify Your Chatpdf Account'

    # Attach both plain text and HTML versions
    text_content = f"""
    Chatpdf Account Verification

    Hello {username},

    Thank you for creating your Chatpdf account. To complete your registration, please use the following One-Time Password (OTP):

    Your OTP is: {otp}

    This OTP was generated on {current_time} and will expire in 5 minutes.

    If you did not request this, please ignore this email.

    Visit Chatpdf: https://www.chatpdf.com

    © 2024 Chatpdf. All rights reserved.
    """
    
    text_part = MIMEText(text_content, 'plain')
    html_part = MIMEText(html_content, 'html')

    message.attach(text_part)
    message.attach(html_part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.sendmail(sender, email, message.as_string())
        server.quit()
        return "Email sent successfully"
    except smtplib.SMTPException as e:
        return f"Failed to send email: {e}"
 
##############
def resend_otp_email(email: str, otp: int,username:str):
    sender = settings.SENDER_EMAIL_ID
    password = settings.SENDER_EMAIL_ID_PASSWORD

    if not is_valid_email_format(email):
        return "Invalid email format"

    if not is_valid_email_domain(email):
        return "Email domain is not valid"

    if not verify_email_smtp(email):
        return "The email address does not exist"

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username=username
    # HTML template (content of the updated artifact)
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Chatpdf Account Verification</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding: 20px; background-color: #ffffff;">
                    <h1 style="font-size: 28px; font-weight: bold; margin-bottom: 20px; color: #000000;">Chatpdf Verification</h1>
                    
                    <div style="border-top: 1px solid #e6e6e6; padding-top: 20px;">
                        <h2 style="font-size: 22px; margin-bottom: 10px;">TODAY'S VERIFICATION CODE</h2>
                        
                        <div style="background-color: #f9f9f9; border: 1px solid #e6e6e6; padding: 20px; margin-bottom: 20px;">
                            <p style="font-size: 16px; margin-bottom: 10px;">Hello {username},</p>
                            <p style="font-size: 16px; margin-bottom: 20px;">Thank you for creating your Chatpdf account. To complete your registration, please use the following One-Time Password (OTP):</p>
                            <p style="font-size: 32px; font-weight: bold; color: #0091F7; margin-bottom: 20px; text-align: center;">{otp}</p>
                            <p style="font-size: 14px; color: #666;">This OTP was generated on {current_time} and will expire in 5 minutes.</p>
                        </div>
                        
                        <p style="font-size: 14px; color: #666;">If you did not request this, please ignore this email.</p>
                    </div>
                    
                    
                    
                    <p style="font-size: 12px; color: #666; margin-top: 30px; text-align: center;">
                        © 2024 Chatpdf. All rights reserved.<br>
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Format the HTML content with the OTP and current time
    html_content = html_template.format(otp=otp, current_time=current_time,username=username)

    message = MIMEMultipart('alternative')
    message['From'] = sender
    message['To'] = email
    message['Subject'] = 'Verify Your Chatpdf Account'

    # Attach both plain text and HTML versions
    text_content = f"""
    Chatpdf Account Verification

    Hello {username},

    Thank you for creating your Chatpdf account. To complete your registration, please use the following One-Time Password (OTP):

    Your OTP is: {otp}

    This OTP was generated on {current_time} and will expire in 5 minutes.

    If you did not request this, please ignore this email.

    Visit Chatpdf: https://www.chatpdf.com

    © 2024 Chatpdf. All rights reserved.
    """
    
    text_part = MIMEText(text_content, 'plain')
    html_part = MIMEText(html_content, 'html')

    message.attach(text_part)
    message.attach(html_part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender, password)
        server.sendmail(sender, email, message.as_string())
        server.quit()
        return "Email sent successfully"
    except smtplib.SMTPException as e:
        return f"Failed to send email: {e}"
    
  
############################
# def send_otp_email(email: str, otp: int):
#     sender = 'hariomkumawat.steveailab@gmail.com'
#     password = 'tsep ossh kpip vlkf'

#     if not is_valid_email_format(email):
#         return "Invalid email format"

#     if not is_valid_email_domain(email):
#         return "Email domain is not valid"

#     if not verify_email_smtp(email):
#         return "The email address does not exist"

#     current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     body = f"""
#     Hello!

#     Thank you for creating your Chatpdf account.

#     To complete your registration, please use the following OTP (One-Time Password):

#     Your OTP for email verification is: {otp}

#     This OTP was generated on {current_time} and will expire in 5 minute.

#     If you did not request this, please ignore this email.

#     Best regards,
#     The Chatpdf Team
#     https://www.Chatpdf.com
    
#     """

#     message = MIMEMultipart()
#     message['From'] = sender
#     message['To'] = email
#     message['Subject'] = 'Verify Your Chatpdf Account'
#     message.attach(MIMEText(body, 'plain'))

#     try:
#         server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
#         server.login(sender, password)
#         server.sendmail(sender, email, message.as_string())
#         server.quit()
#         return "Email sent successfully"
#     except smtplib.SMTPException as e:
#         return f"Failed to send email: {e}"



def post( request):
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    otp = random.randint(100000, 999999)
    result = send_otp_email(email, otp)

    if result == "Email sent successfully":
        return Response({"message": "OTP sent successfully", "otp": otp}, status=status.HTTP_200_OK)
    else:
        return Response({"error": result}, status=status.HTTP_400_BAD_REQUEST)
    
    