import tkinter as tk
from controller.main_controller import MainController

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1520x750")  
    app = MainController(root)
    root.mainloop()
