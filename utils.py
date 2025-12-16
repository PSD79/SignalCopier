import datetime
import json
import re

from config import BLOCKLIST

import nltk
from config import BLOCKLIST
from nltk.corpus import stopwords
import requests

# tickers = requests.get("https://api.binance.com/api/v1/exchangeInfo").json()
# symbols = [x["symbol"] for x in tickers['symbols']]
# symbols = sorted(symbols, key=lambda i: len(i), reverse=True)

# nltk.download('stopwords')
# nltk.download('punkt_tab')

symbols = []
with open("symbols.json", "r") as f:
    symbols = json.loads(f.read())


def stoploss_generator(entries, possition):
    entry = float(entries[0])
    stoploss = entry - (0.1 * entry)
    if possition == "Short":
        stoploss = entry + (0.1 * entry)
    return round(stoploss, 8)


def validate_entries(datas):
    entries = datas["entries"].copy()
    if len(entries) <= 1:
        return entries
    if datas["type"] == "Short":
        entries = sorted(entries, reverse=True)
        diff = (abs(entries[0] - entries[1])/max(entries))*100
        if diff > 20:
            del entries[entries.index(max(entries))]
    else:
        entries = sorted(entries)
        diff = (abs(entries[0] - entries[1])/min(entries))*100
        if diff > 20:
            del entries[entries.index(min(entries))]
    # entries = ["{:.8f}".format(round(ent, 8)) if round(ent, 8) < 1 else "{:.2f}".format(round(ent, 8)) for ent in entries]
    return entries


def remove_item(l, i):
    try:
        l.remove(i)
    except:
        pass


def find_items_after_identifier(l, identifier, char_error=True):
    result = []
    for item in l[l.index(identifier):]:
        try:
            res = float(item)
        except:
            if char_error:
                if len(result) != 0:
                    break
                else:
                    remove_item(l, item)
                    continue
            if item.replace("-", "").isnumeric():
                res = item + "%"
            else:
                if len(result) != 0:
                    break
                else:
                    remove_item(l, item)
                    continue
        result.append(res)
        remove_item(l, item)
    return result


