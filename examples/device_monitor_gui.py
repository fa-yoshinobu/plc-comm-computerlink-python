#!/usr/bin/env python
import argparse
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Dict, Optional

from toyopuc import ToyopucHighLevelClient, resolve_device


class MonitorApp:
    def __init__(self, root: tk.Tk, args):
        self.root = root
        self.args = args
        self.root.title('toyopuc Device Monitor')
        self.client: Optional[ToyopucHighLevelClient] = None
        self.poll_job = None
        self.last_values: Dict[str, object] = {}
        self.units: Dict[str, str] = {}
        self.interval_ms = int(args.interval * 1000)

        self._build_ui()
        self._connect()
        for device in args.watch:
            self._add_device(device)
        self._schedule_poll()
        self.root.protocol('WM_DELETE_WINDOW', self._on_close)

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill='x')

        self.device_var = tk.StringVar(value='D0000')
        self.value_var = tk.StringVar(value='0x1234')
        self.interval_var = tk.StringVar(value=f'{self.args.interval:.1f}')

        ttk.Label(top, text='Device').grid(row=0, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.device_var, width=18).grid(row=0, column=1, sticky='w')
        ttk.Button(top, text='Add', command=self._on_add).grid(row=0, column=2, padx=4)
        ttk.Button(top, text='Remove', command=self._on_remove).grid(row=0, column=3, padx=4)
        ttk.Button(top, text='Read', command=self._on_read).grid(row=0, column=4, padx=4)

        ttk.Label(top, text='Value').grid(row=1, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.value_var, width=18).grid(row=1, column=1, sticky='w')
        ttk.Button(top, text='Write', command=self._on_write).grid(row=1, column=2, padx=4)
        ttk.Button(top, text='Clock', command=self._on_clock).grid(row=1, column=3, padx=4)
        ttk.Button(top, text='Status', command=self._on_status).grid(row=1, column=4, padx=4)

        ttk.Label(top, text='Interval(s)').grid(row=2, column=0, sticky='w')
        ttk.Entry(top, textvariable=self.interval_var, width=18).grid(row=2, column=1, sticky='w')
        ttk.Button(top, text='Apply', command=self._on_interval).grid(row=2, column=2, padx=4)
        ttk.Button(top, text='Poll now', command=self._poll_once).grid(row=2, column=3, padx=4)

        table_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        table_frame.pack(fill='both', expand=True)

        self.tree = ttk.Treeview(table_frame, columns=('scheme', 'unit', 'value', 'updated'), show='headings', height=16)
        self.tree.heading('scheme', text='Scheme')
        self.tree.heading('unit', text='Unit')
        self.tree.heading('value', text='Value')
        self.tree.heading('updated', text='Updated')
        self.tree.column('scheme', width=110, anchor='w')
        self.tree.column('unit', width=60, anchor='center')
        self.tree.column('value', width=120, anchor='w')
        self.tree.column('updated', width=150, anchor='w')
        self.tree.pack(side='left', fill='both', expand=True)
        self.tree.tag_configure('changed', background='#fff2b3')
        self.tree.tag_configure('error', background='#ffd6d6')

        yscroll = ttk.Scrollbar(table_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side='right', fill='y')

        log_frame = ttk.Frame(self.root, padding=(8, 0, 8, 8))
        log_frame.pack(fill='both', expand=False)
        ttk.Label(log_frame, text='Log').pack(anchor='w')
        self.log_text = tk.Text(log_frame, height=8, width=100)
        self.log_text.pack(fill='both', expand=True)

    def _connect(self):
        self.client = ToyopucHighLevelClient(
            self.args.host,
            self.args.port,
            protocol=self.args.protocol,
            local_port=self.args.local_port,
            timeout=self.args.timeout,
            retries=self.args.retries,
        )
        self.client.connect()
        self._log(f'connected: {self.args.host}:{self.args.port} ({self.args.protocol})')

    def _log(self, line: str):
        self.log_text.insert('end', line + '\n')
        self.log_text.see('end')

    def _format_value(self, unit: str, value: object) -> str:
        if unit == 'bit':
            return '1' if bool(value) else '0'
        if unit == 'byte':
            return f'0x{int(value) & 0xFF:02X}'
        return f'0x{int(value) & 0xFFFF:04X}'

    def _selected_device(self) -> Optional[str]:
        selection = self.tree.selection()
        if selection:
            return selection[0]
        device = self.device_var.get().strip().upper()
        return device or None

    def _add_device(self, device: str):
        resolved = resolve_device(device)
        key = resolved.text
        self.units[key] = resolved.unit
        if not self.tree.exists(key):
            self.tree.insert('', 'end', iid=key, values=(resolved.scheme, resolved.unit, '-', '-'))
        self._log(f'watch add: {key}')

    def _on_add(self):
        try:
            self._add_device(self.device_var.get())
        except Exception as exc:
            messagebox.showerror('Add device', str(exc))

    def _on_remove(self):
        device = self._selected_device()
        if not device:
            return
        if self.tree.exists(device):
            self.tree.delete(device)
        self.units.pop(device, None)
        self.last_values.pop(device, None)
        self._log(f'watch remove: {device}')

    def _on_read(self):
        device = self._selected_device()
        if not device:
            return
        try:
            resolved = resolve_device(device)
            value = self.client.read(device)
            self._log(f'{resolved.text} = {self._format_value(resolved.unit, value)}')
        except Exception as exc:
            messagebox.showerror('Read', str(exc))

    def _parse_write_value(self, device: str, text: str) -> int:
        resolved = resolve_device(device)
        value = int(text, 0)
        if resolved.unit == 'bit' and value not in (0, 1):
            raise ValueError('bit value must be 0 or 1')
        if resolved.unit == 'byte' and not 0 <= value <= 0xFF:
            raise ValueError('byte value must be 0x00-0xFF')
        if resolved.unit == 'word' and not 0 <= value <= 0xFFFF:
            raise ValueError('word value must be 0x0000-0xFFFF')
        return value

    def _on_write(self):
        device = self._selected_device()
        if not device:
            return
        try:
            value = self._parse_write_value(device, self.value_var.get().strip())
            self.client.write(device, value)
            unit = resolve_device(device).unit
            self._log(f'{device} <= {self._format_value(unit, value)}')
            self._poll_once()
        except Exception as exc:
            messagebox.showerror('Write', str(exc))

    def _on_clock(self):
        try:
            clock = self.client.read_clock()
            try:
                dt = clock.as_datetime().isoformat(sep=' ')
            except Exception:
                dt = 'unavailable'
            self._log(
                f'clock: second={clock.second:02d} minute={clock.minute:02d} hour={clock.hour:02d} '
                f'day={clock.day:02d} month={clock.month:02d} year={clock.year_2digit:02d} weekday={clock.weekday} ({dt})'
            )
        except Exception as exc:
            messagebox.showerror('Clock', str(exc))

    def _on_status(self):
        try:
            status = self.client.read_cpu_status()
            self._log(
                f'status: raw={status.raw_hex()} '
                f'RUN={status.run} '
                f'Under a stop={status.under_stop} '
                f'Alarm={status.alarm} '
                f'PC10 mode={status.pc10_mode} '
                f'Under program 1 running={status.program1_running} '
                f'Under program 2 running={status.program2_running} '
                f'Under program 3 running={status.program3_running}'
            )
        except Exception as exc:
            messagebox.showerror('Status', str(exc))

    def _on_interval(self):
        try:
            self.interval_ms = int(float(self.interval_var.get()) * 1000)
            self._log(f'interval set: {self.interval_ms} ms')
            self._schedule_poll(reset=True)
        except Exception as exc:
            messagebox.showerror('Interval', str(exc))

    def _poll_once(self):
        for device in self.tree.get_children(''):
            unit = self.units[device]
            try:
                value = self.client.read(device)
                formatted = self._format_value(unit, value)
                changed = device in self.last_values and self.last_values[device] != value
                self.last_values[device] = value
                self.tree.item(device, values=(resolve_device(device).scheme, unit, formatted, datetime.now().strftime('%H:%M:%S')), tags=('changed',) if changed else ())
            except Exception as exc:
                self.tree.item(device, values=(resolve_device(device).scheme, unit, f'ERROR: {exc}', datetime.now().strftime('%H:%M:%S')), tags=('error',))
        self._schedule_poll()

    def _schedule_poll(self, reset: bool = False):
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
            self.poll_job = None
        self.poll_job = self.root.after(self.interval_ms, self._poll_once)

    def _on_close(self):
        if self.poll_job is not None:
            self.root.after_cancel(self.poll_job)
        if self.client is not None:
            try:
                self.client.close()
            except Exception:
                pass
        self.root.destroy()


def main() -> int:
    # Tkinter example monitor for periodic reads and simple writes.
    parser = argparse.ArgumentParser(description='Tkinter device monitor example for toyopuc-computerlink')
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--protocol', choices=['tcp', 'udp'], default='tcp')
    parser.add_argument('--local-port', type=int, default=0)
    parser.add_argument('--timeout', type=float, default=3.0)
    parser.add_argument('--retries', type=int, default=0)
    parser.add_argument('--interval', type=float, default=1.0)
    parser.add_argument('--watch', nargs='*', default=['M0000', 'D0000'])
    args = parser.parse_args()

    root = tk.Tk()
    MonitorApp(root, args)
    root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
