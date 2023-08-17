import curses

stdscr = curses.initscr()

curses.start_color()
curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)

curses.noecho()
curses.cbreak()

COLOR_INACTIVE = curses.color_pair(1)
COLOR_ACTIVE = curses.color_pair(2)
COLOR_NORMAL = curses.color_pair(3)


class Line:
    def __init__(self, line_str, y_pos=0, color=COLOR_NORMAL):
        self.line_str = line_str
        self.y_pos = y_pos
        self.color = color


class Window:
    def __init__(self, stdscr, height, width, y_pos, x_pos, title=''):
        screen_height, screen_width = stdscr.getmaxyx()

        self.height = height if height + y_pos < screen_height else screen_height - y_pos
        self.width = width if width + x_pos < screen_width else screen_width - x_pos
        self.title = title

        self._is_focused = False
        self._content = []

        self.window = stdscr.subwin(self.height, self.width, y_pos, x_pos)

        self.window.keypad(True)
        self.window.refresh()
        self.render()

    @property
    def is_focused(self):
        return self._is_focused

    @is_focused.setter
    def is_focused(self, value):
        if value == True:
            self._is_focused = True
        elif value == False:
            self._is_focused = False
        self.render()
    
    def set_cursor(self, y_pos=1, x_pos=1):
        if y_pos < self.height and x_pos < self.width:
            self.window.move(y_pos,x_pos)
    
    def erase(self):
        self._content = []

    def render_border(self):
        color = COLOR_ACTIVE if self.is_focused else COLOR_INACTIVE
        self.window.border()
        self.window.bkgd(' ', color)
        self.window.addstr(0, 1, self.title, color)
    
    def render(self, content=[], cursor_y_pos=1, cursor_x_pos=1):
        if self._content and not content:
            content = self._content
        else:
            self._content = content
        
        self.window.clear()
        self.render_border()
        for item in content:
            self.window.addstr(item.y_pos + 1, 1, item.line_str, item.color)
        self.set_cursor(cursor_y_pos, cursor_x_pos)
        self.window.refresh()


class Textbox:
    def __init__(self, win_obj, ch_limit=None, width=None, placeholder=''):
        self.win_obj = win_obj
        self.view_width = width if width else self.win_obj.width-2
        self.ch_limit = ch_limit
        self.placeholder = placeholder

        self.text = ''
        self.view_pos = 0
        self.cursor_pos = 0

    def render(self):
        try:
            self.win_obj.is_focused = True
            self._handle_keys()
            self.win_obj.is_focused = False
        except KeyboardInterrupt:
            curses.endwin()

    def _handle_keys(self):
        while True:
            if not self.text:
                self.win_obj.render([Line(self.placeholder, color=COLOR_INACTIVE)])

            ch = self.win_obj.window.getch()

            if 32 <= ch <= 126:
                if self.ch_limit and len(self.text) > self.ch_limit:
                    continue
                self.text = self.text[:self.cursor_pos+self.view_pos] + chr(ch) + self.text[self.cursor_pos+self.view_pos:]
                if self.cursor_pos+1 < self.view_width:
                    self.cursor_pos += 1
                elif len(self.text) >= self.view_width:
                    self.view_pos += 1
            elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
                return
            elif ch == curses.KEY_BACKSPACE:
                if len(self.text) > self.view_width and self.view_pos > 0:
                    self.text = self.text[:self.view_pos+self.cursor_pos-1] + self.text[self.view_pos+self.cursor_pos:]
                    self.view_pos -= 1
                elif self.cursor_pos > 0:
                    self.text = self.text[:self.view_pos+self.cursor_pos-1] + self.text[self.view_pos+self.cursor_pos:]
                    self.cursor_pos -= 1
            elif ch == curses.KEY_DC:
                if self.view_pos+self.cursor_pos < len(self.text):
                    self.text = self.text[:self.cursor_pos] + self.text[self.cursor_pos+1:]
            elif ch == curses.KEY_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                elif self.view_pos > 0:
                    self.view_pos -= 1
            elif ch == curses.KEY_RIGHT:
                if self.cursor_pos+self.view_pos < len(self.text) and self.cursor_pos+1 < self.view_width:
                    self.cursor_pos += 1
                elif self.view_pos+self.cursor_pos < len(self.text) and self.cursor_pos+1 == self.view_width:
                    self.view_pos += 1
            elif ch == curses.KEY_UP:
                if len(self.text) > self.view_width:
                    self.view_pos = len(self.text) - self.view_width+1
                    self.cursor_pos = self.view_width-1
                else:
                    self.view_pos = 0
                    self.cursor_pos = len(self.text)
            elif ch == curses.KEY_DOWN:
                self.view_pos = 0
                self.cursor_pos = 0

            view_text = self.text[self.view_pos:self.view_width+self.view_pos]
    
            self.win_obj.render([Line(view_text)], cursor_x_pos=self.cursor_pos+1)
        

        
