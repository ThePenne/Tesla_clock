#!/usr/bin/env python
import yfinance as yf
import time
from datetime import datetime

from luma.led_matrix.device import max7219
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.core.legacy import text, show_message
from luma.core.legacy.font import proportional #, TINY_FONT , CP437_FONT, SEG7_FONT
from Font import TSLA_FONT

def minute_change(device):
    '''When we reach a minute change, animate it.'''
    hours = datetime.now().strftime('%H')
    minutes = datetime.now().strftime('%M')

    def helper(current_y):
        with canvas(device) as draw:
            text(draw, (1, 0), hours, fill="white", font=proportional(TSLA_FONT))
            text(draw, (15, 0), ":", fill="white", font=proportional(TSLA_FONT))
            text(draw, (18, current_y), minutes, fill="white", font=proportional(TSLA_FONT))
        time.sleep(0.1)

    for current_y in range(1, 9):
        helper(current_y)
    minutes = datetime.now().strftime('%M')
    for current_y in range(9, 1, -1):
        helper(current_y)


def animation(device, from_y, to_y):
    '''Animate the whole thing, moving it into/out of the abyss.'''
    hourstime = datetime.now().strftime('%H')
    mintime = datetime.now().strftime('%M')
    current_y = from_y
    while current_y != to_y:
        with canvas(device) as draw:
            text(draw, (1, current_y), hourstime, fill="white", font=proportional(TSLA_FONT))
            text(draw, (15, current_y), ":", fill="white", font=proportional(TSLA_FONT))
            text(draw, (18, current_y), mintime, fill="white", font=proportional(TSLA_FONT))
        time.sleep(0.1)
        current_y += 1 if to_y > from_y else -1


def main():
    # Setup for Banggood version of 4 x 8x8 LED Matrix (https://bit.ly/2Gywazb)
    serial = spi(port=0, device=0, gpio=noop())
    device = max7219(serial, cascaded=4, block_orientation=-90, blocks_arranged_in_reverse_order=False)
    device.contrast(16)
    tsla = yf.Ticker('TSLA')

    # The time ascends from the abyss...
    animation(device, 8, 0)

    toggle = False  # Toggle the second indicator every second
    while True:
        toggle = not toggle
        sec = datetime.now().second
        if sec == 59:
            # When we change minutes, animate the minute change
            minute_change(device)
        elif sec == 30 or sec == 50:
            # Half-way through each minute, display the complete date/time,
            # animating the time display into and out of the abyss.
            tsla_info = tsla.info
            tsla_price = tsla_info['regularMarketPrice']
            tsla_prev_close_price = tsla_info['regularMarketPreviousClose']
            if tsla_prev_close_price > tsla_price:
                arrow = '\37'
            else:
                arrow = '\36'
            full_msg = "TSLA " + arrow + " " + str(tsla_price)
            animation(device, 0, 8)
            show_message(device, full_msg, fill="white", font=proportional(TSLA_FONT), scroll_delay=0.1)
            animation(device, 8, 0)
        else:
            # Do the following twice a second (so the seconds' indicator blips).
            # I'd optimize if I had to - but what's the point?
            # Even my Raspberry PI2 can do this at 4% of a single one of the 4 cores!
            hours = datetime.now().strftime('%H')
            minutes = datetime.now().strftime('%M')
            with canvas(device) as draw:
                text(draw, (1, 0), hours, fill="white", font=proportional(TSLA_FONT))
                text(draw, (15, 0), ":" if toggle else " ", fill="white", font=proportional(TSLA_FONT))
                text(draw, (18, 0), minutes, fill="white", font=proportional(TSLA_FONT))
            time.sleep(0.5)


if __name__ == "__main__":
    main()
