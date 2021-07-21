def get_text_button(text, color):
    return {
        "action": {
            "type": "text",
            "payload": "{}",
            "label": f"{text}"
        },
        "color": f"{color}"
    }


def get_callback_button(text, color, payload=None):
    if payload is None:
        payload = {}
    return {
        "action": {
            "type": "callback",
            "payload": payload,
            "label": text
        },
        "color": color
    }
