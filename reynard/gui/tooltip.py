
try:
    # for Python2
    import Tkinter as tk
except ImportError:
    # for Python3
    import tkinter as tk


class CreateToolTip(object):
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info', delay=1000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.__event = None
        self.__tw = None
        self.widget.bind("<Enter>", self.delayed_enter)
        self.widget.bind("<Leave>", self.cancel_enter)

    def delayed_enter(self, event=None):
        self.__event = self.widget.after(self.delay,self.enter)

    def cancel_enter(self, event=None):
        if self.__event is not None:
            self.widget.after_cancel(self.__event)
            self.__event = None
        self.close()

    def enter(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.__tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.__tw.wm_overrideredirect(True)
        self.__tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(self.__tw, text=self.text, justify='left',
                         background='yellow', relief='solid', borderwidth=1,
                         font=("times", "10", "normal"))
        label.pack(ipadx=1)

    def close(self, event=None):
        if self.__tw is not None:
            self.__tw.destroy()
            self.__tw = None



# testing ...
if __name__ == '__main__':
    root = tk.Tk()

    btn1 = tk.Button(root, text="button 1")
    btn1.pack(padx=10, pady=5)
    button1_ttp = CreateToolTip(btn1, "mouse is over button 1",delay=2000)

    btn2 = tk.Button(root, text="button 2")
    btn2.pack(padx=10, pady=5)
    button2_ttp = CreateToolTip(btn2, "mouse is over button 2", delay=100)

    root.mainloop()