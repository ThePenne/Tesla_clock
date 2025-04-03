#!/usr/bin/python3
import sys
import time
import requests
from holidays.financial import ny_stock_exchange

from datetime import datetime, timedelta
from pytz import timezone

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT
from Font import TSLA_FONT
from threading import Thread, Event

price_change = {"arrow": "-", "tsla_price": 0}

def minute_change(device):
    # When we reach a minute change, animate it.
    hours = datetime.now().strftime("%H")
    minutes = datetime.now().strftime("%M")

    def helper(current_y):
        with canvas(device) as draw:
            text(draw, (1, 0), hours, fill="white", font=proportional(TSLA_FONT))
            text(draw, (15, 0), ":", fill="white", font=proportional(TSLA_FONT))
            text(draw, (18, current_y), minutes, fill="white", font=proportional(TSLA_FONT))
        time.sleep(0.1)

    for current_y in range(1, 9):
        helper(current_y)
    minutes = datetime.now().strftime("%M")
    for current_y in range(9, 1, -1):
        helper(current_y)


def animation(device, from_y, to_y):
    # Animate the whole thing, moving it into/out of the abyss.
    hourstime = datetime.now().strftime("%H")
    mintime = datetime.now().strftime("%M")
    current_y = from_y
    while current_y != to_y:
        with canvas(device) as draw:
            text(draw, (1, current_y), hourstime, fill="white", font=proportional(TSLA_FONT))
            text(draw, (15, current_y), ":", fill="white", font=proportional(TSLA_FONT))
            text(draw, (18, current_y), mintime, fill="white", font=proportional(TSLA_FONT))
        time.sleep(0.1)
        current_y += 1 if to_y > from_y else -1


def main():

    t = Thread(target=update_tsla_price, args=(price_change,), daemon=True)
    t.start()

    # Setup for AliExpress version of 4 x 8x8 Max7219 LED Matrix
    # https://he.aliexpress.com/item/4001131640516.html?gatewayAdapt=glo2isr&spm=a2g0o.order_list.0.0.21ef1802Xq5r1c
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, blocks_arranged_in_reverse_order=False)
    device.contrast(0)

    # The time ascends from the abyss...
    animation(device, 8, 0)

    toggle = False  # Toggle the second indicator every second
    while True:
        try:
            toggle = not toggle
            sec = datetime.now().second
            if sec == 59:
                # When we change minutes, animate the minute change
                minute_change(device)
            elif (sec == 30) and (int(datetime.now().strftime("%M")) % 5 == 0):
                # every 5 minutes, display the Tesla stock price
                full_msg = "TSLA " + price_change["arrow"] + " " + str(price_change["tsla_price"])
                animation(device, 0, 8)
                show_message(device, full_msg, fill="white", font=proportional(TSLA_FONT), scroll_delay=0.1)
                show_message(device, full_msg, fill="white", font=proportional(TSLA_FONT), scroll_delay=0.1)
                animation(device, 8, 0)
            elif (sec == 30) and (int(datetime.now().strftime("%M")) % 5 == 2):
                # every 5 minutes, show current date
                full_msg = datetime.now().strftime("%d.%m.%y - %a")
                animation(device, 0, 8)
                show_message(device, full_msg, fill="white", font=proportional(CP437_FONT), scroll_delay=0.1)
                show_message(device, full_msg, fill="white", font=proportional(CP437_FONT), scroll_delay=0.1)
                animation(device, 8, 0)
            else:
                # alternate the seconds indicator (:) twice a second.
                hours = datetime.now().strftime("%H")
                minutes = datetime.now().strftime("%M")
                with canvas(device) as draw:
                    text(draw, (1, 0), hours, fill="white", font=proportional(TSLA_FONT))
                    text(draw, (15, 0), ":" if toggle else " ", fill="white", font=proportional(TSLA_FONT))
                    text(draw, (18, 0), minutes, fill="white", font=proportional(TSLA_FONT))
                time.sleep(0.5)
        except KeyboardInterrupt:
            break

def get_nyse_closing_time():
    """
    Returns a datetime object representing the NYSE closing time, considering holidays.
    If the market is closed, it waits until the next opening.
    """

    nyse_tz = timezone('America/New_York')
    nyse_holidays = ny_stock_exchange.NewYorkStockExchange(years=datetime.now().year)

    def is_nyse_open(now):
        """Checks if the NYSE is open at the given datetime, considering holidays."""
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        date = now.date()

        # NYSE is open Monday-Friday, 9:30 AM to 4:00 PM Eastern Time, excluding holidays
        if weekday < 5 and 9 <= hour < 16 and date not in nyse_holidays:
            if hour == 9 and minute < 30:
                return False
            else:
                return True
        else:
            return False

    def get_next_opening(now):
        """Calculates the next NYSE opening time, considering holidays."""
        next_day = now + timedelta(days=1)
        while next_day.weekday() >= 5 or next_day.date() in nyse_holidays:  # Skip weekends and holidays
            next_day += timedelta(days=1)
        return nyse_tz.localize(datetime(next_day.year, next_day.month, next_day.day, 9, 30))

    while True:
        now = datetime.now(nyse_tz)
        if is_nyse_open(now):
            closing_time = nyse_tz.localize(datetime(now.year, now.month, now.day, 16, 0))
            return closing_time
        else:
            next_opening = get_next_opening(now)
            sleep_time = (next_opening - now).total_seconds()
            print(f"NYSE is closed. Sleeping for {sleep_time:.2f} seconds until {next_opening} Eastern Time.")
            time.sleep(sleep_time)

def update_tsla_price(price_change):
    delay = 300  # 5 minutes
    delay_on_error = 900  # 15 minutes

    # Get Tingo API key from TIINGO_API_KEY.txt file
    try:
        with open('TIINGO_API_KEY.txt', 'r') as file:
            TIINGO_API_KEY = file.read().strip()
    except FileNotFoundError:
        with open('tsla_ticker_info.txt', 'a') as file:
            file.write(f'{datetime.now().strftime("%d.%m.%y - %H:%M:%S")} -> Error: TIINGO_API_KEY.txt not found.\n')
        sys.exit("Error: TIINGO_API_KEY.txt not found. Please create the file with your Tiingo API key.")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_API_KEY}'
    }
    tiingo_url = f"https://api.tiingo.com/iex/?tickers=tsla&token={TIINGO_API_KEY}"
    
    nyse_closing = get_nyse_closing_time()

    while True:
        try:
            response = requests.get(tiingo_url, headers=headers)
            response.raise_for_status()
            data = response.json()
            last_price = data[0]['tngoLast']
            now_est = datetime.datetime.now(timezone('America/New_York'))

            if now_est > nyse_closing: # Check if need to update closing time
                price_change["arrow"] = "\9"
                price_change["tsla_price"] = "{:.2f}".format(last_price)
                nyse_closing = get_nyse_closing_time()
            else: # market is open
                prev_close_price = data[0]['prevClose']
                change = last_price - prev_close_price
                price_change["arrow"] = "\36" if (change >= 0) else "\37"
                price_change["tsla_price"] = "{:.2f}".format(last_price)
            time.sleep(delay)
        except Exception as error:
            price_change["arrow"] = type(error).__name__ + " -"
            price_change["tsla_price"] = error
            with open('tsla_ticker_info.txt', 'a') as file:
                file.write(f'{datetime.now().strftime("%d.%m.%y - %H:%M:%S")} -> {type(error).__name__} - {error}\n')
            time.sleep(delay_on_error)

if __name__ == "__main__":
    main()
