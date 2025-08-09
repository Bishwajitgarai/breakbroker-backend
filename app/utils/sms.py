import asyncio
from typing import Any

async def send_otp_sms(phone: str, otp: str) -> None:
    # Replace with your real SMS sending logic (e.g. Twilio, Nexmo)
    print(f"Sending OTP {otp} to phone: {phone}")
    # Example async sleep to simulate sending delay
    await asyncio.sleep(0.1)