import asyncio
from typing import Any

async def send_otp_email(email: str, otp: str) -> None:
    # Replace with your real email sending logic (e.g. using SMTP, SendGrid, etc.)
    print(f"Sending OTP {otp} to email: {email}")
    # Example async sleep to simulate sending delay
    await asyncio.sleep(0.1)