def parse_signal(text):
    results = {
        "symbol": None,
        "leverage": None,
        "positionsize": None,
        "trendline": [],
        "type": None,
        "stoploss": None,
        "entries": [],
        "targets": []
    }
    text = remove_emojis(text.lower())
    text = text.replace("_", " _ ").replace("-", " - ").replace(",", " , ").replace("|", " | ").replace("—", " — ").replace("(50%)", " ").replace("(25%)", " ").replace("(75%)", " ").replace("'", "").replace("scalping", "").replace("day trading", "").replace("swing trading", "").replace("cmp/", "")
    words = nltk.word_tokenize(text)
    custom_filtered_words = ["#", ">", "<", ".", "-", ":", ",", "|", "_", "=", "(", ")", "[", "]", "}", "{", "dca", "%", "futures", "exchange", "bingx", "binance", "—", "https", "http", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "leverage", "cross", "isolated", "type", "regular", "mid-term", "accuracy", "breakeven", "reaching", "rest", "put", "first", "30m", "position", "$", "t0", "averaging", "market", "order", "trading", "looking", "im", "higher", "tradercash", "running", "tradercach", "1⃣", "2⃣", "3⃣", "4⃣", "∆", " ", "sc°a˚l°pi", "..."]
    stop_words = set(stopwords.words("english") + custom_filtered_words)
    filtered_words = [word for word in words if word not in stop_words]
    for i in filtered_words:
        if i.endswith("usdt") or i.endswith("usdc") or i.endswith("btc") or i.endswith("eth"):
            if i in ["/usdt", "/usdc"]:
                symbol = filtered_words[filtered_words.index(i)-1]
                results["symbol"] = symbol.upper() + i.upper()
                remove_item(filtered_words, symbol)
                remove_item(filtered_words, i)
            elif i not in ["usdt", "usdc", "btc", "eth"]:
                repl = "usdt"
                if i.endswith("usdc"):
                    repl = "usdc"
                elif i.endswith("btc"):
                    repl = "usdc"
                elif i.endswith("eth"):
                    repl = "usdc"
                symbol = i.replace("/", "").replace(repl, "").upper()
                if i.endswith("usdt"):
                    symbol += "/USDT"
                elif i.endswith("usdc"):
                    symbol += "/USDC"
                elif i.endswith("btc"):
                    symbol += "/BTC"
                elif i.endswith("eth"):
                    symbol += "/ETH"
                results["symbol"] = symbol
                remove_item(filtered_words, i)
            elif i in ["btc", "eth"]:
                symbol = i.replace("/", "").upper() + "/USDT"
                results["symbol"] = symbol
                remove_item(filtered_words, i)
    if not results["symbol"]:
        for symbol in symbols["exceptions"]:
            if symbol.lower() in filtered_words:
                results["symbol"] = symbol + "/USDT"
                break
    if "long" in filtered_words:
        results["type"] = "Long"
    elif "short" in filtered_words:
        results["type"] = "Short"
    try:
        filtered_words.remove(results["type"].lower())
    except:
        pass
    for i in filtered_words:
        if re.search(r"(x\d+\.?\d*|\d+\.?\d*x)|(x\d+\.?\d\-\d+\.?\d*|\d+\.?\d\-\d+\.?\d*x)", i, re.M|re.I):
            leverage = re.search(r"(x\d+\.?\d*|\d+\.?\d*x)|(x\d+\.?\d\-\d+\.?\d*|\d+\.?\d\-\d+\.?\d*x)", text, re.M|re.I).group(1).replace("x", "")
            if leverage.count("-") > 0:
                leverages = list(map(float, leverage.split("-")))
                results["leverage"] = "{}-{}x".format(int(leverages[0]), int(leverages[1]))
            else:
                results["leverage"] = "{}x".format(int(float(leverage)))
            remove_item(filtered_words, i)
            break
    entries_prefixes = ["entry", "entries", "enter", "zone", "buy", "sell", "range"]
    for prefix in entries_prefixes:
        if prefix in filtered_words:
            results["entries"] = find_items_after_identifier(filtered_words, prefix)
            break
    stoploss_prefixes = ["stoploss", "sl", "stop-loss", "stop"]
    for prefix in stoploss_prefixes:
        if prefix in filtered_words:
            try:
                results["stoploss"] = find_items_after_identifier(filtered_words, prefix, char_error=False)[0]
            except IndexError:
                pass
            break
    positionsize_prefixes = ["psl"]
    for prefix in positionsize_prefixes:
        if prefix in filtered_words:
            try:
                results["positionsize"] = find_items_after_identifier(filtered_words, prefix)[0]
            except IndexError:
                pass
            break
    trendline_prefixes = ["trend", "tsl", "trendline", "trend-line"]
    for prefix in trendline_prefixes:
        if prefix in filtered_words:
            results["trendline"] = find_items_after_identifier(filtered_words, prefix)
            break
    targets_prefixes = ["take-profit", "takeprofit", "take", "targets"]
    for prefix in targets_prefixes:
        if prefix in filtered_words:
            if prefix == "targets" and filtered_words.count("target") > 1:
                remove_item(filtered_words, "targets")
                continue
            results["targets"] = find_items_after_identifier(filtered_words, prefix)
            break
    if len(results["targets"]) == 0:
        if filtered_words.count("target") > 1:
            filtered_words[filtered_words.index("target")] = "targets"
            while "target" in filtered_words:
                remove_item(filtered_words, "target")
            results["targets"] = find_items_after_identifier(filtered_words, "targets")
        elif filtered_words.count("tp") > 1:
            filtered_words[filtered_words.index("tp")] = "targets"
            while "tp" in filtered_words:
                remove_item(filtered_words, "tp")
            results["targets"] = find_items_after_identifier(filtered_words, "targets")
        elif filtered_words.count("tp") == 1:
            results["targets"] = find_items_after_identifier(filtered_words, "tp")
        elif filtered_words.count("target") == 1:
            results["targets"] = find_items_after_identifier(filtered_words, "target")
        else:
            targets = []
            for i in filtered_words:
                try:
                    targets.append(float(i))
                except ValueError:
                    continue
            results["targets"] = targets
    if not results["type"]:
        if results["targets"][0] < results["targets"][-1]:
            results["type"] = "Long"
        else:
            results["type"] = "Short"
    results["entries"] = validate_entries(results)
    return results


