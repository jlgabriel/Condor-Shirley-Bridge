#!/usr/bin/env python3

"""
Settings Dialog for Condor-Shirley-Bridge
Dialog for configuring application settings.

Part of the Condor-Shirley-Bridge project.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import logging
import os
import sys
from typing import Optional, Dict, Any, List

# Import from our project structure
# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from condor_shirley_bridge.core.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gui.settings_dialog')


class SettingsDialog:
    """
    Dialog for configuring application settings.
    
    Provides a UI for changing all settings in the application,
    organized by category using a notebook.
    """
    def __init__(self, parent, settings: Settings):
        """
        Initialize the settings dialog.
        
        Args:
            parent: Parent widget
            settings: Settings instance
        """
        self.parent = parent
        self.settings = settings
        self.result = False  # True if settings were changed and OK was clicked
        
        # Create the dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Set dialog size
        self.dialog.geometry("550x500")
        self.dialog.minsize(500, 400)
        
        # Center on parent
        if parent:
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            
            dialog_width = 550
            dialog_height = 500
            
            x = parent_x + (parent_width - dialog_width) // 2
            y = parent_y + (parent_height - dialog_height) // 2
            
            self.dialog.geometry(f"+{x}+{y}")
        
        # Make dialog modal
        self.dialog.focus_set()
        
        # Create widgets
        self._create_widgets()
        
        # Initialize values from settings
        self._load_settings()
        
        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Wait for dialog to close
        self.dialog.wait_window()
    
    def _create_widgets(self) -> None:
        """Create the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook for settings categories
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create settings tabs
        self._create_serial_tab()
        self._create_udp_tab()
        self._create_websocket_tab()
        self._create_logging_tab()
        self._create_ui_tab()
        
        # Button frame at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # OK and Cancel buttons
        self.ok_button = ttk.Button(button_frame, text="OK", command=self._on_ok)
        self.ok_button.pack(side=tk.RIGHT, padx=5)
        
        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # Apply button
        self.apply_button = ttk.Button(button_frame, text="Apply", command=self._on_apply)
        self.apply_button.pack(side=tk.RIGHT, padx=5)
    
    def _create_serial_tab(self) -> None:
        """Create the Serial settings tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Serial")
        
        # Enabled checkbox
        self.serial_enabled_var = tk.BooleanVar()
        self.serial_enabled = ttk.Checkbutton(
            frame,
            text="Enable Serial Port",
            variable=self.serial_enabled_var,
            command=self._update_serial_state
        )
        self.serial_enabled.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Port selection
        ttk.Label(frame, text="Port:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        port_frame = ttk.Frame(frame)
        port_frame.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        self.serial_port_var = tk.StringVar()
        self.serial_port = ttk.Combobox(
            port_frame,
            textvariable=self.serial_port_var,
            width=15
        )
        self.serial_port.pack(side=tk.LEFT)
        
        # Refresh button for ports
        refresh_button = ttk.Button(
            port_frame,
            text="Refresh",
            command=self._refresh_serial_ports
        )
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        # Baudrate
        ttk.Label(frame, text="Baudrate:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.serial_baudrate_var = tk.IntVar()
        baudrates = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        self.serial_baudrate = ttk.Combobox(
            frame,
            textvariable=self.serial_baudrate_var,
            values=baudrates,
            width=15
        )
        self.serial_baudrate.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Timeout
        ttk.Label(frame, text="Timeout (seconds):").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.serial_timeout_var = tk.DoubleVar()
        self.serial_timeout = ttk.Spinbox(
            frame,
            from_=0.1,
            to=10.0,
            increment=0.1,
            textvariable=self.serial_timeout_var,
            width=5
        )
        self.serial_timeout.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Data freshness threshold
        ttk.Label(frame, text="Data Freshness Threshold (seconds):").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.serial_freshness_var = tk.DoubleVar()
        self.serial_freshness = ttk.Spinbox(
            frame,
            from_=1.0,
            to=30.0,
            increment=1.0,
            textvariable=self.serial_freshness_var,
            width=5
        )
        self.serial_freshness.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Fill with available ports
        self._refresh_serial_ports()
    
    def _create_udp_tab(self) -> None:
        """Create the UDP settings tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="UDP")
        
        # Enabled checkbox
        self.udp_enabled_var = tk.BooleanVar()
        self.udp_enabled = ttk.Checkbutton(
            frame,
            text="Enable UDP Receiver",
            variable=self.udp_enabled_var,
            command=self._update_udp_state
        )
        self.udp_enabled.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Host
        ttk.Label(frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.udp_host_var = tk.StringVar()
        self.udp_host = ttk.Entry(
            frame,
            textvariable=self.udp_host_var,
            width=20
        )
        self.udp_host.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Port
        ttk.Label(frame, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.udp_port_var = tk.IntVar()
        self.udp_port = ttk.Spinbox(
            frame,
            from_=1024,
            to=65535,
            textvariable=self.udp_port_var,
            width=7
        )
        self.udp_port.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Buffer size
        ttk.Label(frame, text="Buffer Size:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.udp_buffer_var = tk.IntVar()
        self.udp_buffer = ttk.Spinbox(
            frame,
            from_=1024,
            to=131072,
            increment=1024,
            textvariable=self.udp_buffer_var,
            width=7
        )
        self.udp_buffer.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Data freshness threshold
        ttk.Label(frame, text="Data Freshness Threshold (seconds):").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.udp_freshness_var = tk.DoubleVar()
        self.udp_freshness = ttk.Spinbox(
            frame,
            from_=1.0,
            to=30.0,
            increment=1.0,
            textvariable=self.udp_freshness_var,
            width=5
        )
        self.udp_freshness.grid(row=4, column=1, sticky=tk.W, pady=5)
    
    def _create_websocket_tab(self) -> None:
        """Create the WebSocket settings tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="WebSocket")
        
        # Enabled checkbox
        self.ws_enabled_var = tk.BooleanVar()
        self.ws_enabled = ttk.Checkbutton(
            frame,
            text="Enable WebSocket Server",
            variable=self.ws_enabled_var,
            command=self._update_ws_state
        )
        self.ws_enabled.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Host
        ttk.Label(frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.ws_host_var = tk.StringVar()
        self.ws_host = ttk.Entry(
            frame,
            textvariable=self.ws_host_var,
            width=20
        )
        self.ws_host.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        # Port
        ttk.Label(frame, text="Port:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.ws_port_var = tk.IntVar()
        self.ws_port = ttk.Spinbox(
            frame,
            from_=1024,
            to=65535,
            textvariable=self.ws_port_var,
            width=7
        )
        self.ws_port.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Path
        ttk.Label(frame, text="API Path:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.ws_path_var = tk.StringVar()
        self.ws_path = ttk.Entry(
            frame,
            textvariable=self.ws_path_var,
            width=20
        )
        self.ws_path.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Broadcast interval
        ttk.Label(frame, text="Broadcast Interval (seconds):").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.ws_interval_var = tk.DoubleVar()
        self.ws_interval = ttk.Spinbox(
            frame,
            from_=0.05,
            to=1.0,
            increment=0.05,
            textvariable=self.ws_interval_var,
            width=5
        )
        self.ws_interval.grid(row=4, column=1, sticky=tk.W, pady=5)

        self.ws_compatibility_var = tk.BooleanVar()
        self.ws_compatibility = ttk.Checkbutton(
            frame,
            text="FlyShirley Compatibility Mode (current version)",
            variable=self.ws_compatibility_var
        )
        self.ws_compatibility.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5)

        # Help text for FlyShirley
        help_text = ttk.Label(
            frame,
            text="Note: FlyShirley expects the WebSocket server at port 2992 with API path '/api/v1'",
            font=("", 9, "italic"),
            foreground="gray"
        )
        help_text.grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=10)
    
    def _create_logging_tab(self) -> None:
        """Create the Logging settings tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="Logging")
        
        # Log level
        ttk.Label(frame, text="Log Level:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.log_level_var = tk.StringVar()
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level = ttk.Combobox(
            frame,
            textvariable=self.log_level_var,
            values=log_levels,
            width=10
        )
        self.log_level.grid(row=0, column=1, sticky=tk.W, pady=5)
        
        # Log to file checkbox
        self.log_to_file_var = tk.BooleanVar()
        self.log_to_file = ttk.Checkbutton(
            frame,
            text="Log to File",
            variable=self.log_to_file_var,
            command=self._update_log_file_state
        )
        self.log_to_file.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Log file path
        ttk.Label(frame, text="Log File:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        log_file_frame = ttk.Frame(frame)
        log_file_frame.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        self.log_file_var = tk.StringVar()
        self.log_file = ttk.Entry(
            log_file_frame,
            textvariable=self.log_file_var,
            width=30
        )
        self.log_file.pack(side=tk.LEFT)
        
        # Browse button for log file
        browse_button = ttk.Button(
            log_file_frame,
            text="Browse",
            command=self._browse_log_file
        )
        browse_button.pack(side=tk.LEFT, padx=5)
        
        # Max log files
        ttk.Label(frame, text="Max Log Files:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.max_log_files_var = tk.IntVar()
        self.max_log_files = ttk.Spinbox(
            frame,
            from_=1,
            to=20,
            textvariable=self.max_log_files_var,
            width=3
        )
        self.max_log_files.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Max log size
        ttk.Label(frame, text="Max Log Size (MB):").grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.max_log_size_var = tk.IntVar()
        self.max_log_size = ttk.Spinbox(
            frame,
            from_=1,
            to=100,
            textvariable=self.max_log_size_var,
            width=3
        )
        self.max_log_size.grid(row=4, column=1, sticky=tk.W, pady=5)
    
    def _create_ui_tab(self) -> None:
        """Create the UI settings tab."""
        frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(frame, text="UI")
        
        # Start minimized checkbox
        self.start_minimized_var = tk.BooleanVar()
        self.start_minimized = ttk.Checkbutton(
            frame,
            text="Start Minimized",
            variable=self.start_minimized_var
        )
        self.start_minimized.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Always on top checkbox
        self.always_on_top_var = tk.BooleanVar()
        self.always_on_top = ttk.Checkbutton(
            frame,
            text="Always on Top",
            variable=self.always_on_top_var
        )
        self.always_on_top.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Show advanced checkbox
        self.show_advanced_var = tk.BooleanVar()
        self.show_advanced = ttk.Checkbutton(
            frame,
            text="Show Advanced Options",
            variable=self.show_advanced_var
        )
        self.show_advanced.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Theme selection
        ttk.Label(frame, text="Theme:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.theme_var = tk.StringVar()
        themes = ["system", "light", "dark"]
        self.theme = ttk.Combobox(
            frame,
            textvariable=self.theme_var,
            values=themes,
            width=10
        )
        self.theme.grid(row=3, column=1, sticky=tk.W, pady=5)
        
        # Check for updates checkbox
        self.check_updates_var = tk.BooleanVar()
        self.check_updates = ttk.Checkbutton(
            frame,
            text="Check for Updates on Startup",
            variable=self.check_updates_var
        )
        self.check_updates.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # Clear recent configs button
        clear_button = ttk.Button(
            frame,
            text="Clear Recent Configurations",
            command=self._clear_recent_configs
        )
        clear_button.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
    
    def _load_settings(self) -> None:
        """Load settings values into the UI."""
        # Serial settings
        self.serial_enabled_var.set(self.settings.get('serial', 'enabled'))
        self.serial_port_var.set(self.settings.get('serial', 'port'))
        self.serial_baudrate_var.set(self.settings.get('serial', 'baudrate'))
        self.serial_timeout_var.set(self.settings.get('serial', 'timeout'))
        self.serial_freshness_var.set(self.settings.get('serial', 'data_freshness_threshold'))

        # Update serial controls state
        self._update_serial_state()
        
        # UDP settings
        self.udp_enabled_var.set(self.settings.get('udp', 'enabled'))
        self.udp_host_var.set(self.settings.get('udp', 'host'))
        self.udp_port_var.set(self.settings.get('udp', 'port'))
        self.udp_buffer_var.set(self.settings.get('udp', 'buffer_size'))
        self.udp_freshness_var.set(self.settings.get('udp', 'data_freshness_threshold'))
        
        # Update UDP controls state
        self._update_udp_state()
        
        # WebSocket settings
        self.ws_enabled_var.set(self.settings.get('websocket', 'enabled'))
        self.ws_host_var.set(self.settings.get('websocket', 'host'))
        self.ws_port_var.set(self.settings.get('websocket', 'port'))
        self.ws_path_var.set(self.settings.get('websocket', 'path'))
        self.ws_interval_var.set(self.settings.get('websocket', 'broadcast_interval'))
        
        # Update WebSocket controls state
        self._update_ws_state()
        
        # Logging settings
        self.log_level_var.set(self.settings.get('logging', 'level'))
        self.log_to_file_var.set(self.settings.get('logging', 'log_to_file'))
        self.log_file_var.set(self.settings.get('logging', 'log_file_path') or "")
        self.max_log_files_var.set(self.settings.get('logging', 'max_log_files'))
        self.max_log_size_var.set(self.settings.get('logging', 'max_log_size_mb'))
        
        # Update log file controls state
        self._update_log_file_state()
        
        # UI settings
        self.start_minimized_var.set(self.settings.get('ui', 'start_minimized'))
        self.always_on_top_var.set(self.settings.get('ui', 'always_on_top'))
        self.show_advanced_var.set(self.settings.get('ui', 'show_advanced'))
        self.theme_var.set(self.settings.get('ui', 'theme'))
        self.check_updates_var.set(self.settings.get('ui', 'startup_check_updates'))

        # Compatibility mode for old FlyShirley
        self.ws_compatibility_var.set(self.settings.get('websocket', 'compatibility_mode'))
    
    def _save_settings(self) -> bool:
        """
        Save UI values to settings.
        
        Returns:
            bool: True if settings were saved successfully
        """
        try:
            # Serial settings
            self.settings.set('serial', 'enabled', self.serial_enabled_var.get())
            self.settings.set('serial', 'port', self.serial_port_var.get())
            self.settings.set('serial', 'baudrate', self.serial_baudrate_var.get())
            self.settings.set('serial', 'timeout', self.serial_timeout_var.get())
            self.settings.set('serial', 'data_freshness_threshold', self.serial_freshness_var.get())
            
            # UDP settings
            self.settings.set('udp', 'enabled', self.udp_enabled_var.get())
            self.settings.set('udp', 'host', self.udp_host_var.get())
            self.settings.set('udp', 'port', self.udp_port_var.get())
            self.settings.set('udp', 'buffer_size', self.udp_buffer_var.get())
            self.settings.set('udp', 'data_freshness_threshold', self.udp_freshness_var.get())
            
            # WebSocket settings
            self.settings.set('websocket', 'enabled', self.ws_enabled_var.get())
            self.settings.set('websocket', 'host', self.ws_host_var.get())
            self.settings.set('websocket', 'port', self.ws_port_var.get())
            self.settings.set('websocket', 'path', self.ws_path_var.get())
            self.settings.set('websocket', 'broadcast_interval', self.ws_interval_var.get())
            
            # Logging settings
            self.settings.set('logging', 'level', self.log_level_var.get())
            self.settings.set('logging', 'log_to_file', self.log_to_file_var.get())
            self.settings.set('logging', 'log_file_path', self.log_file_var.get())
            self.settings.set('logging', 'max_log_files', self.max_log_files_var.get())
            self.settings.set('logging', 'max_log_size_mb', self.max_log_size_var.get())
            
            # UI settings
            self.settings.set('ui', 'start_minimized', self.start_minimized_var.get())
            self.settings.set('ui', 'always_on_top', self.always_on_top_var.get())
            self.settings.set('ui', 'show_advanced', self.show_advanced_var.get())
            self.settings.set('ui', 'theme', self.theme_var.get())
            self.settings.set('ui', 'startup_check_updates', self.check_updates_var.get())

            # Compatibility mode for old FlyShirley
            self.settings.set('websocket', 'compatibility_mode', self.ws_compatibility_var.get())
            
            # Validate settings
            validation_errors = self.settings.validate()
            if validation_errors:
                # Show validation errors
                error_message = "Invalid settings:\n\n"
                for section, errors in validation_errors.items():
                    error_message += f"[{section}]\n"
                    for error in errors:
                        error_message += f"- {error}\n"
                
                messagebox.showerror("Validation Error", error_message)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Settings Error", f"Failed to save settings: {e}")
            return False
    
    def _update_serial_state(self) -> None:
        """Update the state of serial controls based on enabled state."""
        state = "normal" if self.serial_enabled_var.get() else "disabled"
        
        self.serial_port.config(state=state)
        self.serial_baudrate.config(state=state)
        self.serial_timeout.config(state=state)
        self.serial_freshness.config(state=state)
    
    def _update_udp_state(self) -> None:
        """Update the state of UDP controls based on enabled state."""
        state = "normal" if self.udp_enabled_var.get() else "disabled"
        
        self.udp_host.config(state=state)
        self.udp_port.config(state=state)
        self.udp_buffer.config(state=state)
        self.udp_freshness.config(state=state)
    
    def _update_ws_state(self) -> None:
        """Update the state of WebSocket controls based on enabled state."""
        state = "normal" if self.ws_enabled_var.get() else "disabled"
        
        self.ws_host.config(state=state)
        self.ws_port.config(state=state)
        self.ws_path.config(state=state)
        self.ws_interval.config(state=state)
    
    def _update_log_file_state(self) -> None:
        """Update the state of log file controls based on log_to_file state."""
        state = "normal" if self.log_to_file_var.get() else "disabled"
        
        self.log_file.config(state=state)
        self.max_log_files.config(state=state)
        self.max_log_size.config(state=state)
    
    def _refresh_serial_ports(self) -> None:
        """Refresh the list of available serial ports."""
        ports = self.settings.get_available_serial_ports()
        
        # Update combobox values
        self.serial_port.config(values=ports)
        
        # If current port is not in list and list is not empty, select first port
        current_port = self.serial_port_var.get()
        if ports and current_port not in ports:
            self.serial_port_var.set(ports[0])
    
    def _browse_log_file(self) -> None:
        """Open file dialog to select log file path."""
        current_path = self.log_file_var.get()
        initial_dir = os.path.dirname(current_path) if current_path else None
        
        path = filedialog.asksaveasfilename(
            title="Select Log File",
            defaultextension=".log",
            filetypes=[("Log Files", "*.log"), ("All Files", "*.*")],
            initialdir=initial_dir
        )
        
        if path:
            self.log_file_var.set(path)
    
    def _clear_recent_configs(self) -> None:
        """Clear the list of recent configurations."""
        if messagebox.askyesno(
            "Clear Recent Configurations",
            "Are you sure you want to clear the list of recent configurations?"
        ):
            self.settings.settings.ui.recent_configs = []
            messagebox.showinfo(
                "Recent Configurations",
                "Recent configurations list has been cleared."
            )
    
    def _on_ok(self) -> None:
        """Handle OK button click."""
        if self._save_settings():
            self.result = True
            self.dialog.destroy()
    
    def _on_apply(self) -> None:
        """Handle Apply button click."""
        if self._save_settings():
            self.result = True
    
    def _on_cancel(self) -> None:
        """Handle Cancel button click."""
        self.result = False
        self.dialog.destroy()


# Example usage:
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Settings Dialog Test")
    root.geometry("200x100")
    
    # Create a button to open the dialog
    def open_settings():
        settings = Settings()
        dialog = SettingsDialog(root, settings)
        if dialog.result:
            print("Settings were changed")
        else:
            print("Settings were not changed")
    
    button = ttk.Button(root, text="Settings", command=open_settings)
    button.pack(padx=20, pady=20)
    
    root.mainloop()
