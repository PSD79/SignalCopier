import asyncio
import json
import logging
import time
import traceback

import aioschedule as schedule
from colorama import Fore
from config import API_HASH, API_ID, REDIS_URL, SUDO_USERS
from redis import Redis
from telethon import TelegramClient, errors, events
from utils import (display_notification, display_signal, entry_generator,
                   get_price, parse_notification, parse_signal,
                   stoploss_generator)

client = TelegramClient("bot", API_ID, API_HASH)
redis = Redis.from_url(REDIS_URL, encoding='utf-8', decode_responses=True)
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='./errors.log')


def do_job(job):
    async def inner():
        try:
            await job()
        except Exception as e:
            traceback.print_exc()
        else:
            pass
    return inner


@client.on(events.NewMessage(pattern=r"^\/(set|unset)\s+(.*)\s+?(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def channels_operation(event):
    try:
        op = event.pattern_match.group(1)
        source_channel_id = "-100" + event.pattern_match.group(2)
        dest_channel_id = "-100" + event.pattern_match.group(3)
        if op == "set":
            redis.sadd("SourceChannels", source_channel_id)
            redis.sadd(f"DestinationChannels:{source_channel_id}", dest_channel_id)
            return await event.reply(f"Channel {source_channel_id} Has Been Set To {dest_channel_id}.")
        else:
            if dest_channel_id:
                redis.srem(f"DestinationChannels:{source_channel_id}", dest_channel_id)
                return await event.reply(f"Channel {dest_channel_id} Has Been Unset From {source_channel_id}.")
            else:
                redis.srem("SourceChannels", source_channel_id)
                redis.delete(f"DestinationChannels:{source_channel_id}")
                return await event.reply(f"Channel {source_channel_id} Has Been Unset From Source Channels.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(ping)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def ping(event):
    try:
        return await event.reply("Pong!")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(help)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def help(event):
    try:
        text = """Bot Usage Help :

Test bot status :
/ping

Show this message :
/help

Add source channel with destination channel :
/set source_id dest_id

Remove destination from a source channel :
/unset source_id dest_id

Remove all destinations of source channel :
/unset source_id

Set signal format for destination channel :
/setformat dest_id

Set notification format of destination channel :
/set_notif_format dest_id

Unset notification format for destination channel :
/unset_nofit_format dest_id

Activate check price for destination channel :
/set_check_price dest_id

Deactivate check price for destination channel :
/unset_check_price dest_id

Set update format of destination channel for specific target :
/set_update_format target_id dest_id

Unset update format of destination channel for specific target :
/unset_update_format target_id dest_id"""
        return await event.reply(text)
    except:
        pass



@client.on(events.NewMessage(pattern=r"^\/(setformat)\s+(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS and e.reply_to))
async def formats_operation(event):
    try:
        reply_id = event.reply_to.reply_to_msg_id
        reply_message = await client.get_messages(event.chat, ids=reply_id)
        dest_channel_id = "-100" + event.pattern_match.group(2)
        redis.hset("Format", dest_channel_id, reply_message.raw_text)
        return await event.reply(f"Channel {dest_channel_id} Has Been Updated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(set_notif_format)\s+(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS and e.reply_to))
async def set_notif_format(event):
    try:
        reply_id = event.reply_to.reply_to_msg_id
        reply_message = await client.get_messages(event.chat, ids=reply_id)
        dest_channel_id = "-100" + event.pattern_match.group(2)
        redis.hset("NotificationFormat", dest_channel_id, reply_message.raw_text)
        return await event.reply(f"Channel {dest_channel_id} Notification Has Been Updated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(unset_notif_format)\s+(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def unset_notif_format(event):
    try:
        dest_channel_id = "-100" + event.pattern_match.group(2)
        redis.hdel("NotificationFormat", dest_channel_id)
        return await event.reply(f"Channel {dest_channel_id} Notification Has Been Updated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(set_update_format)\s+(\d+)\s+(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS and e.reply_to))
async def set_update_format(event):
    try:
        reply_id = event.reply_to.reply_to_msg_id
        reply_message = await client.get_messages(event.chat, ids=reply_id)
        target_number = event.pattern_match.group(2)
        dest_channel_id = "-100" + event.pattern_match.group(3)
        redis.hset("UpdateFormat", f"{dest_channel_id}:{target_number}", reply_message.raw_text)
        return await event.reply(f"Channel {dest_channel_id} Update Message Has Been Updated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(unset_update_format)\s+(\d+)\s+(.*)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def unset_update_format(event):
    try:
        target_number = event.pattern_match.group(2)
        dest_channel_id = "-100" + event.pattern_match.group(3)
        redis.hdel("UpdateFormat", f"{dest_channel_id}:{target_number}")
        return await event.reply(f"Channel {dest_channel_id} Update Message Has Been Updated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(set_check_price)\s+(\d+)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def set_check_price(event):
    try:
        dest_channel_id = "-100" + event.pattern_match.group(2)
        redis.sadd("CheckPriceList", dest_channel_id)
        return await event.reply(f"Channel {dest_channel_id} Check Price Has Been Activated.")
    except:
        pass


@client.on(events.NewMessage(pattern=r"^\/(unset_check_price)\s+(\d+)$", func=lambda e: e.is_private and e.chat_id in SUDO_USERS))
async def unset_check_price(event):
    try:
        dest_channel_id = "-100" + event.pattern_match.group(2)
        redis.srem("CheckPriceList", dest_channel_id)
        return await event.reply(f"Channel {dest_channel_id} Check Price Has Been Deactivated.")
    except:
        pass


@client.on(events.NewMessage(outgoing=False, func=lambda e: redis.sismember("SourceChannels", e.chat_id)))
async def new_message(event):
    text = event.message.raw_text
    parsed = None
    try:
        parsed = parse_signal(text)
    except:
        pass
    if parsed and not parse_notification(text):
        for dest in redis.smembers(f"DestinationChannels:{event.chat_id}"):
            if redis.hget("Format", dest):
                if redis.sismember("CheckPriceList", dest):
                    price = get_price(parsed["symbol"])
                    if not price:
                        return
                    if price < 0.0001:
                        price *= 1000
                    try:
                        entry = float(parsed["entries"][0])
                    except IndexError:
                        entry = float(entry_generator(parsed, 1))
                    diff = abs(entry-price)/price
                    if diff > 0 and diff <= 2:
                        parsed["entries"][0] = "{:.8f}".format(round(price, 8)) if round(price, 8) < 1 else "{:.2f}".format(round(price, 8))
                        parsed["stoploss"] = stoploss_generator(parsed["entries"], parsed["type"])
                    else:
                        return
                unique = {"symbol": parsed["symbol"], "targets": parsed["targets"]}
                if redis.sismember(f"SentSignalsDatas:{event.chat_id}", json.dumps(unique)) and redis.get(f"SignalLimitExpire:{event.chat_id}:{json.dumps(unique)}"):
                    return False
                redis.sadd(f"Signals:{event.chat_id}", json.dumps(parsed))
                redis.hset("SignalMessageID", json.dumps(parsed), event.id)
                # signal_format = redis.hget("Format", dest)
                # signal = display_signal(signal_format, parsed)
                # msg = await client.send_message(int(dest), signal, parse_mode="HTML")
                # redis.hset(f"SignalDatas:{event.chat_id}", event.id, json.dumps(parsed))
                # redis.sadd(f"SentSignalsDatas:{event.chat_id}", json.dumps(unique))
                # redis.setex(f"SignalLimitExpire:{event.chat_id}:{json.dumps(unique)}", 86400, "true")
                # redis.sadd("SentSignals", event.id)
                # redis.hset(f"MessageIDs:{event.id}", dest, msg.id)


@client.on(events.NewMessage(outgoing=False, func=lambda e: e.reply_to and redis.sismember("SentSignals", e.reply_to.reply_to_msg_id)))
async def new_notification_message(event):
    text = event.message.raw_text
    parsed = None
    try:
        parsed = parse_notification(text)
    except:
        pass
    if parsed:
        try:
            signal_data = json.loads(redis.hget(f"SignalDatas:{event.chat_id}", event.reply_to.reply_to_msg_id))
        except:
            return
        target = parsed["target"]
        if target == "all":
            target = len(signal_data["targets"])
        for dest_id in redis.smembers(f"DestinationChannels:{event.chat_id}"):
            message_id = redis.hget(f"MessageIDs:{event.reply_to.reply_to_msg_id}", dest_id)
            if message_id:
                signal_unique = {"symbol": signal_data["symbol"], "targets": signal_data["targets"]}
                if redis.hget("NotificationFormat", dest_id):
                    if redis.sismember(f"SentNotificationDatas:{dest_id}:{target}", f"{json.dumps(signal_unique)},{json.dumps(parsed)}") and redis.get(f"NotificationLimitExpire:{json.dumps(signal_unique)},{json.dumps(parsed)}"):
                        continue
                    notification = redis.hget("NotificationFormat", dest_id)
                    notification = display_notification(notification, parsed, signal_data)
                    await client.send_message(int(dest_id), notification, reply_to=int(message_id), parse_mode="HTML")
                    redis.sadd(f"SentNotificationDatas:{dest_id}:{target}", f"{json.dumps(signal_unique)},{json.dumps(parsed)}")
                    redis.setex(f"NotificationLimitExpire:{json.dumps(signal_unique)},{json.dumps(parsed)}", 86400, "true")
                if redis.hget("UpdateFormat", f"{dest_id}:{target}"):
                    if redis.sismember(f"SentUpdatesDatas:{dest_id}:{target}", f"{json.dumps(signal_unique)},{json.dumps(parsed)}") and redis.get(f"UpdateLimitExpire:{json.dumps(signal_unique)},{json.dumps(parsed)}"):
                        continue
                    update = redis.hget("UpdateFormat", f"{dest_id}:{target}")
                    update = display_notification(update, parsed, signal_data)
                    await client.send_message(int(dest_id), update, reply_to=int(message_id), parse_mode="HTML")
                    redis.sadd(f"SentUpdatesDatas:{dest_id}:{target}", f"{json.dumps(signal_unique)},{json.dumps(parsed)}")
                    redis.setex(f"UpdateLimitExpire:{json.dumps(signal_unique)},{json.dumps(parsed)}", 86400, "true")


@client.on(events.MessageDeleted(func=lambda e: redis.sismember("SourceChannels", e.chat_id)))
async def deleted_message(event):
    for msg_id in event.deleted_ids:
        for dest_id in redis.smembers(f"DestinationChannels:{event.chat_id}"):
            message_id = redis.hget(f"MessageIDs:{msg_id}", dest_id)
            if message_id:
                try:
                    await client.delete_messages(int(dest_id), int(message_id))
                except:
                    pass


async def send_signals():
    for chat_id in redis.smembers("SourceChannels"):
        for sig in redis.smembers(f"Signals:{chat_id}"):
            if not redis.sismember(f"SentSignals:{chat_id}", sig):
                for dest in redis.smembers(f"DestinationChannels:{chat_id}"):
                    if redis.hget("Format", dest):
                        parsed = json.loads(sig)
                        unique = {"symbol": parsed["symbol"], "targets": parsed["targets"]}
                        message_id = int(redis.hget("SignalMessageID", sig))
                        signal_format = redis.hget("Format", dest)
                        signal = display_signal(signal_format, parsed)
                        if signal:
                            try:
                                msg = await client.send_message(int(dest), signal, parse_mode="HTML")
                            except errors.rpcerrorlist.FloodWaitError as e:
                                time.sleep(e.seconds+1)
                                msg = await client.send_message(int(dest), signal, parse_mode="HTML")
                            redis.hset(f"SignalDatas:{chat_id}", message_id, json.dumps(parsed))
                            redis.sadd(f"SentSignalsDatas:{chat_id}", json.dumps(unique))
                            redis.setex(f"SignalLimitExpire:{chat_id}:{json.dumps(unique)}", 86400, "true")
                            redis.sadd("SentSignals", message_id)
                            redis.hset(f"MessageIDs:{message_id}", dest, msg.id)
                            redis.sadd(f"SentSignals:{chat_id}", json.dumps(parsed))
            redis.srem(f"Signals:{chat_id}", sig)


schedule.every(1).seconds.do(do_job(send_signals))

def run():
    try:
        loop = asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    while True:
        loop.run_until_complete(schedule.run_pending())
        time.sleep(1)


client.start()
print(f"{Fore.LIGHTGREEN_EX}Running bot.py ...{Fore.RESET}")
asyncio.run(run())