class Scrollbox:
    def __init__(self, win_obj):
        self.UP = -1
        self.DOWN = 1
        self.win_obj = win_obj
        pass

    def render(self, content=[]):
        try:
            self.win_obj.is_focused = True
            self._handle_keys(content)
            self.win_obj.is_focused = False
        except KeyboardInterrupt:
            curses.endwin()
        
    def _handle_keys(self, content):
        while True:
            self.win_obj.render([Line('hello'), Line('foo')])

            ch = self.win_obj.window.getch()
            if ch == curses.KEY_UP:
                self.scroll(self.UP)
            elif ch == curses.KEY_DOWN:
                self.scroll(self.DOWN)
            elif ch == curses.KEY_LEFT:
                self.paging(self.UP)
            elif ch == curses.KEY_RIGHT:
                self.paging(self.DOWN)

    def scroll(self, direction):
        next_line = self.current + direction

        if (direction == self.UP) and (self.top > 0 and self.current == 0):
            self.top += direction
            return
        if (direction == self.DOWN) and (next_line == self.max_lines) and (self.top + self.max_lines < self.bottom):
            self.top += direction
            return
        if (direction == self.UP) and (self.top > 0 or self.current > 0):
            self.current = next_line
            return
        if (direction == self.DOWN) and (next_line < self.max_lines) and (self.top + next_line < self.bottom):
            self.current = next_line
            return

    def paging(self, direction):
        current_page = (self.top + self.current) // self.max_lines
        next_page = current_page + direction
        if next_page == self.page:
            self.current = min(self.current, self.bottom % self.max_lines - 1)

        if (direction == self.UP) and (current_page > 0):
            self.top = max(0, self.top - self.max_lines)
            return
        if (direction == self.DOWN) and (current_page < self.page):
            self.top += self.max_lines
            return

    def display(self):
        self.main_box.erase()
        for idx, item in enumerate(self.items[self.top:self.top + self.max_lines]):
            if idx == self.current:
                self.main_box.addstr(idx, 0, item, curses.color_pair(2))
            else:
                self.main_box.addstr(idx, 0, item, curses.color_pair(1))
        self.main_box.refresh()
        self.main_box.border()



    

class View:
    def __init__(self, stdscr):
        self.screen = stdscr
        self.height, self.width = self.screen.getmaxyx()

        self.search_win = Window(self.screen, 3, self.width, 0, 0, 'Search')
        self.results_win = Window(self.screen, self.height, self.width, 3, 0, 'Results')

        self.search_win_box = Textbox(self.search_win)
        self.results_win_box = Scrollbox(self.results_win)

v = View(stdscr)
v.search_win_box.render()
v.results_win_box.render()

