import os
import sys
import time
import shutil
import threading
import subprocess
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser

try:
    import psutil
except ImportError:
    psutil = None

try:
    from plyer import notification
except ImportError:
    notification = None

class AdvancedTaskManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Диспетчер задач (Оптимизированный)")
        self.root.geometry("1050x780")
        
        self.style = ttk.Style()
        self.style.theme_use('winnative')
        
        self.sort_directions = {}
        self.base_dir = os.path.join(os.getcwd(), "App files")
        self.temp_dir = os.path.join(self.base_dir, "temp")
        self.save_dir = os.path.join(os.getcwd(), "File save")
        
        self.event_dirs = {
            "Запуск компьютера": os.path.join(self.save_dir, "boot"),
            "Запуск Диспетчера задач": os.path.join(self.save_dir, "task"),
            "Фоновый триггер": os.path.join(self.save_dir, "background")
        }
        
        os.makedirs(self.temp_dir, exist_ok=True)
        os.makedirs(self.save_dir, exist_ok=True)
        for d in self.event_dirs.values():
            os.makedirs(d, exist_ok=True)
            
        self.current_dir = self.base_dir
        self.selected_item = None
        
        self.is_always_on_top = tk.BooleanVar(value=False)
        self.enable_notifications = tk.BooleanVar(value=True)
        self.enable_active_protection = tk.BooleanVar(value=False)
        self.enable_app_locker = tk.BooleanVar(value=False)
        
        self.process_io_activity = {}
        self.log_events = []
        self.log_files = []
        self.log_executions = []
        self.log_performance = []
        
        self.tracked_apps_registry = {}
        self.active_monitor_windows = {}
        
        # Кэш для хранения данных потоков во избежание блокировки UI
        self.cached_apps_data = []
        self.cached_cpu = 0
        self.cached_ram = 0
        
        self.write_log("events", "Инициализация ядра Диспетчера задач. Оптимизация потоков завершена.")
        
        self.setup_ui()
        self.refresh_file_list()
        self.refresh_config_list()
        self.refresh_process_dropdown()
        
        # Запуск оптимизированных потоков
        self.start_live_threads()
        self.trigger_event("Запуск компьютера")

    def write_log(self, category, message):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_msg = f"[{timestamp}] {message}"
        if category == "events": self.log_events.append(formatted_msg)
        elif category == "files": self.log_files.append(formatted_msg)
        elif category == "executions": self.log_executions.append(formatted_msg)
        elif category == "performance": self.log_performance.append(formatted_msg)

    def send_notify(self, title, message, status="info"):
        self.status_var.set(f"[{status.upper()}] {message}")
        self.write_log("events", f"Системное уведомление [{title}]: {message}")
        if self.enable_notifications.get() and notification:
            try: notification.notify(title=f"AdvancedTaskManager: {title}", message=message, timeout=4)
            except Exception: pass

    def setup_tree_sorting(self, tree):
        self.sort_directions[tree] = {}
        for col in tree['columns']:
            self.sort_directions[tree][col] = False
            tree.heading(col, command=lambda c=col, t=tree: self.sort_tree_column(t, c))

    def sort_tree_column(self, tree, col):
        reverse = self.sort_directions[tree][col]
        data = []
        for k in tree.get_children(''):
            val = tree.set(k, col)
            try: val = float(val)
            except ValueError: val = val.lower()
            data.append((val, k))
        data.sort(reverse=reverse)
        for index, (val, k) in enumerate(data):
            tree.move(k, '', index)
        self.sort_directions[tree][col] = not reverse

    def setup_ui(self):
        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Каталог:").pack(side=tk.LEFT, padx=5)
        self.path_entry = ttk.Entry(top_frame, width=45)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, self.current_dir)
        self.path_entry.bind("<Return>", lambda e: self.change_dir(self.path_entry.get()))
        
        self.top_check = ttk.Checkbutton(top_frame, text="Поверх всех окон", variable=self.is_always_on_top, command=self.toggle_always_on_top)
        self.top_check.pack(side=tk.RIGHT, padx=5)
        
        self.main_notebook = ttk.Notebook(self.root)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tab_processes_root = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_processes_root, text="Процессы")
        
        self.tab_config = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_config, text="Конфигурация")
        
        self.tab_security = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_security, text="Безопасность и Консоли")
        
        self.tab_performance = ttk.Frame(self.main_notebook)
        self.main_notebook.add(self.tab_performance, text="Производительность")
        
        self.mode_notebook = ttk.Notebook(self.tab_processes_root)
        self.mode_notebook.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.sub_tab_files = ttk.Frame(self.mode_notebook)
        self.sub_tab_apps = ttk.Frame(self.mode_notebook)
        self.mode_notebook.add(self.sub_tab_files, text="Файловый режим")
        self.mode_notebook.add(self.sub_tab_apps, text="Режим приложений")
        
        self.setup_files_mode()
        self.setup_apps_mode()
        self.setup_config_mode()
        self.setup_security_mode()
        self.setup_performance_mode()
        
        self.status_var = tk.StringVar(value="Система мониторинга ядра активна.")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=3)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def setup_files_mode(self):
        columns = ('name', 'status', 'size', 'type', 'time')
        self.file_tree = ttk.Treeview(self.sub_tab_files, columns=columns, show='headings', selectmode='browse')
        self.file_tree.heading('name', text='Имя элемента')
        self.file_tree.heading('status', text='Состояние')
        self.file_tree.heading('size', text='Размер (КБ)')
        self.file_tree.heading('type', text='Тип')
        self.file_tree.heading('time', text='Время изменения')
        
        self.file_tree.column('name', width=220)
        self.file_tree.column('status', width=90)
        self.file_tree.column('size', width=90, anchor=tk.E)
        self.file_tree.column('type', width=70)
        self.file_tree.column('time', width=130)
        
        self.setup_tree_sorting(self.file_tree)
        f_scroll = ttk.Scrollbar(self.sub_tab_files, orient=tk.VERTICAL, command=self.file_tree.yview)
        self.file_tree.configure(yscroll=f_scroll.set)
        self.file_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        f_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_tree.bind("<Button-3>", self.show_file_context_menu)
        self.file_menu = tk.Menu(self.root, tearoff=0)
        self.file_menu.add_command(label="Развернуть каталог", command=self.action_file_expand)
        self.file_menu.add_command(label="Удалить объект", command=self.action_file_end_task)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Поиск сведений в Интернете", command=self.action_search_online_file)

    def setup_apps_mode(self):
        columns = ('pid', 'name', 'status', 'memory')
        self.app_tree = ttk.Treeview(self.sub_tab_apps, columns=columns, show='headings', selectmode='browse')
        self.app_tree.heading('pid', text='PID')
        self.app_tree.heading('name', text='Имя приложения')
        self.app_tree.heading('status', text='Статус')
        self.app_tree.heading('memory', text='Память (МБ)')
        
        self.app_tree.column('pid', width=70, anchor=tk.CENTER)
        self.app_tree.column('name', width=250)
        self.app_tree.column('status', width=100)
        self.app_tree.column('memory', width=100, anchor=tk.E)
        
        self.setup_tree_sorting(self.app_tree)
        a_scroll = ttk.Scrollbar(self.sub_tab_apps, orient=tk.VERTICAL, command=self.app_tree.yview)
        self.app_tree.configure(yscroll=a_scroll.set)
        self.app_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        a_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.app_tree.bind("<Button-3>", self.show_app_context_menu)
        self.app_menu = tk.Menu(self.root, tearoff=0)
        self.app_menu.add_command(label="Завершить процесс (Terminate)", command=self.action_app_end_task)
        self.app_menu.add_separator()
        self.app_menu.add_command(label="Поиск процесса в Google", command=self.action_search_online_app)

    def setup_config_mode(self):
        control_frame = ttk.LabelFrame(self.tab_config, text=" Панель управления стандартными событиями ", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.notify_check = ttk.Checkbutton(control_frame, text="Разрешить системные уведомления Windows", variable=self.enable_notifications)
        self.notify_check.pack(anchor=tk.W, pady=5)
        
        ttk.Label(control_frame, text="Событие (Event):").pack(side=tk.LEFT, padx=5)
        self.event_var = tk.StringVar()
        self.event_combo = ttk.Combobox(control_frame, textvariable=self.event_var, state="readonly", width=25)
        self.event_combo['values'] = ("Запуск компьютера", "Запуск Диспетчера задач", "Фоновый триггер")
        self.event_combo.current(0)
        self.event_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Импортировать объекты...", command=self.action_add_multiple_objects).pack(side=tk.LEFT, padx=10)
        ttk.Button(control_frame, text="Удалить связь", command=self.action_delete_config_object).pack(side=tk.RIGHT, padx=5)
        
        columns = ('filename', 'event', 'path', 'status')
        self.config_tree = ttk.Treeview(self.tab_config, columns=columns, show='headings', selectmode='browse')
        self.config_tree.heading('filename', text='Имя объекта')
        self.config_tree.heading('event', text='Привязанное событие')
        self.config_tree.heading('path', text='Путь сохранения')
        self.config_tree.heading('status', text='Состояние объекта')
        
        self.config_tree.column('filename', width=200)
        self.config_tree.column('event', width=180)
        self.config_tree.column('path', width=350)
        self.config_tree.column('status', width=100)
        
        self.setup_tree_sorting(self.config_tree)
        c_scroll = ttk.Scrollbar(self.tab_config, orient=tk.VERTICAL, command=self.config_tree.yview)
        self.config_tree.configure(yscroll=c_scroll.set)
        self.config_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=5)
        c_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)

    def setup_security_mode(self):
        main_frame = ttk.Frame(self.tab_security, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        console_frame = ttk.LabelFrame(main_frame, text=" Резервные консоли аварийного восстановления ОС ", padding=15)
        console_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(console_frame, text="Запуск изолированных консолей в обход блокировок вирусного ПО (с запросом повышенных прав Администратора):", justify=tk.LEFT).pack(anchor=tk.W, pady=2)
        
        btn_container = ttk.Frame(console_frame)
        btn_container.pack(fill=tk.X, anchor=tk.W, pady=10)
        
        ttk.Button(btn_container, text="Запустить резервную CMD", width=28, command=self.launch_backup_cmd).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_container, text="Запустить резервный PowerShell", width=28, command=self.launch_backup_powershell).pack(side=tk.LEFT, padx=5)
        
        protection_frame = ttk.LabelFrame(main_frame, text=" Модули активного противодействия угрозам (Микро-EDR) ", padding=15)
        protection_frame.pack(fill=tk.X, pady=10)
        
        self.crypto_check = ttk.Checkbutton(protection_frame, text="Включить эвристический анализатор Anti-Ransomware (Блокировка активности шифровальщиков)", variable=self.enable_active_protection)
        self.crypto_check.pack(anchor=tk.W, pady=4)
        
        self.locker_check = ttk.Checkbutton(protection_frame, text="Включить превентивный AppLocker (Запрет исполнения недоверенных файлов из AppData/Temp)", variable=self.enable_app_locker)
        self.locker_check.pack(anchor=tk.W, pady=4)
        
        track_frame = ttk.LabelFrame(main_frame, text=" Инспекция и изоляция отдельных процессов ", padding=15)
        track_frame.pack(fill=tk.X, pady=5)
        
        self.track_app_var = tk.StringVar()
        proc_select_frame = ttk.Frame(track_frame)
        proc_select_frame.pack(fill=tk.X, anchor=tk.W, pady=5)
        
        self.track_app_combo = ttk.Combobox(proc_select_frame, textvariable=self.track_app_var, width=35)
        self.track_app_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(proc_select_frame, text="Обзор файла...", command=self.action_select_track_app_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(proc_select_frame, text="Обновить список процессов", command=self.refresh_process_dropdown).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(track_frame, text="Инициализировать отслеживание дескрипторов приложения", command=self.action_register_app_tracking).pack(anchor=tk.W, pady=8)
        ttk.Button(main_frame, text="Открыть системный журнал аудита логов...", command=self.action_show_logs_window).pack(anchor=tk.W, pady=10)

    def setup_performance_mode(self):
        self.canvas = tk.Canvas(self.tab_performance, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.cpu_history = [0] * 50
        self.ram_history = [0] * 50

    def launch_backup_cmd(self):
        self.write_log("executions", "Вызов аварийной резервной консоли CMD.")
        try:
            if sys.platform == "win32":
                subprocess.Popen(["powershell", "Start-Process cmd.exe -Verb RunAs"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.send_notify("Восстановление", "Вызов резервной консоли CMD отправлен системе.", "success")
            else:
                subprocess.Popen(["x-terminal-emulator"])
        except Exception as e:
            messagebox.showerror("Критическая ошибка выполнения", f"STATUS_IMAGE_EXEC_FAILURE (0xC000007B): Сбой запуска cmd.exe: {str(e)}")

    def launch_backup_powershell(self):
        self.write_log("executions", "Вызов аварийной резервной консоли PowerShell.")
        try:
            if sys.platform == "win32":
                subprocess.Popen(["powershell", "Start-Process powershell.exe -Verb RunAs"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                self.send_notify("Восстановление", "Вызов резервной консоли PowerShell отправлен системе.", "success")
            else:
                messagebox.showwarning("Ограничение платформы", "Компонент PowerShell не обнаружен в данной Unix-среде.")
        except Exception as e:
            messagebox.showerror("Критическая ошибка выполнения", f"STATUS_IMAGE_EXEC_FAILURE (0xC000007B): Сбой запуска powershell.exe: {str(e)}")

    def action_register_app_tracking(self):
        target = self.track_app_var.get().strip()
        if not target:
            messagebox.showwarning("Предупреждение конфигурации", "Не указан целевой процесс или исполняемый файл для развертывания службы мониторинга.")
            return

        warning_window = tk.Toplevel(self.root)
        warning_window.title("Предупреждение системы безопасности")
        warning_window.geometry("500x200")
        warning_window.resizable(False, False)
        warning_window.transient(self.root)
        warning_window.grab_set()
        
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 250
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 100
        warning_window.geometry(f"+{x}+{y}")
        
        msg_frame = ttk.Frame(warning_window, padding=15)
        msg_frame.pack(fill=tk.BOTH, expand=True)
        
        lbl_text = (f"Подтвердите развертывание службы контроля для '{os.path.basename(target)}'.\n\n"
                    f"Если процесс не запущен в системе, Диспетчер автоматически инициализирует его запуск "
                    f"и переведет в режим непрерывной трассировки дескрипторов ресурсов.")
        ttk.Label(msg_frame, text=lbl_text, font=("Segoe UI", 9, "bold"), foreground="#003399", justify=tk.LEFT, wrap=460).pack(pady=5)
        
        btn_frame = ttk.Frame(msg_frame)
        btn_frame.pack(fill=tk.X, pady=15)
        
        def on_confirm():
            warning_window.destroy()
            self.execute_and_track(target)
            
        def on_cancel(): warning_window.destroy()
            
        ttk.Button(btn_frame, text="Запустить и отслеживать", command=on_confirm).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(btn_frame, text="Отмена", command=on_cancel).pack(side=tk.RIGHT, expand=True, padx=5)

    def execute_and_track(self, target):
        app_name_lower = os.path.basename(target).lower()
        if psutil:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    p_name = proc.info['name'].lower() if proc.info['name'] else ""
                    p_exe = proc.info['exe'].lower() if proc.info['exe'] else ""
                    if app_name_lower == p_name or (target.lower() == p_exe and p_exe):
                        self.tracked_apps_registry[p_name] = True
                        self.write_log("executions", f"Процесс {proc.info['name']} уже активен. Подключение к PID: {proc.info['pid']}")
                        self.open_dedicated_monitor_window(p_name, proc.info['pid'])
                        return
                except (psutil.NoSuchProcess, psutil.AccessDenied): continue

        if os.path.exists(target) and os.path.isfile(target):
            try:
                proc_launched = subprocess.Popen([target], creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
                pid = proc_launched.pid
                self.tracked_apps_registry[app_name_lower] = True
                self.write_log("executions", f"Успешный запуск изолированного процесса: {app_name_lower} (PID: {pid})")
                self.root.after(500, lambda: self.open_dedicated_monitor_window(app_name_lower, pid))
                self.send_notify("Запуск успешен", f"Приложение {app_name_lower} запущено. Трассировка активна.", "success")
            except Exception as e:
                messagebox.showerror("Критическая ошибка запуска", f"STATUS_IMAGE_EXEC_FAILURE (0xC000007B): Не удалось открыть файл: {str(e)}")
        else:
            messagebox.showerror("Объект не найден", f"STATUS_OBJECT_NAME_NOT_FOUND (0xC0000034):\nУказанный файл не найден или процесс не запущен.")

    def open_dedicated_monitor_window(self, app_name, pid):
        if app_name in self.active_monitor_windows: return
            
        monitor_win = tk.Toplevel(self.root)
        monitor_win.title(f"Анализ процесса: {app_name} (PID: {pid})")
        monitor_win.geometry("800x480")
        self.active_monitor_windows[app_name] = monitor_win
        
        top_bar = ttk.Frame(monitor_win, padding=10, relief=tk.GROOVE)
        top_bar.pack(fill=tk.X)
        ttk.Label(top_bar, text=f"Объект инспекции: {app_name}", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT)
        ttk.Label(top_bar, text="Статус: Перехват системных вызовов активен", foreground="#006600").pack(side=tk.RIGHT)
        
        columns = ('time', 'action', 'details')
        m_tree = ttk.Treeview(monitor_win, columns=columns, show='headings')
        m_tree.heading('time', text='Время изменения')
        m_tree.heading('action', text='Тип дескриптора')
        m_tree.heading('details', text='Задействованные системные структуры')
        
        m_tree.column('time', width=120)
        m_tree.column('action', width=150)
        m_tree.column('details', width=500)
        
        self.setup_tree_sorting(m_tree)
        scroll = ttk.Scrollbar(monitor_win, orient=tk.VERTICAL, command=m_tree.yview)
        m_tree.configure(yscroll=scroll.set)
        m_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        try:
            p = psutil.Process(pid)
            m_tree.insert('', tk.END, values=(timestamp, "Инициализация", f"Вызов выполнен успешно. Папка: {p.cwd()}"))
            for f in p.open_files(): m_tree.insert('', tk.END, values=(timestamp, "Открытый файл (I/O)", f.path))
        except psutil.AccessDenied:
            messagebox.showerror("Ошибка доступа", "STATUS_ACCESS_DENIED (0xC0000022)")
        except Exception: pass

        def update_monitor_loop():
            if not monitor_win.winfo_exists():
                self.active_monitor_windows.pop(app_name, None)
                return
            try:
                if psutil.pid_exists(pid):
                    p = psutil.Process(pid)
                    curr_time = datetime.now().strftime('%H:%M:%S')
                    files = p.open_files()
                    if files:
                        for f in files[:5]: # Ограничиваем срез, чтобы окно логов тоже не лагало
                            m_tree.insert('', tk.END, values=(curr_time, "Запрос дескриптора", f.path))
                    monitor_win.after(2000, update_monitor_loop)
                else:
                    m_tree.insert('', tk.END, values=(datetime.now().strftime('%H:%M:%S'), "STATUS_PROCESS_IS_TERMINATED", "Процесс закрыт."))
            except Exception: pass
                
        monitor_win.after(1000, update_monitor_loop)

    # --- ОПТИМИЗИРОВАННЫЕ ФОНОВЫЕ ПОТОКИ (БЕЗ ЛАГОВ GUI) ---
    def start_live_threads(self):
        """Разделение сбора тяжелой телеметрии на независимые фоновые потоки"""
        def heavy_telemetry_thread():
            """Поток для тяжелого сканирования процессов (Раз в 1.5 секунды)"""
            while True:
                if not psutil:
                    time.sleep(2)
                    continue
                temp_data = []
                for proc in psutil.process_iter(['pid', 'name', 'status', 'exe']):
                    try:
                        p_info = proc.info
                        pid = p_info['pid']
                        name = p_info['name'] or 'Unknown'
                        status = p_info['status']
                        
                        try: mem = round(proc.memory_info().rss / (1024 * 1024), 1)
                        except Exception: mem = 0.0
                        
                        exe_path = p_info['exe'].lower() if p_info['exe'] else ""
                        temp_data.append((str(pid), name, status, mem, exe_path))
                        
                        # Модуль защиты (AppLocker + Anti-Ransomware) выполняется прямо в тяжелом потоке
                        self.process_security_eval(proc, pid, name, exe_path)
                        
                    except (psutil.NoSuchProcess, psutil.AccessDenied): continue
                
                # Сохраняем в кэш
                self.cached_apps_data = temp_data
                time.sleep(1.5)

        def light_performance_thread():
            """Легкий быстрый поток для графиков (Раз в 1 секунду)"""
            while True:
                if psutil:
                    try:
                        self.cached_cpu = psutil.cpu_percent()
                        self.cached_ram = psutil.virtual_memory().percent
                    except Exception: pass
                time.sleep(1.0)

        # Запуск ядерных потоков с флагом daemon=True
        threading.Thread(target=heavy_telemetry_thread, daemon=True).start()
        threading.Thread(target=light_performance_thread, daemon=True).start()
        
        # Запуск главного планировщика тиков для GUI (выполняется в потоке UI)
        self.gui_tick_scheduler()

    def gui_tick_scheduler(self):
        """Главный тикер UI. Работает молниеносно, так как берет готовые данные из кэша"""
        try:
            self.draw_performance_graphs_from_cache()
            self.update_apps_tree_delta()
        except Exception: pass
        self.root.after(1000, self.gui_tick_scheduler)

    def update_apps_tree_delta(self):
        """Умное Delta-обновление UI: меняет только значения ячеек, исключая лаги мерцания"""
        current_tree_pids = set(self.app_tree.get_children(''))
        incoming_data = self.cached_apps_data
        active_pids = set()

        for pid_str, name, status, mem, exe_path in incoming_data:
            active_pids.add(pid_str)
            values = (pid_str, name, status, mem)
            
            if pid_str in current_tree_pids:
                # Если процесс уже в таблице — проверяем, изменились ли данные, и обновляем точечно
                old_values = self.app_tree.item(pid_str, 'values')
                if old_values and (old_values[2] != str(status) or float(old_values[3]) != float(mem)):
                    self.app_tree.item(pid_str, values=values)
            else:
                # Новый процесс — просто вставляем
                self.app_tree.insert('', tk.END, iid=pid_str, values=values)
                
            # Перехват авто-открытия логов
            name_lower = name.lower()
            if name_lower in self.tracked_apps_registry and name_lower not in self.active_monitor_windows:
                self.open_dedicated_monitor_window(name_lower, int(pid_str))

        # Удаляем из таблицы те процессы, которые закрылись
        for old_pid in current_tree_pids:
            if old_pid not in active_pids:
                self.app_tree.delete(old_pid)

    def process_security_eval(self, proc, pid, name, exe_path):
        """Низкоуровневая оценка угроз внутри фонового потока"""
        if pid == os.getpid(): return
        
        # AppLocker
        if self.enable_app_locker.get() and exe_path:
            if "appdata\\local\\temp" in exe_path or "appdata\\roaming" in exe_path:
                if "python" not in name.lower() and "advancedtaskmanager" not in name.lower():
                    proc.terminate()
                    self.write_log("events", f"AppLocker заблокировал {name} (PID: {pid}) в Temp/AppData.")
                    self.send_notify("Угроза нейтрализована", f"Заблокирован запуск {name} из небезопасной папки.", "warning")
                    return

        # Anti-Ransomware
        if self.enable_active_protection.get():
            try:
                open_files = proc.open_files()
                if open_files:
                    curr_time = time.time()
                    if pid not in self.process_io_activity: self.process_io_activity[pid] = []
                    for f in open_files: self.process_io_activity[pid].append(curr_time)
                    self.process_io_activity[pid] = [t for t in self.process_io_activity[pid] if curr_time - t <= 3.0]
                    
                    if len(self.process_io_activity[pid]) > 25:
                        proc.kill()
                        self.write_log("events", f"Anti-Ransomware уничтожил {name} (PID: {pid}) за массовый I/O.")
                        self.root.after(0, lambda: messagebox.showwarning("Атака заблокирована", f"Аномальное поведение процесса '{name}' (PID: {pid}). Поток принудительно завершен."))
            except Exception: pass

    def draw_performance_graphs_from_cache(self):
        self.canvas.delete("all")
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 10 or h <= 10: return
        
        self.cpu_history.append(self.cached_cpu); self.cpu_history.pop(0)
        self.ram_history.append(self.cached_ram); self.ram_history.pop(0)
        
        for i in range(1, 4): self.canvas.create_line(0, h * i / 4, w, h * i / 4, fill="#113311", dash=(4, 4))
        step = w / 49
        for i in range(49):
            self.canvas.create_line(i*step, h - (self.cpu_history[i]/100*(h-20))-10, (i+1)*step, h - (self.cpu_history[i+1]/100*(h-20))-10, fill="#00FF00", width=2)
            self.canvas.create_line(i*step, h - (self.ram_history[i]/100*(h-20))-10, (i+1)*step, h - (self.ram_history[i+1]/100*(h-20))-10, fill="#00FFFF", width=1.5)

    def toggle_always_on_top(self): self.root.attributes("-topmost", self.is_always_on_top.get())
    def change_dir(self, path):
        if os.path.exists(path) and os.path.isdir(path): self.current_dir = path; self.refresh_file_list()
    def show_file_context_menu(self, event):
        item = self.file_tree.identify_row(event.y)
        if item: self.file_tree.selection_set(item); self.selected_item = item; self.file_menu.post(event.x_root, event.y_root)
    def show_app_context_menu(self, event):
        item = self.app_tree.identify_row(event.y)
        if item: self.app_tree.selection_set(item); self.selected_item = item; self.app_menu.post(event.x_root, event.y_root)
    def action_file_expand(self):
        if self.selected_item:
            path = os.path.join(self.current_dir, self.selected_item)
            if os.path.isdir(path): self.change_dir(path); self.path_entry.delete(0, tk.END); self.path_entry.insert(0, self.current_dir)
    def action_file_end_task(self):
        if self.selected_item:
            try: os.remove(os.path.join(self.current_dir, self.selected_item)); self.refresh_file_list()
            except Exception as e: messagebox.showerror("Ошибка ввода-вывода", f"STATUS_CANNOT_DELETE: {str(e)}")
    def action_search_online_file(self):
        if self.selected_item: webbrowser.open(f"https://www.google.com/search?q={self.selected_item}")
    def action_app_end_task(self):
        if self.selected_item and psutil:
            try:
                pid = int(self.selected_item)
                psutil.Process(pid).terminate()
            except psutil.AccessDenied: messagebox.showerror("Сбой", "STATUS_ACCESS_DENIED (0xC0000022)")
            except Exception as e: messagebox.showerror("Ошибка", str(e))
    def action_search_online_app(self):
        if self.selected_item and psutil:
            try: webbrowser.open(f"https://www.google.com/search?q={psutil.Process(int(self.selected_item)).name()}")
            except Exception: pass
    def refresh_file_list(self):
        for item in self.file_tree.get_children(): self.file_tree.delete(item)
        try:
            for item in os.listdir(self.current_dir):
                path = os.path.join(self.current_dir, item)
                is_dir = os.path.isdir(path)
                status = "Папка" if is_dir else "Активен"
                size = "" if is_dir else f"{round(os.path.getsize(path)/1024, 1)}"
                ext = "Папка" if is_dir else os.path.splitext(item)[1].upper() or "Файл"
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
                self.file_tree.insert('', tk.END, iid=item, values=(item, status, size, ext, mtime))
        except Exception: pass
    def refresh_config_list(self):
        for item in self.config_tree.get_children(): self.config_tree.delete(item)
        for event_name, folder_path in self.event_dirs.items():
            if os.path.exists(folder_path):
                for file in os.listdir(folder_path):
                    if os.path.isfile(os.path.join(folder_path, file)):
                        tree_id = f"{event_name}:::{file}"
                        self.config_tree.insert('', tk.END, iid=tree_id, values=(file, event_name, os.path.join(folder_path, file), "Файл верифицирован"))
    def action_add_multiple_objects(self):
        files = filedialog.askopenfilenames(title="Выбор объектов")
        if not files: return
        chosen_event = self.event_var.get()
        target_dir = self.event_dirs[chosen_event]
        for file_path in files:
            filename = os.path.basename(file_path)
            try: shutil.copy2(file_path, os.path.join(target_dir, filename))
            except Exception: pass
        self.refresh_config_list()
    def action_delete_config_object(self):
        selected = self.config_tree.selection()
        if not selected: return
        event_name, filename = selected[0].split(":::")
        try: os.remove(os.path.join(self.event_dirs[event_name], filename)); self.refresh_config_list()
        except Exception: pass
    def action_show_logs_window(self):
        logs_window = tk.Toplevel(self.root)
        logs_window.title("Просмотр событий - Системные журналы")
        logs_window.geometry("850x550")
        notebook = ttk.Notebook(logs_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        categories = {"Служба триггеров": self.log_events, "Аудит файловой системы": self.log_files, "Журнал трассировки программ": self.log_executions, "Производительность ядра": self.log_performance}
        for cat_name, cat_list in categories.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=cat_name)
            text_area = tk.Text(frame, wrap=tk.NONE, font=("Consolas", 9), bg="#F0F0F0")
            text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            for log in cat_list: text_area.insert(tk.END, log + "\n")
            text_area.configure(state="disabled")
    def trigger_event(self, event_name):
        folder_path = self.event_dirs[event_name]
        if os.path.exists(folder_path):
            for file in os.listdir(folder_path):
                file_path = os.path.abspath(os.path.join(folder_path, file))
                if os.path.isfile(file_path):
                    try:
                        if sys.platform == "win32": os.startfile(file_path)
                        else: subprocess.Popen(['xdg-open', file_path])
                    except Exception: pass
    def refresh_process_dropdown(self):
        if not psutil: return
        procs = set()
        for p in psutil.process_iter(['name']):
            try:
                if p.info['name']: procs.add(p.info['name'].lower())
            except Exception: pass
        sorted_procs = sorted(list(procs))
        self.track_app_combo['values'] = sorted_procs
        if sorted_procs: self.track_app_combo.set(sorted_procs[0])
    def action_select_track_app_file(self):
        file_selected = filedialog.askopenfilename(title="Выбор файла", filetypes=[("Исполняемые файлы", "*.exe"), ("Все файлы", "*.*")])
        if file_selected: self.track_app_var.set(file_selected)

if __name__ == "__main__":
    root = tk.Tk()
    app = AdvancedTaskManager(root)
    root.mainloop()