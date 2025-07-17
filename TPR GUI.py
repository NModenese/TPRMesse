import tkinter as tk
from tkinter import ttk
from datetime import datetime
import random
import threading
import time
from PIL import Image, ImageTk

STATUS_STEPS = ["Bereit", "Kontaktieren", "Messen", "Zurückfahren"]

class TPRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TPR Messung für Bipolarplatten")
        self.root.geometry("700x500")
        self.root.minsize(700, 500)
        self.root.configure(background="#1e1e1e")

        # Azure Theme laden
        self.root.tk.call("source", "azure.tcl")
        self.root.tk.call("set_theme", "dark")

        self.is_measuring = False

        # Grid-Konfiguration
        self.root.grid_columnconfigure(0, weight=1)
        self.grid_row_main = [3]  # Zeile 3 wächst
        for row in self.grid_row_main:
            self.root.grid_rowconfigure(row, weight=1)

        # Stil
        style = ttk.Style()
        style.configure("Custom.TButton", foreground="white", background="#009FE3",
                        font=("Bahnschrift Light", 11), padding=6)
        style.map("Custom.TButton", background=[("active", "#009FE3")])
        style.configure("Treeview", background="#1e1e1e", fieldbackground="#1e1e1e",
                        foreground="white", rowheight=28, font=("Bahnschrift Light", 11))
        style.map("Treeview", background=[("selected", "#009FE3")])
        style.configure("Treeview.Heading", background="#1e1e1e", foreground="white",
                        font=("Bahnschrift Light", 12, "bold"))

        # Titel
        title_label = tk.Label(self.root, text="TPR Messung für Bipolarplatten", font=("Bahnschrift Light", 18, "bold"),
                               background="#1e1e1e", foreground="white")
        title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        # Logo oben rechts
        logo_img = Image.open("mafu_logo_w.png").resize((160, 40))
        self.logo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(self.root, image=self.logo, background="#1e1e1e")
        logo_label.grid(row=0, column=1, sticky="e", padx=20, pady=(20, 10))

        # Status + Buttons
        status_frame = tk.Frame(self.root, background="#1e1e1e")
        status_frame.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 5))
        tk.Label(status_frame, text="Status:", font=("Bahnschrift Light", 14),
                 background="#1e1e1e", foreground="white").pack(side="left")
        self.status_var = tk.StringVar(value="Bereit")
        tk.Label(status_frame, textvariable=self.status_var, font=("Bahnschrift Light", 14, "bold"),
                 background="#1e1e1e", foreground="#009FE3").pack(side="left", padx=(5, 0))

        # Startbutton + Spinner oben rechts
        button_frame_top = tk.Frame(self.root, background="#1e1e1e")
        button_frame_top.grid(row=1, column=1, sticky="ne", padx=20, pady=(0, 5))

        self.spinner_images = [
            ImageTk.PhotoImage(Image.open(f"spinner_{i}.png").resize((24, 24)))
            for i in range(18)
        ]
        self.spinner_label = tk.Label(button_frame_top, background="#1e1e1e")
        self.spinner_label.pack(side="left", padx=(0, 18))

        self.start_button = ttk.Button(
            button_frame_top, text="Messung starten",
            command=self.start_measurement, style="Custom.TButton", width=20
        )
        self.start_button.pack(side="left")

        self.spinner_running = False
        self.spinner_index = 0

        # Zusatzinfos (mehrfarbig)
        info_frame = tk.Frame(self.root, background="#1e1e1e")
        info_frame.grid(row=2, column=0, columnspan=1, sticky="w", padx=20, pady=(0, 5))

        def colored_info(label, value):
            tk.Label(info_frame, text=label, font=("Bahnschrift Light", 11),
                     background="#1e1e1e", foreground="white").pack(side="left")
            tk.Label(info_frame, text=value, font=("Bahnschrift Light", 11, "bold"),
                     background="#1e1e1e", foreground="#009FE3").pack(side="left")

        colored_info("Kontaktfläche: ", "5 cm²")
        colored_info("    Druck: ", "1 MPa")
        colored_info("    Strom: ", "1 A")

        # Clear-Button unter Zusatzinfos
        button_frame_bottom = tk.Frame(self.root, background="#1e1e1e")
        button_frame_bottom.grid(row=2, column=1, sticky="ne", padx=20, pady=(0, 5))

        self.clear_button = ttk.Button(button_frame_bottom, text="Löschen",
                                       command=self.clear_table, style="Custom.TButton", width=20)
        self.clear_button.pack()

        # Tabelle + Scrollbar
        table_frame = tk.Frame(self.root, background="#1e1e1e")
        table_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=20, pady=(10, 20))

        columns = ("Zeit", "Flächenwiderstand")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _start_spinner(self):
        self.spinner_running = True
        self._animate_spinner()

    def _animate_spinner(self):
        if not self.spinner_running:
            self.spinner_label.config(image="")
            return
        self.spinner_label.config(image=self.spinner_images[self.spinner_index])
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_images)
        self.root.after(100, self._animate_spinner)

    def _stop_spinner(self):
        self.spinner_running = False

    def start_measurement(self):
        if self.is_measuring:
            return
        self.is_measuring = True
        self.start_button.config(state=tk.DISABLED)
        self._start_spinner()
        threading.Thread(target=self._run_measurement, daemon=True).start()

    def _run_measurement(self):
        for step in STATUS_STEPS:
            self.status_var.set(step)
            time.sleep(1)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resistance = f"{round(random.uniform(10, 15), 2)} mΩ·cm²"
        self.tree.insert("", "end", values=(timestamp, resistance))
        self.tree.yview_moveto(1)

        self.status_var.set("Bereit")
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.root.after(0, self._stop_spinner)
        self.is_measuring = False

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

if __name__ == "__main__":
    root = tk.Tk()
    app = TPRGUI(root)
    root.mainloop()