class Screen:
    def __init__(self, items):
        self.up = -1
        self.down = 1

        self.items = items

        self.window = None

        self.search_win = None
        self.content_win = None

        self.height = 0
        self.width = 0

        self.search_win_text = ''
        self.search_win_position = 0
        self.search_win_width = 0

        self.init_curses()

        self.max_lines = curses.LINES - 1
        self.top = 0
        self.bottom = len(self.items)
        self.current = 0
        self.page = self.bottom // self.max_lines

    def init_curses(self):
        self.window = curses.initscr()
        self.window.clear()

        curses.curs_set(1)
        curses.noecho()
        curses.cbreak()

        curses.start_color()
        curses.init_pair(1, 246, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)

        self.height, self.width = self.window.getmaxyx()

        self.search_win_width = self.width - 1

        self.search_win = self.window.subwin(3, self.search_win_width+1, 0, 0)
        self.content_win = self.window.subwin(self.height - 3, self.width, 3, 0)

        self.search_win.keypad(True)
        self.content_win.keypad(True)

        self.search_win.refresh()
        self.content_win.refresh()

        self.init_win(self.search_win, 'Search')
        self.init_win(self.content_win, 'Results')

    
    def init_win(self, win_obj, title):
        win_obj.border()
        win_obj.bkgd(' ', curses.color_pair(1))
        win_obj.addstr(0, 2, title, curses.color_pair(1))

    def focus_search_win(self):
        curses.curs_set(1)
        while True:
            ch = self.search_win.getch()

            if 32 <= ch <= 126 and len(self.search_win_text) < 100:
                curses.curs_set(1)
                self.search_win_text += chr(ch)
                if len(self.search_win_text) > self.search_win_width:
                    self.search_win_position += 1
            elif ch == curses.KEY_ENTER or ch == 10 or ch == 13:
                self.focus_content_win()
            elif ch == curses.KEY_BACKSPACE:
                self.search_win_position = len(self.search_win_text) - self.search_win_width if len(self.search_win_text) - self.search_win_width > 0 else 0
                self.search_win_text = self.search_win_text[:-1]
                if self.search_win_position > 0:
                    self.search_win_position -= 1
            elif ch == curses.KEY_LEFT and self.search_win_position > 0:
                self.search_win_position -= 1
            elif ch == curses.KEY_RIGHT and self.search_win_position + self.search_win_width < len(self.search_win_text):
                self.search_win_position += 1
    
            display_text = self.search_win_text[self.search_win_position:self.search_win_position + self.search_win_width]

            self.search_win.clear()
            self.init_win(self.search_win, 'Search')
            self.search_win.addstr(1, 1, display_text, curses.color_pair(2)) 
            self.search_win.refresh()
        
    def focus_content_win(self):
        curses.curs_set(0)
        while True:
            self.display()

            ch = self.content_win.getch()
            if ch == curses.KEY_UP:
                self.scroll(self.up)
            elif ch == curses.KEY_DOWN:
                self.scroll(self.down)
            elif ch == curses.KEY_LEFT:
                self.paging(self.up)
            elif ch == curses.KEY_RIGHT:
                self.paging(self.down)
            elif 32 <= ch <= 126:
                self.focus_search_win()
            #elif ch == curses.ascii.ESC:
            #    break

    def scroll(self, direction):
        next_line = self.current + direction

        if (direction == self.up) and (self.top > 0 and self.current == 0):
            self.top += direction
            return
        if (direction == self.down) and (next_line == self.max_lines) and (self.top + self.max_lines < self.bottom):
            self.top += direction
            return
        if (direction == self.up) and (self.top > 0 or self.current > 0):
            self.current = next_line
            return
        if (direction == self.down) and (next_line < self.max_lines) and (self.top + next_line < self.bottom):
            self.current = next_line
            return

    def paging(self, direction):
        current_page = (self.top + self.current) // self.max_lines
        next_page = current_page + direction
        if next_page == self.page:
            self.current = min(self.current, self.bottom % self.max_lines - 1)

        if (direction == self.up) and (current_page > 0):
            self.top = max(0, self.top - self.max_lines)
            return
        if (direction == self.down) and (current_page < self.page):
            self.top += self.max_lines
            return

    def display(self):
        self.content_win.clear()
        for idx, item in enumerate(self.items[self.top:self.top + self.max_lines - 2]):
            if idx == self.current:
                self.content_win.addstr(idx, 1, item, curses.color_pair(2))
            else:
                self.content_win.addstr(idx, 1, item, curses.color_pair(1))
        self.content_win.refresh()
        self.init_win(self.content_win, 'Results')
        
    def run(self):
        try: 
            self.focus_search_win()
            self.focus_content_win()
        except KeyboardInterrupt:
            pass
        finally:
            curses.endwin()


#items = [f'{num + 1}. Item' for num in range(1000)]
#s = Screen(items)
#s.run()
#print(s.search_win_text)

