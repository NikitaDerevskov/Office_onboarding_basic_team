from dialog_bot_sdk.bot import DialogBot
from dialog_bot_sdk import interactive_media
from threading import Timer
from pymongo import MongoClient
import grpc
import time

# Utils
client = MongoClient(
    "mongodb://team:123ert@ds018839.mlab.com:18839/new_hackaton", retryWrites=False
)
db = client.new_hackaton
users = db.users
guides = db.guides
bot_token = "4a3a998e50c55e13fb4ef9a52a224303602da6af"
tokens = db.tokens

# https://github.com/dialogs/chatbot-hackathon - basic things
# https://hackathon.transmit.im/web/#/im/u2108492517 - bot


def add_user_to_admins(id, company):
    users.insert_one({"type": "Office-manager", "id": id, "company":company})


def add_user_to_users(id, company):
    users.insert_one({"type": "User", "id": id, "company":company})


def is_exist(id):
    return False if users.find_one({"id": id}) is None else True


def is_manager(id):
    return True if users.find_one({"id": id})["type"] == "Office-manager" else False


def on_msg(msg, peer):
    bot.messaging.send_message(peer, msg)


def has_token(id, *params):
    message = params[0].message.textMessage.text
    token = tokens.find_one({"token": message})
    if token is None:
        return want_to_create(*params)
    else:
        return whose_token(token, id, params[0].peer)
    

def whose_token(token, id, peer):
    current_time = int(time.time()*1000.0)
    current_token = tokens.find_one({"token": token})
    
    if(current_time - int(token['time']) >= 24*60*60*1000):
        delete_token(token)
        return on_msg("Токен устарел Т_Т, проси новый", peer)

    if token["type"] == "Office-manager":
        on_msg("Ты одмен", peer)
        send_manager_buttons(id, peer)
        return add_user_to_admins(id, token["company"])
    else:
        on_msg("Ты юзер", peer)
        send_guides(id, peer)
        return add_user_to_users(id, token["company"])


def want_to_create(*params):
    bot.messaging.send_message(
        params[0].peer,
        "Создай компанию, плз",
        [
            interactive_media.InteractiveMediaGroup(
                [
                    interactive_media.InteractiveMedia(
                        1,
                        interactive_media.InteractiveMediaButton(
                            "create_company", "Давай"
                        ),
                    ),
                    interactive_media.InteractiveMedia(
                        1, interactive_media.InteractiveMediaButton("Test", "Не давай")
                    ),
                ]
            )
        ],
    )


# TODO
def send_manager_buttons(id, peer):
    bot.messaging.send_message(peer, "Sending manager buttons")

    buttons = [
        interactive_media.InteractiveMediaGroup(
            [
                interactive_media.InteractiveMedia(
                    1,
                    interactive_media.InteractiveMediaButton(
                        "add_guide", "Добавить гайд"
                    ),
                ),
                interactive_media.InteractiveMedia(
                    1,
                    interactive_media.InteractiveMediaButton(
                        "get_user_token", "Получить ключ для юзера"
                    ),
                ),
                interactive_media.InteractiveMedia(
                    1,
                    interactive_media.InteractiveMediaButton(
                        "get_admin_token", "Получить ключ для админа"
                    ),
                ),
                interactive_media.InteractiveMedia(
                    1,
                    interactive_media.InteractiveMediaButton(
                        "delete_guide", "Удалить гайд"
                    ),
                ),
                interactive_media.InteractiveMedia(
                    1,
                    interactive_media.InteractiveMediaButton(
                        "get_guides", "Получить все гайды"
                    ),
                ),
            ]
        )
    ]

    bot.messaging.send_message(peer, "Choose option", buttons)


# TODO
def send_guides(id, peer):
    bot.messaging.send_message(peer, "Sending guides")

    buttons = [
        interactive_media.InteractiveMediaGroup(
            [
                interactive_media.InteractiveMedia(
                    2,
                    interactive_media.InteractiveMediaButton(
                        "kitchen", "Guide about kitchen"
                    ),
                ),
                interactive_media.InteractiveMedia(
                    3,
                    interactive_media.InteractiveMediaButton(
                        "wifi", "Guide about wifi"
                    ),
                ),
            ]
        )
    ]

    bot.messaging.send_message(peer, "Choose guide", buttons)


def auth(id, peer, *params):
    if is_exist(id):
        send_manager_buttons(id, peer) if is_manager(id) else get_guides(id, peer)
    else:
        # TODO WORK WITH TOKEN
        has_token(id, *params)


def start_text(peer):
    bot.messaging.send_message(
        peer, "This is start message, you can use /info to get details!"
    )


def info_text(peer):
    bot.messaging.send_message(peer, "This is info message")


