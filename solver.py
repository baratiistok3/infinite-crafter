import requests
#import requests_cache
import time
import re
from time import sleep
from random import random, shuffle, sample
from itertools import product
from json import loads, dumps
from datetime import datetime
from http.client import HTTPConnection
import logging
import cloudscraper
scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'windows','mobile': False})
req = requests.Session()
log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1

API = 'https://neal.fun/api/infinite-craft/pair'
HEADERS = {
    "Referer": "https://neal.fun/infinite-craft/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0"
}  # required to access the API, seems like rudimentary security

s = requests.Session() 
s.get("https://neal.fun/api/infinite-craft")
# save files
CREATION_TREE = 'creation_tree.json'
TRIED = 'tried.txt'
FIRST_DISCOVERIES = 'first_discoveries.txt'

DELAY = 2.5  # optional delay between requests, in seconds

#requests_cache.install_cache(backend='memory', expire_after=599)

# ANSI escape codes for colored text
class C:
    YELLOW = '\u001b[33m'
    MAGENTA = '\u001b[35m'
    CYAN = '\u001b[36m'
    GREEN = '\u001b[32m'
    RED = '\u001b[31m'
    BOLD = '\u001b[1m'
    UNDERLINE = '\u001b[4m'
    RESET = '\u001b[0m'


def solve():

    print()
    print(f'{C.BOLD}{C.RED}{C.UNDERLINE}Infinite Crafter{C.RESET}')
    print()
    print('Loading save files...')

    creation_tree, available_items, tried = load_files()

    print()
    if DELAY is None:
        print(f'{C.CYAN}Running without a delay!{C.RESET}')
    else:
        print(f'{C.RED}Running with a delay of {DELAY} seconds!{C.RESET}')
    print()
    # try every combination of the available items not already tried

    new_item = False
    banlist = ["Darth", "Tiki", "Cthulhu", "Eel-ectric"]
    banlist.extend([element.lower() for element in banlist])
    counter = 0
    timeout_counter = 0
    
    while True:
        counter = counter + 1
        start = time.time()
        if new_item:
            item1 = available_items[-1]
            item2 = available_items[-1]
            new_item = False
        else:
            item1, item2 = sample(available_items, 2)
        concat = item1 + '' + item2
        if any(re.findall("\\d{5,}", concat.replace(",", ""))) or \
           any(re.findall("\\d{2,}$", item1)) or\
           any(re.findall("\\d{2,}$", item2)) or\
           any(re.findall("\\d.\\d$", item1)) or\
           any(re.findall("\\d.\\d$", item2)):
            continue

        if any(re.findall("\\d{2,}$", item2)):
            continue
        if any(substring in concat for substring in banlist):
            continue
        if len(item1) > 30 or len(item2) > 30:
            continue
        if item1.count(' ') > 2 or item2.count(' ') > 2:
            continue
        if (item1, item1) not in tried: 
            item2 = item1
        if (item2, item2) not in tried:
            item1 = item2
        if (item1, item2) in tried:
            continue

        print(format(counter, "02d")+' ', end="")
        counter = 0
        current_delay = 0;
        if DELAY is not None:
            current_delay = random() * DELAY
            sleep(current_delay)
        try:
            response = req.get(f'{API}?first={item1}&second={item2}', headers=HEADERS, timeout=30)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            print_time(current_delay, start, time.time())
            print(error)
            timeout_counter = timeout_counter + 1
            print(f'{C.RED}#{timeout_counter} timeout{C.RESET}')
            continue

        # handle bad response, e.g. ratelimit
        if response.status_code != 200:
            print_time(current_delay, start, time.time())
            print(f'{C.RED}Error with "{item1}" and "{item2}": {response.status_code}{C.RESET}')
            continue

        tried.append((item1, item2))
        with open(TRIED, 'a') as f:
            f.write(f'{item1}\t{item2}\n')

        data = response.json()
        emoji = data['emoji']
        is_new = data['isNew']
        result = data['result']

        # log the result
        print(f'{C.YELLOW}{item1}{C.RESET} + {C.YELLOW}{item2}{C.RESET} => {C.MAGENTA}{emoji} {result}{C.RESET}', end='')
        if is_new:  # handle first discovery
            print(f', {C.CYAN}{C.BOLD}{C.UNDERLINE}First Discovery!{C.RESET}', end="")
            new_item = True
            if FIRST_DISCOVERIES:
                with open(FIRST_DISCOVERIES, 'a') as f:
                    f.write(f'{datetime.now()} \t->\t {result}\n')
        elif result == 'Nothing':  # handle erroneous result due to server error
            print(f', {C.RED}XXX{C.RESET}')
            print_time(current_delay, start, time.time())
            continue
        elif result not in available_items:  # handle subjectively new result
            print(f', {C.GREEN}New Item!{C.RESET} ', end="")
            new_item = True
        else:  # handle known result
            print()

        # invalid result due to bad server generation, won't combine with anything else
        if '+' in result:
            print_time(current_delay, start, time.time())
            print(f'\t{C.RED}Erroneous result is being omitted from future use...{C.RESET}')
            continue

        # if the result is new, add it to the available items and try it with the other available items
        if result not in available_items:
            # add the result to the creation tree and available items
            available_items.append(result)
            creation_tree[result] = [item1, item2]
            print(f'\tItem {C.GREEN}#{len(available_items)}{C.RESET}')
            if CREATION_TREE:
                with open(CREATION_TREE, 'a') as f:
                    f.write(dumps({result: creation_tree[result]}, indent=2).replace("\n", ""))
                    f.write("\n")
        print_time(current_delay, start, time.time())   
        