def target_generator(datas, index):
    targets = datas["targets"].copy()
    while len(targets) - 1 != index:
        last_target = float(targets[-1])
        if datas["type"] == "Short":
            new_target = last_target - (0.08 * last_target)
        else:
            new_target = last_target + (0.08 * last_target)
        targets.append(str(round(new_target, 5)))
    return round(float(targets[index]), 5)


def entry_generator(datas, index):
    diff = 0.0001
    entries = datas["entries"].copy()
    _type = datas["type"]
    stoploss = datas["stoploss"]
    if not stoploss:
        if len(entries) == 0:
            if _type == "Long":
                stoploss = datas["targets"][0] - (0.1 * datas["targets"][0])
            else:
                stoploss = datas["targets"][0] + (0.1 * datas["targets"][0])
        else:
            stoploss = stoploss_generator(entries, _type)
    if isinstance(stoploss, str):
        stoploss = float(stoploss.replace("%", "")) / 100
        if _type == "Long":
            stoploss = entries[0] - (stoploss * entries[0])
        else:
            stoploss = entries[0] + (stoploss * entries[0])
    time_to_repeat = 0
    if _type is None:
        return 0
    while len(entries) - 1 != index:
        if time_to_repeat > 20:
            return 0
        time_to_repeat += 1
        last_entry = float(entries[-1])
        if _type == "Short":
            new_entry = last_entry + (diff * last_entry)
            if new_entry >= stoploss:
                diff /= 2
                continue
        else:
            new_entry = last_entry - (diff * last_entry)
            if new_entry <= stoploss:
                diff /= 2
                continue
        entries.append(str(round(new_entry, 8)))
    return float(entries[index])


def get_price(symbol):
    price = None
    if not symbol:
        return price
    if symbol.endswith("USDT"):
        symbol = symbol[:-4]
    elif symbol.endswith("ETH"):
        symbol = symbol[:-3]
    try:
        res = requests.get("https://price.alphacyber.me/{}".format(symbol)).json()
        if res["ok"]:
            price = res["result"]
    except:
        pass
    return price


