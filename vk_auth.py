import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.longpoll import VkLongPoll, VkEventType
from no_git_data import bot_token, my_token

vk_session = vk_api.VkApi(token=bot_token)
session_api = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, 205785357)

my_vk_session = vk_api.VkApi(token=my_token)
my_session_api = my_vk_session.get_api()
my_longpoll = VkLongPoll(my_vk_session)
