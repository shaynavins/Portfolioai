"""SendGrid Email Integration
Handles transactional billing emails (subscriptions, payments, cancellations)
"""
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
from typing import Optional
import structlog

from api.config import settings

log = structlog.get_logger()

# Initialize SendGrid client (will be None if API key not configured)
_sg_client = None
if settings.SENDGRID_API_KEY:
    _sg_client = SendGridAPIClient(settings.SENDGRID_API_KEY)


def _get_client():
    """Get SendGrid client, return None if not configured."""
    return _sg_client


def send_subscription_welcome_email(
    user_email: str,
    user_name: str,
    plan: str,
    amount: float,
) -> bool:
    """Send welcome email when subscription is created."""
    if not _get_client():
        log.warning("SendGrid not configured, skipping welcome email")
        return False

    try:
        html_content = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h1 style="color: #1f2937;">Welcome to PortfolioAI {plan.capitalize()}! 🎉</h1>
              <p>Hi {user_name},</p>
              <p>Thank you for upgrading your account. Your {plan} subscription is now active at <strong>${amount}/month</strong>.</p>
              
              <h2 style="color: #1f2937; font-size: 18px;">What's New:</h2>
              <ul>
                <li>Unlimited portfolio rebuilds</li>
                <li>Custom domain support</li>
                <li>Advanced analytics</li>
                <li>Priority support</li>
              </ul>
              
              <p><a href="{settings.APP_URL}/dashboard" style="background-color: #1f2937; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">Go to Dashboard</a></p>
              
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="color: #6b7280; font-size: 12px;">
                Questions? Contact us at hello@portfolioai.app
              </p>
            </div>
          </body>
        </html>
        """

        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(user_email),
            subject=f"Welcome to PortfolioAI {plan.capitalize()}",
            html_content=html_content,
        )
        response = _get_client().send(message)
        log.info("Subscription welcome email sent", user_email=user_email, status=response.status_code)
        return response.status_code == 202
    except Exception as e:
        log.error("Failed to send welcome email", user_email=user_email, error=str(e))
        return False


def send_payment_success_email(
    user_email: str,
    user_name: str,
    amount: float,
    next_billing_date: str,
) -> bool:
    """Send receipt email when payment succeeds."""
    if not _get_client():
        log.warning("SendGrid not configured, skipping payment receipt")
        return False

    try:
        html_content = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h1 style="color: #059669;">Payment Successful ✓</h1>
              <p>Hi {user_name},</p>
              <p>We've received your payment. Your PortfolioAI subscription is confirmed.</p>
              
              <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Amount:</strong> ${amount:.2f}</p>
                <p style="margin: 10px 0;"><strong>Next billing date:</strong> {next_billing_date}</p>
              </div>
              
              <p>You can view your invoices anytime in your <a href="{settings.APP_URL}/dashboard">account settings</a>.</p>
              
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="color: #6b7280; font-size: 12px;">
                Questions? Contact us at hello@portfolioai.app
              </p>
            </div>
          </body>
        </html>
        """

        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(user_email),
            subject="Payment Received - PortfolioAI",
            html_content=html_content,
        )
        response = _get_client().send(message)
        log.info("Payment receipt email sent", user_email=user_email, status=response.status_code)
        return response.status_code == 202
    except Exception as e:
        log.error("Failed to send payment receipt email", user_email=user_email, error=str(e))
        return False


def send_payment_failure_email(
    user_email: str,
    user_name: str,
) -> bool:
    """Send alert email when payment fails."""
    if not _get_client():
        log.warning("SendGrid not configured, skipping payment failure alert")
        return False

    try:
        html_content = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h1 style="color: #dc2626;">Payment Failed</h1>
              <p>Hi {user_name},</p>
              <p>We weren't able to process your payment for your PortfolioAI subscription.</p>
              
              <h2 style="color: #1f2937; font-size: 18px;">What to do:</h2>
              <ol>
                <li>Go to your <a href="{settings.APP_URL}/dashboard">account settings</a></li>
                <li>Update your payment method</li>
                <li>We'll retry the payment automatically</li>
              </ol>
              
              <p style="color: #dc2626;"><strong>Your portfolio will remain live during this grace period, but your subscription may be suspended if payment is not resolved.</strong></p>
              
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="color: #6b7280; font-size: 12px;">
                Need help? Contact us at hello@portfolioai.app
              </p>
            </div>
          </body>
        </html>
        """

        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(user_email),
            subject="Action Required: Payment Failed - PortfolioAI",
            html_content=html_content,
        )
        response = _get_client().send(message)
        log.info("Payment failure alert sent", user_email=user_email, status=response.status_code)
        return response.status_code == 202
    except Exception as e:
        log.error("Failed to send payment failure alert", user_email=user_email, error=str(e))
        return False


def send_subscription_canceled_email(
    user_email: str,
    user_name: str,
) -> bool:
    """Send confirmation email when subscription is canceled."""
    if not _get_client():
        log.warning("SendGrid not configured, skipping cancellation email")
        return False

    try:
        html_content = f"""
        <html>
          <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
              <h1 style="color: #1f2937;">Subscription Canceled</h1>
              <p>Hi {user_name},</p>
              <p>Your PortfolioAI subscription has been canceled. Your portfolio will remain live, but you'll revert to the Free plan.</p>
              
              <h2 style="color: #1f2937; font-size: 18px;">What happens now:</h2>
              <ul>
                <li>You'll be downgraded to the Free plan</li>
                <li>Your portfolio stays published until you delete it</li>
                <li>You can resubscribe anytime</li>
              </ul>
              
              <p>We'd love to have you back. <a href="{settings.APP_URL}/pricing">View our plans</a> anytime.</p>
              
              <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
              <p style="color: #6b7280; font-size: 12px;">
                Feedback? We'd love to hear from you at hello@portfolioai.app
              </p>
            </div>
          </body>
        </html>
        """

        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=To(user_email),
            subject="Your PortfolioAI Subscription Has Been Canceled",
            html_content=html_content,
        )
        response = _get_client().send(message)
        log.info("Subscription cancellation email sent", user_email=user_email, status=response.status_code)
        return response.status_code == 202
    except Exception as e:
        log.error("Failed to send subscription cancellation email", user_email=user_email, error=str(e))
        return False