def display_signal(text, datas):
    try:
        detected_configs = re.findall(r"(\[.*\])", text, re.M)
        configs = {}
        for i in detected_configs:
            text = text.replace(i, "")
            groups = re.search(r"\[(.*)[=](.*)\]", i, re.M).groups()
            configs[groups[0]] = groups[1]
        text = text.strip()
        target_indexes = re.findall(r"\{TARGET(\d+)\}", text, re.M)
        target_status = "all"
        if len(target_indexes) > 1:
            target_indexes = [int(i)-1 for i in target_indexes]
            target_status = "index"
        entry_indexes = re.findall(r"\{ENTRY(\d+)\}", text, re.M)
        entry_status = "all"
        if len(entry_indexes) > 1:
            entry_indexes = [int(i)-1 for i in list(set(entry_indexes))]
            entry_status = "index"
        LEVERAGE = "DELETED_LEVERAGE"
        if datas["leverage"]:
            LEVERAGE = datas["leverage"]
            if configs.get("LEVERAGE_PREFIX"):
                LEVERAGE = configs["LEVERAGE_PREFIX"] + " " + LEVERAGE
        POSITION_SIZE = "DELETED_POSITION_SIZE"
        if datas["positionsize"]:
            POSITION_SIZE = datas["positionsize"]
            if configs.get("POSITION_SIZE_PREFIX"):
                POSITION_SIZE = configs["POSITION_SIZE_PREFIX"] + " " + POSITION_SIZE
        TRENDLINES = "DELETED_TRENDLINE"
        if datas["trendline"]:
            TRENDLINES = datas["trendline"]
            TRENDLINE_SEPERATOR = " - "
            if configs.get("TRENDLINE_SEPERATOR"):
                TRENDLINE_SEPERATOR = configs["TRENDLINE_SEPERATOR"]
            if configs.get("TRENDLINE_PREFIX"):
                prefix = configs["TRENDLINE_PREFIX"]
                TRENDLINES = ["{} {}".format(prefix.replace("NUMBERED", str(TRENDLINES.index(tr)+1)), tr) for tr in TRENDLINES]
            TRENDLINES = TRENDLINE_SEPERATOR.join(TRENDLINES)
        ENTRIES_SEPERATOR = " - "
        if configs.get("ENTRIES_SEPERATOR"):
            ENTRIES_SEPERATOR = configs["ENTRIES_SEPERATOR"]
        ENTRIES = datas["entries"]
        for ent in ENTRIES:
            if not isinstance(ent, str):
                ENTRIES[ENTRIES.index(ent)] = "{:.8f}".format(round(ent, 8)) if round(ent, 8) < 1 else "{:.2f}".format(round(ent, 8))
        if configs.get("ENTRIES_PREFIX"):
            prefix = configs["ENTRIES_PREFIX"]
            ENTRIES = ["{} {}".format(prefix.replace("NUMBERED", str(ENTRIES.index(ent)+1)), "{:.8f}".format(round(ent, 8)) if round(ent, 8) < 1 else "{:.2f}".format(round(ent, 8))) for ent in ENTRIES]
        ENTRIES = list(map(str, ENTRIES))
        TARGETS = datas["targets"]
        TARGETS_COUNT = len(TARGETS)
        if configs.get("TARGETS_COUNT"):
            try:
                TARGETS_COUNT = int(configs["TARGETS_COUNT"])
            except:
                pass
        TARGETS_SEPERATOR = "\n"
        if configs.get("TARGETS_SEPERATOR"):
            TARGETS_SEPERATOR = configs["TARGETS_SEPERATOR"].replace(r'\n', '\n')
        if "{PRICE}" in text:
            price = get_price(datas["symbol"])
            if not price:
                return None
            if price < 0.0001:
                price *= 1000
            if price < 1:
                price = "{:.8f}".format(price)
            else:
                price = "{:.2f}".format(price)
            text = text.replace("{PRICE}", price)
        if "{ID}" in text:
            text = text.replace("{ID}", "#{TYPE}_{SYMBOL}_{DATE}_WithDCA".format(TYPE=datas["type"], SYMBOL=datas["symbol"], DATE=datetime.datetime.now().strftime("%d_%m_%Y_%H_%M")))
        if "{LEVERAGE}" in text:
            text = text.replace("{LEVERAGE}", LEVERAGE)
        if "{POSITION_SIZE}" in text:
            text = text.replace("{POSITION_SIZE}", POSITION_SIZE)
        if "{TRENDLINE}" in text:
            text = text.replace("{TRENDLINE}", TRENDLINES)
        if entry_status == "all":
            ENTRIES = ENTRIES_SEPERATOR.join(ENTRIES)
            text = text.replace("{ENTRIES}", ENTRIES)
        elif entry_status == "index":
            keys = {}
            prefix = ""
            if configs.get("ENTRIES_PREFIX"):
                prefix = configs["ENTRIES_PREFIX"]
            for index in entry_indexes:
                key = "{" + f"ENTRY{index+1}" + "}"
                try:
                    keys[key] = "{} {}".format(prefix.replace("NUMBERED", str(index+1)), "{:.8f}".format(float(ENTRIES[index])) if float(ENTRIES[index]) < 1 else "{:.2f}".format(float(ENTRIES[index]))).strip()
                except IndexError:
                    entry = entry_generator(datas, index)
                    keys[key] = "{} {}".format(prefix.replace("NUMBERED", str(index+1)), "{:.8f}".format(entry) if entry < 1 else "{:.2f}".format(entry)).strip()
            for key, value in keys.items():
                text = text.replace(key, value)
        stoploss = datas["stoploss"]
        if isinstance(stoploss, float):
            stoploss = "{:.8f}".format(stoploss) if float(stoploss) < 1 else "{:.2f}".format(stoploss)
        if target_status == "all":
            if configs.get("TARGETS_PREFIX"):
                prefix = configs["TARGETS_PREFIX"]
                TARGETS = ["{} {}".format(prefix.replace("NUMBERED", str(TARGETS.index(target)+1)), "{:.8f}".format(round(float(target), 5)) if float(target) < 1 else "{:.2f}".format(round(float(target), 5))) for target in TARGETS]
            TARGETS = TARGETS[:TARGETS_COUNT]
            TARGETS = TARGETS_SEPERATOR.join(TARGETS)
            text = text.format(SYMBOL=datas["symbol"], TYPE=datas["type"], TARGETS=TARGETS, STOPLOSS=stoploss)
        elif target_status == "index":
            keys = {}
            prefix = ""
            if configs.get("TARGETS_PREFIX"):
                prefix = configs["TARGETS_PREFIX"]
            for index in target_indexes:
                key = "{" + f"TARGET{index+1}" + "}"
                try:
                    keys[key] = "{} {}".format(prefix.replace("NUMBERED", str(index+1)), "{:.8f}".format(round(float(TARGETS[index]), 5)) if float(TARGETS[index]) < 1 else "{:.2f}".format(round(float(TARGETS[index]), 5))).strip()
                except IndexError:
                    target = target_generator(datas, index)
                    keys[key] = "{} {}".format(prefix.replace("NUMBERED", str(index+1)), "{:.8f}".format(target) if target < 1 else "{:.2f}".format(target)).strip()
            for key, value in keys.items():
                text = text.replace(key, value)
            text = text.format(SYMBOL=datas["symbol"], TYPE=datas["type"], STOPLOSS=stoploss)
        lines = text.split("\n")
        for line in lines:
            for deleted_item in ["DELETED_LEVERAGE", "DELETED_POSITION_SIZE", "DELETED_TRENDLINE"]:
                if line.count(deleted_item) > 0:
                    text = text.replace(line + "\n", "")
        return text
    except IndexError:
        return None