# Main fun
def main(*params):
    id = params[0].peer.id
    peer = params[0].peer
    if params[0].message.textMessage.text == "/info":
        info_text(peer)
        return

    bot.messaging.send_message(peer, "Hey")

    if params[0].message.textMessage.text == "/start":
        start_text(peer)
        return
    if params[0].message.textMessage.text[0:8] == "/company":
        users.insert_one(
            {
                "type": "Office-manager",
                "company": params[0].message.textMessage.text[9:],
                "id": id,
            }
        )
        bot.messaging.send_message(peer, "Компания успешно создана. Теперь вы админ")
        auth(id, peer, *params)
        return

    auth(id, peer, *params)


def render_guides_buttons(peer, guides):
    def make_button(guide):
        return interactive_media.InteractiveMedia(
            1, interactive_media.InteractiveMediaButton(guide["value"], guide["title"])
        )

    buttons = [
        interactive_media.InteractiveMediaGroup([make_button(x) for x in guides])
    ]

    bot.messaging.send_message(peer, "Choose guide", buttons)


def guide_list(id):
    user = users.find_one({"id": id})
    guide_list_res = list(guides.find({"company": user["company"]}))
    return guide_list_res


def get_guides(id, peer):
    guide_list_data = guide_list(id)
    render_guides_buttons(peer, guide_list_data)


def generate_guide_value(company):
    number = len(list(guides.find({"company": company})))
    if number == 0:
        res = "guide" + "1"
    else:
        res = "guide" + str(number + 2)
    return res


def get_company(id):
    res = users.find_one({"id": id})["company"]
    return res


def add_guide(id, company, content, title):
    value = generate_guide_value(company)
    guides.insert_one(
        {"company": company, "value": value, "content": content, "title": title}
    )


def create_company(peer, *params):
    bot.messaging.send_message(peer, "Создайте компанию /company {Company Name}")


def delete_guide(id, peer):
    bot.messaging.send_message(peer, "Напишите название гайда который хотите удалить")

    def delete(*params):
        guide_name = params[0].message.textMessage.text
        delete_res = guides.find_one_and_delete({"title": guide_name})
        if delete_res is None:
            bot.messaging.send_message(peer, "Гайда с таким названием не существует")
        else:
            bot.messaging.send_message(peer, "Гайд " + guide_name + " удалён")
        auth(id, peer, *params)
        bot.messaging.on_message(main, on_click)

    bot.messaging.on_message(delete)


def on_click(*params):
    id = params[0].uid
    value = params[0].value
    peer = bot.users.get_user_peer_by_id(id)
    if value == "create_company":
        create_company(peer, *params)

    all_guides = guide_list(id)
    guides_values = [x["value"] for x in all_guides]

    if value in guides_values:
        guide = guides.find_one({"value": value})
        bot.messaging.send_message(peer, guide["title"])

        time.sleep(1)

        bot.messaging.send_message(peer, guide["content"])

    if value == "add_guide":
        bot.messaging.send_message(peer, "Write Title for guide")

        # TODO DO BETTER PLEASE IT IS SIDE EFFECTS!
        def get_content_and_go_main(*params):
            title = params[0].message.textMessage.text

            bot.messaging.send_message(peer, "Write Content for guide content")

            def fn_and_go_main(*params):
                content = params[0].message.textMessage.text
                company = get_company(id)

                # save guide
                add_guide(id, company, content, title)
                bot.messaging.send_message(peer, "You created guide")

                main(*params)

                bot.messaging.on_message(main, on_click)

            bot.messaging.on_message(fn_and_go_main)

        bot.messaging.on_message(get_content_and_go_main)

    if value == "delete_guide":
        delete_guide(id, peer)

    if value == "get_token":
        current_time = str(int(time.time()*1000.0))
        token = get_company(id) + current_time
        tokens.insert_one({"token":token, "type":"user", "company":get_company(id), "time": current_time})
        bot.messaging.send_message(peer, "Ваш токен: " + token)

    if value == "get_guides":
        get_guides(id, peer)

def delete_token(token):
    tokens.delete_one({"_id":token["_id"]})
    # print("deleted token: "+ token['token'])


if __name__ == "__main__":
    bot = DialogBot.get_secure_bot(
        "hackathon-mob.transmit.im",  # bot endpoint (specify different endpoint if you want to connect to your on-premise environment)
        grpc.ssl_channel_credentials(),  # SSL credentials (empty by default!)
        bot_token,  # bot token Nikita , Nikita 2 - "d3bdd8ab024c03560ecf3350bcc3c250a0bbe9cd",
        verbose=False,  # optional parameter, when it's True bot prints info about the called methods, False by default
    )

# work like return , block code after, if want to use code after, use async vers
bot.messaging.on_message(main, on_click)
