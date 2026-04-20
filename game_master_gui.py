# game_master_gui.py
import socket
import threading
import time
from tkinter import *
from tkinter import ttk, messagebox, font
from shared_simple import *
from protocol import Framed, ProtocolError

class GameMasterGUI:
    def __init__(self):
        self.socket = None
        self.connected = False
        self.current_state = None
        
        # Цветовая схема
        self.colors = {
            'bg': '#0a0e27',
            'bg2': '#1a1f3a',
            'fg': '#ffffff',
            'accent1': '#00d4ff',
            'accent2': '#ff6b6b',
            'accent3': '#6bff6b',
            'accent4': '#ffd700',
            'panel': '#151a33',
            'text': '#e0e0ff'
        }
        
        # Создаем главное окно
        self.root = Tk()
        self.root.title("🎮 ГЕЙММАСТЕР - КОСМИЧЕСКИЙ БОЙ")
        self.root.geometry("1300x900")
        self.root.configure(bg=self.colors['bg'])
        
        # Переменные
        self.current_layer = IntVar(value=0)
        self.cells = [[None for _ in range(10)] for _ in range(10)]
        
        # Создаем интерфейс
        self.create_widgets()
        
        # Запускаем окно подключения
        self.show_connection_window()
    
    def create_widgets(self):
        """Создает основные виджеты интерфейса"""
        # Верхняя панель с заголовком
        header_frame = Frame(self.root, bg='#000000', height=80)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)
        
        # Заголовок
        title_label = Label(header_frame,
                           text="🎮 ГЕЙММАСТЕР - КОСМИЧЕСКИЙ БОЙ 10x10x10",
                           bg='#000000', fg=self.colors['accent4'],
                           font=('Arial', 20, 'bold'))
        title_label.pack(expand=True)
        
        subtitle_label = Label(header_frame,
                              text="ПОЛНАЯ ВИДИМОСТЬ • УПРАВЛЕНИЕ ИГРОЙ",
                              bg='#000000', fg='white',
                              font=('Arial', 12))
        subtitle_label.pack()
        
        # Статусная строка
        status_bar = Frame(self.root, bg=self.colors['panel'], height=30)
        status_bar.pack(fill=X, padx=10, pady=5)
        status_bar.pack_propagate(False)
        
        self.status_label = Label(status_bar, text="⚫ Не подключен",
                                  bg=self.colors['panel'], fg='red',
                                  font=('Arial', 10, 'bold'))
        self.status_label.pack(side=LEFT, padx=10)
        
        # Основной контейнер
        main_container = Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Левая панель - карта
        left_panel = Frame(main_container, bg=self.colors['bg'])
        left_panel.pack(side=LEFT, fill=BOTH, expand=True)
        
        # Правая панель - информация
        right_panel = Frame(main_container, bg=self.colors['bg'], width=400)
        right_panel.pack(side=RIGHT, fill=Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Создаем панели
        self.create_map_panel(left_panel)
        self.create_info_panel(right_panel)
        self.create_control_panel(right_panel)
        self.create_hits_panel(right_panel)
        self.create_stats_panel(right_panel)
        self.create_legend_panel(right_panel)
    
    def create_map_panel(self, parent):
        """Панель с картой"""
        map_frame = LabelFrame(parent, text="🗺️ КАРТА ПОЛЯ",
                               bg=self.colors['panel'], fg=self.colors['accent1'],
                               font=('Arial', 12, 'bold'))
        map_frame.pack(fill=BOTH, expand=True)
        
        # Управление слоями
        control_frame = Frame(map_frame, bg=self.colors['panel'])
        control_frame.pack(fill=X, padx=10, pady=10)
        
        Label(control_frame, text="🔽 Слой Z:",
              bg=self.colors['panel'], fg='white',
              font=('Arial', 11)).pack(side=LEFT)
        
        # Слайдер с отслеживанием изменений
        layer_scale = Scale(control_frame, from_=0, to=9, variable=self.current_layer,
                           orient=HORIZONTAL, length=300,
                           bg=self.colors['panel'], fg=self.colors['accent1'],
                           troughcolor=self.colors['bg2'],
                           activebackground=self.colors['accent1'],
                           highlightbackground=self.colors['panel'],
                           command=self.on_layer_change)  # Добавляем команду
        layer_scale.pack(side=LEFT, padx=10)
        
        self.layer_label = Label(control_frame, text="Z = 0",
                                bg=self.colors['panel'], fg=self.colors['accent1'],
                                font=('Arial', 14, 'bold'))
        self.layer_label.pack(side=LEFT, padx=10)
        
        Button(control_frame, text="🔄 ОБНОВИТЬ",
               bg=self.colors['accent1'], fg='black',
               font=('Arial', 10, 'bold'),
               command=self.update_map).pack(side=RIGHT)
        
        # Карта
        map_container = Frame(map_frame, bg=self.colors['bg2'], bd=2, relief=SUNKEN)
        map_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        map_grid = Frame(map_container, bg=self.colors['bg2'])
        map_grid.pack(expand=True)
        
        # Создаем сетку 10x10
        for row in range(10):
            for col in range(10):
                cell = Label(map_grid, text=" ", width=4, height=2,
                           relief=RAISED, borderwidth=2,
                           font=('Arial', 10, 'bold'),
                           bg=self.colors['bg2'], fg='white')
                cell.grid(row=row, column=col, padx=2, pady=2)
                self.cells[row][col] = cell
    
    def on_layer_change(self, value):
        """Обработчик изменения слоя"""
        layer = int(float(value))
        self.layer_label.config(text=f"Z = {layer}")
        self.update_map()
    
    def create_info_panel(self, parent):
        """Панель с информацией о ходе"""
        info_frame = LabelFrame(parent, text="📊 ИНФОРМАЦИЯ О ХОДЕ",
                                bg=self.colors['panel'], fg=self.colors['accent4'],
                                font=('Arial', 12, 'bold'))
        info_frame.pack(fill=X, pady=(0, 10))
        
        info_grid = Frame(info_frame, bg=self.colors['panel'])
        info_grid.pack(fill=X, padx=10, pady=10)
        
        # Ход
        Label(info_grid, text="Текущий ход:", bg=self.colors['panel'],
              fg='white').grid(row=0, column=0, sticky=W, pady=5)
        self.turn_label = Label(info_grid, text="0", bg=self.colors['panel'],
                                fg=self.colors['accent4'], font=('Arial', 12, 'bold'))
        self.turn_label.grid(row=0, column=1, sticky=W, padx=10, pady=5)
        
        # Фаза
        Label(info_grid, text="Фаза игры:", bg=self.colors['panel'],
              fg='white').grid(row=1, column=0, sticky=W, pady=5)
        self.phase_label = Label(info_grid, text="ожидание", bg=self.colors['panel'],
                                 fg='orange', font=('Arial', 12, 'bold'))
        self.phase_label.grid(row=1, column=1, sticky=W, padx=10, pady=5)
        
        # Статус
        Label(info_grid, text="Статус игры:", bg=self.colors['panel'],
              fg='white').grid(row=2, column=0, sticky=W, pady=5)
        self.game_status_label = Label(info_grid, text="Идет", bg=self.colors['panel'],
                                       fg=self.colors['accent3'], font=('Arial', 12, 'bold'))
        self.game_status_label.grid(row=2, column=1, sticky=W, padx=10, pady=5)
    
    def create_control_panel(self, parent):
        """Панель управления ходом (start / end / stop / override)."""
        frame = LabelFrame(parent, text="🎛️ УПРАВЛЕНИЕ ХОДОМ",
                           bg=self.colors['panel'], fg=self.colors['accent1'],
                           font=('Arial', 12, 'bold'))
        frame.pack(fill=X, pady=(0, 10))

        inner = Frame(frame, bg=self.colors['panel'])
        inner.pack(fill=X, padx=10, pady=10)

        self.timer_label = Label(
            inner,
            text="⏱ ожидание…",
            bg=self.colors['panel'],
            fg=self.colors['accent4'],
            font=('Arial', 11, 'bold'),
        )
        self.timer_label.grid(row=0, column=0, columnspan=3, sticky=W, pady=(0, 8))

        self.btn_start = Button(
            inner, text="▶ Начать ход",
            bg='#228B22', fg='white', font=('Arial', 10, 'bold'),
            command=lambda: self.send_gm_command('start_turn'),
            state=DISABLED,
        )
        self.btn_start.grid(row=1, column=0, sticky=EW, padx=2, pady=2)

        self.btn_end = Button(
            inner, text="⏹ Завершить сбор",
            bg='#b8860b', fg='white', font=('Arial', 10, 'bold'),
            command=lambda: self.send_gm_command('end_planning'),
            state=DISABLED,
        )
        self.btn_end.grid(row=1, column=1, sticky=EW, padx=2, pady=2)

        self.btn_stop = Button(
            inner, text="🛑 Стоп",
            bg='#8b0000', fg='white', font=('Arial', 10, 'bold'),
            command=lambda: self.send_gm_command('stop'),
            state=DISABLED,
        )
        self.btn_stop.grid(row=1, column=2, sticky=EW, padx=2, pady=2)

        self.btn_override = Button(
            inner, text="🛠 Override позиции корабля",
            bg=self.colors['accent1'], fg='black', font=('Arial', 10, 'bold'),
            command=self.open_override_dialog,
            state=DISABLED,
        )
        self.btn_override.grid(row=2, column=0, columnspan=3, sticky=EW, padx=2, pady=(6, 2))

        for col in range(3):
            inner.grid_columnconfigure(col, weight=1, uniform='gm_btn')

    def create_hits_panel(self, parent):
        """Панель с попаданиями"""
        hits_frame = LabelFrame(parent, text="💥 ПОПАДАНИЯ В ПОСЛЕДНЕМ ХОДУ",
                                bg=self.colors['panel'], fg=self.colors['accent2'],
                                font=('Arial', 12, 'bold'))
        hits_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Текстовое поле с прокруткой
        text_frame = Frame(hits_frame, bg=self.colors['panel'])
        text_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.hits_text = Text(text_frame, height=8,
                              bg='#000000', fg='#ff6b6b',
                              font=('Courier', 10),
                              wrap=WORD)
        scrollbar = Scrollbar(text_frame, command=self.hits_text.yview)
        self.hits_text.configure(yscrollcommand=scrollbar.set)
        
        self.hits_text.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Настройка цветов
        self.hits_text.tag_config('hit', foreground='#ff6b6b')
        self.hits_text.tag_config('info', foreground='#00d4ff')
    
    def create_stats_panel(self, parent):
        """Панель со статистикой команд"""
        stats_frame = LabelFrame(parent, text="📈 СТАТИСТИКА КОМАНД",
                                 bg=self.colors['panel'], fg=self.colors['accent3'],
                                 font=('Arial', 12, 'bold'))
        stats_frame.pack(fill=BOTH, expand=True, pady=(0, 10))
        
        # Treeview для статистики
        tree_frame = Frame(stats_frame, bg=self.colors['panel'])
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Стиль для Treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview",
                       background=self.colors['bg2'],
                       foreground='white',
                       fieldbackground=self.colors['bg2'])
        style.configure("Treeview.Heading",
                       background=self.colors['accent1'],
                       foreground='black',
                       font=('Arial', 10, 'bold'))
        
        columns = ("team", "total", "alive", "destroyed", "hits")
        self.stats_tree = ttk.Treeview(tree_frame, columns=columns,
                                        show="headings", height=4)
        
        self.stats_tree.heading("team", text="Команда")
        self.stats_tree.heading("total", text="Всего")
        self.stats_tree.heading("alive", text="Живых")
        self.stats_tree.heading("destroyed", text="Уничтожено")
        self.stats_tree.heading("hits", text="Попаданий")
        
        self.stats_tree.column("team", width=80)
        self.stats_tree.column("total", width=50)
        self.stats_tree.column("alive", width=50)
        self.stats_tree.column("destroyed", width=70)
        self.stats_tree.column("hits", width=70)
        
        self.stats_tree.pack(fill=BOTH, expand=True)
        
        # Цветные теги для команд
        self.stats_tree.tag_configure('team_a', foreground='#4169E1')
        self.stats_tree.tag_configure('team_b', foreground='#DC143C')
        self.stats_tree.tag_configure('team_c', foreground='#228B22')
    
    def create_legend_panel(self, parent):
        """Панель с легендой"""
        legend_frame = LabelFrame(parent, text="📖 ЛЕГЕНДА КАРТЫ",
                                  bg=self.colors['panel'], fg=self.colors['accent1'],
                                  font=('Arial', 12, 'bold'))
        legend_frame.pack(fill=X)
        
        legend_grid = Frame(legend_frame, bg=self.colors['panel'])
        legend_grid.pack(fill=X, padx=10, pady=10)
        
        # Команды
        Label(legend_grid, text="🟦 Team A", bg=self.colors['panel'],
              fg='#4169E1', font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=W, pady=2)
        
        Label(legend_grid, text="🟥 Team B", bg=self.colors['panel'],
              fg='#DC143C', font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=W, padx=20, pady=2)
        
        Label(legend_grid, text="🟩 Team C", bg=self.colors['panel'],
              fg='#228B22', font=('Arial', 10, 'bold')).grid(row=0, column=2, sticky=W, padx=20, pady=2)
        
        # Типы кораблей
        Label(legend_grid, text="К - Крейсер", bg=self.colors['panel'],
              fg='white').grid(row=1, column=0, sticky=W, pady=2)
        
        Label(legend_grid, text="А - Артиллерия", bg=self.colors['panel'],
              fg='white').grid(row=1, column=1, sticky=W, padx=20, pady=2)
        
        Label(legend_grid, text="Р - Радиовышка", bg=self.colors['panel'],
              fg='white').grid(row=1, column=2, sticky=W, padx=20, pady=2)
        
        Label(legend_grid, text="Б - Базовый", bg=self.colors['panel'],
              fg='white').grid(row=2, column=0, sticky=W, pady=2)
        
        Label(legend_grid, text="💥 - Попадания", bg=self.colors['panel'],
              fg='orange').grid(row=2, column=1, sticky=W, padx=20, pady=2)
        
        Label(legend_grid, text="💀 - Уничтожен", bg=self.colors['panel'],
              fg='gray').grid(row=2, column=2, sticky=W, padx=20, pady=2)
        
        # Сообщения
        self.message_label = Label(parent, text="",
                                    bg=self.colors['panel'], fg=self.colors['accent1'],
                                    font=('Arial', 10))
        self.message_label.pack(fill=X, pady=5)
    
    def show_connection_window(self):
        """Показывает окно подключения"""
        conn_window = Toplevel(self.root)
        conn_window.title("🎮 Подключение гейммастера")
        conn_window.geometry("400x400")
        conn_window.configure(bg=self.colors['bg'])
        conn_window.transient(self.root)
        conn_window.grab_set()
        
        # Заголовок
        title_font = font.Font(family='Arial', size=16, weight='bold')
        Label(conn_window, text="🎮 ПОДКЛЮЧЕНИЕ ГЕЙММАСТЕРА",
              bg=self.colors['bg'], fg=self.colors['accent4'],
              font=title_font).pack(pady=20)
        
        # Рамка с полями
        input_frame = Frame(conn_window, bg=self.colors['panel'], bd=2, relief=RAISED)
        input_frame.pack(padx=30, pady=10, fill=BOTH, expand=True)
        
        # IP сервера
        Label(input_frame, text="🌐 IP сервера:",
              bg=self.colors['panel'], fg='white',
              font=('Arial', 11)).pack(anchor=W, padx=20, pady=(15,5))
        
        self.ip_entry = Entry(input_frame, width=30, font=('Arial', 11),
                              bg=self.colors['bg2'], fg='white',
                              insertbackground='white')
        self.ip_entry.insert(0, "localhost")
        self.ip_entry.pack(padx=20, pady=5, fill=X)
        
        # Имя
        Label(input_frame, text="👤 Ваше имя:",
              bg=self.colors['panel'], fg='white',
              font=('Arial', 11)).pack(anchor=W, padx=20, pady=(15,5))
        
        self.name_entry = Entry(input_frame, width=30, font=('Arial', 11),
                                bg=self.colors['bg2'], fg='white',
                                insertbackground='white')
        self.name_entry.insert(0, "Гейммастер")
        self.name_entry.pack(padx=20, pady=5, fill=X)
        
        # Кнопки
        button_frame = Frame(conn_window, bg=self.colors['bg'])
        button_frame.pack(pady=20)
        
        Button(button_frame, text="🎮 ПОДКЛЮЧИТЬСЯ",
               bg=self.colors['accent3'], fg='black',
               font=('Arial', 12, 'bold'),
               command=self.connect).pack(side=LEFT, padx=10)
        
        Button(button_frame, text="❌ ВЫХОД",
               bg='red', fg='white',
               font=('Arial', 12, 'bold'),
               command=self.root.quit).pack(side=LEFT, padx=10)
    
    def connect(self):
        """Подключается к серверу"""
        server_ip = self.ip_entry.get().strip()
        player_name = self.name_entry.get().strip()
        
        if not server_ip:
            server_ip = "localhost"
        if not player_name:
            player_name = "Гейммастер"
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((server_ip, 5555))
            self.framed = Framed(self.socket)

            # Отправляем информацию о гейммастере
            game_master_info = {
                'type': 'game_master',
                'player_name': player_name,
            }
            self.framed.send(game_master_info)

            self.connected = True
            self.status_label.config(text="✅ Подключен к серверу", fg=self.colors['accent3'])
            
            # Закрываем окно подключения
            self.ip_entry.master.master.destroy()
            
            # Запускаем поток для получения данных
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            
            messagebox.showinfo("Успех", "🎮 Успешно подключен как гейммастер!\nВы видите все корабли и попадания.")
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться: {e}")
    
    def receive_loop(self):
        """Цикл получения данных от сервера через framed-протокол."""
        while self.connected:
            try:
                msg = self.framed.recv_once(timeout=1)
            except ProtocolError as e:
                if self.connected:
                    self.connected = False
                    self.root.after(
                        0,
                        lambda err=str(e): messagebox.showinfo(
                            "Соединение", f"Сервер закрыл соединение: {err}"
                        ),
                    )
                break
            except Exception as e:
                if self.connected:
                    err_text = f"Ошибка получения данных: {e}"
                    self.root.after(
                        0,
                        lambda t=err_text: self.message_label.config(
                            text=t, fg='red'
                        ),
                    )
                    time.sleep(1)
                continue

            if msg is None:
                continue

            if isinstance(msg, dict) and msg.get('type') == 'reject':
                reason = msg.get('reason', 'Сервер отклонил подключение')
                self.connected = False
                self.root.after(
                    0,
                    lambda r=reason: messagebox.showerror("Отказ сервера", r),
                )
                break

            self.current_state = msg
            self.root.after(0, self.update_interface, msg)
    
    def update_interface(self, state):
        """Обновляет интерфейс на основе полученного состояния"""
        turn = state.get('turn', 0) + 1
        phase = state.get('phase', 'unknown')
        message = state.get('message', '')
        game_over = state.get('game_over', False)

        # Обновляем информацию
        self.turn_label.config(text=str(turn))

        if phase == 'planning':
            self.phase_label.config(text="📝 ПЛАНИРОВАНИЕ", fg=self.colors['accent3'])
        elif phase == 'results':
            self.phase_label.config(text="📊 РЕЗУЛЬТАТЫ", fg='orange')
        elif phase == 'waiting_for_gm':
            self.phase_label.config(text="⏳ ЖДЁТ GM", fg=self.colors['accent4'])
        else:
            self.phase_label.config(text=phase.upper(), fg='gray')

        if game_over:
            winner = state.get('winner', 'Не определен')
            self.game_status_label.config(text=f"Окончена. Победитель: {winner}", fg='red')
            self.message_label.config(text=f"🏆 ИГРА ОКОНЧЕНА! Победитель: {winner}", fg=self.colors['accent4'])
        else:
            self.game_status_label.config(text="Идет", fg=self.colors['accent3'])
            self.message_label.config(text=message, fg='white')

        # Статус кнопок управления: зависит от фазы.
        can_start = (phase == 'waiting_for_gm') and not game_over
        can_end = (phase == 'planning') and not game_over
        can_stop = not game_over
        can_override = not game_over
        self.btn_start.config(state=(NORMAL if can_start else DISABLED))
        self.btn_end.config(state=(NORMAL if can_end else DISABLED))
        self.btn_stop.config(state=(NORMAL if can_stop else DISABLED))
        self.btn_override.config(state=(NORMAL if can_override else DISABLED))

        # Таймер фазы планирования.
        deadline = state.get('planning_deadline')
        if phase == 'planning' and deadline:
            remaining = max(0, int(deadline - time.time()))
            received = state.get('actions_received_teams', [])
            connected = state.get('connected_teams', [])
            self.timer_label.config(
                text=f"⏱ {remaining}с  |  действия: {len(received)}/{len(connected)}"
            )
        elif phase == 'waiting_for_gm':
            self.timer_label.config(text="⏸ ждём старта — нажмите «Начать ход»")
        elif phase == 'results':
            self.timer_label.config(text="📊 результаты хода")
        elif game_over:
            self.timer_label.config(text="🏁 игра окончена")
        else:
            self.timer_label.config(text="⏱ ожидание…")

        # Обновляем статистику команд
        self.update_stats(state)

        # Обновляем информацию о попаданиях
        self.update_hits_info(state)

        # Обновляем карту
        self.update_map()
    
    def update_stats(self, state):
        """Обновляет статистику команд"""
        # Очищаем список
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        all_ships = state.get('all_ships', {})
        
        # Собираем статистику по командам
        team_stats = {
            'Team A': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0},
            'Team B': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0},
            'Team C': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0}
        }
        
        for ship_id, ship in all_ships.items():
            team = ship['team']
            if team in team_stats:
                team_stats[team]['total'] += 1
                if ship['alive']:
                    team_stats[team]['alive'] += 1
                    team_stats[team]['hits'] += ship['hits']
                else:
                    team_stats[team]['destroyed'] += 1
        
        # Добавляем в Treeview с цветными тегами
        self.stats_tree.insert("", "end", values=(
            'Team A',
            team_stats['Team A']['total'],
            team_stats['Team A']['alive'],
            team_stats['Team A']['destroyed'],
            team_stats['Team A']['hits']
        ), tags=('team_a',))
        
        self.stats_tree.insert("", "end", values=(
            'Team B',
            team_stats['Team B']['total'],
            team_stats['Team B']['alive'],
            team_stats['Team B']['destroyed'],
            team_stats['Team B']['hits']
        ), tags=('team_b',))
        
        self.stats_tree.insert("", "end", values=(
            'Team C',
            team_stats['Team C']['total'],
            team_stats['Team C']['alive'],
            team_stats['Team C']['destroyed'],
            team_stats['Team C']['hits']
        ), tags=('team_c',))
    
    def update_hits_info(self, state):
        """Перерисовывает журнал всех попаданий партии (scrollable)."""
        self.hits_text.delete(1.0, END)

        history = state.get('hit_history', [])
        if not history:
            self.hits_text.insert(END, "Попаданий ещё не было\n", 'info')
            return

        self.hits_text.insert(END, f"💥 ЖУРНАЛ ПОПАДАНИЙ ({len(history)}):\n\n", 'info')
        for hit in history:
            turn = hit.get('turn', '?')
            attacker = hit.get('attacker', '?')
            attacker_name = hit.get('attacker_name', '?')
            target = hit.get('target', '?')
            target_name = hit.get('target_name', '?')
            position = hit.get('position', '?')
            killed = hit.get('killed', False)
            marker = "💀" if killed else "🎯"
            self.hits_text.insert(
                END,
                f"T{turn:>2}: {marker} {attacker} {attacker_name} → "
                f"{target} {target_name} @ {position}\n",
                'hit',
            )
        self.hits_text.see(END)

    # ─────────────────────────── GM commands ──────────────────────────
    def send_gm_command(self, command, **payload):
        """Отправить gm_command серверу. Тихо логирует ошибки в status_bar."""
        if not self.connected or self.framed is None:
            messagebox.showwarning("Нет соединения", "Не подключен к серверу")
            return False
        msg = {'type': 'gm_command', 'command': command}
        msg.update(payload)
        try:
            self.framed.send(msg)
        except ProtocolError as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить: {e}")
            self.connected = False
            return False
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить: {e}")
            return False
        return True

    def open_override_dialog(self):
        """Диалог принудительного изменения позиции/состояния корабля (арбитраж)."""
        if not self.current_state:
            messagebox.showinfo("Нет данных", "Данные о кораблях ещё не получены")
            return
        all_ships = self.current_state.get('all_ships', {})
        if not all_ships:
            messagebox.showinfo("Нет кораблей", "На карте нет кораблей")
            return

        dlg = Toplevel(self.root)
        dlg.title("🛠 Override корабля")
        dlg.configure(bg=self.colors['bg'])
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("420x380")

        Label(dlg, text="🛠 РУЧНОЕ ИЗМЕНЕНИЕ ПОЗИЦИИ",
              bg=self.colors['bg'], fg=self.colors['accent4'],
              font=('Arial', 13, 'bold')).pack(pady=10)

        form = Frame(dlg, bg=self.colors['panel'], bd=2, relief=RAISED)
        form.pack(padx=20, pady=10, fill=BOTH, expand=True)

        # Корабль
        Label(form, text="Корабль:", bg=self.colors['panel'], fg='white',
              font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=W, padx=10, pady=6)
        ship_options = []
        for sid, s in sorted(all_ships.items()):
            label = (f"{sid}  [{s.get('team','?')}]  {s.get('name','')}  "
                     f"({s.get('x','?')},{s.get('y','?')},{s.get('z','?')})  "
                     f"{'alive' if s.get('alive') else 'DEAD'} "
                     f"hits={s.get('hits',0)}")
            ship_options.append((sid, label, s))

        id_var = StringVar(value=ship_options[0][1])
        ship_menu = ttk.Combobox(form, textvariable=id_var,
                                 values=[lbl for (_, lbl, _) in ship_options],
                                 state='readonly', width=48)
        ship_menu.grid(row=0, column=1, columnspan=3, sticky=EW, padx=10, pady=6)

        # X / Y / Z
        def _coord_row(label, r, default):
            Label(form, text=label, bg=self.colors['panel'], fg='white',
                  font=('Arial', 10, 'bold')).grid(row=r, column=0, sticky=W, padx=10, pady=6)
            sv = IntVar(value=default)
            Spinbox(form, from_=0, to=9, textvariable=sv, width=6,
                    font=('Arial', 10)).grid(row=r, column=1, sticky=W, padx=10, pady=6)
            return sv

        first_ship = ship_options[0][2]
        x_var = _coord_row("X (0–9):", 1, int(first_ship.get('x', 0)))
        y_var = _coord_row("Y (0–9):", 2, int(first_ship.get('y', 0)))
        z_var = _coord_row("Z (0–9):", 3, int(first_ship.get('z', 0)))

        # alive / hits
        alive_var = BooleanVar(value=bool(first_ship.get('alive', True)))
        Checkbutton(form, text="Жив", variable=alive_var,
                    bg=self.colors['panel'], fg='white',
                    selectcolor=self.colors['bg2'],
                    activebackground=self.colors['panel'],
                    font=('Arial', 10, 'bold')
                    ).grid(row=4, column=0, sticky=W, padx=10, pady=6)

        Label(form, text="Попаданий:", bg=self.colors['panel'], fg='white',
              font=('Arial', 10, 'bold')).grid(row=4, column=1, sticky=E, padx=5, pady=6)
        hits_var = IntVar(value=int(first_ship.get('hits', 0)))
        Spinbox(form, from_=0, to=10, textvariable=hits_var, width=6,
                font=('Arial', 10)).grid(row=4, column=2, sticky=W, pady=6)

        # Обновляем поля при смене корабля.
        def _on_ship_selected(*_):
            idx = ship_menu.current()
            if idx < 0:
                return
            sid, _label, s = ship_options[idx]
            x_var.set(int(s.get('x', 0)))
            y_var.set(int(s.get('y', 0)))
            z_var.set(int(s.get('z', 0)))
            alive_var.set(bool(s.get('alive', True)))
            hits_var.set(int(s.get('hits', 0)))
        ship_menu.bind("<<ComboboxSelected>>", _on_ship_selected)

        # Кнопки
        btns = Frame(dlg, bg=self.colors['bg'])
        btns.pack(pady=10)

        def _apply():
            idx = ship_menu.current()
            if idx < 0:
                return
            sid = ship_options[idx][0]
            ok = self.send_gm_command(
                'override_ship',
                ship_id=sid,
                x=int(x_var.get()),
                y=int(y_var.get()),
                z=int(z_var.get()),
                alive=bool(alive_var.get()),
                hits=int(hits_var.get()),
            )
            if ok:
                dlg.destroy()

        Button(btns, text="✅ Применить", bg=self.colors['accent3'], fg='black',
               font=('Arial', 10, 'bold'), width=15, command=_apply).pack(side=LEFT, padx=10)
        Button(btns, text="Отмена", bg=self.colors['accent2'], fg='white',
               font=('Arial', 10, 'bold'), width=10,
               command=dlg.destroy).pack(side=LEFT, padx=10)
    
    def update_map(self, *args):
        """Обновляет отображение карты для текущего слоя"""
        if not self.current_state:
            return
        
        layer = self.current_layer.get()
        # Обновляем надпись слоя
        self.layer_label.config(text=f"Z = {layer}")
        
        all_ships = self.current_state.get('all_ships', {})
        
        # Очищаем карту
        for row in range(10):
            for col in range(10):
                self.cells[row][col].config(
                    text=" ",
                    bg=self.colors['bg2'],
                    fg="white"
                )
        
        # Отображаем все корабли на текущем слое
        for ship_id, ship in all_ships.items():
            if ship['z'] == layer:
                x, y = ship['x'], ship['y']
                
                # Определяем цвет команды
                if ship['team'] == 'Team A':
                    bg_color = '#4169E1'  # Синий
                elif ship['team'] == 'Team B':
                    bg_color = '#DC143C'  # Красный
                else:
                    bg_color = '#228B22'  # Зелёный
                
                # Определяем символ для типа корабля
                ship_type = ship.get('type', 'Базовый')
                if ship_type == 'Крейсер':
                    type_char = "К"
                elif ship_type == 'Артиллерия':
                    type_char = "А"
                elif ship_type == 'Радиовышка':
                    type_char = "Р"
                else:
                    type_char = "Б"
                
                # Если корабль уничтожен
                if not ship['alive']:
                    display_text = f"💀{type_char}"
                    bg_color = '#4a4a4a'  # Серый
                elif ship['hits'] > 0:
                    display_text = f"{type_char}{ship['hits']}"
                    bg_color = 'orange'
                else:
                    display_text = type_char
                
                self.cells[y][x].config(
                    text=display_text,
                    bg=bg_color,
                    fg='white',
                    font=('Arial', 10, 'bold')
                )
    
    def tick_timer(self):
        """Каждую секунду пересчитывает таймер из current_state, даже если от
        сервера нет нового пуша."""
        try:
            state = self.current_state
            if state is not None and state.get('phase') == 'planning':
                deadline = state.get('planning_deadline')
                if deadline:
                    remaining = max(0, int(deadline - time.time()))
                    received = state.get('actions_received_teams', [])
                    connected = state.get('connected_teams', [])
                    self.timer_label.config(
                        text=f"⏱ {remaining}с  |  действия: "
                             f"{len(received)}/{len(connected)}"
                    )
        finally:
            self.root.after(500, self.tick_timer)

    def run(self):
        """Запускает приложение"""
        self.root.after(500, self.tick_timer)
        self.root.mainloop()

if __name__ == "__main__":
    app = GameMasterGUI()
    app.run()