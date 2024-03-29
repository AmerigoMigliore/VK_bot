def get_text_button(text, color):
    return {
        "action": {
            "type": "text",
            "label": str(text)
        },
        "color": color
    }


def get_callback_button(text, color, payload):
    if payload is None:
        payload = {}
    return {
        "action": {
            "type": "callback",
            "payload": payload,
            "label": str(text)
        },
        "color": color
    }


def get_vkpay_button(description, amount=1):
    return {
        "action": {
            "type": "vkpay",
            "hash": "action=pay-to-group&"
                    "amount={}&"
                    "description={}&"
                    "group_id=205785357&"
                    "aid=205785357".format(amount, description)
        }
    }
