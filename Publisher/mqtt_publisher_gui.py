"""
MQTT Publisher GUI Application

A Python Tkinter-based graphical interface for publishing MQTT messages with template support.
This application allows users to connect to MQTT brokers, select message templates,
fill in dynamic fields, and publish messages to specified topics.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

# Import our new components
from template_manager import TemplateManager
from mqtt_client import MqttClient
from config_manager import ConfigManager

class CreateToolTip:
    """Create a tooltip for a given widget"""
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.close)
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def close(self, event=None):
        self.unschedule()
        self.hide_tooltip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.show_tooltip)

    def unschedule(self):
        id_ = getattr(self, 'id', None)
        if id_:
            self.widget.after_cancel(id_)
            self.id = None

    def show_tooltip(self):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        
        label = ttk.Label(self.tw, text=self.text, justify='left',
                         background='#ffffe0', relief='solid', borderwidth=1,
                         padding=(5, 2, 5, 2))
        label.pack(ipadx=1)

    def hide_tooltip(self):
        if self.tw:
            self.tw.destroy()
            self.tw = None

try:
    import yaml
except ImportError:
    error_root = tk.Tk()
    error_root.withdraw()
    messagebox.showerror(
        "Missing Library",
        "FATAL ERROR: The 'PyYAML' library is not installed.\n\nPlease install it by running this command in your terminal:\n\npip install pyyaml"
    )
    sys.exit(1)

MAX_HISTORY = 20

class MqttPublisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generic MQTT Publisher")

        self.config_manager = ConfigManager('mqtt_publisher_config.json')
        self.config_manager.load()

        geometry = self.config_manager.get_window_geometry()
        self.preview_pane_width = geometry.get('preview_width', 400)
        self.main_pane_height = geometry.get('main_pane_height', 300)  # Height for main vertical pane
        self.root.geometry(f"{geometry.get('width', 800)}x{geometry.get('height', 750)}+{geometry.get('x', 100)}+{geometry.get('y', 100)}")

        self.mqtt_client = MqttClient()
        self.mqtt_client.set_callbacks(on_connect=self._on_mqtt_connect, on_disconnect=self._on_mqtt_disconnect)
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        templates_dir = os.path.join(script_dir, 'payload_templates')
        self.template_manager = TemplateManager(templates_dir)
        self.template_widgets = {}
        self._mqtt_connected = False

        self._setup_ui()
        self._load_connection_settings()

        self.root.after(100, self._restore_pane_geometry)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        
        bg_color = '#f0f0f0'
        style.configure('TFrame', background=bg_color)
        style.configure('TLabelframe', background=bg_color, borderwidth=2, relief='groove', labelmargins=(10, 2, 10, 2))
        style.configure('TLabelframe.Label', font=('Helvetica', 10, 'bold'), background=bg_color, foreground='#2c3e50')
        style.configure('TLabel', background=bg_color, font=('Helvetica', 9))
        style.configure('Bold.TLabel', font=('Helvetica', 9, 'bold'), background=bg_color)
        
        self.root.configure(bg=bg_color)
        
        self.main_container = ttk.Frame(self.root, padding=(5, 5, 5, 0))
        self.main_container.pack(fill='both', expand=True)
        self.main_container.columnconfigure(0, weight=1)
        
        config_frame = self._create_config_frame()
        config_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        topic_frame = self._create_topic_frame()
        topic_frame.grid(row=1, column=0, sticky='ew', pady=(0, 5))
        
        self.main_paned = ttk.Panedwindow(self.main_container, orient=tk.VERTICAL)
        style.configure('TPanedwindow', background='#f0f0f0', sashwidth=5, sashpad=2)
        
        self._create_payload_frame()
        self.main_paned.add(self.payload_frame, weight=1)
        
        self._create_status_frame()
        self.main_paned.add(self.status_frame, weight=1)
        
        self.main_paned.grid(row=2, column=0, sticky='nsew', pady=(0, 5))
        
        self.main_container.grid_rowconfigure(2, weight=1)
        
        self._create_bottom_button_frame()
        self._refresh_templates()

    def _create_config_frame(self):
        self.config_frame = tk.LabelFrame(self.main_container, text=" Setup MQTT Broker Connection ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        
        style = ttk.Style()
        style.map('Connect.TButton', foreground=[('!disabled', 'white')], background=[('active', '#45a049'), ('!disabled', '#4CAF50')])
        style.map('Disconnect.TButton', foreground=[('!disabled', 'white')], background=[('active', '#d32f2f'), ('!disabled', '#f44336')])
        style.configure('Error.TLabel', foreground='red')
        
        label_padx = (8,2); entry_padx = (60,8); entry_width = 32
        
        ttk.Label(self.config_frame, text="Broker", style='Bold.TLabel').grid(row=0, column=0, sticky="w", padx=label_padx, pady=2)
        self.broker_entry = ttk.Entry(self.config_frame, width=entry_width, font=('Helvetica', 9))
        self.broker_entry.grid(row=0, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Port", style='Bold.TLabel').grid(row=1, column=0, sticky="w", padx=label_padx, pady=2)
        self.port_entry = ttk.Entry(self.config_frame, width=10, font=('Helvetica', 9))
        self.port_entry.grid(row=1, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Username", style='Bold.TLabel').grid(row=2, column=0, sticky="w", padx=label_padx, pady=2)
        self.username_entry = ttk.Entry(self.config_frame, width=20, font=('Helvetica', 9))
        self.username_entry.grid(row=2, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Password", style='Bold.TLabel').grid(row=3, column=0, sticky="w", padx=label_padx, pady=2)
        self.password_entry = ttk.Entry(self.config_frame, show="*", width=20, font=('Helvetica', 9))
        self.password_entry.grid(row=3, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Client ID", style='Bold.TLabel').grid(row=4, column=0, sticky="w", padx=label_padx, pady=2)
        self.client_id_var = tk.StringVar(value="MQTT_Publisher_GUI")
        self.client_id_entry = ttk.Entry(self.config_frame, textvariable=self.client_id_var, width=entry_width, font=('Helvetica', 9), state="readonly")
        self.client_id_entry.grid(row=4, column=1, sticky="w", padx=entry_padx, pady=2)
        
        self.config_frame.grid_columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.config_frame)
        button_frame.grid(row=1, column=3, rowspan=5, sticky="nsw", padx=(18,5), pady=(2,2))
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self._connect_mqtt, style='Connect.TButton')
        self.connect_button.pack(fill="x", padx=2, pady=(2,6), ipadx=10)
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self._disconnect_mqtt, state="disabled", style='Disconnect.TButton')
        self.disconnect_button.pack(fill="x", padx=2, pady=(2,2), ipadx=10)

        self.connection_status_var = tk.StringVar(value="Disconnected")
        self.connection_status_label = ttk.Label(self.config_frame, textvariable=self.connection_status_var, style='Error.TLabel')
        self.connection_status_label.grid(row=6, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 2))

        return self.config_frame

    def _create_topic_frame(self):
        self.topic_frame = tk.LabelFrame(self.main_container, text=" Select Topic ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        self.topic_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.topic_frame, text="Topic:", style='Bold.TLabel').grid(row=0, column=0, sticky="w", padx=5, pady=3)
        self.topic_combobox = ttk.Combobox(self.topic_frame, width=50, font=('Helvetica', 9))
        self.topic_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        self.topic_combobox.bind('<<ComboboxSelected>>', lambda e: self._update_publish_button_state())
        self.topic_combobox.bind('<KeyRelease>', lambda e: self._update_publish_button_state())
        
        ttk.Label(self.topic_frame, text="QoS:", style='Bold.TLabel').grid(row=0, column=2, sticky="e", padx=5, pady=3)
        self.qos_combobox = ttk.Combobox(self.topic_frame, values=["0", "1", "2"], width=5, state="readonly", font=('Helvetica', 9))
        self.qos_combobox.set("0")
        self.qos_combobox.grid(row=0, column=3, sticky="w", padx=5, pady=5)
        
        style = ttk.Style(); style.configure('Italic.TLabel', font=('Helvetica', 9, 'italic'), foreground='#6c757d')
        ttk.Label(self.topic_frame, text="Configure your payload in the section below", style='Italic.TLabel').grid(row=1, column=0, columnspan=4, sticky="w", padx=10, pady=(0, 5))
        
        return self.topic_frame

    def _create_payload_frame(self):
        self.payload_frame = tk.LabelFrame(self.main_paned, text=" Configure Message Payload ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        self.payload_frame.columnconfigure(0, weight=1)
        self.payload_frame.rowconfigure(1, weight=0)
        
        # Create tabbed interface
        self.payload_notebook = ttk.Notebook(self.payload_frame)
        self.payload_notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # JSON Template Tab
        self.json_tab = ttk.Frame(self.payload_notebook)
        self.payload_notebook.add(self.json_tab, text=" Use JSON Templates to Configure MessagePayload ")
        self.json_tab.columnconfigure(0, weight=1)
        self.json_tab.rowconfigure(1, weight=0)
        
        # Template selection frame for JSON tab
        template_frame = tk.Frame(self.json_tab, padx=0, pady=5)
        template_frame.grid(row=0, column=0, sticky="ew")
        template_frame.columnconfigure(1, weight=1)
        
        ttk.Label(template_frame, text="Payload Template:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.template_combobox = ttk.Combobox(template_frame, state="readonly", width=40)
        self.template_combobox.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        btn_frame = tk.Frame(template_frame)
        btn_frame.grid(row=0, column=2, sticky="e")
        
        self.refresh_btn = ttk.Button(btn_frame, text="⟳", width=3, command=self._refresh_templates)
        self.refresh_btn.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.refresh_btn, "Refresh templates")
        
        self.edit_btn = ttk.Button(btn_frame, text="✎", width=3, command=self._edit_template)
        self.edit_btn.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.edit_btn, "Edit template")
        
        self.new_btn = ttk.Button(btn_frame, text="+", width=3, command=self._create_template)
        self.new_btn.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.new_btn, "New template")
        
        # Paned window for JSON template interface
        self.paned_window = ttk.PanedWindow(self.json_tab, orient=tk.HORIZONTAL)
        self.paned_window.grid(row=1, column=0, sticky="nsew")
        
        self.input_frame = tk.LabelFrame(self.paned_window, text=" Template Fields", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=8, pady=6, bd=2, relief='groove')
        self.paned_window.add(self.input_frame, weight=1)
        
        self.input_frame.columnconfigure(0, weight=1)
        self.input_frame.rowconfigure(0, weight=0)
        
        self.field_canvas = tk.Canvas(self.input_frame)
        scrollbar = ttk.Scrollbar(self.input_frame, orient="vertical", command=self.field_canvas.yview)
        self.field_canvas.configure(yscrollcommand=scrollbar.set)
        self.field_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.field_frame = tk.Frame(self.field_canvas)
        self.field_canvas.create_window((0, 0), window=self.field_frame, anchor='nw')
        self.field_frame.bind("<Configure>", lambda e: self.field_canvas.configure(scrollregion=self.field_canvas.bbox("all")))
        
        self.preview_frame = tk.LabelFrame(self.paned_window, text=" Payload Preview", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=8, pady=6, bd=2, relief='groove')
        self.paned_window.add(self.preview_frame, weight=2)
        
        self.preview_text = tk.Text(self.preview_frame, wrap=tk.WORD, height=4, state="normal", bg='white', fg='black', font=('Consolas', 10), relief='flat', padx=5, pady=5)
        preview_scroll = ttk.Scrollbar(self.preview_frame, command=self.preview_text.yview)
        self.preview_text.configure(yscrollcommand=preview_scroll.set)
        preview_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # String Payload Tab
        self.string_tab = ttk.Frame(self.payload_notebook)
        self.payload_notebook.add(self.string_tab, text="Use String Payload in the Message ")
        self.string_tab.columnconfigure(0, weight=1)
        self.string_tab.rowconfigure(0, weight=1)
        
        # String payload input area
        string_input_frame = tk.LabelFrame(self.string_tab, text=" String Payload", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=10, pady=10, bd=2, relief='groove')
        string_input_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        string_input_frame.columnconfigure(0, weight=1)
        string_input_frame.rowconfigure(0, weight=0)
        
        # Add a label with instructions
        instruction_label = ttk.Label(string_input_frame, text="Enter your message payload below:", font=('Helvetica', 9, 'bold'))
        instruction_label.grid(row=0, column=0, sticky="w", padx=5, pady=(0, 5))
        
        # String payload text area
        self.string_payload_text = tk.Text(string_input_frame, wrap=tk.WORD, height=12, bg='white', fg='black', font=('Consolas', 10), relief='solid', padx=5, pady=5)
        string_scroll = ttk.Scrollbar(string_input_frame, command=self.string_payload_text.yview)
        self.string_payload_text.configure(yscrollcommand=string_scroll.set)
        self.string_payload_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        string_scroll.grid(row=1, column=1, sticky="ns")
        
        # No placeholder text needed
        self.string_payload_text.bind("<KeyRelease>", lambda e: self._update_publish_button_state())
        
        # Publish button will be created in the bottom button frame
        
        # Bind tab change event
        self.payload_notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
        
        # Initialize template selection
        self.template_combobox.bind('<<ComboboxSelected>>', self._on_template_selected)
        self._show_no_template_message()
        
        # Track current payload mode
        self.current_payload_mode = "json"  # "json" or "string"
        
    def _show_no_template_message(self):
        for widget in self.field_frame.winfo_children(): widget.destroy()
        self.no_template_label = ttk.Label(self.field_frame, text="Select a template to configure the payload fields", foreground="gray")
        self.no_template_label.pack(expand=True, pady=20)
        if hasattr(self, 'preview_text'):
            self.preview_text.config(state="normal")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.config(state="disabled")

    def _on_tab_changed(self, event=None):
        """Handle tab change events to update the current payload mode."""
        current_tab = self.payload_notebook.select()
        if current_tab == str(self.json_tab):
            self.current_payload_mode = "json"
        elif current_tab == str(self.string_tab):
            self.current_payload_mode = "string"
        self._update_publish_button_state()

    # Removed placeholder text functionality

    def _create_status_frame(self):
        self.status_frame = tk.LabelFrame(self.main_paned, text=" Status Log ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=10, pady=10, bd=2, relief='groove')
        self.status_frame.columnconfigure(0, weight=1); self.status_frame.rowconfigure(0, weight=1)
        
        self.status_text = tk.Text(self.status_frame, wrap=tk.WORD, state="disabled", bg='white', fg='#212529', font=('Consolas', 9), padx=5, pady=5, relief='flat', highlightthickness=1, highlightbackground='#ced4da', highlightcolor='#80bdff')
        self.status_text.tag_configure('info', foreground='#007bff'); self.status_text.tag_configure('success', foreground='#28a745'); self.status_text.tag_configure('warning', foreground='#ffc107'); self.status_text.tag_configure('error', foreground='#dc3545')
        
        scrollbar = ttk.Scrollbar(self.status_frame, command=self.status_text.yview); self.status_text.configure(yscrollcommand=scrollbar.set)
        self.status_text.grid(row=0, column=0, sticky='nsew'); scrollbar.grid(row=0, column=1, sticky='ns')
        
        self.status_text_menu = tk.Menu(self.root, tearoff=0); self.status_text_menu.add_command(label="Copy", command=self._copy_status_text); self.status_text_menu.add_command(label="Copy All", command=self._copy_all_status_text); self.status_text_menu.add_separator(); self.status_text_menu.add_command(label="Clear", command=self._clear_status_text)
        self.status_text.bind("<Button-3>", self._show_status_text_menu)
        self._log_message("MQTT Publisher started. Configure your connection and select a template.", "info")

    def _log_message(self, message, msg_type="info"):
        if not hasattr(self, 'status_text'): return
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.status_text.config(state="normal")
        self.status_text.insert(tk.END, f"[{timestamp}] ", ("timestamp_tag",))
        self.status_text.insert(tk.END, f"{message}\n", (msg_type,))
        self.status_text.see(tk.END)
        self.status_text.config(state="disabled")

    
    # This code replaces the existing _create_bottom_button_frame method

    def _create_bottom_button_frame(self):
        """Create the bottom button frame with styled Help and Close buttons."""
        button_container = tk.Frame(self.main_container, padx=0, pady=5)
        button_container.grid(row=3, column=0, sticky='ew', pady=(5, 0))

        separator = tk.Frame(button_container, height=2, bg='#cccccc')
        separator.pack(fill='x', pady=(0, 5))

        button_frame = tk.Frame(button_container, padx=5, pady=5)
        button_frame.pack(fill='x')

        style = ttk.Style()

        # --- Style for the Help button (Blue) ---
        style.configure('Help.TButton',
                    background='#007bff',
                    foreground='white',
                    font=('Helvetica', 9, 'bold'))
        style.map('Help.TButton',
                background=[('active', '#0056b3')],  # Darker blue on hover
                foreground=[('active', 'white')])

        # --- Style for the Publish button (Green) ---
        style.configure('Green.TButton',
                    background='#28a745',
                    foreground='white',
                    font=('Helvetica', 9, 'bold'))
        style.map('Green.TButton',
                background=[('active', '#218838')],  # Darker green on hover
                foreground=[('active', 'white')])

        # --- Style for the Clear Log button (Gray) ---
        style.configure('Clear.TButton',
                    background='#6c757d',
                    foreground='white',
                    font=('Helvetica', 9, 'bold'))
        style.map('Clear.TButton',
                background=[('active', '#5a6268')],
                foreground=[('active', 'white')])

        # --- Style for the Close button (Red) ---
        style.configure('Close.TButton',
                    background='#dc3545',
                    foreground='white',
                    font=('Helvetica', 9, 'bold'))
        style.map('Close.TButton',
                background=[('active', '#c82333')],  # Darker red on hover
                foreground=[('active', 'white')])

        # --- Create Buttons ---
        
        # Help button on the left
        self.help_button = ttk.Button(
            button_frame,
            text="Help (F1)",
            command=self._show_help,
            style='Help.TButton'  # Apply the new blue style
        )
        self.help_button.pack(side='left', padx=5)
        
        # Publish button in the middle
        self.publish_button = ttk.Button(
            button_frame,
            text="Publish Message",
            command=self._publish_message,
            state="disabled",
            style='Green.TButton'
        )
        self.publish_button.pack(side='left', padx=10)
        
        # Clear Log button beside Publish button
        self.clear_status_button = ttk.Button(
            button_frame,
            text="Clear Log",
            command=self._clear_status_text,
            style='Clear.TButton'
        )
        self.clear_status_button.pack(side='left', padx=5)
        
        # Close button on the right
        self.close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self._on_closing,
            style='Close.TButton' # Apply the red style
        )
        self.close_button.pack(side='right', padx=5)

        # Version label will be pushed to the right before the close button
        ttk.Label(
            button_frame,
            text="Version: 1.4.16",
            foreground='gray',
            font=('Helvetica', 8)
        ).pack(side='right', padx=(0, 20))

        self.root.bind('<F1>', lambda e: self._show_help())
        return button_container



    def _show_status_text_menu(self, event):
        self.status_text_menu.tk_popup(event.x_root, event.y_root)
    
    def _copy_status_text(self):
        try: self.root.clipboard_append(self.status_text.get("sel.first", "sel.last")); self.root.update()
        except tk.TclError: pass
    
    def _copy_all_status_text(self):
        self.root.clipboard_clear(); self.root.clipboard_append(self.status_text.get("1.0", "end-1c"))
    
    def _clear_status_text(self):
        self.status_text.config(state="normal"); self.status_text.delete("1.0", "end"); self.status_text.config(state="disabled")

    def _connect_mqtt(self):
        broker=self.broker_entry.get().strip(); port_str=self.port_entry.get().strip()
        if not broker or not port_str: messagebox.showerror("Error", "Broker and Port cannot be empty."); return
        try: port = int(port_str)
        except ValueError: messagebox.showerror("Error", "Port must be an integer."); return
        username=self.username_entry.get().strip(); password=self.password_entry.get()
        self.config_manager.set_connection_settings(broker, port, username); self.config_manager.save()
        try:
            self._log_message(f"Connecting to {broker}:{port}...")
            self.mqtt_client.connect(broker, port, username, password)
        except Exception as e:
            self._log_message(f"Connection failed: {e}", "error"); messagebox.showerror("Connection Failed", f"Could not connect to broker.\nError: {e}")

    def _on_mqtt_connect(self, reason_code):
        mqtt_codes = {0: "Connection successful", 1: "Incorrect protocol version", 2: "Client identifier rejected", 3: "Server unavailable", 4: "Bad username or password", 5: "Not authorized"}
        if reason_code == 0:
            self._mqtt_connected = True; self._log_message("Connected to MQTT Broker successfully!", "success"); self.connection_status_var.set("Connected"); self.connection_status_label.config(foreground="#28a745")
            self.connect_button.config(state="disabled"); self.disconnect_button.config(state="normal")
        else:
            self._mqtt_connected = False; self.connection_status_var.set("Disconnected"); self.connection_status_label.config(foreground="#dc3545")
            messagebox.showerror("Connection Failed", f"Could not connect to MQTT broker.\n\nError: {mqtt_codes.get(reason_code, f'Unknown error (code {reason_code})')}")
        self._update_publish_button_state()

    def _disconnect_mqtt(self):
        self.mqtt_client.disconnect()

    def _on_mqtt_disconnect(self, reason_code):
        self._mqtt_connected = False; self._log_message(f"Disconnected from MQTT Broker", "error"); self.connection_status_var.set("Disconnected"); self.connection_status_label.config(foreground="#dc3545")
        self.connect_button.config(state="normal"); self.disconnect_button.config(state="disabled")
        self._update_publish_button_state()

    def _refresh_templates(self):
        try:
            templates = self.template_manager.list_templates()
            # Strip .yaml and .yml extensions from template names for display
            display_names = []
            for template in templates:
                if template.endswith('.yaml'):
                    display_names.append(template[:-5])  # Remove .yaml
                elif template.endswith('.yml'):
                    display_names.append(template[:-4])  # Remove .yml
                else:
                    display_names.append(template)
            
            self.template_combobox['values'] = display_names
            if display_names and not self.template_combobox.get(): 
                self.template_combobox.set(display_names[0])
                self._on_template_selected()
        except Exception as e: self._log_message(f"Error loading templates: {e}", "error")
            
    def _on_template_selected(self, event=None):
        display_name = self.template_combobox.get()
        if not display_name: return
        
        # Convert display name back to actual filename
        template_file = None
        templates = self.template_manager.list_templates()
        for template in templates:
            if template.endswith('.yaml') and template[:-5] == display_name:
                template_file = template
                break
            elif template.endswith('.yml') and template[:-4] == display_name:
                template_file = template
                break
            elif template == display_name:
                template_file = template
                break
        
        if not template_file:
            self._log_message(f"Template file not found for: {display_name}", "error")
            return
            
        try:
            for widget in self.field_frame.winfo_children(): widget.destroy()
            self.template_widgets = {}
            self.preview_text.config(state="normal")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.config(state="disabled")
            self.current_template = self.template_manager.load_template(template_file)
            # Debug logging (can be removed in production)
            # self._log_message(f"Loaded template with {len(self.current_template.get('fields', []))} fields", "info")
            if 'fields' in self.current_template:
                for i, field in enumerate(self.current_template.get('fields', [])):
                    # Debug logging (can be removed in production)
                    # self._log_message(f"Processing field {i}: {field.get('name', 'unnamed')} - depends_on: {field.get('depends_on', 'None')}", "info")
                    self._add_template_field(field, i)
            self.field_frame.columnconfigure(1, weight=1)
            # Set up dependency handlers and check initial visibility
            self._setup_dependency_handlers()
            self._check_field_dependencies()
            self.root.after(100, self._force_update_preview)
        except Exception as e: self._log_message(f"Error loading template: {e}", "error")
            
    def _load_connection_settings(self):
        settings = self.config_manager.get_connection_settings()
        self.broker_entry.insert(0, settings.get('broker', '')); self.port_entry.insert(0, settings.get('port', '1883')); self.username_entry.insert(0, settings.get('username', ''))
        self._update_combobox_values()
            
    def _add_template_field(self, field_def, row):
        field_name = field_def.get('name', '')
        field_label = field_def.get('prompt', field_name)
        default_value = field_def.get('default', '')
        help_text = field_def.get('help', '')
        choices = field_def.get('choices', None)
        range_constraint = field_def.get('range', None)
        depends_on = field_def.get('depends_on', None)  # New dependency support
        
        # Create container frame for this field (to enable show/hide)
        field_container = tk.Frame(self.field_frame)
        field_container.grid(row=row, column=0, columnspan=2, sticky="ew", padx=5, pady=2)
        field_container.columnconfigure(1, weight=1)
        
        # Create label (all fields are now required)
        label_text = field_label + ":"
        
        label = ttk.Label(field_container, text=label_text)
        label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        
        # Create variable and trace for preview updates
        var = tk.StringVar(value=str(default_value))
        var.trace_add('write', lambda *_: self._update_preview())
        
        # Create control based on field constraints
        if choices and isinstance(choices, list):
            # Create combobox for fields with choices
            control = ttk.Combobox(field_container, textvariable=var, values=choices, state="readonly")
            control.grid(row=0, column=1, sticky="ew")
            
            # Add validation for combobox (ensure value is in choices)
            def validate_choice_input(value):
                if not value:
                    return False  # Empty is not valid - all fields are required
                return value in choices
            
            def on_combobox_focus_out(event):
                if not validate_choice_input(var.get()):
                    # Log validation error
                    self._log_message(f"Invalid choice '{var.get()}' for field '{field_label}'. Must be one of: {', '.join(choices)}", "error")
                    # Reset to default value if invalid
                    var.set(str(default_value))
            
            control.bind('<FocusOut>', on_combobox_focus_out)
            
            # Add tooltip to the control (not the label)
            if help_text:
                CreateToolTip(control, help_text)
                
        elif range_constraint and isinstance(range_constraint, dict) and 'min' in range_constraint and 'max' in range_constraint:
            # Create entry with range validation for integer fields
            control = ttk.Entry(field_container, textvariable=var)
            control.grid(row=0, column=1, sticky="ew")
            
            # Add validation for integer range
            def validate_range_input(value):
                if not value:
                    return False  # Empty is not valid - all fields are required
                try:
                    int_val = int(value)
                    min_val = range_constraint['min']
                    max_val = range_constraint['max']
                    return min_val <= int_val <= max_val
                except ValueError:
                    return False
            
            # Bind validation to the entry widget
            def on_focus_out(event):
                if not validate_range_input(var.get()):
                    # Log validation error
                    value = var.get()
                    try:
                        int_val = int(value)
                        self._log_message(f"Value {int_val} is out of range [{range_constraint['min']}, {range_constraint['max']}] for field '{field_label}'", "error")
                    except ValueError:
                        self._log_message(f"Invalid integer value '{value}' for field '{field_label}'", "error")
                    # Reset to default value if invalid
                    var.set(str(default_value))
            
            control.bind('<FocusOut>', on_focus_out)
            
            # Add range info to help text if not already present
            if help_text and f"Range: {range_constraint['min']}-{range_constraint['max']}" not in help_text:
                help_text += f" (Range: {range_constraint['min']}-{range_constraint['max']})"
            
            # Add tooltip to the control (not the label)
            if help_text:
                CreateToolTip(control, help_text)
        else:
            # Create regular entry for fields without constraints
            control = ttk.Entry(field_container, textvariable=var)
            control.grid(row=0, column=1, sticky="ew")
            
            # Add basic validation for text fields
            def validate_text_input(value):
                # Basic validation - ensure it's not just whitespace
                if not value or not value.strip():
                    return False  # Empty is not valid - all fields are required
                return len(value.strip()) > 0
            
            def on_text_focus_out(event):
                if not validate_text_input(var.get()):
                    # Log validation error
                    self._log_message(f"Invalid text value for field '{field_label}'. Value cannot be empty or whitespace only", "error")
                    # Reset to default value if invalid
                    var.set(str(default_value))
            
            control.bind('<FocusOut>', on_text_focus_out)
            
            # Add tooltip to the control (not the label)
            if help_text:
                CreateToolTip(control, help_text)
        
        # Store field information including dependency data
        self.template_widgets[field_name] = {
            'var': var, 
            'control': control, 
            'range': range_constraint,
            'container': field_container,
            'depends_on': depends_on,
            'field_def': field_def
        }
        
        # Debug logging for field creation (can be removed in production)
        # if depends_on:
        #     self._log_message(f"Created field '{field_name}' with dependency: {depends_on}", "info")
        
        self.field_frame.columnconfigure(1, weight=1)
    
    def _setup_dependency_handlers(self):
        """Set up change handlers for fields that have dependent fields."""
        # Find all parent fields (fields that other fields depend on)
        parent_fields = set()
        for field_name, field_info in self.template_widgets.items():
            depends_on = field_info.get('depends_on')
            if depends_on and ':' in depends_on:
                parent_field = depends_on.split(':', 1)[0]
                parent_fields.add(parent_field)
        
        # Debug logging (can be removed in production)
        # self._log_message(f"Setting up dependency handlers for parent fields: {list(parent_fields)}", "info")
        
        # Add change handlers to parent fields
        for parent_field in parent_fields:
            if parent_field in self.template_widgets:
                parent_var = self.template_widgets[parent_field]['var']
                # Add dependency check handler
                def make_handler():
                    def handler(*args):
                        self._check_field_dependencies()
                    return handler
                parent_var.trace_add('write', make_handler())
                # Debug logging (can be removed in production)
                # self._log_message(f"Added dependency handler to field: {parent_field}", "info")
    
    def _check_field_dependencies(self):
        """Check all field dependencies and update visibility."""
        for field_name, field_info in self.template_widgets.items():
            if field_info.get('depends_on'):
                self._check_field_visibility(field_name)
    
    def _check_field_visibility(self, field_name):
        """Check if a field should be visible based on its dependencies."""
        if field_name not in self.template_widgets:
            return
            
        field_info = self.template_widgets[field_name]
        depends_on = field_info.get('depends_on')
        
        if not depends_on:
            return
            
        # Parse dependency: "field_name:value" or "field_name:value1,value2,value3"
        if ':' not in depends_on:
            return
            
        parent_field, required_values = depends_on.split(':', 1)
        required_values = [v.strip() for v in required_values.split(',')]
        
        # Check if parent field exists and has the required value
        if parent_field in self.template_widgets:
            parent_value = self.template_widgets[parent_field]['var'].get()
            should_show = parent_value in required_values
            
            # Debug logging (can be removed in production)
            # self._log_message(f"Field '{field_name}' depends on '{parent_field}'='{parent_value}', required: {required_values}, showing: {should_show}", "info")
            
            container = field_info.get('container')
            if container:
                if should_show:
                    container.grid()
                else:
                    container.grid_remove()
                # Update preview when field visibility changes
                self._update_preview()
        else:
            self._log_message(f"Parent field '{parent_field}' not found for field '{field_name}'", "warning")
    
    def _is_field_visible(self, field_name):
        """Check if a field is currently visible."""
        if field_name not in self.template_widgets:
            return False
            
        field_info = self.template_widgets[field_name]
        depends_on = field_info.get('depends_on')
        
        # If field has no dependencies, it's always visible
        if not depends_on:
            return True
            
        # Parse dependency: "field_name:value" or "field_name:value1,value2,value3"
        if ':' not in depends_on:
            return True
            
        parent_field, required_values = depends_on.split(':', 1)
        required_values = [v.strip() for v in required_values.split(',')]
        
        # Check if parent field exists and has the required value
        if parent_field in self.template_widgets:
            parent_value = self.template_widgets[parent_field]['var'].get()
            return parent_value in required_values
        
        return False
    
    def _force_update_preview(self): self._update_preview()
        
    def _update_preview(self):
        if not hasattr(self, 'current_template') or not self.current_template:
            return
        template_text = self.current_template.get('template', '')
        
        # Only include values from visible fields (all fields are now required)
        field_values = {}
        for name, info in self.template_widgets.items():
            # Check if field is visible
            if self._is_field_visible(name):
                field_value = info['var'].get()
                # Include field if it has a value (all fields are required)
                if field_value.strip():
                    field_values[name] = field_value
        
        # Always include timestamp and sender
        field_values['timestamp'] = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
        field_values['sender'] = 'mqtt_publisher_gui'
        
        try:
            preview = template_text
            
            # Remove template variables for hidden fields
            import re
            for name, info in self.template_widgets.items():
                if not self._is_field_visible(name):
                    # Remove the entire JSON key-value pair for hidden fields using regex
                    # Handle both with and without quotes around the value
                    preview = re.sub(rf'\s*"{name}"\s*:\s*{{{{{name}}}}}\s*,?\s*', '', preview)
                    preview = re.sub(rf'\s*"{name}"\s*:\s*"{{{{{name}}}"}}\s*,?\s*', '', preview)
                    # Also remove any remaining variable placeholders
                    preview = preview.replace(f'{{{{{name}}}}}', '')
            
            # Clean up any trailing commas or extra commas
            import re
            preview = re.sub(r',\s*}', '}', preview)  # Remove comma before closing brace
            preview = re.sub(r',\s*,', ',', preview)  # Remove double commas
            
            # Now replace the remaining variables with their values
            for key, value in field_values.items():
                preview = preview.replace(f'{{{{{key}}}}}', str(value))
            try:
                preview = preview.format(**{k: str(v) for k, v in field_values.items()})
            except KeyError:
                pass
            try:
                formatted_preview = json.dumps(json.loads(preview), indent=2)
            except (json.JSONDecodeError, TypeError):
                formatted_preview = preview
            self.preview_text.config(state="normal")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, formatted_preview)
            self.preview_text.config(state="disabled")
        except Exception as e:
            self.preview_text.config(state="normal")
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Error: {e}")
            self.preview_text.config(state="disabled")
    
    def _create_template(self):
        name = simpledialog.askstring("New Template", "Enter template name:")
        if not name: return
        if not name.endswith('.yaml'): name += '.yaml'
        template = {'description': 'New template', 'fields': [{'name': 'field1', 'prompt': 'Field 1', 'default': 'value1'}], 'template': '{"key": "{{field1}}"}'}
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, 'payload_templates', name)
            with open(template_path, 'w') as f: yaml.dump(template, f)
            self._refresh_templates(); self.template_combobox.set(name); self._on_template_selected(); self._edit_template()
        except Exception as e: messagebox.showerror("Error", f"Failed to create template: {e}")
    
    def _edit_template(self):
        display_name = self.template_combobox.get()
        if not display_name: return
        
        # Convert display name back to actual filename
        template_file = None
        templates = self.template_manager.list_templates()
        for template in templates:
            if template.endswith('.yaml') and template[:-5] == display_name:
                template_file = template
                break
            elif template.endswith('.yml') and template[:-4] == display_name:
                template_file = template
                break
            elif template == display_name:
                template_file = template
                break
        
        if not template_file:
            messagebox.showerror("Error", f"Template file not found for: {display_name}")
            return
            
        try: 
            script_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(script_dir, 'payload_templates', template_file)
            os.startfile(template_path)
        except Exception as e: messagebox.showerror("Error", f"Failed to open template: {e}")
    
    def _generate_payload(self):
        """Generate payload based on current mode (JSON template or string)."""
        if self.current_payload_mode == "json":
            if not self.current_template:
                raise ValueError("No template selected")
            
            # Generate payload with only visible fields (all fields are now required)
            template_text = self.current_template.get('template', '')
            field_values = {}
            
            for name, info in self.template_widgets.items():
                # Check if field is visible
                if self._is_field_visible(name):
                    field_value = info['var'].get()
                    # Include field if it has a value (all fields are required)
                    if field_value.strip():
                        field_values[name] = field_value
            
            # Always include timestamp and sender
            field_values['timestamp'] = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')
            field_values['sender'] = 'mqtt_publisher_gui'
            
            # Generate the payload
            try:
                payload = template_text
                
                # Remove template variables for hidden fields
                import re
                for name, info in self.template_widgets.items():
                    if not self._is_field_visible(name):
                        # Remove the entire JSON key-value pair for hidden fields using regex
                        # Handle both with and without quotes around the value
                        payload = re.sub(rf'\s*"{name}"\s*:\s*{{{{{name}}}}}\s*,?\s*', '', payload)
                        payload = re.sub(rf'\s*"{name}"\s*:\s*"{{{{{name}}}"}}\s*,?\s*', '', payload)
                        # Also remove any remaining variable placeholders
                        payload = payload.replace(f'{{{{{name}}}}}', '')
                
                # Clean up any trailing commas or extra commas
                import re
                payload = re.sub(r',\s*}', '}', payload)  # Remove comma before closing brace
                payload = re.sub(r',\s*,', ',', payload)  # Remove double commas
                
                # Now replace the remaining variables with their values
                for key, value in field_values.items():
                    payload = payload.replace(f'{{{{{key}}}}}', str(value))
                try:
                    payload = payload.format(**{k: str(v) for k, v in field_values.items()})
                except KeyError:
                    pass
                return payload
            except Exception as e:
                raise ValueError(f"Error generating payload: {e}")
                
        elif self.current_payload_mode == "string":
            payload = self.string_payload_text.get("1.0", "end-1c").strip()
            if not payload:
                raise ValueError("Please enter a message in the string payload field")
            return payload
        else:
            raise ValueError("Unknown payload mode")
    
    def _publish_message(self):
        if not self._mqtt_connected: messagebox.showerror("Error", "Not connected to MQTT broker"); return
        topic = self.topic_combobox.get().strip()
        if not topic: messagebox.showerror("Error", "Topic cannot be empty"); return
        try:
            payload = self._generate_payload()
            if self.mqtt_client.publish(topic, payload):
                self._log_message(f"Published to {topic}: {payload}", "success")
                self.config_manager.add_topic_to_history(topic); self.config_manager.save()
                self._update_combobox_values()
            else: self._log_message("Failed to publish message", "error")
        except Exception as e: self._log_message(f"Publish error: {e}", "error")

    def _update_combobox_values(self):
        topics = self.config_manager.get_topic_history()
        if not topics: topics = ['home/livingroom/light', 'office/desk/sensor']
        self.topic_combobox['values'] = topics
        if topics and not self.topic_combobox.get(): self.topic_combobox.set(topics[0])



    def _show_help(self):
        """Show a detailed, modal help dialog for the application."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - MQTT Publisher v1.4.15")
        help_window.minsize(600, 500)
        help_window.resizable(False, False)

        # --- Make the window modal ---
        help_window.transient(self.root)  # Keep it on top of the main window
        help_window.grab_set()           # Direct all events to this window
        help_window.focus_set()          # Set focus to the help window

        # Main container frame
        main_frame = ttk.Frame(help_window, padding=15)
        main_frame.pack(fill="both", expand=True)

        # --- Content Sections ---
        
        # Overview Section
        overview_frame = ttk.LabelFrame(main_frame, text=" Overview ", padding=10)
        overview_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(
            overview_frame,
            text="This application is a generic MQTT client that allows you to publish messages to an MQTT broker using flexible, file-based templates.",
            wraplength=550,
            justify="left"
        ).pack(fill="x")

        # Getting Started Section
        start_frame = ttk.LabelFrame(main_frame, text=" Getting Started ", padding=10)
        start_frame.pack(fill="x", pady=(0, 10))
        
        steps = [
            "1.  Enter your MQTT broker details (Broker, Port, etc.) and click 'Connect'.",
            "2.  Choose your payload type:",
            "    •  JSON Templates: Select a template and fill in the fields",
            "    •  String Payload: Type your message directly in the text area",
            "3.  For JSON templates: Fill in the values for the 'Template Fields' that appear.",
            "4.  For JSON templates: The 'Payload Preview' will update in real-time.",
            "5.  Enter a 'Topic' and click 'Publish Message' to send the payload."
        ]
        for step in steps:
            ttk.Label(start_frame, text=step, wraplength=550, justify="left").pack(anchor="w", pady=2)

        # Payload Modes Section
        modes_frame = ttk.LabelFrame(main_frame, text=" Payload Modes ", padding=10)
        modes_frame.pack(fill="x", pady=(0, 10))
        
        modes_info = (
            "The application supports two payload modes:\n\n"
            "JSON Templates (Tab 1):\n"
            "•  Use structured YAML templates for complex JSON messages\n"
            "•  Dynamic field validation and real-time preview\n"
            "•  Ideal for structured data and API integrations\n\n"
            "String Payload (Tab 2):\n"
            "•  Simple text input for basic messages\n"
            "•  No template required - just type your message\n"
            "•  Perfect for simple commands or text notifications"
        )
        ttk.Label(modes_frame, text=modes_info, wraplength=550, justify="left").pack(anchor="w", pady=2)

        # Template Management Section
        template_frame = ttk.LabelFrame(main_frame, text=" Template Management ", padding=10)
        template_frame.pack(fill="x", pady=(0, 10))
        
        template_info = (
            "Templates are powerful YAML (.yaml) files stored in the 'payload_templates' directory.\n\n"
            "•  Click '+' to create a new template file.\n"
            "•  Click '✎' to open the selected template in your default text editor.\n"
            "•  Click '⟳' to refresh the list after creating or editing templates."
        )
        ttk.Label(template_frame, text=template_info, wraplength=550, justify="left").pack(anchor="w", pady=2)

        # Automatic Saving Section
        saving_frame = ttk.LabelFrame(main_frame, text=" Automatic Saving ", padding=10)
        saving_frame.pack(fill="x", pady=(0, 10))
        
        saving_info = (
            "The following settings are automatically saved when you close the application:\n\n"
            "•  MQTT broker connection details (broker, port, username)\n"
            "•  Window position and size\n"
            "•  Message topic history\n"
            "•  Pane geometry (payload preview width, main pane height)\n"
            "•  All configuration settings"
        )
        ttk.Label(saving_frame, text=saving_info, wraplength=550, justify="left").pack(anchor="w", pady=2)

        # --- Bottom Buttons ---
        button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        button_frame.pack(fill="x", side="bottom")
        
        # Detailed Help button on the left
        detailed_help_button = ttk.Button(
            button_frame,
            text="Detailed Template Help",
            command=lambda: self._show_detailed_help(help_window)
        )
        detailed_help_button.pack(side="left")
        
        # Close button on the right
        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=help_window.destroy
        )
        close_button.pack(side="right")

        # --- Finalize Window ---
        
        # Bind Escape key to close the window
        help_window.bind('<Escape>', lambda e: help_window.destroy())
        
        # Center the window on the parent
        help_window.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        
        win_width = help_window.winfo_width()
        win_height = help_window.winfo_height()
        
        x = parent_x + (parent_width // 2) - (win_width // 2)
        y = parent_y + (parent_height // 2) - (win_height // 2)
        
        help_window.geometry(f'+{x}+{y}')

        # Wait for the window to be closed before returning
        self.root.wait_window(help_window)   
    
    def _show_detailed_help(self, parent_window=None):
        """Show comprehensive detailed help dialog for template system."""
        detailed_help_window = tk.Toplevel(self.root)
        detailed_help_window.title("Detailed Template Help - MQTT Publisher v1.4.15")
        detailed_help_window.minsize(800, 700)
        detailed_help_window.resizable(True, True)

        # --- Make the window modal ---
        detailed_help_window.transient(self.root)
        detailed_help_window.grab_set()
        detailed_help_window.focus_set()

        # Main container with scrollable content
        main_container = ttk.Frame(detailed_help_window, padding=10)
        main_container.pack(fill="both", expand=True)

        # Create scrollable frame
        canvas = tk.Canvas(main_container, bg='white')
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # --- Content Sections ---

        # Template System Overview
        overview_frame = ttk.LabelFrame(scrollable_frame, text=" Template System Overview ", padding=15)
        overview_frame.pack(fill="x", pady=(0, 15))
        
        overview_text = (
            "The MQTT Publisher uses a powerful YAML-based template system that allows you to create "
            "structured, reusable message payloads. Templates are stored as .yaml files in the "
            "'payload_templates' directory and define both the message structure and the input fields "
            "presented to users.\n\n"
            "Each template consists of two main sections:\n"
            "•  template: The actual message structure with variable placeholders\n"
            "•  fields: Definitions of input fields with validation rules"
        )
        ttk.Label(overview_frame, text=overview_text, wraplength=750, justify="left").pack(fill="x")

        # Template Structure Section
        structure_frame = ttk.LabelFrame(scrollable_frame, text=" Template File Structure ", padding=15)
        structure_frame.pack(fill="x", pady=(0, 15))
        
        structure_text = (
            "Every template file must contain these two main sections:\n\n"
            "1. TEMPLATE SECTION:\n"
            "   Defines the actual message payload structure using variable placeholders.\n"
            "   Variables are enclosed in curly braces: {variable_name} or {{variable_name}}\n\n"
            "2. FIELDS SECTION:\n"
            "   Defines the input fields that users will see and fill in.\n"
            "   Each field can have various properties for validation and user experience."
        )
        ttk.Label(structure_frame, text=structure_text, wraplength=750, justify="left").pack(fill="x")

        # Template Section Details
        template_section_frame = ttk.LabelFrame(scrollable_frame, text=" Template Section Details ", padding=15)
        template_section_frame.pack(fill="x", pady=(0, 15))
        
        template_section_text = (
            "The 'template' section defines your message payload structure:\n\n"
            "•  Use YAML's literal block scalar (|) for multi-line JSON\n"
            "•  Variables are referenced with {variable_name} or {{variable_name}}\n"
            "•  Special variables 'timestamp' and 'sender' are automatically provided\n"
            "•  The template is rendered as JSON when published\n\n"
            "EXAMPLE:\n"
            "template: |\n"
            "  {\n"
            "    \"device_id\": \"{device_id}\",\n"
            "    \"command\": \"{command}\",\n"
            "    \"value\": {value},\n"
            "    \"timestamp\": \"{timestamp}\",\n"
            "    \"sender\": \"{sender}\"\n"
            "  }"
        )
        ttk.Label(template_section_frame, text=template_section_text, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x")

        # Field Properties Section
        field_props_frame = ttk.LabelFrame(scrollable_frame, text=" Field Properties Reference ", padding=15)
        field_props_frame.pack(fill="x", pady=(0, 15))
        
        field_props_text = (
            "Each field in the 'fields' section can have these properties:\n\n"
            "REQUIRED PROPERTIES:\n"
            "•  name: Variable name used in the template (must match template variables)\n"
            "•  prompt: Label displayed next to the input field\n\n"
            "OPTIONAL PROPERTIES:\n"
            "•  help: Tooltip text shown when hovering over the field\n"
            "•  default: Default value for the field\n"
            "•  required: Whether the field must be filled (true/false)\n"
            "•  choices: List of predefined options for dropdown fields\n"
            "•  range: Dictionary with 'min' and 'max' for integer validation\n"
            "•  depends_on: Controls when the field is visible (dynamic fields)\n\n"
            "FIELD TYPES (determined by properties):\n"
            "•  Dropdown: Has 'choices' property\n"
            "•  Range-constrained: Has 'range' property\n"
            "•  Dynamic: Has 'depends_on' property\n"
            "•  Text entry: No special properties"
        )
        ttk.Label(field_props_frame, text=field_props_text, wraplength=750, justify="left").pack(fill="x")

        # Field Type Examples
        field_types_frame = ttk.LabelFrame(scrollable_frame, text=" Field Type Examples ", padding=15)
        field_types_frame.pack(fill="x", pady=(0, 15))
        
        # Dropdown field example
        dropdown_example = (
            "DROPDOWN FIELD (with choices):\n"
            "- name: command\n"
            "  prompt: \"Command\"\n"
            "  help: \"Select the action to perform\"\n"
            "  choices: [\"on\", \"off\", \"toggle\", \"status\"]\n"
            "  default: \"on\"\n"
            "  required: true"
        )
        ttk.Label(field_types_frame, text=dropdown_example, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x", pady=(0, 10))
        
        # Range field example
        range_example = (
            "RANGE-CONSTRAINED FIELD (with range):\n"
            "- name: brightness\n"
            "  prompt: \"Brightness Level\"\n"
            "  help: \"Brightness from 0 to 100\"\n"
            "  default: 50\n"
            "  range:\n"
            "    min: 0\n"
            "    max: 100\n"
            "  required: true"
        )
        ttk.Label(field_types_frame, text=range_example, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x", pady=(0, 10))
        
        # Text field example
        text_example = (
            "TEXT ENTRY FIELD (no constraints):\n"
            "- name: device_id\n"
            "  prompt: \"Device ID\"\n"
            "  help: \"Enter the target device identifier\"\n"
            "  default: \"device-001\"\n"
            "  required: true"
        )
        ttk.Label(field_types_frame, text=text_example, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x", pady=(0, 10))
        
        # Dynamic field example
        dynamic_example = (
            "DYNAMIC FIELD (with depends_on):\n"
            "- name: flash_rate\n"
            "  prompt: \"Flash Rate (Hz)\"\n"
            "  help: \"How fast the light flashes\"\n"
            "  default: 2\n"
            "  range:\n"
            "    min: 1\n"
            "    max: 10\n"
            "  required: true\n"
            "  depends_on: \"action:flash\""
        )
        ttk.Label(field_types_frame, text=dynamic_example, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x")

        # Dynamic Fields Section
        dynamic_fields_frame = ttk.LabelFrame(scrollable_frame, text=" Dynamic Fields (Dependencies) ", padding=15)
        dynamic_fields_frame.pack(fill="x", pady=(0, 15))
        
        dynamic_fields_text = (
            "Dynamic fields allow you to show or hide fields based on the values of other fields. "
            "This creates more intuitive forms where only relevant fields are displayed.\n\n"
            "DEPENDENCY SYNTAX:\n"
            "•  Format: \"parent_field:value1,value2,value3\"\n"
            "•  The field is visible when the parent field has ANY of the specified values\n"
            "•  Multiple values are separated by commas (OR logic)\n\n"
            "EXAMPLES:\n"
            "•  depends_on: \"action:flash\" - Show only when action is \"flash\"\n"
            "•  depends_on: \"action:flash,fade\" - Show when action is \"flash\" OR \"fade\"\n"
            "•  depends_on: \"mode:advanced,expert\" - Show when mode is \"advanced\" OR \"expert\"\n\n"
            "BEST PRACTICES:\n"
            "•  Use dynamic fields to reduce form complexity\n"
            "•  Group related fields that depend on the same parent\n"
            "•  Provide clear help text for dynamic fields\n"
            "•  Set sensible default values for hidden fields\n"
            "•  Test all dependency combinations thoroughly"
        )
        ttk.Label(dynamic_fields_frame, text=dynamic_fields_text, wraplength=750, justify="left").pack(fill="x")

        # Complete Template Example
        complete_example_frame = ttk.LabelFrame(scrollable_frame, text=" Complete Template Example ", padding=15)
        complete_example_frame.pack(fill="x", pady=(0, 15))
        
        complete_example = (
            "# Light Control Template with Dynamic Fields\n"
            "template: |\n"
            "  {\n"
            "    \"device_id\": \"{device_id}\",\n"
            "    \"action\": \"{action}\",\n"
            "    \"brightness\": {brightness},\n"
            "    \"color\": \"{color}\",\n"
            "    \"flash_rate\": {flash_rate},\n"
            "    \"fade_duration\": {fade_duration},\n"
            "    \"timestamp\": \"{timestamp}\",\n"
            "    \"sender\": \"{sender}\"\n"
            "  }\n\n"
            "fields:\n"
            "  - name: device_id\n"
            "    prompt: \"Device ID\"\n"
            "    help: \"Target device identifier\"\n"
            "    default: \"living_room_light\"\n"
            "    required: true\n\n"
            "  - name: action\n"
            "    prompt: \"Action\"\n"
            "    help: \"Light action to perform\"\n"
            "    choices: [\"on\", \"off\", \"toggle\", \"flash\", \"fade\"]\n"
            "    default: \"on\"\n"
            "    required: true\n\n"
            "  - name: brightness\n"
            "    prompt: \"Brightness\"\n"
            "    help: \"Brightness level (0-100)\"\n"
            "    default: 75\n"
            "    range:\n"
            "      min: 0\n"
            "      max: 100\n"
            "    required: false\n\n"
            "  - name: color\n"
            "    prompt: \"Color\"\n"
            "    help: \"Light color (hex code or name)\"\n"
            "    default: \"#FFFFFF\"\n"
            "    required: false\n\n"
            "  - name: flash_rate\n"
            "    prompt: \"Flash Rate (Hz)\"\n"
            "    help: \"How fast the light flashes\"\n"
            "    default: 2\n"
            "    range:\n"
            "      min: 1\n"
            "      max: 10\n"
            "    required: true\n"
            "    depends_on: \"action:flash\"\n\n"
            "  - name: fade_duration\n"
            "    prompt: \"Fade Duration (seconds)\"\n"
            "    help: \"How long the fade should take\"\n"
            "    default: 5\n"
            "    range:\n"
            "      min: 1\n"
            "      max: 60\n"
            "    required: true\n"
            "    depends_on: \"action:fade\""
        )
        ttk.Label(complete_example_frame, text=complete_example, wraplength=750, justify="left", font=('Consolas', 9)).pack(fill="x")

        # Validation and Error Handling
        validation_frame = ttk.LabelFrame(scrollable_frame, text=" Validation and Error Handling ", padding=15)
        validation_frame.pack(fill="x", pady=(0, 15))
        
        validation_text = (
            "The template system includes automatic validation:\n\n"
            "DROPDOWN FIELDS:\n"
            "•  Users can only select from predefined choices\n"
            "•  Prevents typos and ensures data consistency\n\n"
            "RANGE-CONSTRAINED FIELDS:\n"
            "•  Only accepts integer values within the specified range\n"
            "•  Shows warning messages for invalid values\n"
            "•  Automatically resets to default value if invalid\n"
            "•  Range information is displayed in tooltips\n\n"
            "DYNAMIC FIELDS:\n"
            "•  Automatically show/hide based on parent field values\n"
            "•  Hidden fields retain their values when not visible\n"
            "•  Dependencies are checked in real-time as users change values\n"
            "•  Smooth transitions with no flickering\n\n"
            "TEXT FIELDS:\n"
            "•  Accept any text input\n"
            "•  No validation constraints\n\n"
            "ERROR HANDLING:\n"
            "•  Validation errors appear in the status log\n"
            "•  Invalid values are automatically corrected\n"
            "•  Template loading errors are clearly reported\n"
            "•  Dependency errors are handled gracefully"
        )
        ttk.Label(validation_frame, text=validation_text, wraplength=750, justify="left").pack(fill="x")

        # Best Practices
        best_practices_frame = ttk.LabelFrame(scrollable_frame, text=" Best Practices ", padding=15)
        best_practices_frame.pack(fill="x", pady=(0, 15))
        
        best_practices_text = (
            "TEMPLATE DESIGN:\n"
            "•  Use descriptive field names and prompts\n"
            "•  Provide helpful tooltips for complex fields\n"
            "•  Set sensible default values\n"
            "•  Use dropdowns for limited, known options\n"
            "•  Use range constraints for numeric values\n"
            "•  Use dynamic fields to reduce form complexity\n\n"
            "DYNAMIC FIELD DESIGN:\n"
            "•  Group related fields that depend on the same parent\n"
            "•  Use clear, logical parent field names\n"
            "•  Test all dependency combinations thoroughly\n"
            "•  Provide fallback values for hidden fields\n"
            "•  Keep dependency chains simple (avoid deep nesting)\n\n"
            "FILE ORGANIZATION:\n"
            "•  Use descriptive filenames (e.g., 'light_control.yaml')\n"
            "•  Include comments in your YAML files\n"
            "•  Group related templates in subdirectories if needed\n\n"
            "VALIDATION:\n"
            "•  Always test templates after creation\n"
            "•  Use range constraints for numeric fields\n"
            "•  Provide clear error messages in help text\n"
            "•  Set appropriate default values\n"
            "•  Test dynamic field behavior with all parent values\n\n"
            "MAINTENANCE:\n"
            "•  Keep templates simple and focused\n"
            "•  Document complex templates with comments\n"
            "•  Regularly review and update templates\n"
            "•  Use version control for template files"
        )
        ttk.Label(best_practices_frame, text=best_practices_text, wraplength=750, justify="left").pack(fill="x")

        # Troubleshooting
        troubleshooting_frame = ttk.LabelFrame(scrollable_frame, text=" Troubleshooting ", padding=15)
        troubleshooting_frame.pack(fill="x", pady=(0, 15))
        
        troubleshooting_text = (
            "COMMON ISSUES AND SOLUTIONS:\n\n"
            "TEMPLATE NOT LOADING:\n"
            "•  Check YAML syntax (use online YAML validator)\n"
            "•  Ensure file is saved with .yaml or .yml extension\n"
            "•  Verify file is in the 'payload_templates' directory\n"
            "•  Click the refresh button (⟳) to reload templates\n\n"
            "FIELDS NOT APPEARING:\n"
            "•  Check that field names match template variables\n"
            "•  Verify 'fields' section is properly formatted\n"
            "•  Ensure proper YAML indentation (use spaces, not tabs)\n"
            "•  For dynamic fields: check parent field value matches dependency\n\n"
            "DYNAMIC FIELDS NOT SHOWING:\n"
            "•  Verify 'depends_on' syntax: 'parent_field:value1,value2'\n"
            "•  Check that parent field name matches exactly\n"
            "•  Ensure parent field value matches one of the dependency values\n"
            "•  Test by changing parent field value manually\n\n"
            "VALIDATION ERRORS:\n"
            "•  Check range constraints are properly formatted\n"
            "•  Verify default values are within specified ranges\n"
            "•  Ensure choices lists are properly formatted\n\n"
            "PREVIEW NOT UPDATING:\n"
            "•  Check template syntax for variable references\n"
            "•  Verify all required fields have values\n"
            "•  Look for JSON syntax errors in the template\n"
            "•  For dynamic fields: ensure hidden fields have valid values"
        )
        ttk.Label(troubleshooting_frame, text=troubleshooting_text, wraplength=750, justify="left").pack(fill="x")

        # --- Bottom Close Button ---
        button_frame = ttk.Frame(scrollable_frame, padding=(0, 15, 0, 0))
        button_frame.pack(fill="x", side="bottom")
        
        close_button = ttk.Button(
            button_frame,
            text="Close",
            command=detailed_help_window.destroy
        )
        close_button.pack(side="right")

        # --- Finalize Window ---
        detailed_help_window.bind('<Escape>', lambda e: detailed_help_window.destroy())
        
        # Center the window
        detailed_help_window.update_idletasks()
        parent_x = self.root.winfo_x()
        parent_y = self.root.winfo_y()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        
        win_width = detailed_help_window.winfo_width()
        win_height = detailed_help_window.winfo_height()
        
        x = parent_x + (parent_width // 2) - (win_width // 2)
        y = parent_y + (parent_height // 2) - (win_height // 2)
        
        detailed_help_window.geometry(f'+{x}+{y}')

        # Clean up mousewheel binding when window closes
        def cleanup():
            canvas.unbind_all("<MouseWheel>")
            detailed_help_window.destroy()
        
        detailed_help_window.protocol("WM_DELETE_WINDOW", cleanup)
    
    def _update_publish_button_state(self):
        """Update publish button state based on connection and payload availability."""
        topic_valid = bool(self.topic_combobox.get().strip())
        
        if self.current_payload_mode == "json":
            # For JSON mode, need template selected
            template_valid = hasattr(self, 'current_template') and self.current_template is not None
            enable = self._mqtt_connected and topic_valid and template_valid
        elif self.current_payload_mode == "string":
            # For string mode, need non-empty string payload
            payload = self.string_payload_text.get("1.0", "end-1c").strip()
            string_valid = bool(payload.strip())
            enable = self._mqtt_connected and topic_valid and string_valid
        else:
            enable = False
            
        if hasattr(self, 'publish_button'):
            self.publish_button.config(state="normal" if enable else "disabled")

    def _restore_pane_geometry(self):
        """Restore the saved pane geometry after the window is idle."""
        try:
            # Restore horizontal pane width (preview pane)
            if hasattr(self, 'paned_window') and self.paned_window.winfo_exists():
                self.paned_window.sashpos(0, self.preview_pane_width)
            
            # Restore main vertical pane height (payload vs status split)
            if hasattr(self, 'main_paned') and self.main_paned.winfo_exists():
                self.main_paned.sashpos(0, self.main_pane_height)
        except tk.TclError:
            pass

    def _on_closing(self):
        """Get final geometry and save all settings on exit."""
        try:
            width = self.root.winfo_width(); height = self.root.winfo_height(); x = self.root.winfo_x(); y = self.root.winfo_y()
            
            # Save horizontal pane width (preview pane)
            preview_width = self.paned_window.sashpos(0) if hasattr(self, 'paned_window') else self.preview_pane_width
            
            # Save main vertical pane height (payload vs status split)
            main_pane_height = self.main_paned.sashpos(0) if hasattr(self, 'main_paned') else self.main_pane_height
            
            final_geometry = {
                'width': width, 
                'height': height, 
                'x': x, 'y': y, 
                'preview_width': preview_width,
                'main_pane_height': main_pane_height
            }
            self.config_manager.set_window_geometry(final_geometry)
        except tk.TclError:
            pass
        self.config_manager.save()
        if hasattr(self, 'mqtt_client') and self.mqtt_client.is_connected():
            self.mqtt_client.disconnect()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MqttPublisherApp(root)
    root.mainloop()