import datetime
import json

from utils import get_next_creation_time_file_name


def load_next_creation_time_data():
    try:
        with open(get_next_creation_time_file_name(), 'r') as f:
            next_creation_times = json.load(f)
    except FileNotFoundError:
        next_creation_times = dict()

    return next_creation_times


def fill_in_badges_with_next_creation_times_loaded_from_disk(aggregated_badge_data,
                                                             verbose=True):
    next_creation_times_loaded_from_disk = load_next_creation_time_data()

    for app_id in aggregated_badge_data.keys():
        try:
            next_creation_time = next_creation_times_loaded_from_disk[app_id]
        except KeyError:
            next_creation_time = None

        if next_creation_time is not None:
            previously_loaded_next_creation_time = aggregated_badge_data[app_id]['next_creation_time']
            aggregated_badge_data[app_id]['next_creation_time'] = next_creation_time

            if verbose:
                if previously_loaded_next_creation_time is None:
                    print('Loading next creation time ({}) from disk for appID={}.'.format(
                        next_creation_time,
                        app_id))
                else:
                    # NB: Data stored in data/next_creation_times.json is assumed to be more up-to-date compared to
                    #     data stored in data/booster_game_creator_from_javascript.txt. Indeed, if you  update the .txt
                    #     file with data found on your Booster Pack Creator page, then the .json file would be useless,
                    #     and you should delete it. Therefore, if the .json file is present on your disk, it can be
                    #     assumed that it was created by running this program, thus is more recent than the .txt file.
                    print('Replacing next creation time ({}) with one loaded from disk ({}) for appID={}.'.format(
                        previously_loaded_next_creation_time,
                        next_creation_time,
                        app_id))

    return aggregated_badge_data


def get_current_time():
    current_time = datetime.datetime.today()

    return current_time


def get_creation_time_format():
    # Reference: https://docs.python.org/3/library/time.html#time.strftime

    # The format used in: '14 Sep @ 10:48pm'
    time_format = '%d %b @ %I:%M%p'

    return time_format


def get_formatted_time(time_struct=None):
    if time_struct is None:
        time_struct = get_current_time()

    formatted_time_as_str = datetime.datetime.strftime(time_struct,
                                                       get_creation_time_format())

    return formatted_time_as_str


def get_formatted_current_time(delay_in_days=0):
    current_time = get_current_time()

    if delay_in_days != 0:
        current_time += datetime.timedelta(days=delay_in_days)

    formatted_current_time_as_str = get_formatted_time(current_time)

    return formatted_current_time_as_str


def get_crafting_cooldown_duration_in_days():
    # For every game, a booster pack can be crafted every day.
    crafting_cooldown_duration_in_days = 1

    return crafting_cooldown_duration_in_days


def get_crafting_cooldown_duration_in_seconds():
    crafting_cooldown_duration_in_seconds = 24 * 3600 * get_crafting_cooldown_duration_in_days()

    return crafting_cooldown_duration_in_seconds


def determine_whether_a_booster_pack_can_be_crafted(badge_data,
                                                    current_time=None):
    if current_time is None:
        current_time = get_current_time()

    next_creation_time = badge_data['next_creation_time']

    if next_creation_time is None:
        a_booster_pack_can_be_crafted = True
    else:
        parsed_next_creation_time = datetime.datetime.strptime(next_creation_time,
                                                               get_creation_time_format())

        # Manually set the year, because it was not stored at creation time, following Valve's time format.
        parsed_next_creation_time = parsed_next_creation_time.replace(year=current_time.year)

        delta = parsed_next_creation_time - current_time
        delta_in_seconds = delta.total_seconds()

        # parsed_next_creation_time < current_time
        cooldown_has_ended = bool(delta_in_seconds < 0)

        # current_time + cooldown < parsed_next_creation_time
        # NB: this is necessary because we do not keep track of the year.
        cooldown_actually_ended_last_year = bool(get_crafting_cooldown_duration_in_seconds() < delta_in_seconds)

        a_booster_pack_can_be_crafted = cooldown_has_ended or cooldown_actually_ended_last_year

    return a_booster_pack_can_be_crafted


def main():
    print(get_formatted_current_time())

    return True


if __name__ == '__main__':
    main()