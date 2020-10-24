# Objective: retrieve the ask and bid for Booster Packs.

import json
import time

import requests

from market_listing import get_item_nameid, get_item_nameid_batch
from personal_info import get_cookie_dict, update_and_save_cookie_to_disk_if_values_changed
from utils import get_market_order_file_name


def get_steam_market_order_url():
    return 'https://steamcommunity.com/market/itemordershistogram'


def get_market_order_parameters(item_nameid):
    return {
        'country': 'FR',
        'language': 'english',
        'currency': '3',
        'item_nameid': str(item_nameid),
        'two_factor': '0',
    }


def get_steam_api_rate_limits_for_market_order(has_secured_cookie=False):
    # Objective: return the rate limits of Steam API for the market.

    if has_secured_cookie:

        rate_limits = {
            'max_num_queries': 50,
            'cooldown': (1 * 60) + 10,  # 1 minute plus a cushion
        }

    else:

        rate_limits = {
            'max_num_queries': 25,
            'cooldown': (5 * 60) + 10,  # 5 minutes plus a cushion
        }

    return rate_limits


def download_market_order_data(listing_hash,
                               item_nameid=None,
                               verbose=False,
                               listing_details_output_file_name=None):
    cookie = get_cookie_dict()
    has_secured_cookie = bool(len(cookie) > 0)

    if item_nameid is None:
        item_nameid = get_item_nameid(listing_hash,
                                      listing_details_output_file_name=listing_details_output_file_name)

    if item_nameid is not None:

        url = get_steam_market_order_url()
        req_data = get_market_order_parameters(item_nameid=item_nameid)

        if has_secured_cookie:
            resp_data = requests.get(url, params=req_data, cookies=cookie)
        else:
            resp_data = requests.get(url, params=req_data)

        status_code = resp_data.status_code

    else:
        print('No query to download market orders for {}, because item name ID is unknown.'.format(listing_hash))

        resp_data = None
        status_code = -1

    if status_code == 200:
        result = resp_data.json()

        if has_secured_cookie:
            jar = dict(resp_data.cookies)
            cookie = update_and_save_cookie_to_disk_if_values_changed(cookie, jar)

        try:
            buy_order_graph = result['buy_order_graph']

            try:
                # highest_buy_order
                bid_info = buy_order_graph[0]
                bid_price = bid_info[0]
                bid_volume = bid_info[1]
            except IndexError:
                bid_price = -1
                bid_volume = -1
        except KeyError:
            bid_price = -1
            bid_volume = -1

        try:
            sell_order_graph = result['sell_order_graph']

            try:
                # lowest_sell_order
                ask_info = sell_order_graph[0]
                ask_price = ask_info[0]
                ask_volume = ask_info[1]
            except IndexError:
                ask_price = -1
                ask_volume = -1
        except KeyError:
            ask_price = -1
            ask_volume = -1

    else:
        bid_price = -1
        bid_volume = -1
        ask_price = -1
        ask_volume = -1

    if verbose:
        print('Listing: {} ; item id: {} ; ask: {:.2f}€ ({}) ; bid: {:.2f}€ ({})'.format(listing_hash,
                                                                                         item_nameid,
                                                                                         ask_price,
                                                                                         ask_volume,
                                                                                         bid_price,
                                                                                         bid_volume))

    return bid_price, ask_price, bid_volume, ask_volume