def parse_notification(text):
    try:
        result = {
            "period": None,
            "profit": None,
            "target": None
        }
        if re.search(r"(period)\s*\:?\s*(?P<days>\d+\s*days)?\s*(?P<hours>\d+\s*hours)?\s*(?P<minutes>\d+\s*minutes)?\s*(?P<seconds>\d+\s*seconds)?", text, re.M|re.I):
            period_dict = re.search(r"(period)\s*\:?\s*(?P<days>\d+\s*days)?\s*(?P<hours>\d+\s*hours)?\s*(?P<minutes>\d+\s*minutes)?\s*(?P<seconds>\d+\s*seconds)?", text, re.M|re.I).groupdict()
            keys_to_delete = []
            for key, value in period_dict.items():
                if value is None:
                    keys_to_delete.append(key)
            for key in keys_to_delete:
                del period_dict[key]
            for key, value in period_dict.items():
                period_dict[key] = int(re.search(r"(\d+)", value, re.M|re.I).group(1))
            result["period"] = period_dict
        target_num = re.search(r"(target)\s*(s|\d+)", text, re.M|re.I).group(2).lower()
        if target_num == "s":
            result["target"] = "all"
        else:
            result["target"] = int(target_num)
        text = re.sub(r"take-profit", "", text, re.M|re.I)
        result["profit"] = float(re.search(r"(profit)\s*\:?\s*([0-9]+\.?[0-9]*)%", text, re.M|re.I).group(2))
        return result
    except AttributeError:
        return None


def display_notification(text, notif_datas, signal_datas):
    if notif_datas["target"] == "all":
        notif_datas["target"] = len(signal_datas["targets"])
    if "{TARGET}" in text:
        text = text.replace("{TARGET}", str(notif_datas["target"]))
    if "{SYMBOL}" in text:
        text = text.replace("{SYMBOL}", signal_datas["symbol"])
    if "{PROFIT}" in text:
        text = text.replace("{PROFIT}", str(notif_datas["profit"]))
    if "{TYPE}" in text:
        text = text.replace("{TYPE}", signal_datas["type"])
    if "{PERIOD}" in text:
        period = ""
        if notif_datas["period"]:
            for key, value in notif_datas["period"].items():
                period += f" {value} {key.title()}"
            text = text.replace("{PERIOD}", period.strip())
        else:
            text = re.sub(r".*{PERIOD}.*", "", text, 1, re.M|re.I)
    if "{ID}" in text:
        text = text.replace("{ID}", "#{TYPE}_{SYMBOL}_{DATE}_WithDCA".format(TYPE=signal_datas["type"], SYMBOL=signal_datas["symbol"].replace("/", ""), DATE=datetime.datetime.now().strftime("%d_%m_%Y_%H_%M")))
    if "{STOPLOSS}" in text:
        text = text.replace("{STOPLOSS}", str(signal_datas["targets"][0]))
    return text


def remove_emojis(text):
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002500-\U00002BEF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"
        u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', text)