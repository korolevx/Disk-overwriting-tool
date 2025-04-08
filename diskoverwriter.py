#!/usr/bin/env python3

import os
import subprocess
import time
import threading
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, GObject

class DiskOverwriter(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Disk Overwriter Tool")
        self.set_default_size(700, 550)
        
        self.CHUNK_SIZE = 4 * 1024 * 1024 
        self.MAX_PASSES = 35
            
        self.devices = []
        self.stop_event = threading.Event()
        self.current_pass = 0
        self.total_passes = 1
        self.method = "zero"
        self.device = ""
        self.device_size = 0
        self.start_time = 0
        self.bytes_written_total = 0
        
        self.setup_ui()
        self.refresh_devices()

    def setup_ui(self):

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_border_width(12)
        self.add(main_box)

        device_frame = Gtk.Frame(label="Disk Selection")
        device_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        main_box.pack_start(device_frame, False, False, 0)
        
        device_grid = self.create_device_selection()
        device_frame.add(device_grid)

        config_frame = Gtk.Frame(label="Erase Settings")
        config_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        main_box.pack_start(config_frame, False, False, 0)
        
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        config_frame.add(config_box)
        
        method_box = self.create_method_selection()
        config_box.pack_start(method_box, False, False, 0)

        passes_box = self.create_passes_selection()
        config_box.pack_start(passes_box, False, False, 0)

        info_frame = Gtk.Frame(label="Disk Information")
        info_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        main_box.pack_start(info_frame, False, False, 0)
        
        self.lbl_device_info = Gtk.Label(label="No device selected")
        self.lbl_device_info.set_line_wrap(True)
        self.lbl_device_info.set_halign(Gtk.Align.START)
        info_frame.add(self.lbl_device_info)

        progress_frame = Gtk.Frame(label="Erase Progress")
        progress_frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        main_box.pack_start(progress_frame, True, True, 0)
        
        progress_box = self.create_progress_indicator()
        progress_frame.add(progress_box)

        action_buttons = self.create_action_buttons()
        main_box.pack_start(action_buttons, False, False, 5)

    def create_device_selection(self):
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_border_width(8)
        
        lbl_devices = Gtk.Label(label="Available Disks:", xalign=0)
        self.cmb_devices = Gtk.ComboBoxText()
        self.cmb_devices.set_hexpand(True)
        
        btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        btn_refresh.connect("clicked", self.on_refresh_clicked)
        btn_refresh.set_tooltip_text("Refresh disk list")

        grid.attach(lbl_devices, 0, 0, 1, 1)
        grid.attach(self.cmb_devices, 1, 0, 1, 1)
        grid.attach(btn_refresh, 2, 0, 1, 1)
        self.cmb_devices.connect("changed", self.on_device_changed)
        
        return grid

    def create_method_selection(self):
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_border_width(8)
        
        lbl_method = Gtk.Label(label="Erase Method:", xalign=0)
        self.cmb_method = Gtk.ComboBoxText()
        self.cmb_method.set_hexpand(True)
        
        self.cmb_method.append_text("Single Zero Pass (Fast)")
        self.cmb_method.append_text("DoD 3 Passes (Secure)")
        self.cmb_method.append_text("Gutmann 35 Passes (Paranoid)")
        self.cmb_method.append_text("Custom Passes")
        self.cmb_method.set_active(0)
        
        self.cmb_method.connect("changed", self.on_method_changed)

        btn_help = Gtk.Button.new_from_icon_name("dialog-information-symbolic", Gtk.IconSize.BUTTON)
        btn_help.connect("clicked", self.show_method_help)
        btn_help.set_tooltip_text("Show method information")

        method_box = Gtk.Box(spacing=5)
        method_box.pack_start(self.cmb_method, True, True, 0)
        method_box.pack_start(btn_help, False, False, 0)

        grid.attach(lbl_method, 0, 0, 1, 1)
        grid.attach(method_box, 1, 0, 2, 1)
        
        return grid

    def create_passes_selection(self):
        grid = Gtk.Grid(column_spacing=8, row_spacing=8)
        grid.set_border_width(8)
        
        lbl_passes = Gtk.Label(label="Number of Passes:", xalign=0)
        self.spn_passes = Gtk.SpinButton.new_with_range(1, self.MAX_PASSES, 1)
        self.spn_passes.set_value(1)
        self.spn_passes.set_sensitive(False)

        grid.attach(lbl_passes, 0, 0, 1, 1)
        grid.attach(self.spn_passes, 1, 0, 1, 1)
        
        return grid

    def create_progress_indicator(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_border_width(8)
        
        self.lbl_pass = Gtk.Label()
        self.lbl_pass.set_halign(Gtk.Align.START)
        self.progress_pass = Gtk.ProgressBar()
        
        self.lbl_total = Gtk.Label()
        self.lbl_total.set_halign(Gtk.Align.START)
        self.progress_total = Gtk.ProgressBar()
        
        self.lbl_stats = Gtk.Label()
        self.lbl_stats.set_halign(Gtk.Align.START)
        
        for widget in [self.lbl_pass, self.progress_pass, 
                      self.lbl_total, self.progress_total, 
                      self.lbl_stats]:
            box.pack_start(widget, False, False, 2)
            
        return box

    def create_action_buttons(self):
        btn_box = Gtk.Box(spacing=10)
        btn_box.set_border_width(5)
        
        self.btn_start = Gtk.Button.new_with_label("Start Secure Erase")
        self.btn_start.connect("clicked", self.on_start_clicked)
        self.btn_start.get_style_context().add_class("suggested-action")
        
        self.btn_stop = Gtk.Button.new_with_label("Abort Process")
        self.btn_stop.connect("clicked", self.on_stop_clicked)
        self.btn_stop.set_sensitive(False)
        self.btn_stop.get_style_context().add_class("destructive-action")
        
        btn_box.pack_start(self.btn_start, True, True, 0)
        btn_box.pack_start(self.btn_stop, True, True, 0)
        
        return btn_box

    def on_refresh_clicked(self, button):
        """Atualiza a lista de dispositivos disponíveis"""
        self.refresh_devices()

    def on_method_changed(self, combo):
        method = combo.get_active()
        if method == 3:  
            self.spn_passes.set_sensitive(True)
        else:
            self.spn_passes.set_sensitive(False)

    def refresh_devices(self):
        self.devices = []
        self.cmb_devices.remove_all()
        
        try:

            result = subprocess.run(
                ["lsblk", "-d", "-n", "-o", "NAME,SIZE,MODEL,VENDOR,MOUNTPOINT,RO"],
                check=True, capture_output=True, text=True
            )
            
            for line in result.stdout.splitlines():
                if not line.strip():
                    continue
                
                parts = line.split(maxsplit=5)
                if len(parts) < 3:
                    continue
                
                device = f"/dev/{parts[0]}"
                size = parts[1]
                model = f"{parts[2]} {parts[3]}" if len(parts) > 4 else "Unknown"
                mounted = "[Mounted]" if len(parts) > 5 and parts[4] else ""
                ro = "[Read-Only]" if len(parts) > 5 and parts[5] == "1" else ""
                
                self.devices.append((device, size, model))
                self.cmb_devices.append_text(f"{device} - {size} - {model} {mounted} {ro}")
                
        except subprocess.CalledProcessError as e:
            self.show_error(f"Error listing devices: {e.stderr}")

    def on_device_changed(self, combo):
        index = combo.get_active()
        if 0 <= index < len(self.devices):
            device, size, model = self.devices[index]
            self.device = device
            self.lbl_device_info.set_text(f"Device: {device}\nSize: {size}\nModel: {model}")
            self.get_device_size()

    def get_device_size(self):
        try:
            result = subprocess.run(
                ["blockdev", "--getsize64", self.device],
                check=True, capture_output=True, text=True
            )
            self.device_size = int(result.stdout.strip())
        except subprocess.CalledProcessError as e:
            self.show_error(f"Error getting device size: {e.stderr}")
            self.device_size = 0

    def validate_device(self):
        if not self.device:
            return False, "No device selected"
            
        if not os.path.exists(self.device):
            return False, "Device does not exist"
            
        try:
            result = subprocess.run(
                ["findmnt", "-n", "-o", "TARGET", "--source", self.device],
                capture_output=True, text=True
            )
            if result.stdout.strip():
                return False, "Device is mounted! Unmount before proceeding."
        except FileNotFoundError:
            pass
            
        if not os.access(self.device, os.W_OK):
            return False, "No write permission on device (run as root)"
            
        return True, ""

    def on_start_clicked(self, button):

        valid, message = self.validate_device()
        if not valid:
            self.show_error(message)
            return
            
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="WARNING: Data Destruction"
        )
        dialog.format_secondary_text(
            f"You are about to PERMANENTLY ERASE all data on:\n\n"
            f"Device: {self.device}\n"
            f"Size: {self.device_size / (1024**3):.2f} GB\n\n"
            f"THIS ACTION CANNOT BE UNDONE!\n"
            f"Are you absolutely sure you want to continue?"
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response != Gtk.ResponseType.OK:
            return
            
        method = self.cmb_method.get_active()
        if method == 0:  
            self.total_passes = 1
            self.method = "zero"
        elif method == 1:  
            self.total_passes = 3
            self.method = "dod"
        elif method == 2:  
            self.total_passes = 35
            self.method = "gutmann"
        else:  
            self.total_passes = self.spn_passes.get_value_as_int()
            self.method = "custom"
        
        self.set_controls_sensitive(False)
        self.btn_start.set_sensitive(False)
        self.btn_stop.set_sensitive(True)
        self.stop_event.clear()
        self.current_pass = 0
        self.bytes_written_total = 0
        self.start_time = time.time()
        
        self.overwrite_thread = threading.Thread(target=self.overwrite_device)
        self.overwrite_thread.daemon = True
        self.overwrite_thread.start()

    def set_controls_sensitive(self, sensitive):
        self.cmb_devices.set_sensitive(sensitive)
        self.cmb_method.set_sensitive(sensitive)
        self.spn_passes.set_sensitive(sensitive and self.cmb_method.get_active() == 3)

    def on_stop_clicked(self, button):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Confirm Abort"
        )
        dialog.format_secondary_text(
            "Are you sure you want to abort the erase process?\n"
            "Partial data may still be recoverable."
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.stop_event.set()
            self.btn_stop.set_sensitive(False)

    def overwrite_device(self):
        try:
            for pass_num in range(1, self.total_passes + 1):
                if self.stop_event.is_set():
                    break
                    
                self.current_pass = pass_num
                pattern = self.get_pattern_for_pass(pass_num)
                
                with open(self.device, 'wb') as f:
                    bytes_written = 0
                    while bytes_written < self.device_size and not self.stop_event.is_set():
                        chunk = self.generate_chunk(pattern, bytes_written)
                        f.write(chunk)
                        bytes_written += len(chunk)
                        self.bytes_written_total += len(chunk)
                        
                        if bytes_written % (10 * self.CHUNK_SIZE) == 0:
                            self.update_progress(bytes_written, pass_num)
                    
                    self.update_progress(bytes_written, pass_num)
            
            GLib.idle_add(self.operation_complete)
            
        except Exception as e:
            GLib.idle_add(self.show_error, f"Erase failed: {str(e)}")
        finally:
            self.stop_event.clear()

    def get_pattern_for_pass(self, pass_num):
        if self.method == "zero":
            return b'\x00' * self.CHUNK_SIZE
        elif self.method == "dod":
            if pass_num == 1: return os.urandom(self.CHUNK_SIZE)
            elif pass_num == 2: return b'\xff' * self.CHUNK_SIZE
            else: return os.urandom(self.CHUNK_SIZE)
        elif self.method == "gutmann":
            if pass_num in [1, 2, 35, 36]:
                return os.urandom(self.CHUNK_SIZE)
            else:
                return bytes([pass_num % 256] * self.CHUNK_SIZE)
        else:  
            return os.urandom(self.CHUNK_SIZE)

    def generate_chunk(self, pattern, position):
        if isinstance(pattern, bytes):
            chunk_size = min(self.CHUNK_SIZE, self.device_size - position)
            return pattern[:chunk_size]
        return pattern(self.CHUNK_SIZE)

    def update_progress(self, bytes_written, current_pass):
        progress_pass = bytes_written / self.device_size
        progress_total = self.bytes_written_total / (self.device_size * self.total_passes)
        
        elapsed = time.time() - self.start_time
        speed = self.bytes_written_total / max(elapsed, 0.001)  
        remaining_bytes = (self.device_size * self.total_passes) - self.bytes_written_total
        eta = remaining_bytes / max(speed, 1)
        
        GLib.idle_add(self.update_ui_progress, progress_pass, progress_total,
                     current_pass, self.bytes_written_total, eta)

    def update_ui_progress(self, pass_prog, total_prog, current_pass, total_written, eta):
        self.progress_pass.set_fraction(pass_prog)
        self.progress_total.set_fraction(total_prog)
        
        total_size = self.device_size * self.total_passes
        written_gib = total_written / (1024**3)
        total_gib = total_size / (1024**3)
        speed_mbs = (total_written / (1024**2)) / max(time.time() - self.start_time, 1)
        
        self.lbl_pass.set_text(
            f"Current Pass {current_pass}/{self.total_passes}: "
            f"{pass_prog*100:.1f}% Complete"
        )
        self.lbl_total.set_text(
            f"Total Progress: {written_gib:.2f} GiB of {total_gib:.2f} GiB "
            f"({total_prog*100:.1f}%)"
        )
        self.lbl_stats.set_text(
            f"Speed: {speed_mbs:.1f} MB/s • Elapsed: {self.format_time(time.time() - self.start_time)} "
            f"• Remaining: {self.format_time(eta)}"
        )

    def format_time(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def operation_complete(self):
        self.set_controls_sensitive(True)
        self.btn_start.set_sensitive(True)
        self.btn_stop.set_sensitive(False)
        
        if self.stop_event.is_set():
            self.show_info("Operation Aborted", "The erase process was cancelled by user.")
        else:
            self.show_info("Operation Completed", 
                          f"Disk overwrite finished successfully.\n"
                          f"Total passes: {self.total_passes}\n"
                          f"Total data written: {self.bytes_written_total / (1024**3):.2f} GiB")
        
        self.progress_pass.set_fraction(0)
        self.progress_total.set_fraction(0)
        self.lbl_pass.set_text("")
        self.lbl_total.set_text("")
        self.lbl_stats.set_text("")

    def show_method_help(self, button):
        method = self.cmb_method.get_active()
        
        if method == 0:  
            title = "Single Zero Pass"
            message = ("Writes all zeros to the disk in a single pass.\n\n"
                      "• Fastest method\n"
                      "• Basic protection against casual recovery\n"
                      "• Not secure against advanced forensic techniques")
        elif method == 1:  
            title = "DoD 5220.22-M Standard"
            message = ("Uses the 3-pass DoD 5220.22-M erasure standard:\n"
                      "1. Random data\n"
                      "2. Complementary data (0xFF)\n"
                      "3. Random data\n\n"
                      "• Good balance between speed and security\n"
                      "• Meets US Department of Defense standards\n"
                      "• Effective against most recovery methods")
        elif method == 2:  
            title = "Gutmann Method"
            message = ("35-pass secure erase method developed by Peter Gutmann.\n\n"
                      "• Most secure method\n"
                      "• Designed for older magnetic media\n"
                      "• Overkill for modern storage devices\n"
                      "• Very slow - can take many hours")
        else:  
            title = "Custom Passes"
            message = ("Custom number of passes with random data.\n\n"
                      "• Choose your own security level\n"
                      "• Each pass writes different random data\n"
                      "• More passes = more secure but slower")
        
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

    def show_info(self, title, message):
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

if __name__ == "__main__":

    if os.geteuid() != 0:
        print("Error: This program must be run as root.")
        exit(1)
        
    app = DiskOverwriter()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()
