#!/usr/bin/python3
import sys
import time
import requests
import yfinance as yf

from datetime import datetime

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional, CP437_FONT #, TINY_FONT, SEG7_FONT
from Font import TSLA_FONT
from threading import Thread, Event

event = Event()

price_change = {"arrow": "-", "tsla_price": 0}

def minute_change(device):
    '''When we reach a minute change, animate it.'''
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
    '''Animate the whole thing, moving it into/out of the abyss.'''
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
    t = Thread(target=update_tsla_price, args = (price_change, ))
    t.start()

    # Setup for AliExpress version of 4 x 8x8 Max7219 LED Matrix (https://he.aliexpress.com/item/4001131640516.html?gatewayAdapt=glo2isr&spm=a2g0o.order_list.0.0.21ef1802Xq5r1c)
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
                # every 5 minutes, display the Tesla stock price,
                # animating the time display into and out of the abyss.
                full_msg = "TSLA " + price_change["arrow"] + " " + str(price_change["tsla_price"])
                animation(device, 0, 8)
                show_message(device, full_msg, fill="white", font=proportional(TSLA_FONT), scroll_delay=0.1)
                show_message(device, full_msg, fill="white", font=proportional(TSLA_FONT), scroll_delay=0.1)
                animation(device, 8, 0)
            elif (sec == 30) and (int(datetime.now().strftime("%M")) % 5 == 2):
                # show current date
                full_msg = datetime.now().strftime("%d.%m.%y - %a")
                animation(device, 0, 8)
                show_message(device, full_msg, fill="white", font=proportional(CP437_FONT), scroll_delay=0.1)
                show_message(device, full_msg, fill="white", font=proportional(CP437_FONT), scroll_delay=0.1)
                animation(device, 8, 0)
            else:
                # Do the following twice a second (so the seconds' indicator blips).
                # I'd optimize if I had to - but what's the point?
                # Even my Raspberry PI2 can do this at 4% of a single one of the 4 cores!
                hours = datetime.now().strftime("%H")
                minutes = datetime.now().strftime("%M")
                with canvas(device) as draw:
                    text(draw, (1, 0), hours, fill="white", font=proportional(TSLA_FONT))
                    text(draw, (15, 0), ":" if toggle else " ", fill="white", font=proportional(TSLA_FONT))
                    text(draw, (18, 0), minutes, fill="white", font=proportional(TSLA_FONT))
                time.sleep(0.5)
        except KeyboardInterrupt:
            event.set()
            break
    t.join()

def update_tsla_price(price_change):
    import yfinance as yf

    tsla_ticker = yf.Ticker("TSLA")
    while True:
        if (int(datetime.now().strftime("%M")) % 2) == 1:
            try:
                history = tsla_ticker.history(period="1d")
                latest_price = float(history.iloc[-1]["Close"])
                change = latest_price - float(history.iloc[-1]["Open"])
                price_change["arrow"] = "\36" if (change >= 0) else "\37"
                price_change["tsla_price"] = "{:.2f}".format(latest_price)
            except requests.ConnectionError:
                price_change["arrow"] = "-"
                price_change["tsla_price"] = "Error: Connection Failed. Retrying..."
                time.sleep(5)
                continue
            except Exception as error:
                price_change["arrow"] = type(error).__name__ + " -"
                price_change["tsla_price"] = error
                with open('tsla_ticker_info.txt', 'w') as file:
                    file.write(f'{datetime.now().strftime("%d.%m.%y - %H:%M:%S")} -> {type(error).__name__} - {error}\n')
                    
        time.sleep(30)
        if event.is_set():
            break

if __name__ == "__main__":
    main()
