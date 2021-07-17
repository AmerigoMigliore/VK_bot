from vk_api.longpoll import VkLongPoll, VkEventType
from no_git_data import token
import vk_api


vk_session = vk_api.VkApi(token=token)
session_api = vk_session.get_api()
longpoll = VkLongPoll(vk_session)
