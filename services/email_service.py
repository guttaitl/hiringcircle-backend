"""
Email service for sending transactional emails.
Supports SMTP (Gmail, SendGrid, etc.) with HTML templates.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"

# Jinja2 environment
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)


class EmailService:
    """Service for sending transactional emails."""
    
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.smtp_username = settings.SMTP_USERNAME
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_TLS
        self.use_ssl = settings.SMTP_SSL
        
        # 🔥 ADD THESE DEBUG LINES
        print("===== EMAIL CONFIG DEBUG =====")
        print("SMTP_SERVER:", self.smtp_server)
        print("SMTP_PORT:", self.smtp_port)
        print("SMTP_USERNAME:", self.smtp_username)
        print("SMTP_PASSWORD:", "SET" if self.smtp_password else None)
        print("SMTP_FROM_EMAIL:", self.from_email)
        print("================================")

    def _get_smtp_connection(self):
        """Create SMTP connection."""
        if self.use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context)
        else:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            
        if self.use_tls:
            context = ssl.create_default_context()
            server.starttls(context=context)
            
        if self.smtp_username and self.smtp_password:
            server.login(self.smtp_username, self.smtp_password)
            
        return server
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context."""
        try:
            template = jinja_env.get_template(f"{template_name}.html")
            return template.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            # Fallback to simple text
            return self._get_fallback_template(template_name, context)
    
    def _get_fallback_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Get fallback text template when HTML template is not available."""
        if template_name == "verification":
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Verify Your Email</h2>
                    <p>Hello {context.get('first_name', 'there')},</p>
                    <p>Thank you for signing up! Please click the button below to verify your email address:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{context.get('verification_url')}" 
                           style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Verify Email
                        </a>
                    </div>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{context.get('verification_url')}</p>
                    <p>This link will expire in 24 hours.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        If you didn't create an account, you can safely ignore this email.
                    </p>
                </div>
            </body>
            </html>
            """
        elif template_name == "password_reset":
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Reset Your Password</h2>
                    <p>Hello {context.get('first_name', 'there')},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{context.get('reset_url')}" 
                           style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Password
                        </a>
                    </div>
                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #666;">{context.get('reset_url')}</p>
                    <p>This link will expire in 1 hour.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                    <p style="color: #666; font-size: 12px;">
                        If you didn't request a password reset, you can safely ignore this email.
                    </p>
                </div>
            </body>
            </html>
            """
        elif template_name == "welcome":
            return f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #4F46E5;">Welcome to HiringCircle!</h2>
                    <p>Hello {context.get('first_name', 'there')},</p>
                    <p>Thank you for joining HiringCircle. Your account has been successfully created and verified.</p>
                    <p>You can now log in and start using our platform.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{context.get('login_url', settings.FRONTEND_URL + '/login')}" 
                           style="background-color: #4F46E5; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Log In
                        </a>
                    </div>
                </div>
            </body>
            </html>
            """
        return "<html><body>Email content</body></html>"
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email content
            text_content: Optional plain text content
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not all([self.smtp_username, self.smtp_password]):
            logger.warning("Email not configured. Would have sent:")
            logger.warning(f"To: {to_email}, Subject: {subject}")
            logger.warning(f"Content: {html_content[:200]}...")
            return True  # Return True in development to not block flow
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add plain text version
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML version
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with self._get_smtp_connection() as server:
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def send_verification_email(
        self,
        to_email: str,
        first_name: str,
        verification_token: str
    ) -> bool:
        """
        Send email verification email.
        
        Args:
            to_email: Recipient email address
            first_name: User's first name
            verification_token: Verification token
            
        Returns:
            True if sent successfully
        """
        verification_url = f"{settings.VERIFICATION_CALLBACK_URL}?token={verification_token}"
        
        context = {
            'first_name': first_name,
            'verification_url': verification_url,
            'app_name': settings.APP_NAME
        }
        
        html_content = self._render_template('verification', context)
        
        return self.send_email(
            to_email=to_email,
            subject=f"Verify your email - {settings.APP_NAME}",
            html_content=html_content,
            text_content=f"Please verify your email by clicking: {verification_url}"
        )
    
    def send_password_reset_email(
        self,
        to_email: str,
        first_name: str,
        reset_token: str
    ) -> bool:
        """
        Send password reset email.
        
        Args:
            to_email: Recipient email address
            first_name: User's first name
            reset_token: Password reset token
            
        Returns:
            True if sent successfully
        """
        reset_url = f"{settings.PASSWORD_RESET_CALLBACK_URL}?token={reset_token}"
        
        context = {
            'first_name': first_name,
            'reset_url': reset_url,
            'app_name': settings.APP_NAME
        }
        
        html_content = self._render_template('password_reset', context)
        
        return self.send_email(
            to_email=to_email,
            subject=f"Reset your password - {settings.APP_NAME}",
            html_content=html_content,
            text_content=f"Reset your password by clicking: {reset_url}"
        )
    
    def send_welcome_email(
        self,
        to_email: str,
        first_name: str
    ) -> bool:
        """
        Send welcome email after verification.
        
        Args:
            to_email: Recipient email address
            first_name: User's first name
            
        Returns:
            True if sent successfully
        """
        context = {
            'first_name': first_name,
            'login_url': f"{settings.FRONTEND_URL}/login",
            'app_name': settings.APP_NAME
        }
        
        html_content = self._render_template('welcome', context)
        
        return self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.APP_NAME}!",
            html_content=html_content,
            text_content=f"Welcome to {settings.APP_NAME}! Your account is now verified."
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get email service singleton instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
