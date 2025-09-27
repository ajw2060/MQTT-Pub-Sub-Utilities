import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import sys
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

# Import our new components
import mqtt_client
import config_manager

# Check for the yaml library and provide a helpful error if it's missing.
try:
    import yaml
except ImportError:
    # Use a simple Tkinter window for the error if the main app can't start.
    error_root = tk.Tk()
    error_root.withdraw() # Hide the main window
    messagebox.showerror(
        "Missing Library",
        "FATAL ERROR: The 'PyYAML' library is not installed.\n\nPlease install it by running this command in your terminal:\n\npip install pyyaml"
    )
    sys.exit(1)

# --- Configuration ---

class MqttSubscriberApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Generic MQTT Subscriber")

        self.config_manager = config_manager.ConfigManager('mqtt_subscriber_config.json')
        self.config_manager.load()

        geometry = self.config_manager.get_window_geometry()
        self.root.geometry(f"{geometry.get('width', 750)}x{geometry.get('height', 650)}+{geometry.get('x', 100)}+{geometry.get('y', 100)}")

        self.mqtt_client = mqtt_client.MqttClient()
        self.mqtt_client.set_callbacks(on_connect=self._on_mqtt_connect, on_disconnect=self._on_mqtt_disconnect, 
                                      on_message=self._on_mqtt_message, on_subscribe=self._on_mqtt_subscribe)
        
        self.subscribed_topics = set()
        self._mqtt_connected = False
        
        # Setup overall UI styling first
        self._setup_ui()
        
        # Create GUI Frames
        self._create_config_frame()
        self._create_subscription_frame()
        self._create_messages_frame()
        self._create_bottom_button_frame()

        # Load connection settings
        self._load_connection_settings()

        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui(self):
        """Setup the overall UI styling to match publisher."""
        style = ttk.Style(self.root)
        style.theme_use('clam')
        
        bg_color = '#f0f0f0'
        style.configure('TFrame', background=bg_color)
        style.configure('TLabelframe', background=bg_color, borderwidth=2, relief='groove', labelmargins=(10, 2, 10, 2))
        style.configure('TLabelframe.Label', font=('Helvetica', 10, 'bold'), background=bg_color, foreground='#2c3e50')
        style.configure('TLabel', background=bg_color, font=('Helvetica', 9))
        style.configure('Bold.TLabel', font=('Helvetica', 9, 'bold'), background=bg_color)
        
        self.root.configure(bg=bg_color)
        
        # Create main container with grid layout like publisher
        self.main_container = ttk.Frame(self.root, padding=(5, 5, 5, 0))
        self.main_container.pack(fill='both', expand=True)
        self.main_container.columnconfigure(0, weight=1)

    def _create_config_frame(self):
        self.config_frame = tk.LabelFrame(self.main_container, text=" Setup MQTT Broker Connection ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        self.config_frame.grid(row=0, column=0, sticky='ew', pady=(0, 5))
        
        style = ttk.Style()
        style.map('Connect.TButton', foreground=[('!disabled', 'white')], background=[('active', '#45a049'), ('!disabled', '#4CAF50')])
        style.map('Disconnect.TButton', foreground=[('!disabled', 'white')], background=[('active', '#d32f2f'), ('!disabled', '#f44336')])
        style.map('Subscribe.TButton', foreground=[('!disabled', 'white')], background=[('active', '#218838'), ('!disabled', '#28a745')])
        style.map('Unsubscribe.TButton', foreground=[('!disabled', 'white')], background=[('active', '#c82333'), ('!disabled', '#dc3545')])
        style.configure('Error.TLabel', foreground='red')
        
        label_padx = (8,2); entry_padx = (60,8); entry_width = 32
        
        ttk.Label(self.config_frame, text="Broker", font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", padx=label_padx, pady=2)
        self.broker_entry = ttk.Entry(self.config_frame, width=entry_width, font=('Helvetica', 9))
        self.broker_entry.grid(row=0, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Port", font=('Helvetica', 9, 'bold')).grid(row=1, column=0, sticky="w", padx=label_padx, pady=2)
        self.port_entry = ttk.Entry(self.config_frame, width=10, font=('Helvetica', 9))
        self.port_entry.grid(row=1, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Username", font=('Helvetica', 9, 'bold')).grid(row=2, column=0, sticky="w", padx=label_padx, pady=2)
        self.username_entry = ttk.Entry(self.config_frame, width=20, font=('Helvetica', 9))
        self.username_entry.grid(row=2, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Password", font=('Helvetica', 9, 'bold')).grid(row=3, column=0, sticky="w", padx=label_padx, pady=2)
        self.password_entry = ttk.Entry(self.config_frame, show="*", width=20, font=('Helvetica', 9))
        self.password_entry.grid(row=3, column=1, sticky="w", padx=entry_padx, pady=2)

        ttk.Label(self.config_frame, text="Client ID", font=('Helvetica', 9, 'bold')).grid(row=4, column=0, sticky="w", padx=label_padx, pady=2)
        self.client_id_var = tk.StringVar(value="MQTT_Subscriber_GUI")
        self.client_id_entry = ttk.Entry(self.config_frame, textvariable=self.client_id_var, width=entry_width, font=('Helvetica', 9), state="readonly")
        self.client_id_entry.grid(row=4, column=1, sticky="w", padx=entry_padx, pady=2)
        
        self.config_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(self.config_frame)
        button_frame.grid(row=1, column=3, rowspan=5, sticky="nsw", padx=(18,5), pady=(2,2))
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self._connect_mqtt, style='Connect.TButton')
        self.connect_button.pack(fill="x", padx=2, pady=(2,6), ipadx=10)
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self._disconnect_mqtt, state="disabled", style='Disconnect.TButton')
        self.disconnect_button.pack(fill="x", padx=2, pady=(2,2), ipadx=10)

        self.connection_status_var = tk.StringVar(value="Disconnected")
        self.connection_status_label = ttk.Label(self.config_frame, textvariable=self.connection_status_var, style='Error.TLabel')
        self.connection_status_label.grid(row=6, column=0, columnspan=4, sticky="w", padx=5, pady=(10, 2))

    def _connect_mqtt(self):
        broker = self.broker_entry.get().strip()
        port_str = self.port_entry.get().strip()
        if not broker or not port_str:
            messagebox.showerror("Error", "Broker and Port cannot be empty.")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Port must be an integer.")
            return
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        self.config_manager.set_connection_settings(broker, port_str, username)
        self.config_manager.save()
        try:
            self._log_message(f"Connecting to {broker}:{port}...")
            self.mqtt_client.connect(broker, port, username, password)
        except Exception as e:
            self._log_message(f"Connection failed: {e}", "error")
            messagebox.showerror("Connection Failed", f"Could not connect to broker.\nError: {e}")

    def _on_mqtt_connect(self, reason_code):
        mqtt_codes = {0: "Connection successful", 1: "Incorrect protocol version", 2: "Client identifier rejected", 3: "Server unavailable", 4: "Bad username or password", 5: "Not authorized"}
        if reason_code == 0:
            self._mqtt_connected = True
            self._log_message("Connected to MQTT Broker successfully!", "success")
            self.connection_status_var.set("Connected")
            self.connection_status_label.config(foreground="#28a745")
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="normal")
            self.subscribe_button.config(state="normal")
        else:
            self._mqtt_connected = False
            self.connection_status_var.set("Disconnected")
            self.connection_status_label.config(foreground="#dc3545")
            messagebox.showerror("Connection Failed", f"Could not connect to MQTT broker.\n\nError: {mqtt_codes.get(reason_code, f'Unknown error (code {reason_code})')}")

    def _disconnect_mqtt(self):
        self.mqtt_client.disconnect()

    def _on_mqtt_disconnect(self, reason_code):
        self._mqtt_connected = False
        self._log_message(f"Disconnected from MQTT Broker", "error")
        self.connection_status_var.set("Disconnected")
        self.connection_status_label.config(foreground="#dc3545")
        self.connect_button.config(state="normal")
        self.disconnect_button.config(state="disabled")
        self.subscribe_button.config(state="disabled")
        self.subscribed_topics.clear()
        self.topics_listbox.delete(0, tk.END)
        
    def _create_subscription_frame(self):
        sub_frame = tk.LabelFrame(self.main_container, text=" Subscribe to Topic ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        sub_frame.grid(row=1, column=0, sticky='ew', pady=(0, 5))


        ttk.Label(sub_frame, text="Topic:", font=('Helvetica', 9, 'bold')).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.topic_entry = ttk.Combobox(sub_frame, width=50, font=('Helvetica', 9))
        self.topic_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.topic_entry.bind('<Return>', lambda e: self._subscribe_topic())
        
        ttk.Label(sub_frame, text="QoS:", font=('Helvetica', 9, 'bold')).grid(row=0, column=2, sticky="w", padx=5, pady=2)
        self.qos_combobox = ttk.Combobox(sub_frame, width=5, values=["0", "1", "2"], state="readonly", font=('Helvetica', 9))
        self.qos_combobox.set("0")
        self.qos_combobox.grid(row=0, column=3, padx=5)
        
        # Listbox for subscribed topics
        ttk.Label(sub_frame, text="Subscribed Topics:", font=('Helvetica', 9, 'bold')).grid(row=1, column=0, columnspan=5, sticky="w", pady=(10, 2))
        self.topics_listbox = tk.Listbox(sub_frame, height=5, font=('Helvetica', 9))
        self.topics_listbox.grid(row=2, column=0, columnspan=4, sticky="nsew", pady=5)
        
        # Scrollbar for topics listbox
        scrollbar = ttk.Scrollbar(sub_frame, orient="vertical", command=self.topics_listbox.yview)
        scrollbar.grid(row=2, column=4, sticky="ns")
        self.topics_listbox.config(yscrollcommand=scrollbar.set)
        
        # Button frame for subscribe and unsubscribe buttons
        button_frame = tk.Frame(sub_frame)
        button_frame.grid(row=3, column=0, columnspan=5, pady=5, sticky="w")
        
        self.subscribe_button = ttk.Button(button_frame, text="Subscribe", command=self._subscribe_topic, state="disabled", style='Subscribe.TButton')
        self.subscribe_button.pack(side="left", padx=(0, 5))
        
        # Unsubscribe button
        self.unsubscribe_button = ttk.Button(button_frame, text="Unsubscribe", 
                                           command=self._unsubscribe_topic, 
                                           state="disabled",
                                           style='Unsubscribe.TButton')
        self.unsubscribe_button.pack(side="left", padx=5)
        
        sub_frame.columnconfigure(1, weight=1)
        
    def _subscribe_topic(self):
        if not self._mqtt_connected:
            messagebox.showwarning("Not Connected", "Not connected to MQTT broker.")
            return
            
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning("Error", "Topic cannot be empty.")
            return
            
        # Add to topic history using config manager
        self.config_manager.add_topic_to_history(topic)
        self.config_manager.save()
        
        # Update the combobox values
        self.topic_entry['values'] = self.config_manager.get_topic_history()
            
        if topic in self.subscribed_topics:
            messagebox.showinfo("Info", f"Already subscribed to: {topic}")
            return
            
        try:
            qos = int(self.qos_combobox.get())
            if self.mqtt_client.subscribe(topic, qos):
                self.subscribed_topics.add(topic)
                self.topics_listbox.insert(tk.END, topic)
                self.topic_entry.delete(0, tk.END)
                self._log_message(f"Subscribed to: {topic} (QoS: {qos})", "success")
                self.unsubscribe_button.config(state="normal")
            else:
                self._log_message(f"Failed to subscribe to: {topic}", "error")
        except Exception as e:
            error_msg = f"Error subscribing to topic: {e}"
            self._log_message(error_msg, "error")
            messagebox.showerror("Subscription Error", error_msg)
            
    def _unsubscribe_topic(self, topic=None, update_ui=True):
        if not topic:
            # Get selected topic from listbox
            selection = self.topics_listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a topic to unsubscribe from.")
                return
                
            topic = self.topics_listbox.get(selection[0])
        
        if not self._mqtt_connected:
            messagebox.showwarning("Not Connected", "Not connected to MQTT broker.")
            return
            
        try:
            if self.mqtt_client.unsubscribe(topic):
                if topic in self.subscribed_topics:
                    self.subscribed_topics.remove(topic)
                    
                if update_ui:
                    # Find and remove the topic from the listbox
                    items = self.topics_listbox.get(0, tk.END)
                    index = items.index(topic) if topic in items else -1
                    if index >= 0:
                        self.topics_listbox.delete(index)
                    self._log_message(f"Unsubscribed from: {topic}", "success")
                    
                    # Disable unsubscribe button if no more topics
                    if not self.subscribed_topics:
                        self.unsubscribe_button.config(state="disabled")
            else:
                self._log_message(f"Failed to unsubscribe from: {topic}", "error")
                    
        except Exception as e:
            error_msg = f"Error unsubscribing from topic: {e}"
            self._log_message(error_msg, "error")
            messagebox.showerror("Unsubscribe Error", error_msg)
            
    def _on_mqtt_message(self, msg):
        try:
            # Get current timestamp
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # Try to parse as JSON for pretty printing
            try:
                payload = json.loads(msg.payload.decode())
                formatted_payload = json.dumps(payload, indent=2)
            except:
                formatted_payload = msg.payload.decode()
                
            # Create the log message with timestamp, topic, and payload
            log_msg = f"[{timestamp}] {msg.topic}\n{formatted_payload}"
            
            # Schedule the update on the main thread
            self.root.after(0, self._log_message, log_msg)
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            self.root.after(0, self._log_message, error_msg)

    def _on_mqtt_subscribe(self, mid, reason_codes):
        # This callback is called when the broker responds to a subscribe request
        pass  # We handle the subscription UI updates in _subscribe_topic
        
            
    def _create_messages_frame(self):
        msg_frame = tk.LabelFrame(self.main_container, text=" Status Log ", font=('Helvetica', 10, 'bold'), labelanchor='nw', padx=15, pady=15, bd=2, relief='groove')
        msg_frame.grid(row=2, column=0, sticky='nsew', pady=(0, 5))
        
        # Configure row 2 to expand (main content area)
        self.main_container.grid_rowconfigure(2, weight=1)
        
        # Text widget for displaying messages
        self.messages_text = tk.Text(msg_frame, wrap="word", state="disabled", bg='white', fg='#212529', font=('Consolas', 9), padx=5, pady=5, relief='flat', highlightthickness=1, highlightbackground='#ced4da', highlightcolor='#80bdff')
        
        # Configure tags for different message types
        self.messages_text.tag_configure('info', foreground='#007bff')
        self.messages_text.tag_configure('success', foreground='#28a745')
        self.messages_text.tag_configure('warning', foreground='#ffc107')
        self.messages_text.tag_configure('error', foreground='#dc3545')
        
        scrollbar = ttk.Scrollbar(msg_frame, command=self.messages_text.yview)
        self.messages_text.config(yscrollcommand=scrollbar.set)
        
        self.messages_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add initial log message
        self._log_message("MQTT Subscriber started. Configure your connection and subscribe to topics.", "info")
        
    def _create_bottom_button_frame(self):
        """Create the bottom button frame with styled buttons matching publisher."""
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
            style='Help.TButton'
        )
        self.help_button.pack(side='left', padx=5)
        
        # Clear Log button beside Help button
        self.clear_button = ttk.Button(
            button_frame,
            text="Clear Log",
            command=self._clear_messages,
            style='Clear.TButton'
        )
        self.clear_button.pack(side='left', padx=5)
        
        # Close button on the right
        self.close_button = ttk.Button(
            button_frame,
            text="Close",
            command=self._on_closing,
            style='Close.TButton'
        )
        self.close_button.pack(side='right', padx=5)

        # Version label will be pushed to the right before the close button
        ttk.Label(
            button_frame,
            text="Version: 1.0.7",
            foreground='gray',
            font=('Helvetica', 8)
        ).pack(side='right', padx=(0, 20))

        # Bind F1 key to help
        self.root.bind('<F1>', lambda e: self._show_help())
        return button_container

    def _log_message(self, message, msg_type="info"):
        if not hasattr(self, 'messages_text'): return
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.messages_text.config(state="normal")
        self.messages_text.insert(tk.END, f"[{timestamp}] ", ("timestamp_tag",))
        self.messages_text.insert(tk.END, f"{message}\n", (msg_type,))
        self.messages_text.see(tk.END)
        self.messages_text.config(state="disabled")
        
    def _clear_messages(self):
        self.messages_text.config(state="normal")
        self.messages_text.delete(1.0, tk.END)
        self.messages_text.config(state="disabled")
        
    def _load_connection_settings(self):
        settings = self.config_manager.get_connection_settings()
        self.broker_entry.insert(0, settings.get('broker', ''))
        self.port_entry.insert(0, settings.get('port', '1883'))
        self.username_entry.insert(0, settings.get('username', ''))
        
        # Load topic history
        topics = self.config_manager.get_topic_history()
        if topics:
            self.topic_entry['values'] = topics
            
    def _on_closing(self):
        if self.mqtt_client and self.mqtt_client.is_connected():
            self._disconnect_mqtt()
        
        # Auto-save geometry and config on close
        try:
            self.root.update_idletasks()
            
            geometry = {
                'width': max(100, self.root.winfo_width()),
                'height': max(100, self.root.winfo_height()),
                'x': max(0, self.root.winfo_x()),
                'y': max(0, self.root.winfo_y())
            }
            
            self.config_manager.set_window_geometry(geometry)
            self.config_manager.save()
        except Exception as e:
            print(f"Error saving config on close: {e}")
            # Don't prevent closing if save fails
            
        self.root.destroy()

    def _show_help(self):
        """Show a help dialog for the subscriber application."""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help - MQTT Subscriber v1.0.7")
        help_window.minsize(600, 400)
        help_window.resizable(False, False)

        # Make the window modal
        help_window.transient(self.root)
        help_window.grab_set()
        help_window.focus_set()

        # Main container frame
        main_frame = ttk.Frame(help_window, padding=15)
        main_frame.pack(fill="both", expand=True)

        # Overview Section
        overview_frame = ttk.LabelFrame(main_frame, text=" Overview ", padding=10)
        overview_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(
            overview_frame,
            text="This application is an MQTT subscriber client that allows you to connect to an MQTT broker and subscribe to topics to receive messages.",
            wraplength=550,
            justify="left"
        ).pack(fill="x")

        # Getting Started Section
        start_frame = ttk.LabelFrame(main_frame, text=" Getting Started ", padding=10)
        start_frame.pack(fill="x", pady=(0, 10))
        
        steps = [
            "1.  Enter your MQTT broker details (Broker, Port, Username, Password) and click 'Connect'.",
            "2.  Once connected, enter a topic name in the 'Topic' field.",
            "3.  Select the desired QoS level (0, 1, or 2).",
            "4.  Click 'Subscribe' to start receiving messages from that topic.",
            "5.  Messages will appear in the 'Received Messages' area below.",
            "6.  Use 'Unsubscribe' to stop receiving messages from a selected topic.",
            "7.  Click 'Clear Messages' to clear the message display area."
        ]
        for step in steps:
            ttk.Label(start_frame, text=step, wraplength=550, justify="left").pack(anchor="w", pady=2)

        # Features Section
        features_frame = ttk.LabelFrame(main_frame, text=" Features ", padding=10)
        features_frame.pack(fill="x", pady=(0, 10))
        
        features_info = (
            "•  Connect to any MQTT broker with authentication support\n"
            "•  Subscribe to multiple topics simultaneously\n"
            "•  Automatic message formatting (JSON pretty-printing)\n"
            "•  Topic history for easy re-subscription\n"
            "•  Timestamped message display\n"
            "•  Configuration persistence\n"
            "•  Support for QoS levels 0, 1, and 2\n\n"
            "AUTOMATIC SAVING:\n"
            "The following settings are automatically saved when you close the application:\n"
            "•  MQTT broker connection details (broker, port, username)\n"
            "•  Window position and size\n"
            "•  Topic subscription history\n"
            "•  All configuration settings"
        )
        ttk.Label(features_frame, text=features_info, wraplength=550, justify="left").pack(fill="x")

        # Close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=help_window.destroy
        )
        close_button.pack(side="right", pady=(10, 0))

        # Bind Escape key to close
        help_window.bind('<Escape>', lambda e: help_window.destroy())

        # Center the window
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


if __name__ == "__main__":
    root = tk.Tk()
    app = MqttSubscriberApp(root)
    root.mainloop()
