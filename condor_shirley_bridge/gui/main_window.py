#!/usr/bin/env python3

"""
Main Window for Condor-Shirley-Bridge
The primary GUI window that contains all panels and controls
for managing the bridge.

Part of the Condor-Shirley-Bridge project.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
import webbrowser

# Add parent directory to path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import from our project structure
from condor_shirley_bridge.core.bridge import Bridge
from condor_shirley_bridge.core.settings import Settings
from condor_shirley_bridge.gui.status_panel import StatusPanel
from condor_shirley_bridge.gui.settings_dialog import SettingsDialog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gui.main_window')


class MainWindow:
    """
    Main application window for Condor-Shirley-Bridge.
    
    This window contains:
    - Menu bar with file, tools, and help options
    - Status panel showing connection status and data flow
    - Control panel with buttons to start/stop the bridge
    - Status bar with brief status information
    """
    def __init__(self, master: tk.Tk):
        """
        Initialize the main window.
        
        Args:
            master: Tkinter root window
        """
        self.master = master
        self.bridge: Optional[Bridge] = None
        self.settings = Settings()
        
        # Asyncio event loop for the bridge
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.bridge_thread: Optional[threading.Thread] = None
        
        # Setup UI
        self._setup_window()
        self._create_menu()
        self._create_widgets()
        
        # Update status periodically
        self._update_status()
        
        # Initialize Bridge (but don't start it yet)
        self._init_bridge()
        
        # Handle window close
        self.master.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Show "first run" message if applicable
        if self.settings.settings.first_run:
            self._show_first_run_message()

    def _setup_window(self) -> None:
        """Configure the main window."""
        self.master.title("Condor-Shirley-Bridge")
        self.master.geometry("1000x740") # Set default size
        self.master.minsize(700, 450) # Set minimum size

        # Rest of the method remains the same
        # Set icon if available
        try:
            icon_path = os.path.join(os.path.dirname(__file__), '../../assets/icon.ico')
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
        except Exception as e:
            logger.warning(f"Could not set window icon: {e}")

        # Configure grid layout
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(1, weight=1)  # Status panel gets all extra space

        # Apply theme from settings
        self._apply_theme()
    
    def _apply_theme(self) -> None:
        """Apply the selected theme from settings."""
        theme = self.settings.get('ui', 'theme')
        
        if theme == 'system':
            # Use system theme (default)
            style = ttk.Style()
            if sys.platform == 'win32':
                style.theme_use('vista')
            elif sys.platform == 'darwin':
                style.theme_use('aqua')
            else:
                style.theme_use('clam')
        elif theme == 'light':
            # Light theme
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('.', background='#f0f0f0')
            style.configure('TFrame', background='#f0f0f0')
            style.configure('TButton', background='#e0e0e0')
            style.configure('TLabel', background='#f0f0f0')
            style.configure('TNotebook', background='#f0f0f0')
            style.configure('TNotebook.Tab', background='#e0e0e0')
        elif theme == 'dark':
            # Dark theme
            style = ttk.Style()
            style.theme_use('clam')
            style.configure('.', background='#303030', foreground='white')
            style.configure('TFrame', background='#303030')
            style.configure('TButton', background='#505050', foreground='white')
            style.configure('TLabel', background='#303030', foreground='white')
            style.configure('TNotebook', background='#303030')
            style.configure('TNotebook.Tab', background='#505050', foreground='white')
    
    def _create_menu(self) -> None:
        """Create the menu bar."""
        self.menu_bar = tk.Menu(self.master)
        
        # File menu
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="Open Configuration...", command=self._open_config)
        self.file_menu.add_command(label="Save Configuration", command=self._save_config)
        self.file_menu.add_command(label="Save Configuration As...", command=self._save_config_as)
        self.file_menu.add_separator()
        
        # Recent configs submenu
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self._update_recent_menu()
        self.file_menu.add_cascade(label="Recent Configurations", menu=self.recent_menu)
        
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self._on_close)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        
        # Tools menu
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="Settings...", command=self._open_settings)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Reset to Default Settings", command=self._reset_settings)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="View Log File", command=self._view_log_file, state=tk.DISABLED)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        
        # Help menu
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="Documentation", command=self._open_documentation)
        self.help_menu.add_command(label="GitHub Repository", command=self._open_github)
        self.help_menu.add_separator()
        self.help_menu.add_command(label="About", command=self._show_about)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        
        # Set menu bar
        self.master.config(menu=self.menu_bar)
    
    def _update_recent_menu(self) -> None:
        """Update the recent configurations menu."""
        # Clear existing items
        self.recent_menu.delete(0, tk.END)
        
        # Add recent configs
        recent_configs = self.settings.settings.ui.recent_configs
        if recent_configs:
            for path in recent_configs:
                # Use a lambda with default argument to capture the current path
                self.recent_menu.add_command(
                    label=os.path.basename(path),
                    command=lambda p=path: self._open_config(p)
                )
        else:
            self.recent_menu.add_command(label="No recent configurations", state=tk.DISABLED)

    # Añadir este metodo a la clase MainWindow en main_window.py
    def _setup_log_handler(self) -> None:
        """Set up a custom log handler to show logs in the UI."""
        # Importar el sistema centralizado de logs
        from condor_shirley_bridge.core.log_config import add_text_handler

        # Agregar el manejador de texto
        add_text_handler(self.log_text)

    def _create_widgets(self) -> None:
        """Create the main window widgets."""
        # Control panel at the top
        self.control_frame = ttk.Frame(self.master, padding="10")
        self.control_frame.grid(row=0, column=0, sticky="ew")

        # Start/Stop button
        self.start_stop_button = ttk.Button(
            self.control_frame,
            text="Start Bridge",
            command=self._toggle_bridge
        )
        self.start_stop_button.pack(side="left", padx=5)

        # Settings button
        self.settings_button = ttk.Button(
            self.control_frame,
            text="Settings",
            command=self._open_settings
        )
        self.settings_button.pack(side="left", padx=5)

        log_info_label = ttk.Label(self.control_frame, text="Log Level: INFO")
        log_info_label.pack(side="left", padx=(10, 2))

        # Clear log button
        clear_log_button = ttk.Button(
            self.control_frame,
            text="Clear Log",
            command=self._clear_log
        )
        clear_log_button.pack(side="left", padx=5)

        # Connection status indicators
        self.indicators_frame = ttk.Frame(self.control_frame)
        self.indicators_frame.pack(side="right", padx=5)

        # Serial indicator
        self.serial_frame = ttk.Frame(self.indicators_frame)
        self.serial_frame.pack(side="left", padx=5)

        self.serial_label = ttk.Label(self.serial_frame, text="Serial:")
        self.serial_label.pack(side="left")

        self.serial_status = ttk.Label(
            self.serial_frame,
            text="Disconnected",
            foreground="red"
        )
        self.serial_status.pack(side="left")

        # UDP indicator
        self.udp_frame = ttk.Frame(self.indicators_frame)
        self.udp_frame.pack(side="left", padx=5)

        self.udp_label = ttk.Label(self.udp_frame, text="UDP:")
        self.udp_label.pack(side="left")

        self.udp_status = ttk.Label(
            self.udp_frame,
            text="Disconnected",
            foreground="red"
        )
        self.udp_status.pack(side="left")

        # WebSocket indicator
        self.ws_frame = ttk.Frame(self.indicators_frame)
        self.ws_frame.pack(side="left", padx=5)

        self.ws_label = ttk.Label(self.ws_frame, text="WebSocket:")
        self.ws_label.pack(side="left")

        self.ws_status = ttk.Label(
            self.ws_frame,
            text="Disconnected",
            foreground="red"
        )
        self.ws_status.pack(side="left")

        # Status panel with notebook for different views
        self.status_frame = ttk.Frame(self.master, padding="10")
        self.status_frame.grid(row=1, column=0, sticky="nsew")

        self.status_notebook = ttk.Notebook(self.status_frame)
        self.status_notebook.pack(fill=tk.BOTH, expand=True)

        # Add status panel
        self.status_panel = StatusPanel(self.status_notebook)
        self.status_notebook.add(self.status_panel.frame, text="Status")

        # Log panel
        self.log_frame = ttk.Frame(self.status_notebook)
        self.status_notebook.add(self.log_frame, text="Log")

        self.log_text = tk.Text(
            self.log_frame,
            wrap=tk.WORD,
            height=10,
            width=80,
            state=tk.DISABLED
        )
        self.log_scrollbar = ttk.Scrollbar(
            self.log_frame,
            orient=tk.VERTICAL,
            command=self.log_text.yview
        )
        self.log_text['yscrollcommand'] = self.log_scrollbar.set

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure custom log handler to show logs in the UI
        self._setup_log_handler()

        # Status bar at the bottom
        self.status_bar = ttk.Label(
            self.master,
            text="Ready",
            anchor=tk.W,
            padding="5 2"
        )
        self.status_bar.grid(row=2, column=0, sticky="ew")

    def set_text_handler_level(level: int) -> None:
        """
        Cambia el nivel del manejador de texto actual.

        Args:
            level: Nuevo nivel de logging
        """
        # Intentar buscar manejadores de texto en el logger raíz
        root_logger = logging.getLogger()

        # Buscar manejadores de texto
        text_handlers = []
        for handler in root_logger.handlers:
            # Verificar si es un manejador de texto basado en un atributo distintivo
            if hasattr(handler, 'text_widget'):
                text_handlers.append(handler)

        # Actualizar los manejadores encontrados
        if text_handlers:
            for handler in text_handlers:
                handler.setLevel(level)

            # Registrar el cambio
            logging.info(f"GUI log level set to {logging.getLevelName(level)}")
        else:
            logging.warning("No text handler found to change log level")

    def _clear_log(self) -> None:
        """Clear the log text widget."""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _init_bridge(self) -> None:
        """Initialize the bridge instance."""
        try:
            self.bridge = Bridge()
            logger.info("Bridge initialized")
            self.status_bar.config(text="Bridge initialized")
        except Exception as e:
            logger.error(f"Error initializing bridge: {e}")
            messagebox.showerror(
                "Initialization Error",
                f"Failed to initialize bridge: {e}"
            )
            self.status_bar.config(text="Bridge initialization failed")
    
    def _toggle_bridge(self) -> None:
        """Start or stop the bridge."""
        if not self.bridge:
            messagebox.showerror(
                "Bridge Error",
                "Bridge not initialized. Please restart the application."
            )
            return
            
        if self.bridge_thread and self.bridge_thread.is_alive():
            # Bridge is running, stop it
            self._stop_bridge()
        else:
            # Bridge is not running, start it
            self._start_bridge()
    
    def _start_bridge(self) -> None:
        """Start the bridge in a separate thread."""
        # Disable the button while starting
        self.start_stop_button.config(state=tk.DISABLED)
        self.status_bar.config(text="Starting bridge...")
        
        # Function to run the bridge in a background thread
        def run_bridge():
            try:
                # Create a new event loop for this thread
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # Start the bridge
                self.loop.run_until_complete(self.bridge.start())
                
                # Update UI in main thread
                self.master.after(0, lambda: self._on_bridge_started())
                
                # Run the event loop
                self.loop.run_forever()
                
            except Exception as e:
                logger.error(f"Error in bridge thread: {e}")
                # Update UI in main thread
                self.master.after(0, lambda: self._on_bridge_error(str(e)))
                
            finally:
                # Clean up
                if self.loop and self.loop.is_running():
                    self.loop.close()
                
                # Update UI in main thread
                self.master.after(0, lambda: self._on_bridge_stopped())
        
        # Start the bridge in a background thread
        self.bridge_thread = threading.Thread(target=run_bridge, daemon=True)
        self.bridge_thread.start()
    
    def _on_bridge_started(self) -> None:
        """Called when the bridge has started."""
        self.start_stop_button.config(text="Stop Bridge", state=tk.NORMAL)
        self.status_bar.config(text="Bridge running")
        
        # Save settings for next time
        self.settings.save()
    
    def _on_bridge_error(self, error_msg: str) -> None:
        """Called when there's an error starting the bridge."""
        self.start_stop_button.config(text="Start Bridge", state=tk.NORMAL)
        self.status_bar.config(text=f"Bridge error: {error_msg}")
        
        messagebox.showerror(
            "Bridge Error",
            f"Failed to start bridge: {error_msg}"
        )

    def _stop_bridge(self) -> None:
        """Stop the bridge."""
        if not self.bridge or not self.loop:
            return

        # Disable the button while stopping
        self.start_stop_button.config(state=tk.DISABLED)
        self.status_bar.config(text="Stopping bridge...")

        # Stop the bridge asynchronously
        def stop_async():
            try:
                asyncio.run_coroutine_threadsafe(self.bridge.stop(), self.loop)
            except Exception as e:
                logger.error(f"Error stopping bridge: {e}")
                # Ensure the button is re-enabled
                self.master.after(0, self._on_bridge_stopped)

        # Run in a thread to avoid blocking the GUI
        thread = threading.Thread(target=stop_async, daemon=True)
        thread.start()

        # Start polling to check if the bridge has stopped
        self._poll_bridge_stopped()

    def _poll_bridge_stopped(self) -> None:
        """Poll to check if the bridge has stopped."""
        # If bridge is defined but not running, it's stopped
        if self.bridge and not self.bridge.running:
            self._on_bridge_stopped()
        else:
            # Check if the bridge thread is still alive
            if self.bridge_thread and not self.bridge_thread.is_alive():
                self._on_bridge_stopped()
            else:
                # Continue polling every 100ms
                self.master.after(100, self._poll_bridge_stopped)

        # Also set a timeout (5 seconds) to ensure the UI gets updated
        if not hasattr(self, '_stop_timeout_id'):
            self._stop_timeout_id = self.master.after(5000, self._force_bridge_stopped)

    def _force_bridge_stopped(self) -> None:
        """Force UI update if bridge takes too long to stop."""
        if hasattr(self, '_stop_timeout_id'):
            del self._stop_timeout_id

        # Only force if button is still disabled
        if self.start_stop_button.cget('state') == tk.DISABLED:
            logger.warning("Force stopping bridge UI update after timeout")
            self._on_bridge_stopped()

    def _on_bridge_stopped(self) -> None:
        """Called when the bridge has stopped."""
        # Cancel any pending timeout
        if hasattr(self, '_stop_timeout_id'):
            self.master.after_cancel(self._stop_timeout_id)
            del self._stop_timeout_id

        # Reset button state
        self.start_stop_button.config(text="Start Bridge", state=tk.NORMAL)
        self.status_bar.config(text="Bridge stopped")

    def _update_status(self) -> None:
        """Update status displays periodically."""
        if self.bridge and self.bridge.running:
            try:
                # Get bridge status
                status = self.bridge.get_status()
                logger.debug(f"MainWindow._update_status received: {status}")

                # Update status panel
                self.status_panel.update_status(status)

                # Update connection indicators
                self._update_connection_indicators(status)
            except Exception as e:
                logger.error(f"Error updating status: {e}")
        else:
            # Bridge not running, show disconnected status
            self._update_connection_indicators(None)

            # Reset all status indicators to show disconnected state
            self.status_panel.reset_status()

        # Schedule next update
        self.master.after(1000, self._update_status)
    
    def _update_connection_indicators(self, status: Optional[Dict[str, Any]]) -> None:
        """Update the connection status indicators."""
        if not status:
            # Not running, all disconnected
            self.serial_status.config(text="Disconnected", foreground="red")
            self.udp_status.config(text="Disconnected", foreground="red")
            self.ws_status.config(text="Disconnected", foreground="red")
            return
        
        # Serial status
        if 'serial' in status and status['serial']:
            serial_enabled = self.settings.get('serial', 'enabled')
            if serial_enabled and status['serial']['connected']:
                self.serial_status.config(text="Connected", foreground="green")
            elif serial_enabled:
                self.serial_status.config(text="Error", foreground="orange")
            else:
                self.serial_status.config(text="Disabled", foreground="gray")
        else:
            self.serial_status.config(text="Disconnected", foreground="red")
        
        # UDP status
        if 'udp' in status and status['udp']:
            udp_enabled = self.settings.get('udp', 'enabled')
            if udp_enabled and status['udp']['bound']:
                self.udp_status.config(text="Connected", foreground="green")
            elif udp_enabled:
                self.udp_status.config(text="Error", foreground="orange")
            else:
                self.udp_status.config(text="Disabled", foreground="gray")
        else:
            self.udp_status.config(text="Disconnected", foreground="red")
        
        # WebSocket status
        if 'websocket' in status and status['websocket']:
            ws_enabled = self.settings.get('websocket', 'enabled')
            if ws_enabled and status['websocket']['running']:
                self.ws_status.config(text="Running", foreground="green")
            elif ws_enabled:
                self.ws_status.config(text="Error", foreground="orange")
            else:
                self.ws_status.config(text="Disabled", foreground="gray")
        else:
            self.ws_status.config(text="Disconnected", foreground="red")
    
    def _open_config(self, path: Optional[str] = None) -> None:
        """Open a configuration file."""
        if not path:
            # Show file dialog
            path = filedialog.askopenfilename(
                title="Open Configuration",
                filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
            )
            
        if path:
            # Load the configuration
            if self.bridge.update_settings(path):
                self.settings = self.bridge.settings  # Keep our settings in sync
                self.settings.add_recent_config(path)
                self._update_recent_menu()
                self.status_bar.config(text=f"Loaded configuration from {path}")
            else:
                messagebox.showerror(
                    "Configuration Error",
                    f"Failed to load configuration from {path}"
                )
    
    def _save_config(self) -> None:
        """Save the current configuration."""
        if self.settings.save():
            self.status_bar.config(text=f"Configuration saved to {self.settings.config_file}")
        else:
            messagebox.showerror(
                "Configuration Error",
                "Failed to save configuration"
            )
    
    def _save_config_as(self) -> None:
        """Save the configuration to a new file."""
        path = filedialog.asksaveasfilename(
            title="Save Configuration As",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if path:
            if self.settings.save(path):
                self.settings.add_recent_config(path)
                self._update_recent_menu()
                self.status_bar.config(text=f"Configuration saved to {path}")
            else:
                messagebox.showerror(
                    "Configuration Error",
                    f"Failed to save configuration to {path}"
                )
    
    def _open_settings(self) -> None:
        """Open the settings dialog."""
        # Create settings dialog
        dialog = SettingsDialog(self.master, self.settings)
        
        # Get result (True if settings were changed)
        if dialog.result:
            # Settings were changed, apply them
            self._apply_settings_changes()
    
    def _apply_settings_changes(self) -> None:
        """Apply changes to settings."""
        # Apply theme
        self._apply_theme()
        
        # Apply logging settings
        self.settings.apply_logging_settings()
        
        # Update log file menu item
        log_file = self.settings.get('logging', 'log_file_path')
        if log_file and self.settings.get('logging', 'log_to_file'):
            self.tools_menu.entryconfig("View Log File", state=tk.NORMAL)
        else:
            self.tools_menu.entryconfig("View Log File", state=tk.DISABLED)
        
        # If bridge is running, we need to restart it to apply new settings
        if self.bridge and self.bridge.running:
            if messagebox.askyesno(
                "Restart Required",
                "Settings have changed. Restart the bridge to apply them?"
            ):
                # Stop then start the bridge
                self._stop_bridge()
                # Wait a moment before starting
                self.master.after(1000, self._start_bridge)
            else:
                # Save settings anyway
                self.settings.save()
        else:
            # Just save settings
            self.settings.save()
    
    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        if messagebox.askyesno(
            "Reset Settings",
            "Are you sure you want to reset all settings to default values?"
        ):
            self.settings.reset_to_defaults()
            self._apply_settings_changes()
            self.status_bar.config(text="Settings reset to defaults")
    
    def _view_log_file(self) -> None:
        """Open the log file in the default text editor."""
        log_file = self.settings.get('logging', 'log_file_path')
        if log_file and os.path.exists(log_file):
            # Open with default application
            if sys.platform == 'win32':
                os.startfile(log_file)
            elif sys.platform == 'darwin':
                os.system(f'open "{log_file}"')
            else:
                os.system(f'xdg-open "{log_file}"')
        else:
            messagebox.showerror(
                "Log File Error",
                "Log file not found or logging to file is disabled"
            )
    
    def _open_documentation(self) -> None:
        """Open the documentation in a web browser."""
        webbrowser.open('https://github.com/jlgabriel/ForeFlight-Shirley-Bridge')
    
    def _open_github(self) -> None:
        """Open the GitHub repository in a web browser."""
        webbrowser.open('https://github.com/jlgabriel/ForeFlight-Shirley-Bridge')
    
    def _show_about(self) -> None:
        """Show the about dialog."""
        messagebox.showinfo(
            "About Condor-Shirley-Bridge",
            "Condor-Shirley-Bridge\n\n"
            "Version: 1.0.0\n\n"
            "A bridge between Condor Soaring Simulator and FlyShirley.\n\n"
            "Based on ForeFlight-Shirley-Bridge by Juan Luis Gabriel.\n\n"
            "© 2025 Juan Luis Gabriel"
        )
    
    def _show_first_run_message(self) -> None:
        """Show a welcome message for first-time users."""
        messagebox.showinfo(
            "Welcome to Condor-Shirley-Bridge",
            "Welcome to Condor-Shirley-Bridge!\n\n"
            "This appears to be your first time running the application.\n\n"
            "Please configure your Serial, UDP, and WebSocket settings before starting the bridge.\n\n"
            "If you need help, click on Help > Documentation."
        )

    def _on_close(self) -> None:
        """Handle window close event."""
        if self.bridge and self.bridge.running:
            if not messagebox.askyesno(
                    "Quit",
                    "The bridge is still running. Are you sure you want to quit?"
            ):
                return

            # Stop the bridge
            self._stop_bridge()

            # Wait a moment to let it stop cleanly
            self.master.after(200)

        # Eliminar el manejador de texto antes de cerrar
        from condor_shirley_bridge.core.log_config import remove_text_handler
        remove_text_handler()

        # Save settings
        self.settings.save()

        # Destroy the window
        self.master.destroy()


# Run the application if this script is executed directly
if __name__ == "__main__":
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
