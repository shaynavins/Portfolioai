"""
Razorpay Configuration for PortfolioAI India

Single tier: ₹200/month with 14-day free trial
"""

from pydantic_settings import BaseSettings
from typing import Optional


class RazorpaySettings(BaseSettings):
    """Razorpay payment processor configuration."""
    
    # Razorpay API Keys
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_plan_id: str = ""  # Plan for ₹200/month
    razorpay_webhook_secret: str = ""
    
    # Subscription settings
    monthly_price_inr: int = 200  # ₹200/month
    trial_days: int = 14  # 14-day free trial
    currency: str = "INR"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def is_configured(self) -> bool:
        """Check if Razorpay is configured."""
        return bool(self.razorpay_key_id and self.razorpay_key_secret)
