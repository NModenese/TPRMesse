import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import matplotlib.pyplot as plt
from PIL import Image, ImageTk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from Backend import MeasurementBackend  # Importiere das neue Backend

STATUS_STEPS = ["Bereit", "Kontaktieren", "Messen", "Zurückfahren"]


class TPRGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TPR Messung für Bipolarplatten")
        self.root.geometry("800x800")
        self.root.minsize(800, 800)
        self.root.configure(background="#1e1e1e")

        self.backend = MeasurementBackend()

        self.root.tk.call("source", "azure.tcl")
        self.root.tk.call("set_theme", "dark")

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Styling für Buttons und Tabellen
        style = ttk.Style()
        style.configure("Custom.TButton", foreground="white", background="#009FE3",
                        font=("Bahnschrift Light", 11), padding=6)
        style.map("Custom.TButton", background=[("active", "#009FE3")])
        style.configure("Treeview", background="#1e1e1e", fieldbackground="#1e1e1e",
                        foreground="white", rowheight=28, font=("Bahnschrift Light", 11))
        style.configure("Treeview.Heading", background="#1e1e1e", foreground="white",
                        font=("Bahnschrift Light", 12, "bold"))

        # Oberes Steuerpanel
        main_top = tk.Frame(self.root, background="#1e1e1e")
        main_top.grid(row=0, column=0, sticky="new", padx=10, pady=5)
        for r in range(3):
            main_top.grid_rowconfigure(r, weight=0)
        for c in range(2):
            main_top.grid_columnconfigure(c, weight=1)

        # Titel und Logo
        title_label = tk.Label(main_top, text="TPR Messung für Bipolarplatten",
                               font=("Bahnschrift Light", 18, "bold"), background="#1e1e1e", foreground="white")
        title_label.grid(row=0, column=0, sticky="w")
        logo_img = Image.open("mafu_logo_w.png").resize((160, 40))
        self.logo = ImageTk.PhotoImage(logo_img)
        logo_label = tk.Label(main_top, image=self.logo, background="#1e1e1e")
        logo_label.grid(row=0, column=1, sticky="e")

        # Statusanzeige
        status_label = tk.Label(main_top, text="Status:", font=("Bahnschrift Light", 14),
                                background="#1e1e1e", foreground="white")
        status_label.grid(row=1, column=0, sticky="w", pady=5)
        self.status_var = tk.StringVar(value="Bereit")
        status_value = tk.Label(main_top, textvariable=self.status_var, font=("Bahnschrift Light", 14, "bold"),
                                background="#1e1e1e", foreground="#009FE3")
        status_value.grid(row=1, column=0, sticky="w", padx=(65, 0))

        # Spinner und Startbutton
        top_right_controls = tk.Frame(main_top, background="#1e1e1e")
        top_right_controls.grid(row=1, column=1, sticky="e")
        self.spinner_images = [ImageTk.PhotoImage(Image.open(f"spinner_{i}.png").resize((24, 24))) for i in range(18)]
        self.empty_spinner = ImageTk.PhotoImage(Image.new("RGBA", (24, 24), (0, 0, 0, 0)))
        self.spinner_label = tk.Label(top_right_controls, image=self.empty_spinner, background="#1e1e1e")
        self.spinner_label.grid(row=0, column=0, sticky="e", pady=5)
        self.start_button = ttk.Button(top_right_controls, text="Messung starten", underline=0,
                                       command=self.start_measurement, style="Custom.TButton", width=20)
        self.start_button.grid(row=0, column=1, sticky="e", pady=5)

        # Zusatzinfos
        info_frame = tk.Frame(main_top, background="#1e1e1e")
        info_frame.grid(row=2, column=0, sticky="w")

        def colored_info(label, value):
            tk.Label(info_frame, text=label, font=("Bahnschrift Light", 11),
                     background="#1e1e1e", foreground="white").pack(side="left")
            tk.Label(info_frame, text=value, font=("Bahnschrift Light", 11, "bold"),
                     background="#1e1e1e", foreground="#009FE3").pack(side="left")

        colored_info("Kontaktfläche: ", "5 cm²")
        colored_info("    Druck: ", "1 MPa")
        colored_info("    Strom: ", "1 A")

        # Löschen und Stop Buttons
        bottom_right_controls = tk.Frame(main_top, background="#1e1e1e")
        bottom_right_controls.grid(row=2, column=1, sticky="e", pady=5)
        bottom_right_controls.grid_columnconfigure(0, weight=1)
        bottom_right_controls.grid_columnconfigure(1, weight=1)

        # Löschen-Button
        self.clear_button = ttk.Button(
            bottom_right_controls, text="Löschen", underline=0,
            command=self.clear_table, style="Custom.TButton", width=20
        )
        self.clear_button.grid(row=0, column=0, sticky="e", padx=(0, 5))

        # Messung stoppen-Button
        self.stop_button = ttk.Button(
            bottom_right_controls, text="Messung stoppen", underline=8,
            command=self.stop_measurement, style="Custom.TButton", width=20
        )
        self.stop_button.grid(row=0, column=1, sticky="e")

        # Diagrammbereich
        graph_frame = tk.Frame(self.root, background="#1e1e1e")
        graph_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        for i in range(3):
            graph_frame.grid_rowconfigure(i, weight=1, uniform="grp1")
        for i in range(2):
            graph_frame.grid_columnconfigure(i, weight=1, uniform="grp2")

        self.graph_titles = ["Spannung U (V)", "Strom I (A)", "Flächenwiderstand R (mΩ cm²)",
                             "Elevatorhöhe h (mm)", "Federspannung F_k (N)"]
        self.graph_axes = []
        self.graph_lines = []
        self.time_data = [[] for _ in self.graph_titles]
        self.graph_data = [[] for _ in self.graph_titles]

        # Erstellen der einzelnen Plots
        for idx, title in enumerate(self.graph_titles):
            fig, ax = plt.subplots(figsize=(3, 2), dpi=100)
            ax.set_title(title, fontsize=9)
            ax.set_xlabel("t (s)", fontsize=8)
            ax.set_ylabel(title.split()[0], fontsize=8)
            ax.grid(True, linestyle=":", alpha=0.6)
            canvas = FigureCanvasTkAgg(fig, master=graph_frame)
            canvas_widget = canvas.get_tk_widget()
            row = idx % 3
            col = 0 if idx < 3 else 1
            canvas_widget.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
            line, = ax.plot([], [], linewidth=1)
            self.graph_axes.append(ax)
            self.graph_lines.append(line)

        # Tabelle für Messwerte
        table_frame = tk.Frame(graph_frame, background="#1e1e1e")
        table_frame.grid(row=2, column=1, sticky="nsew", padx=5, pady=5)
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        columns = ("Zeit", "Flächenwiderstand")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Keybindings
        self.root.bind_all("<m>", lambda e: self.start_measurement())
        self.root.bind_all("<l>", lambda e: self.clear_table())
        self.root.bind_all("<s>", lambda e: self.stop_measurement())
        self.root.bind_all("<Control-c>", lambda e: self.stop_measurement())

    # Spinner starten
    def _start_spinner(self):
        self.spinner_index = 0
        self.spinner_running = True
        self._animate_spinner()

    def _animate_spinner(self):
        if not self.spinner_running:
            self.spinner_label.config(image=self.empty_spinner)
            return
        self.spinner_label.config(image=self.spinner_images[self.spinner_index])
        self.spinner_index = (self.spinner_index + 1) % len(self.spinner_images)
        self.root.after(100, self._animate_spinner)

    def _stop_spinner(self):
        self.spinner_running = False

    # Start der Messung per Thread
    def start_measurement(self):
        if self.backend.is_running():
            return

        self._start_spinner()
        self.status_var.set("Kontaktieren")
        self.time_data.clear()
        for lst in self.graph_data:
            lst.clear()

        self.start_time = time.time()
        self.backend.start_measurement(callback=self.handle_measurement_update, on_done=self._on_measurement_done)

    def stop_measurement(self):
        self.backend.stop()

    def _on_measurement_done(self):
        self._stop_spinner()
        self.status_var.set("Bereit")
        self.start_button.config(state=tk.NORMAL)

    def handle_measurement_update(self, data):
        timestamp = round(time.time() - self.start_time, 2)

        voltage = data.get("voltage")
        current = data.get("current")
        resistance = data.get("resistance")
        elevator = data.get("elevator")
        compression = data.get("compression")

        values = [voltage, current, resistance, elevator, compression]

        for i, val in enumerate(values):
            if val is not None:
                # robust: Zeit nur speichern, wenn Wert existiert
                while len(self.time_data) <= i:
                    self.time_data.append([])  # initialisiere falls nötig
                while len(self.graph_data) <= i:
                    self.graph_data.append([])

                self.time_data[i].append(timestamp)
                self.graph_data[i].append(val)
                self.graph_lines[i].set_data(self.time_data[i], self.graph_data[i])
                ax = self.graph_axes[i]
                ax.relim()
                ax.autoscale_view()
                ax.figure.canvas.draw_idle()

        if data.get("final") and resistance is not None:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.tree.insert("", "end", values=(now, f"{resistance:.2f}"))
            self.tree.yview_moveto(1)

    def clear_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def closeEvent(self, event):
        self.backend.shutdown()
        event.accept()


# Startpunkt der Anwendung
if __name__ == "__main__":
    root = tk.Tk()
    app = TPRGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (root.destroy(), exit()))
    root.mainloop()
