import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import os
from typing import Optional, List
import logging
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config.settings import get_settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        """Initialize the EmailService with SMTP configuration from settings"""
        try:
            self.settings = get_settings()
            
            # SMTP Configuration from settings
            self.smtp_server = self.settings.SMTP_SERVER
            self.smtp_port = self.settings.SMTP_PORT
            self.email_user = self.settings.EMAIL_USER
            self.email_password = self.settings.EMAIL_PASSWORD
            self.from_email = self.settings.FROM_EMAIL or self.email_user
            
            # Email Templates Configuration
            template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'email')
            self.env = Environment(loader=FileSystemLoader(template_dir))
            
            # Thread pool for async email sending
            self.executor = ThreadPoolExecutor(max_workers=3)
            
            logger.info(f"EmailService initialized with SMTP server: {self.smtp_server}:{self.smtp_port}")
            
        except Exception as e:
            logger.error(f"Failed to initialize EmailService: {str(e)}")
            raise

    def _send_email_sync(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Synchronous email sending method"""
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.from_email
            message["To"] = to_email

            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Create secure connection and send email
            context = ssl.create_default_context()
            logger.info(f"Attempting to connect to SMTP server {self.smtp_server}:{self.smtp_port}")
            logger.info(f"Using email credentials - User: {self.email_user}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                logger.info("SMTP connection established, starting TLS")
                server.starttls(context=context)
                
                logger.info("TLS started, attempting login")
                server.login(self.email_user, self.email_password)
                
                logger.info("Login successful, sending email")
                server.sendmail(self.from_email, to_email, message.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_email_async(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Asynchronous email sending method"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, 
            self._send_email_sync, 
            to_email, 
            subject, 
            html_content, 
            text_content
        )

    def render_template(self, template_name: str, **kwargs) -> str:
        """Render email template with provided context"""
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            return f"<html><body><h1>Email Content</h1><p>Error rendering template: {str(e)}</p></body></html>"

    async def send_registration_confirmation(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        event_date: str, 
        venue: str,
        registration_id: Optional[str] = None
    ) -> bool:
        """Send registration confirmation email"""
        try:
            subject = f"Registration Confirmed - {event_title}"
            
            html_content = self.render_template(
                'registration_confirmation.html',
                student_name=student_name,
                event_title=event_title,
                event_date=event_date,
                event_venue=venue,
                registration_id=registration_id
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send registration confirmation: {str(e)}")
            return False

    async def send_payment_confirmation(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        amount: float, 
        payment_id: str,
        event_date: Optional[str] = None
    ) -> bool:
        """Send payment confirmation email"""
        try:
            subject = f"Payment Confirmed - {event_title}"
            
            html_content = self.render_template(
                'payment_confirmation.html',
                student_name=student_name,
                event_title=event_title,
                amount=amount,
                payment_id=payment_id,
                event_date=event_date
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send payment confirmation: {str(e)}")
            return False

    async def send_attendance_confirmation(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        attendance_date: str,
        event_venue: Optional[str] = None
    ) -> bool:
        """Send attendance confirmation email"""
        try:
            subject = f"Attendance Confirmed - {event_title}"
            
            html_content = self.render_template(
                'attendance_confirmation.html',
                student_name=student_name,
                event_title=event_title,
                attendance_date=attendance_date,
                event_venue=event_venue
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send attendance confirmation: {str(e)}")
            return False

    async def send_feedback_confirmation(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str,
        event_date: Optional[str] = None
    ) -> bool:
        """Send feedback submission confirmation email"""
        try:
            subject = f"Thank you for your feedback - {event_title}"
            
            html_content = self.render_template(
                'feedback_confirmation.html',
                student_name=student_name,
                event_title=event_title,
                event_date=event_date
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send feedback confirmation: {str(e)}")
            return False

    async def send_event_reminder(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        event_date: str, 
        event_venue: str,
        reminder_type: str = "upcoming"
    ) -> bool:
        """Send event reminder email"""
        try:
            subject = f"Reminder: {event_title} - {reminder_type.title()}"
            
            html_content = self.render_template(
                'event_reminder.html',
                student_name=student_name,
                event_title=event_title,
                event_date=event_date,
                event_venue=event_venue,
                reminder_type=reminder_type
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send event reminder: {str(e)}")
            return False

    async def send_certificate_notification(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        certificate_url: str,
        event_date: Optional[str] = None
    ) -> bool:
        """Send certificate available notification email"""
        try:
            subject = f"Certificate Available - {event_title}"
            
            html_content = self.render_template(
                'certificate_notification.html',
                student_name=student_name,
                event_title=event_title,
                certificate_url=certificate_url,
                event_date=event_date
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send certificate notification: {str(e)}")
            return False

    async def send_new_event_notification(
        self, 
        student_email: str, 
        student_name: str, 
        event_title: str, 
        event_date: str, 
        event_venue: str,
        registration_url: Optional[str] = None
    ) -> bool:
        """Send new event notification email"""
        try:
            subject = f"New Event Available: {event_title}"
            
            html_content = self.render_template(
                'new_event_notification.html',
                student_name=student_name,
                event_title=event_title,
                event_date=event_date,
                event_venue=event_venue,
                registration_url=registration_url
            )
            
            return await self.send_email_async(student_email, subject, html_content)
            
        except Exception as e:
            logger.error(f"Failed to send new event notification: {str(e)}")
            return False

    async def send_bulk_emails(self, email_tasks: List[tuple]) -> List[bool]:
        """Send multiple emails concurrently"""
        try:
            tasks = []
            for task in email_tasks:
                method_name, args = task[0], task[1:]
                if hasattr(self, method_name):
                    method = getattr(self, method_name)
                    tasks.append(method(*args))
            
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return [isinstance(result, bool) and result for result in results]
            return []
            
        except Exception as e:
            logger.error(f"Failed to send bulk emails: {str(e)}")
            return [False] * len(email_tasks)

    def __del__(self):
        """Clean up the thread pool executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)