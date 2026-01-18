"""
Telegram Bot Integration for DoseClock.
Handles sending medication reminders via Telegram.
"""

import requests
import json
from datetime import datetime
from django.conf import settings

# Bot Token - DO NOT share this publicly
TELEGRAM_BOT_TOKEN = "8291858617:AAEXmQWkkztJ0AHaGT9BqHWzJJZIHdt5uys"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def send_telegram_message(chat_id, text, reply_markup=None):
    """
    Send a message to a Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        text: Message text (supports HTML formatting)
        reply_markup: Optional inline keyboard
    
    Returns:
        dict with success status and response
    """
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            return {"success": True, "message_id": result["result"]["message_id"]}
        else:
            return {"success": False, "error": result.get("description", "Unknown error")}
    
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def send_dose_reminder(chat_id, medication_name, scheduled_time, dose_id):
    """
    Send a medication reminder with confirm button.
    
    Args:
        chat_id: Telegram chat ID
        medication_name: Name of the medication
        scheduled_time: Scheduled time for the dose
        dose_id: UUID of the dose for confirmation
    """
    time_str = scheduled_time.strftime("%H:%M")
    date_str = scheduled_time.strftime("%d/%m/%Y")
    
    text = (
        f"<b>💊 Recordatorio de Medicamento</b>\n\n"
        f"<b>Medicamento:</b> {medication_name}\n"
        f"<b>Hora programada:</b> {time_str}\n"
        f"<b>Fecha:</b> {date_str}\n\n"
        f"<i>Recuerda tomar tu medicamento a tiempo.</i>"
    )
    
    # Inline keyboard with confirm button
    reply_markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Confirmar Toma", "callback_data": f"confirm_{dose_id}"}
            ],
            [
                {"text": "⏰ Recordar en 15 min", "callback_data": f"snooze_{dose_id}"}
            ]
        ]
    }
    
    return send_telegram_message(chat_id, text, reply_markup)


def send_upcoming_reminder(chat_id, medication_name, minutes_until):
    """
    Send a reminder that a dose is coming up.
    
    Args:
        chat_id: Telegram chat ID
        medication_name: Name of the medication
        minutes_until: Minutes until the dose
    """
    text = (
        f"<b>⏰ Recordatorio Anticipado</b>\n\n"
        f"En <b>{minutes_until} minutos</b> debes tomar:\n"
        f"<b>💊 {medication_name}</b>\n\n"
        f"<i>Prepara tu medicamento.</i>"
    )
    
    return send_telegram_message(chat_id, text)


def send_missed_dose_alert(chat_id, medication_name, scheduled_time):
    """
    Send alert for a missed dose.
    
    Args:
        chat_id: Telegram chat ID
        medication_name: Name of the medication
        scheduled_time: When the dose was scheduled
    """
    time_str = scheduled_time.strftime("%H:%M")
    
    text = (
        f"<b>⚠️ Toma No Confirmada</b>\n\n"
        f"No confirmaste la toma de:\n"
        f"<b>💊 {medication_name}</b>\n"
        f"Programada para las <b>{time_str}</b>\n\n"
        f"<i>Si ya la tomaste, puedes ignorar este mensaje.</i>"
    )
    
    return send_telegram_message(chat_id, text)


def send_welcome_message(chat_id, user_name=None):
    """
    Send welcome message when user links their account.
    
    Args:
        chat_id: Telegram chat ID
        user_name: Optional user name
    """
    greeting = f"Hola {user_name}! " if user_name else "Hola! "
    
    text = (
        f"<b>💊 Bienvenido a DoseClock</b>\n\n"
        f"{greeting}Tu cuenta de Telegram ha sido vinculada correctamente.\n\n"
        f"<b>Recibiras:</b>\n"
        f"• Recordatorios de tus medicamentos\n"
        f"• Alertas anticipadas\n"
        f"• Notificaciones de tomas pendientes\n\n"
        f"<b>Comandos disponibles:</b>\n"
        f"/estado - Ver tus proximas tomas\n"
        f"/ayuda - Mostrar ayuda\n\n"
        f"<i>Puedes confirmar tus tomas directamente desde aqui!</i>"
    )
    
    return send_telegram_message(chat_id, text)


def get_bot_updates(offset=None):
    """
    Get updates (messages) sent to the bot.
    Used to get chat_id when user starts conversation.
    
    Args:
        offset: Update offset to avoid duplicates
    
    Returns:
        List of updates
    """
    url = f"{TELEGRAM_API_URL}/getUpdates"
    params = {"timeout": 30}
    
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params, timeout=35)
        result = response.json()
        
        if result.get("ok"):
            return result.get("result", [])
        return []
    
    except requests.RequestException:
        return []


def get_chat_id_from_username(username):
    """
    Try to find chat_id from recent messages.
    User must have sent a message to the bot first.
    
    Args:
        username: Telegram username (without @)
    
    Returns:
        chat_id if found, None otherwise
    """
    updates = get_bot_updates()
    
    for update in updates:
        message = update.get("message", {})
        from_user = message.get("from", {})
        
        if from_user.get("username", "").lower() == username.lower():
            return from_user.get("id")
    
    return None


def verify_bot_token():
    """
    Verify the bot token is valid.
    
    Returns:
        dict with bot info if valid
    """
    url = f"{TELEGRAM_API_URL}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        
        if result.get("ok"):
            return {
                "valid": True,
                "bot_name": result["result"].get("first_name"),
                "bot_username": result["result"].get("username")
            }
        return {"valid": False, "error": result.get("description")}
    
    except requests.RequestException as e:
        return {"valid": False, "error": str(e)}


def process_callback_query(callback_query_id, text="Procesado"):
    """
    Answer a callback query (button press).
    
    Args:
        callback_query_id: ID of the callback query
        text: Text to show as notification
    """
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    
    payload = {
        "callback_query_id": callback_query_id,
        "text": text
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.RequestException:
        pass