def load_files():
    """Load the save files, or create them if they don't exist."""

    creation_tree = {}
    available_items = ['Water', 'Fire', 'Wind', 'Earth']
    try:
        with open(CREATION_TREE, 'r') as f:
           for line in f:
                creation = loads(line)
                creation_tree.update(creation) 
        available_items.extend(creation_tree.keys())
        print(f'{C.GREEN}Loaded {CREATION_TREE} with {len(available_items)} items!{C.RESET}')
    except FileNotFoundError:
        print(f'{C.RED}Creation tree save not found, using defaults: {C.YELLOW}{", ".join(available_items)}{C.RESET}')
        with open(CREATION_TREE, 'w') as f:
            f.write("")

    tried = []
    try:
        with open(TRIED, 'r', encoding='utf-8') as f:
            tried = [tuple(combo.split('\t')) for combo in f.read().strip().split('\n')]
        print(f'{C.GREEN}Loaded {TRIED} with {len(tried)} combinations!{C.RESET}')
    except FileNotFoundError:
        print(f'{C.RED}Tried combinations file not found, creating one with the name: "{TRIED}"{C.RESET}')
        open(TRIED, 'w').close()

    try:
        with open(FIRST_DISCOVERIES, 'r', encoding='utf-8') as f:
            first_discoveries = f.read().strip().splitlines()
            print(f'{C.GREEN}Loaded {FIRST_DISCOVERIES} with {len(first_discoveries)} first discoveries!{C.RESET}')
    except FileNotFoundError:
        print(f'{C.RED}First discoveries file not found, creating one with the name: "{FIRST_DISCOVERIES}"{C.RESET}')
        open(FIRST_DISCOVERIES, 'w').close()

    return creation_tree, available_items, tried

def print_time(delay, start, end):
    all_time = end - start
    process = all_time-delay
    print(f"{delay:.2f}+{process:.2f}={all_time:.2f} ", end="")

def find_depth(creation_tree, result):
    """Find an item's depth through the creation tree."""
    for res, (ingredient_1, ingredient_2) in creation_tree.items():
        if res == result:
            return max(find_depth(creation_tree, ingredient_1), find_depth(creation_tree, ingredient_2)) + 1
    return 0


if __name__ == '__main__':
    solve()

