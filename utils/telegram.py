import httpx


async def send_telegram_message(
    bottoken: str, chatid: str, message: str
) -> dict:
    url = f"https://api.telegram.org/bot{bottoken}/sendMessage"
    payload = {"chat_id": chatid, "text": message}
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
    return response.json()