def download_market_order_data_batch(badge_data,
                                     market_order_dict=None,
                                     verbose=False,
                                     save_to_disk=True,
                                     market_order_output_file_name=None,
                                     listing_details_output_file_name=None):
    if market_order_output_file_name is None:
        market_order_output_file_name = get_market_order_file_name()

    # Pre-retrieval of item name ids

    listing_hashes = [badge_data[app_id]['listing_hash'] for app_id in badge_data.keys()]

    item_nameids = get_item_nameid_batch(listing_hashes,
                                         listing_details_output_file_name=listing_details_output_file_name)

    # Retrieval of market orders (bid, ask)

    cookie = get_cookie_dict()
    has_secured_cookie = bool(len(cookie) > 0)

    rate_limits = get_steam_api_rate_limits_for_market_order(has_secured_cookie)

    if market_order_dict is None:
        market_order_dict = dict()

    query_count = 0

    for app_id in badge_data.keys():
        listing_hash = badge_data[app_id]['listing_hash']
        bid_price, ask_price, bid_volume, ask_volume = download_market_order_data(listing_hash,
                                                                                  verbose=verbose,
                                                                                  listing_details_output_file_name=listing_details_output_file_name)

        market_order_dict[listing_hash] = dict()
        market_order_dict[listing_hash]['bid'] = bid_price
        market_order_dict[listing_hash]['ask'] = ask_price
        market_order_dict[listing_hash]['bid_volume'] = bid_volume
        market_order_dict[listing_hash]['ask_volume'] = ask_volume
        market_order_dict[listing_hash]['is_marketable'] = item_nameids[listing_hash]['is_marketable']

        if query_count >= rate_limits['max_num_queries']:
            if save_to_disk:
                with open(market_order_output_file_name, 'w', encoding='utf-8') as f:
                    json.dump(market_order_dict, f)

            cooldown_duration = rate_limits['cooldown']
            print('Number of queries {} reached. Cooldown: {} seconds'.format(query_count, cooldown_duration))
            time.sleep(cooldown_duration)
            query_count = 0

        query_count += 1

    if save_to_disk:
        with open(market_order_output_file_name, 'w', encoding='utf-8') as f:
            json.dump(market_order_dict, f)

    return market_order_dict


def load_market_order_data(badge_data=None,
                           trim_output=False,
                           retrieve_market_orders_online=True):
    market_order_dict = load_market_order_data_from_disk()

    if retrieve_market_orders_online:
        market_order_dict = download_market_order_data_batch(badge_data,
                                                             save_to_disk=True,
                                                             market_order_dict=market_order_dict)

    if trim_output:
        trimmed_market_order_dict, app_ids_with_missing_data = trim_market_order_data(badge_data,
                                                                                      market_order_dict)

        if retrieve_market_orders_online and len(app_ids_with_missing_data) > 0:
            raise AssertionError()

    else:
        trimmed_market_order_dict = market_order_dict

    return trimmed_market_order_dict


def trim_market_order_data(badge_data,
                           market_order_dict):
    trimmed_market_order_dict = {}
    app_ids_with_missing_data = []

    for app_id in badge_data.keys():
        listing_hash = badge_data[app_id]['listing_hash']

        try:
            market_data = market_order_dict[listing_hash]
        except KeyError:
            print('[{}] Market order data is not available offline. Allow downloading it!'.format(listing_hash))
            app_ids_with_missing_data.append(app_id)
            continue

        trimmed_market_order_dict[listing_hash] = dict()
        trimmed_market_order_dict[listing_hash] = market_data

    print()

    return trimmed_market_order_dict, app_ids_with_missing_data


def load_market_order_data_from_disk(market_order_output_file_name=None):
    if market_order_output_file_name is None:
        market_order_output_file_name = get_market_order_file_name()

    try:
        with open(market_order_output_file_name, 'r', encoding='utf-8') as f:
            market_order_dict = json.load(f)
    except FileNotFoundError:
        market_order_dict = None

    return market_order_dict


def main():
    listing_hash = '290970-1849 Booster Pack'

    # Download based on a listing hash

    bid_price, ask_price, bid_volume, ask_volume = download_market_order_data(listing_hash, verbose=True)

    # Download based on badge data

    app_id = listing_hash.split('-')[0]

    badge_data = dict()
    badge_data[app_id] = dict()
    badge_data[app_id]['listing_hash'] = listing_hash

    market_order_dict = download_market_order_data_batch(badge_data,
                                                         save_to_disk=False,
                                                         verbose=True)

    # Test listing hashes with special characters

    listing_hashes = [
        # The item name ID will not be retrieved for the following two listhing hashes due to special characters:
        '614910-#monstercakes Booster Pack',
        '505730-Holy Potatoes! We’re in Space?! Booster Pack',
        # This fixes the aforementioned issue:
        '614910-%23monstercakes Booster Pack',
        '505730-Holy Potatoes! We’re in Space%3F! Booster Pack',
    ]
    for listing_hash_to_test in listing_hashes:
        bid_price, ask_price, bid_volume, ask_volume = download_market_order_data(listing_hash_to_test, verbose=True)

    return True


if __name__ == '__main__':
    main()
