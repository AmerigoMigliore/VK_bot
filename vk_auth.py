import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from no_git_data import token

vk_session = vk_api.VkApi(token=token)
session_api = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, 205785357)
