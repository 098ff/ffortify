from linebot.models import FollowEvent, TextSendMessage
from app.modules.line_api import line_bot_api, handler
from app.setup.database import check_is_registered

from app.messages.no_param import FOLLOW_WELCOME

@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=FOLLOW_WELCOME))

    # If already registered, link the member Rich Menu
    if check_is_registered(user_id):
        try:
            from app.modules.rich_menu import link_member_menu
            link_member_menu(user_id)
        except Exception as e:
            print(f"Rich Menu link on follow error (non-critical): {e}")