import requests
import time
from time import sleep
from random import random, shuffle, sample
from itertools import product
from json import loads, dumps
from datetime import datetime


API = 'https://neal.fun/api/infinite-craft/pair'
HEADERS = {
    "Referer": "https://neal.fun/infinite-craft/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}  # required to access the API, seems like rudimentary security

# save files
CREATION_TREE = 'creation_tree.json'
TRIED = 'tried.txt'
FIRST_DISCOVERIES = 'first_discoveries.txt'

DELAY = 5  # optional delay between requests, in seconds


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
    end = time.time()
    # try every combination of the available items not already tried
    while True:
        start = time.time()
        item1, item2 = sample(available_items, 2)
        if (item1, item2) in tried:
            continue

        if DELAY is not None:
            sleep(random() * DELAY)
        response = requests.get(f'{API}?first={item1}&second={item2}', headers=HEADERS)

        # handle bad response, e.g. ratelimit
        if response.status_code != 200:
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
            print(f', {C.CYAN}{C.BOLD}{C.UNDERLINE}First Discovery!{C.RESET}')
            if FIRST_DISCOVERIES:
                with open(FIRST_DISCOVERIES, 'a') as f:
                    f.write(f'{datetime.now()} \t->\t {result}\n')
        elif result == 'Nothing':  # handle erroneous result due to server error
            print(f', {C.RED}XXX{C.RESET}')
            continue
        elif result not in available_items:  # handle subjectively new result
            print(f', {C.GREEN}New Item!{C.RESET}')
        else:  # handle known result
            print()

        # invalid result due to bad server generation, won't combine with anything else
        if '+' in result:
            print(f'\t{C.RED}Erroneous result is being omitted from future use...{C.RESET}')
            continue

        # if the result is new, add it to the available items and try it with the other available items
        if result not in available_items:
            # add the result to the creation tree and available items
            available_items.append(result)
            creation_tree[result] = [item1, item2]
            print(f'\tItem {C.GREEN}#{len(available_items)}{C.RESET} @ depth {C.GREEN}{find_depth(creation_tree, result)}{C.RESET}')
            if CREATION_TREE:
                with open(CREATION_TREE, 'a') as f:
                    f.write(dumps({result: creation_tree[result]}, indent=2).replace("\n", ""))
                    f.write("\n")

        end = time.time()
        print(format(end - start, ".2f") + " ", end="")



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
        with open(TRIED, 'r') as f:
            tried = [tuple(combo.split('\t')) for combo in f.read().strip().split('\n')]
        print(f'{C.GREEN}Loaded {TRIED} with {len(tried)} combinations!{C.RESET}')
    except FileNotFoundError:
        print(f'{C.RED}Tried combinations file not found, creating one with the name: "{TRIED}"{C.RESET}')
        open(TRIED, 'w').close()

    try:
        with open(FIRST_DISCOVERIES, 'r') as f:
            first_discoveries = f.read().strip().splitlines()
            print(f'{C.GREEN}Loaded {FIRST_DISCOVERIES} with {len(first_discoveries)} first discoveries!{C.RESET}')
    except FileNotFoundError:
        print(f'{C.RED}First discoveries file not found, creating one with the name: "{FIRST_DISCOVERIES}"{C.RESET}')
        open(FIRST_DISCOVERIES, 'w').close()

    return creation_tree, available_items, tried


def find_depth(creation_tree, result):
    """Find an item's depth through the creation tree."""
    for res, (ingredient_1, ingredient_2) in creation_tree.items():
        if res == result:
            return max(find_depth(creation_tree, ingredient_1), find_depth(creation_tree, ingredient_2)) + 1
    return 0


if __name__ == '__main__':
    solve()
