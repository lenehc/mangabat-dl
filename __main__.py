import curses

BOX_WIDTH = 50

def main():
    stdscr = curses.initscr()
    curses.curs_set(0) 
    stdscr.clear()
    stdscr.refresh()

    box = stdscr.subwin(1, BOX_WIDTH+1, 0, 0)
    box.scrollok(True)
    box.keypad(True)
#    box.border()

    full_text = ""
    pos = 0


    while True:
        if not full_text:
            box.addstr(0, 0, 'Search') 

        ch = box.getch()

        if 32 <= ch <= 126:
            full_text += chr(ch)
            if len(full_text) > BOX_WIDTH:
                pos += 1
        elif ch == curses.KEY_BACKSPACE:
            pos = len(full_text) - BOX_WIDTH if pos > 0 else pos
            full_text = full_text[:-1]
            if pos > 0:
                pos -= 1
        elif ch == curses.KEY_LEFT and pos > 0:
            pos -= 1
        elif ch == curses.KEY_RIGHT and pos+BOX_WIDTH < len(full_text):
            pos += 1

        display_text = full_text[pos:pos+BOX_WIDTH]

        box.clear()
        box.addstr(0, 0, display_text) 
        box.refresh()


if __name__ == "__main__":
    main()
