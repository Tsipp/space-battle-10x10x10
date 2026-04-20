# server_full_visibility.py
import socket
import threading
import time
from shared_simple import *
from protocol import Framed, ProtocolError

# Tkinter импортируется опционально: игровая логика (GameServer) работает без него,
# GUI-класс GameServerGUI просто не будет доступен в окружениях без Tk.
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox, font
    _HAS_TK = True
except Exception:  # pragma: no cover - в окружении с Tk эта ветка не срабатывает
    tk = None
    ttk = scrolledtext = messagebox = font = None
    _HAS_TK = False

class GameServerGUI:
    def __init__(self):
        self.server = None
        self.game_mode = 'advanced'
        self.host = '0.0.0.0'
        self.port = 5555
        self.running = False
        
        # Данные сервера
        self.clients = {}  # team -> socket
        self.game_state = {
            'turn': 0,
            'ships': {},
            'phase': 'waiting',
            'game_over': False,
            'winner': None,
            'last_hits': [],
            'game_mode': 'advanced'
        }
        self.actions_received = {}
        # (GUI-поле, оставляем для совместимости отображения)
        self.game_master_socket = None

        # Создаём главное окно
        self.root = tk.Tk()
        self.root.title("🚀 КОСМИЧЕСКИЙ БОЙ - СЕРВЕР")
        self.root.geometry("1200x800")
        self.root.configure(bg='#0a0e27')  # Тёмно-синий космический фон
        
        # Настраиваем стили
        self.setup_styles()
        
        # Создаём интерфейс
        self.create_widgets()
        
        # Показываем стартовое меню
        self.show_start_menu()
    
    def setup_styles(self):
        """Настраивает стили для виджетов"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Космическая цветовая схема
        self.colors = {
            'bg': '#0a0e27',
            'bg2': '#1a1f3a',
            'fg': '#ffffff',
            'accent1': '#00d4ff',  # Голубой неон
            'accent2': '#ff6b6b',  # Красный неон
            'accent3': '#6bff6b',  # Зелёный неон
            'accent4': '#ffd700',  # Золотой
            'panel': '#151a33',
            'text': '#e0e0ff'
        }
        
        # Настройка стилей
        style.configure('Cosmic.TLabel', 
                       background=self.colors['bg'],
                       foreground=self.colors['text'],
                       font=('Arial', 10))
        
        style.configure('Cosmic.TButton',
                       background=self.colors['accent1'],
                       foreground='black',
                       font=('Arial', 11, 'bold'),
                       borderwidth=2,
                       relief='raised')
        
        style.map('Cosmic.TButton',
                 background=[('active', self.colors['accent2'])])
    
    def create_widgets(self):
        """Создаёт все виджеты интерфейса"""
        # Верхняя панель с заголовком
        self.create_header()
        
        # Основной контейнер
        main_container = tk.Frame(self.root, bg=self.colors['bg'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Левая панель (информация и статистика)
        left_panel = tk.Frame(main_container, bg=self.colors['panel'], width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_panel.pack_propagate(False)
        
        # Правая панель (логи и консоль)
        right_panel = tk.Frame(main_container, bg=self.colors['panel'], width=600)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        right_panel.pack_propagate(False)
        
        # Создаём виджеты на левой панели
        self.create_info_panel(left_panel)
        self.create_stats_panel(left_panel)
        self.create_teams_panel(left_panel)
        
        # Создаём виджеты на правой панели
        self.create_console_panel(right_panel)
        self.create_control_panel(right_panel)
    
    def create_header(self):
        """Создаёт красивый заголовок"""
        header_frame = tk.Frame(self.root, bg='#000000', height=80)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Градиентный эффект
        canvas = tk.Canvas(header_frame, height=80, bg='#000000', highlightthickness=0)
        canvas.pack(fill=tk.X)
        
        # Создаём звёздный фон
        for i in range(50):
            x = i * 20
            y = 40
            canvas.create_oval(x, y, x+2, y+2, fill='white', outline='')
        
        # Заголовок
        title_font = font.Font(family='Arial', size=24, weight='bold')
        canvas.create_text(400, 40, text='🚀 КОСМИЧЕСКИЙ БОЙ 10x10x10', 
                          fill='#00d4ff', font=title_font)
        
        # Подзаголовок
        subtitle_font = font.Font(family='Arial', size=12)
        canvas.create_text(400, 65, text='СЕРВЕР УПРАВЛЕНИЯ', 
                          fill='#ffffff', font=subtitle_font)
    
    def create_info_panel(self, parent):
        """Панель с информацией о сервере"""
        frame = tk.LabelFrame(parent, text="📊 ИНФОРМАЦИЯ О СЕРВЕРЕ", 
                             bg=self.colors['panel'], fg=self.colors['accent1'],
                             font=('Arial', 12, 'bold'))
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # IP и порт
        info_grid = tk.Frame(frame, bg=self.colors['panel'])
        info_grid.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(info_grid, text="🌐 IP адрес:", bg=self.colors['panel'], 
                fg=self.colors['text']).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ip_label = tk.Label(info_grid, text="0.0.0.0", bg=self.colors['panel'],
                                fg=self.colors['accent1'], font=('Arial', 10, 'bold'))
        self.ip_label.grid(row=0, column=1, sticky=tk.W, padx=10, pady=2)
        
        tk.Label(info_grid, text="📞 Порт:", bg=self.colors['panel'],
                fg=self.colors['text']).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port_label = tk.Label(info_grid, text="5555", bg=self.colors['panel'],
                                  fg=self.colors['accent1'], font=('Arial', 10, 'bold'))
        self.port_label.grid(row=1, column=1, sticky=tk.W, padx=10, pady=2)
        
        tk.Label(info_grid, text="🎮 Режим игры:", bg=self.colors['panel'],
                fg=self.colors['text']).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.mode_label = tk.Label(info_grid, text="ПРОДВИНУТЫЙ", bg=self.colors['panel'],
                                  fg=self.colors['accent2'], font=('Arial', 10, 'bold'))
        self.mode_label.grid(row=2, column=1, sticky=tk.W, padx=10, pady=2)
        
        # Статус подключений
        status_frame = tk.Frame(frame, bg=self.colors['panel'])
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(status_frame, text="👥 Игроки:", bg=self.colors['panel'],
                fg=self.colors['text']).pack(side=tk.LEFT)
        self.players_label = tk.Label(status_frame, text="0/3", bg=self.colors['panel'],
                                     fg=self.colors['accent3'], font=('Arial', 10, 'bold'))
        self.players_label.pack(side=tk.LEFT, padx=5)
        
        tk.Label(status_frame, text="🎮 Гейммастер:", bg=self.colors['panel'],
                fg=self.colors['text']).pack(side=tk.LEFT, padx=(20, 5))
        self.gm_label = tk.Label(status_frame, text="❌", bg=self.colors['panel'],
                                fg='red', font=('Arial', 10, 'bold'))
        self.gm_label.pack(side=tk.LEFT)
    
    def create_stats_panel(self, parent):
        """Панель со статистикой игры"""
        frame = tk.LabelFrame(parent, text="📈 СТАТИСТИКА ИГРЫ", 
                             bg=self.colors['panel'], fg=self.colors['accent1'],
                             font=('Arial', 12, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Текущий ход
        turn_frame = tk.Frame(frame, bg=self.colors['panel'])
        turn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(turn_frame, text="Текущий ход:", bg=self.colors['panel'],
                fg=self.colors['text']).pack(side=tk.LEFT)
        self.turn_label = tk.Label(turn_frame, text="0", bg=self.colors['panel'],
                                  fg=self.colors['accent4'], font=('Arial', 14, 'bold'))
        self.turn_label.pack(side=tk.LEFT, padx=5)
        
        tk.Label(turn_frame, text="Фаза:", bg=self.colors['panel'],
                fg=self.colors['text']).pack(side=tk.LEFT, padx=(20, 5))
        self.phase_label = tk.Label(turn_frame, text="Ожидание", bg=self.colors['panel'],
                                   fg='orange', font=('Arial', 10, 'bold'))
        self.phase_label.pack(side=tk.LEFT)
        
        # Таблица статистики команд
        columns = ('team', 'total', 'alive', 'destroyed', 'hits')
        self.stats_tree = ttk.Treeview(frame, columns=columns, show='headings', height=5)
        
        self.stats_tree.heading('team', text='Команда')
        self.stats_tree.heading('total', text='Всего')
        self.stats_tree.heading('alive', text='Живых')
        self.stats_tree.heading('destroyed', text='Уничтожено')
        self.stats_tree.heading('hits', text='Попаданий')
        
        self.stats_tree.column('team', width=80)
        self.stats_tree.column('total', width=50)
        self.stats_tree.column('alive', width=50)
        self.stats_tree.column('destroyed', width=70)
        self.stats_tree.column('hits', width=70)
        
        self.stats_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def create_teams_panel(self, parent):
        """Панель с состоянием команд"""
        frame = tk.LabelFrame(parent, text="🚀 СОСТОЯНИЕ КОМАНД", 
                             bg=self.colors['panel'], fg=self.colors['accent1'],
                             font=('Arial', 12, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Текстовое поле для отображения состояния
        self.teams_text = scrolledtext.ScrolledText(frame, height=10,
                                                   bg='#000000', fg='#00ff00',
                                                   font=('Courier', 10))
        self.teams_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Добавляем подсветку синтаксиса
        self.teams_text.tag_config('team_a', foreground='#00d4ff')
        self.teams_text.tag_config('team_b', foreground='#ff6b6b')
        self.teams_text.tag_config('team_c', foreground='#6bff6b')
        self.teams_text.tag_config('dead', foreground='#808080')
    
    def create_console_panel(self, parent):
        """Панель с консолью"""
        frame = tk.LabelFrame(parent, text="📋 КОНСОЛЬ СЕРВЕРА", 
                             bg=self.colors['panel'], fg=self.colors['accent1'],
                             font=('Arial', 12, 'bold'))
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Текстовое поле для логов
        self.console_text = scrolledtext.ScrolledText(frame, height=20,
                                                      bg='#000000', fg='#e0e0ff',
                                                      font=('Courier', 10))
        self.console_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Настройка цветов для разных типов сообщений
        self.console_text.tag_config('info', foreground='#ffffff')
        self.console_text.tag_config('success', foreground='#00ff00')
        self.console_text.tag_config('warning', foreground='#ffff00')
        self.console_text.tag_config('error', foreground='#ff0000')
        self.console_text.tag_config('system', foreground='#00d4ff')
    
    def create_control_panel(self, parent):
        """Панель управления"""
        frame = tk.Frame(parent, bg=self.colors['panel'])
        frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Кнопки управления
        self.start_btn = tk.Button(frame, text="🚀 ЗАПУСТИТЬ СЕРВЕР",
                                   bg=self.colors['accent3'], fg='black',
                                   font=('Arial', 11, 'bold'),
                                   command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(frame, text="⏹️ ОСТАНОВИТЬ",
                                  bg=self.colors['accent2'], fg='black',
                                  font=('Arial', 11, 'bold'),
                                  command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.clear_btn = tk.Button(frame, text="🧹 ОЧИСТИТЬ КОНСОЛЬ",
                                   bg='orange', fg='black',
                                   font=('Arial', 11, 'bold'),
                                   command=self.clear_console)
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        self.exit_btn = tk.Button(frame, text="❌ ВЫХОД",
                                  bg='red', fg='white',
                                  font=('Arial', 11, 'bold'),
                                  command=self.root.quit)
        self.exit_btn.pack(side=tk.RIGHT, padx=5)
    
    def show_start_menu(self):
        """Показывает стартовое меню"""
        menu_window = tk.Toplevel(self.root)
        menu_window.title("Выбор режима игры")
        menu_window.geometry("600x500")
        menu_window.configure(bg=self.colors['bg'])
        menu_window.transient(self.root)
        menu_window.grab_set()
        
        # Заголовок
        title_font = font.Font(family='Arial', size=18, weight='bold')
        tk.Label(menu_window, text="🚀 ВЫБЕРИТЕ РЕЖИМ ИГРЫ", 
                bg=self.colors['bg'], fg=self.colors['accent1'],
                font=title_font).pack(pady=30)
        
        # Рамка для режимов
        modes_frame = tk.Frame(menu_window, bg=self.colors['panel'], bd=2, relief=tk.RAISED)
        modes_frame.pack(padx=30, pady=20, fill=tk.BOTH, expand=True)
        
        # Продвинутый режим
        adv_frame = tk.Frame(modes_frame, bg=self.colors['panel'])
        adv_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(adv_frame, text="🚀 ПРОДВИНУТЫЙ РЕЖИМ", 
                bg=self.colors['panel'], fg=self.colors['accent1'],
                font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        
        adv_desc = """• Разные типы кораблей:
  - Крейсер    (1 хит, движется)
  - Артиллерия (3 хита, стреляет куда угодно, не движется)
  - Радиовышка (2 хита, сканирует всю плоскость Z)
  - Базовый    (2 хита, стандартный)
• Разные способности и тактики
• Командная игра"""
        
        tk.Label(adv_frame, text=adv_desc, bg=self.colors['panel'],
                fg=self.colors['text'], font=('Arial', 10),
                justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        
        tk.Button(adv_frame, text="ВЫБРАТЬ ПРОДВИНУТЫЙ", 
                 bg=self.colors['accent3'], fg='black',
                 font=('Arial', 11, 'bold'),
                 command=lambda: self.select_mode('advanced', menu_window)).pack(pady=10)
        
        # Разделитель
        ttk.Separator(modes_frame, orient='horizontal').pack(fill=tk.X, padx=20, pady=10)
        
        # Обычный режим
        basic_frame = tk.Frame(modes_frame, bg=self.colors['panel'])
        basic_frame.pack(fill=tk.X, padx=20, pady=15)
        
        tk.Label(basic_frame, text="⚫ ОБЫЧНЫЙ РЕЖИМ", 
                bg=self.colors['panel'], fg='gray',
                font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        
        basic_desc = """• Только крейсеры (5 на команду)
• Пустое поле без способностей
• Классический бой
⚠️ РЕЖИМ В РАЗРАБОТКЕ"""
        
        tk.Label(basic_frame, text=basic_desc, bg=self.colors['panel'],
                fg='gray', font=('Arial', 10),
                justify=tk.LEFT).pack(anchor=tk.W, pady=5)
        
        tk.Button(basic_frame, text="В РАЗРАБОТКЕ", 
                 bg='gray', fg='white',
                 font=('Arial', 11, 'bold'),
                 state=tk.DISABLED).pack(pady=10)
        
        # Поле для ввода IP
        ip_frame = tk.Frame(menu_window, bg=self.colors['bg'])
        ip_frame.pack(fill=tk.X, padx=30, pady=10)
        
        tk.Label(ip_frame, text="IP адрес сервера:", 
                bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT)
        
        ip_entry = tk.Entry(ip_frame, width=20, font=('Arial', 10))
        ip_entry.insert(0, "0.0.0.0")
        ip_entry.pack(side=tk.LEFT, padx=10)
        
        tk.Label(ip_frame, text="Порт:", 
                bg=self.colors['bg'], fg=self.colors['text']).pack(side=tk.LEFT, padx=(20,5))
        
        port_entry = tk.Entry(ip_frame, width=10, font=('Arial', 10))
        port_entry.insert(0, "5555")
        port_entry.pack(side=tk.LEFT)
        
        # Сохраняем ссылки на поля ввода
        self.ip_entry = ip_entry
        self.port_entry = port_entry
    
    def select_mode(self, mode, menu_window):
        """Выбирает режим игры"""
        self.game_mode = mode
        self.host = self.ip_entry.get().strip() or '0.0.0.0'
        self.port = int(self.port_entry.get().strip() or '5555')
        
        # Обновляем информацию на главном окне
        self.ip_label.config(text=self.host)
        self.port_label.config(text=str(self.port))
        
        mode_text = "ПРОДВИНУТЫЙ" if mode == 'advanced' else "ОБЫЧНЫЙ"
        mode_color = self.colors['accent2'] if mode == 'advanced' else 'gray'
        self.mode_label.config(text=mode_text, fg=mode_color)
        
        menu_window.destroy()
        
        # Активируем кнопку запуска
        self.start_btn.config(state=tk.NORMAL)
        
        self.log("✅ Режим игры выбран", 'success')
        self.log(f"🌐 Сервер будет запущен на {self.host}:{self.port}", 'info')
    
    def log(self, message, tag='info'):
        """Добавляет сообщение в консоль"""
        timestamp = time.strftime("%H:%M:%S")
        self.console_text.insert(tk.END, f"[{timestamp}] ", 'system')
        self.console_text.insert(tk.END, f"{message}\n", tag)
        self.console_text.see(tk.END)
        self.root.update()
    
    def update_stats(self):
        """Обновляет статистику в интерфейсе"""
        if not hasattr(self, 'game_server') or not self.game_server:
            return

        # Снимаем копию списка под блокировкой — сам доступ к атрибутам
        # корабля безопасен, но `ships` может быть перезаписан в create_ships
        # или модифицирован в process_turn из сетевого потока.
        with self.game_server.state_lock:
            ships = dict(self.game_server.game_state['ships'])
        
        # Обновляем статистику команд
        team_stats = {
            'Team A': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0},
            'Team B': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0},
            'Team C': {'total': 0, 'alive': 0, 'destroyed': 0, 'hits': 0}
        }
        
        for ship_id, ship in ships.items():
            team = ship.team.value
            if team in team_stats:
                team_stats[team]['total'] += 1
                if ship.alive:
                    team_stats[team]['alive'] += 1
                    team_stats[team]['hits'] += ship.hits
                else:
                    team_stats[team]['destroyed'] += 1
        
        # Очищаем и обновляем Treeview
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        for team, stats in team_stats.items():
            self.stats_tree.insert("", "end", values=(
                team,
                stats['total'],
                stats['alive'],
                stats['destroyed'],
                stats['hits']
            ))
        
        # Обновляем состояние команд
        self.teams_text.delete(1.0, tk.END)
        
        for team in [Team.TEAM_A, Team.TEAM_B, Team.TEAM_C]:
            team_ships = [s for s in ships.values() if s.team == team]
            alive = [s for s in team_ships if s.alive]
            
            team_tag = 'team_a' if team == Team.TEAM_A else 'team_b' if team == Team.TEAM_B else 'team_c'
            team_symbol = "🟦" if team == Team.TEAM_A else "🟥" if team == Team.TEAM_B else "🟩"
            
            self.teams_text.insert(tk.END, f"{team_symbol} {team.value}:\n", team_tag)
            
            for ship in team_ships:
                status = "✅" if ship.alive else "💀"
                ship_type = ship.ship_type.value
                hits_status = "💥" * ship.hits + "○" * (ship.max_hits - ship.hits)
                pos = f"({ship.x},{ship.y},{ship.z})"
                
                if ship.alive:
                    self.teams_text.insert(tk.END, f"  {status} {ship_type} {ship.id}: {pos} {hits_status}\n", team_tag)
                else:
                    self.teams_text.insert(tk.END, f"  {status} {ship_type} {ship.id}: {pos}\n", 'dead')
            
            self.teams_text.insert(tk.END, "\n")
        
        # Обновляем информацию о ходе
        self.turn_label.config(text=str(self.game_server.game_state['turn'] + 1))
        self.phase_label.config(text=self.game_server.game_state['phase'].upper())
        
        # Обновляем информацию о подключениях
        players = len(self.game_server.clients)
        self.players_label.config(text=f"{players}/3")
        
        gm_connected = self.game_server.game_master_framed is not None
        gm_status = "✅" if gm_connected else "❌"
        gm_color = self.colors['accent3'] if gm_connected else 'red'
        self.gm_label.config(text=gm_status, fg=gm_color)
    
    def start_server(self):
        """Запускает сервер"""
        try:
            self.game_server = GameServer(
                host=self.host,
                port=self.port,
                game_mode=self.game_mode,
                gui=self  # Передаём ссылку на GUI
            )
            
            self.running = True
            
            # Запускаем сервер в отдельном потоке
            self.server_thread = threading.Thread(target=self.game_server.start, daemon=True)
            self.server_thread.start()
            
            # Обновляем интерфейс
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            self.log("🚀 Сервер успешно запущен!", 'success')
            self.log(f"📡 Ожидание подключений на {self.host}:{self.port}", 'info')
            
            # Запускаем обновление статистики
            self.update_stats_loop()
            
        except Exception as e:
            self.log(f"❌ Ошибка запуска сервера: {e}", 'error')
            messagebox.showerror("Ошибка", f"Не удалось запустить сервер: {e}")
    
    def update_stats_loop(self):
        """Цикл обновления статистики"""
        if self.running:
            self.update_stats()
            self.root.after(1000, self.update_stats_loop)  # Обновляем каждую секунду
    
    def stop_server(self):
        """Останавливает сервер"""
        if hasattr(self, 'game_server'):
            self.game_server.stop()
            self.running = False
            
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            self.log("⏹️ Сервер остановлен", 'warning')
    
    def clear_console(self):
        """Очищает консоль"""
        self.console_text.delete(1.0, tk.END)
    
    def run(self):
        """Запускает GUI"""
        self.root.mainloop()

class GameServer:
    def __init__(self, host='0.0.0.0', port=5555, game_mode='advanced', gui=None):
        self.host = host
        self.port = port
        self.game_mode = game_mode
        self.gui = gui  # Ссылка на GUI для логирования
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}  # team -> Framed
        self.client_threads = {}  # team -> thread
        self.game_state = {
            'turn': 0,
            'ships': {},
            'phase': 'waiting',
            'game_over': False,
            'winner': None,
            'last_hits': [],
            'game_mode': game_mode
        }
        self.actions_received = {}
        self.running = True

        # Защита общего состояния — методы обработки хода изменяют `ships`,
        # а GUI-поток одновременно читает их при построении статистики.
        self.state_lock = threading.RLock()

        # Для гейммастера
        self.game_master_framed = None
        self.game_master_thread = None

        # Сигналы от гейммастера для управления ходом.
        # start_event  — начать очередную фазу планирования (и первую, и все следующие).
        # end_event    — завершить текущую фазу планирования досрочно.
        # stop_event   — прекратить игру.
        self.gm_start_event = threading.Event()
        self.gm_end_planning_event = threading.Event()
        self.gm_stop_event = threading.Event()

        # Длительность фазы планирования в секундах. GM может это поменять.
        self.planning_timeout = 60
        # Время, когда истечёт текущая фаза планирования (epoch seconds),
        # None если сейчас не фаза сбора действий.
        self.planning_deadline = None

        # История попаданий за всю партию — для показа в клиентах.
        self.game_state['hit_history'] = []

        # Создаем корабли
        self.create_ships()
    
    def log(self, message, tag='info'):
        """Логирует сообщение через GUI"""
        if self.gui:
            self.gui.log(message, tag)
        else:
            print(message)
    
    def create_ships(self):
        """Создаёт корабли в зависимости от режима игры"""
        ships = {}
        
        if self.game_mode == 'basic':
            # Обычный режим - только крейсеры
            self.log("📦 Обычный режим: создаю 5 крейсеров для каждой команды", 'info')
            
            # Команда A
            for i in range(5):
                ship = Ship(
                    f"A_{i+1}", 
                    f"Крейсер A{i+1}", 
                    Team.TEAM_A, 
                    x=0, y=i*2, z=0,
                    ship_type=ShipType.CRUISER
                )
                ships[ship.id] = ship
            
            # Команда B
            for i in range(5):
                ship = Ship(
                    f"B_{i+1}", 
                    f"Крейсер B{i+1}", 
                    Team.TEAM_B, 
                    x=9, y=9-i*2, z=9,
                    ship_type=ShipType.CRUISER
                )
                ships[ship.id] = ship
            
            # Команда C
            for i in range(5):
                ship = Ship(
                    f"C_{i+1}", 
                    f"Крейсер C{i+1}", 
                    Team.TEAM_C, 
                    x=i*2, y=9, z=4,
                    ship_type=ShipType.CRUISER
                )
                ships[ship.id] = ship
                
        else:
            # Продвинутый режим - разные типы
            self.log("🚀 Продвинутый режим: создаю разные типы кораблей", 'success')
            
            # Команда A — стартует на грани x=0
            ships["A_1"] = Ship("A_1", "Крейсер A1", Team.TEAM_A, 0, 0, 0, ShipType.CRUISER)
            ships["A_2"] = Ship("A_2", "Артиллерия A2", Team.TEAM_A, 0, 2, 0, ShipType.ARTILLERY)
            ships["A_3"] = Ship("A_3", "Радиовышка A3", Team.TEAM_A, 0, 4, 0, ShipType.RADIO)
            ships["A_4"] = Ship("A_4", "Базовый A4", Team.TEAM_A, 0, 6, 0, ShipType.BASE)
            ships["A_5"] = Ship("A_5", "Базовый A5", Team.TEAM_A, 0, 8, 0, ShipType.BASE)
            # Новые типы (по ТЗ) — одна штука каждого, на той же грани, z=1
            ships["A_6"] = Ship("A_6", "Прыгун A6", Team.TEAM_A, 0, 1, 1, ShipType.JUMPER)
            ships["A_7"] = Ship("A_7", "Факел A7", Team.TEAM_A, 0, 3, 1, ShipType.TORCH)
            ships["A_8"] = Ship("A_8", "Тишина A8", Team.TEAM_A, 0, 5, 1, ShipType.SILENCE)
            ships["A_9"] = Ship("A_9", "Бурав A9", Team.TEAM_A, 0, 7, 1, ShipType.DRILL)
            ships["A_10"] = Ship("A_10", "Провокатор A10", Team.TEAM_A, 0, 9, 1, ShipType.PROVOCATEUR)
            ships["A_11"] = Ship("A_11", "Паук A11", Team.TEAM_A, 0, 0, 1, ShipType.SPIDER)

            # Команда B — стартует на грани x=9
            ships["B_1"] = Ship("B_1", "Крейсер B1", Team.TEAM_B, 9, 9, 9, ShipType.CRUISER)
            ships["B_2"] = Ship("B_2", "Артиллерия B2", Team.TEAM_B, 9, 7, 9, ShipType.ARTILLERY)
            ships["B_3"] = Ship("B_3", "Радиовышка B3", Team.TEAM_B, 9, 5, 9, ShipType.RADIO)
            ships["B_4"] = Ship("B_4", "Базовый B4", Team.TEAM_B, 9, 3, 9, ShipType.BASE)
            ships["B_5"] = Ship("B_5", "Базовый B5", Team.TEAM_B, 9, 1, 9, ShipType.BASE)
            ships["B_6"] = Ship("B_6", "Прыгун B6", Team.TEAM_B, 9, 8, 8, ShipType.JUMPER)
            ships["B_7"] = Ship("B_7", "Факел B7", Team.TEAM_B, 9, 6, 8, ShipType.TORCH)
            ships["B_8"] = Ship("B_8", "Тишина B8", Team.TEAM_B, 9, 4, 8, ShipType.SILENCE)
            ships["B_9"] = Ship("B_9", "Бурав B9", Team.TEAM_B, 9, 2, 8, ShipType.DRILL)
            ships["B_10"] = Ship("B_10", "Провокатор B10", Team.TEAM_B, 9, 0, 8, ShipType.PROVOCATEUR)
            ships["B_11"] = Ship("B_11", "Паук B11", Team.TEAM_B, 9, 9, 8, ShipType.SPIDER)

            # Команда C — стартует на грани y=9
            ships["C_1"] = Ship("C_1", "Крейсер C1", Team.TEAM_C, 4, 9, 4, ShipType.CRUISER)
            ships["C_2"] = Ship("C_2", "Артиллерия C2", Team.TEAM_C, 5, 9, 4, ShipType.ARTILLERY)
            ships["C_3"] = Ship("C_3", "Радиовышка C3", Team.TEAM_C, 6, 9, 4, ShipType.RADIO)
            ships["C_4"] = Ship("C_4", "Базовый C4", Team.TEAM_C, 7, 9, 4, ShipType.BASE)
            ships["C_5"] = Ship("C_5", "Базовый C5", Team.TEAM_C, 8, 9, 4, ShipType.BASE)
            ships["C_6"] = Ship("C_6", "Прыгун C6", Team.TEAM_C, 4, 9, 5, ShipType.JUMPER)
            ships["C_7"] = Ship("C_7", "Факел C7", Team.TEAM_C, 5, 9, 5, ShipType.TORCH)
            ships["C_8"] = Ship("C_8", "Тишина C8", Team.TEAM_C, 6, 9, 5, ShipType.SILENCE)
            ships["C_9"] = Ship("C_9", "Бурав C9", Team.TEAM_C, 7, 9, 5, ShipType.DRILL)
            ships["C_10"] = Ship("C_10", "Провокатор C10", Team.TEAM_C, 8, 9, 5, ShipType.PROVOCATEUR)
            ships["C_11"] = Ship("C_11", "Паук C11", Team.TEAM_C, 3, 9, 4, ShipType.SPIDER)
        
        self.game_state['ships'] = ships
        self.log(f"✅ Создано {len(ships)} кораблей", 'success')
    
    def get_visible_enemies(self, team):
        """Возвращает вражеские корабли в радиусе видимости"""
        visible_enemies = {}
        team_ships = [s for s in self.game_state['ships'].values() if s.team == team and s.alive]
        
        for ship in self.game_state['ships'].values():
            if ship.team != team and ship.alive:
                visible = False
                
                for ally in team_ships:
                    # Для радиовышки - видит всю плоскость Z
                    if self.game_mode == 'advanced' and ally.ship_type == ShipType.RADIO and ally.alive:
                        if ally.z == ship.z:
                            visible = True
                            break
                    
                    # Обычная видимость (радиус 3 клетки)
                    distance = max(
                        abs(ship.x - ally.x),
                        abs(ship.y - ally.y),
                        abs(ship.z - ally.z)
                    )
                    if distance <= 3:
                        visible = True
                        break
                
                if visible:
                    visible_enemies[ship.id] = ship.to_dict()
        
        return visible_enemies
    
    def get_full_map_for_game_master(self):
        """Возвращает полную карту для гейммастера"""
        all_ships = {}
        for ship_id, ship in self.game_state['ships'].items():
            all_ships[ship_id] = ship.to_dict()
        
        return all_ships
    
    def start(self):
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(4)
            self.log(f"📡 Сервер слушает на {self.host}:{self.port}", 'system')
            
            accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
            accept_thread.start()
            
            self.main_loop()
            
        except Exception as e:
            self.log(f"❌ Ошибка запуска сервера: {e}", 'error')
        finally:
            self.stop()
    
    def accept_clients(self):
        while self.running:
            try:
                client_socket, address = self.server.accept()
                self.log(f"📡 Новое подключение от {address}", 'info')
                
                thread = threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True)
                thread.start()
                
            except Exception as e:
                if self.running:
                    self.log(f"❌ Ошибка при принятии подключения: {e}", 'error')
    
    def handle_client(self, client_socket, address):
        framed = Framed(client_socket)
        try:
            # Первое сообщение — handshake от клиента.
            # Ограничиваем время ожидания, иначе зависший коннект удерживает поток.
            info = framed.recv_once(timeout=10)
            if info is None:
                self.log(f"⌛ Клиент {address} не прислал приветствие за 10с", 'warning')
                framed.close()
                return

            client_type = info.get('type', 'player')

            if client_type == 'game_master':
                if self.game_master_framed is not None:
                    self.log(f"⚠️ Гейммастер уже подключён — отказ {address}", 'warning')
                    try:
                        framed.send({'type': 'reject', 'reason': 'Гейммастер уже подключён'})
                    except Exception:
                        pass
                    framed.close()
                    return
                self.game_master_framed = framed
                self.game_master_thread = threading.current_thread()
                self.log(f"🎮 Подключился ГЕЙММАСТЕР", 'success')

                # Отправляем полную карту гейммастеру
                self.send_full_state_to_game_master()

                # Читаем управляющие команды от GM и диспатчим их.
                self._game_master_loop(framed)
                return

            # Подключение игрока
            team_name = info.get('team')
            player_name = info.get('player_name', 'Неизвестный')

            team_map = {
                "Team A": Team.TEAM_A,
                "Team B": Team.TEAM_B,
                "Team C": Team.TEAM_C,
            }
            team = team_map.get(team_name)
            if team is None:
                self.log(f"❌ Неизвестная команда: {team_name!r}", 'error')
                try:
                    framed.send({'type': 'reject', 'reason': f'Неизвестная команда: {team_name}'})
                except Exception:
                    pass
                framed.close()
                return

            if team in self.clients:
                self.log(f"⚠️ Команда {team.value} уже подключена", 'warning')
                try:
                    framed.send({'type': 'reject', 'reason': f'Команда {team.value} уже занята'})
                except Exception:
                    pass
                framed.close()
                return

            self.clients[team] = framed
            self.client_threads[team] = threading.current_thread()
            self.log(f"✅ Подключился {player_name} как {team.value}", 'success')
            self.log(f"   Всего игроков: {len(self.clients)}/3", 'info')

            # Отправляем начальное состояние игроку
            self.send_state_to_team(team)

            while self.running and not self.game_state['game_over']:
                time.sleep(0.5)

        except ProtocolError as e:
            self.log(f"❌ Протокольная ошибка от {address}: {e}", 'error')
        except Exception as e:
            self.log(f"❌ Ошибка в обработке клиента {address}: {e}", 'error')
    
    def send_state_to_team(self, team):
        """Отправляет состояние команде через framed-протокол."""
        framed = self.clients.get(team)
        if framed is None:
            return
        try:
            with self.state_lock:
                my_ships = {}
                for ship_id, ship in self.game_state['ships'].items():
                    if ship.team == team:
                        my_ships[ship_id] = ship.to_dict()
                visible_enemies = self.get_visible_enemies(team)

                state = {
                    'turn': self.game_state['turn'],
                    'my_ships': my_ships,
                    'visible_enemies': visible_enemies,
                    'team': team.value,
                    'phase': self.game_state['phase'],
                    'message': 'Планируйте ход' if self.game_state['phase'] == 'planning' else 'Результаты хода',
                    'game_over': self.game_state['game_over'],
                    'winner': self.game_state['winner'],
                    'game_mode': self.game_state['game_mode'],
                    'last_hits': self.game_state['last_hits'],
                    'hit_history': self.game_state['hit_history'],
                    'planning_deadline': self.planning_deadline,
                    'planning_timeout': self.planning_timeout,
                }
            framed.send(state)
        except Exception as e:
            self.log(f"❌ Ошибка отправки состояния команде {team.value}: {e}", 'error')
            self._drop_client(team)

    def _drop_client(self, team):
        """Безопасно удаляет клиента из словарей."""
        framed = self.clients.pop(team, None)
        self.client_threads.pop(team, None)
        if framed is not None:
            framed.close()

    def _game_master_loop(self, framed):
        """Поток, обслуживающий единственного GM. Ждёт сообщений типа
        ``{'type':'gm_command', 'command': ..., ...}`` и диспатчит их.

        Поддерживаемые команды:
          - ``start_turn``: разрешить main_loop начать очередную фазу планирования.
          - ``end_planning``: досрочно завершить сбор действий у игроков.
          - ``stop``: завершить игру.
          - ``set_timeout`` (seconds): поменять таймаут фазы планирования.
          - ``override_ship`` (ship_id, x, y, z, alive?): вручную поменять
            положение/состояние корабля (арбитраж GM).
        """
        while self.running and not self.game_state['game_over']:
            try:
                msg = framed.recv_once(timeout=0.5)
            except ProtocolError as e:
                self.log(f"❌ GM разорвал связь: {e}", 'error')
                self.game_master_framed = None
                # Будим все ожидающие циклы, иначе main_loop зависнет в
                # receive_actions на полный planning_timeout (до 60 с) до того,
                # как заметит gm_stop_event.
                self.gm_stop_event.set()
                self.gm_start_event.set()
                self.gm_end_planning_event.set()
                return
            except Exception as e:
                self.log(f"❌ Ошибка от GM: {e}", 'error')
                continue

            if msg is None:
                continue
            if not isinstance(msg, dict) or msg.get('type') != 'gm_command':
                continue

            self.handle_gm_command(msg)

    def handle_gm_command(self, msg):
        """Применяет одну команду от гейммастера. Выделено как метод, чтобы
        его можно было вызывать из тестов без поднятия сокета."""
        command = msg.get('command')

        if command == 'start_turn':
            self.log("🎮 GM: начинаем ход", 'success')
            self.gm_start_event.set()

        elif command == 'end_planning':
            self.log("🎮 GM: принудительно завершает фазу планирования", 'warning')
            self.gm_end_planning_event.set()

        elif command == 'stop':
            self.log("🎮 GM: остановка игры", 'warning')
            self.gm_stop_event.set()
            self.gm_start_event.set()
            self.gm_end_planning_event.set()

        elif command == 'set_timeout':
            try:
                seconds = int(msg.get('seconds', self.planning_timeout))
            except (TypeError, ValueError):
                self.log("❌ GM: set_timeout — нечисло", 'error')
                return
            if seconds < 5 or seconds > 600:
                self.log("❌ GM: set_timeout вне диапазона 5..600", 'error')
                return
            self.planning_timeout = seconds
            self.log(f"🎮 GM: таймаут фазы = {seconds}с", 'info')

        elif command == 'override_ship':
            ship_id = msg.get('ship_id')
            with self.state_lock:
                ship = self.game_state['ships'].get(ship_id)
                if ship is None:
                    self.log(f"❌ GM override: неизвестный ship_id {ship_id}", 'error')
                    return
                x = msg.get('x', ship.x)
                y = msg.get('y', ship.y)
                z = msg.get('z', ship.z)
                if not (0 <= x < 10 and 0 <= y < 10 and 0 <= z < 10):
                    self.log(f"❌ GM override: ({x},{y},{z}) вне куба", 'error')
                    return
                old = (ship.x, ship.y, ship.z, ship.alive)
                ship.x, ship.y, ship.z = int(x), int(y), int(z)
                if 'alive' in msg:
                    ship.alive = bool(msg['alive'])
                if 'hits' in msg:
                    try:
                        hits = int(msg['hits'])
                        ship.hits = max(0, min(ship.max_hits, hits))
                    except (TypeError, ValueError):
                        pass
                self.log(
                    f"🎮 GM override {ship.name}: {old} → "
                    f"({ship.x},{ship.y},{ship.z},alive={ship.alive},hits={ship.hits})",
                    'warning',
                )
            self.send_state_to_all()

        else:
            self.log(f"⚠️ GM: неизвестная команда {command!r}", 'warning')

    def send_full_state_to_game_master(self):
        """Отправляет полное состояние гейммастеру."""
        if self.game_master_framed is None:
            return
        try:
            with self.state_lock:
                all_ships = self.get_full_map_for_game_master()
                state = {
                    'type': 'game_master',
                    'turn': self.game_state['turn'],
                    'all_ships': all_ships,
                    'phase': self.game_state['phase'],
                    'game_over': self.game_state['game_over'],
                    'winner': self.game_state['winner'],
                    'last_hits': self.game_state['last_hits'],
                    'hit_history': self.game_state['hit_history'],
                    'message': f'Ход {self.game_state["turn"] + 1} - {self.game_state["phase"]}',
                    'game_mode': self.game_state['game_mode'],
                    'planning_deadline': self.planning_deadline,
                    'planning_timeout': self.planning_timeout,
                    'actions_received_teams': [t.value for t in self.actions_received.keys()],
                    'connected_teams': [t.value for t in self.clients.keys()],
                }
            self.game_master_framed.send(state)
            self.log(f"📊 Отправлена полная карта гейммастеру", 'info')
        except Exception as e:
            self.log(f"❌ Ошибка отправки состояния гейммастеру: {e}", 'error')
            try:
                self.game_master_framed.close()
            except Exception:
                pass
            self.game_master_framed = None

    def send_state_to_all(self):
        """Отправляет состояние всем подключенным"""
        for team in list(self.clients.keys()):
            self.send_state_to_team(team)
        self.send_full_state_to_game_master()
    
    def receive_actions(self, timeout=None):
        if timeout is None:
            timeout = self.planning_timeout
        self.log(f"\n{'='*60}", 'system')
        self.log(f"⏳ СБОР ДЕЙСТВИЙ (таймаут: {timeout} сек)", 'system')
        self.log(f"{'='*60}", 'system')

        self.actions_received.clear()
        start_time = time.time()
        self.planning_deadline = start_time + timeout
        self.gm_end_planning_event.clear()
        # Оповещаем всех о свежем дедлайне (чтобы клиенты смогли показать таймер).
        self.send_state_to_all()
        dropped = []

        while time.time() - start_time < timeout and self.running:
            for team, framed in list(self.clients.items()):
                if team in self.actions_received:
                    continue
                try:
                    msg = framed.recv_once(timeout=0.2)
                except ProtocolError as e:
                    self.log(f"❌ Разрыв связи с {team.value}: {e}", 'error')
                    dropped.append(team)
                    continue
                except Exception as e:
                    self.log(f"❌ Ошибка от {team.value}: {e}", 'error')
                    continue
                if msg is None:
                    continue
                try:
                    actions = [Action.from_dict(d) for d in msg]
                except (KeyError, ValueError, TypeError) as e:
                    self.log(f"❌ Некорректные действия от {team.value}: {e}", 'error')
                    continue
                self.actions_received[team] = actions
                self.log(f"✅ Получено {len(actions)} действий от {team.value}", 'success')

            for team in dropped:
                self._drop_client(team)
            dropped.clear()

            connected_teams = list(self.clients.keys())
            if connected_teams and all(team in self.actions_received for team in connected_teams):
                self.log(f"\n✅ Все команды отправили действия!", 'success')
                self.planning_deadline = None
                return True

            if self.gm_end_planning_event.is_set():
                self.log("\n⏹  GM принудительно завершил фазу планирования", 'warning')
                break

            time.sleep(0.05)

        if not self.gm_end_planning_event.is_set():
            self.log(f"\n⏰ Время вышло!", 'warning')

        self.gm_end_planning_event.clear()
        self.planning_deadline = None
        for team in list(self.clients.keys()):
            if team not in self.actions_received:
                self.actions_received[team] = []
                self.log(f"⚠️ {team.value} не ответила", 'warning')

        return True
    
    def process_turn(self):
        """Обрабатывает ход: сначала все перемещения (с проверкой коллизий
        клеток), затем симультанный залп — все попадания фиксируются от
        ПРЕДШЕСТВУЮЩИХ позиций, и только потом применяется урон. Это убирает
        эффект «кто первый отправил ход — тот первый стреляет»."""
        with self.state_lock:
            return self._process_turn_locked()

    def _process_turn_locked(self):
        self.log(f"\n{'='*60}", 'system')
        self.log(f"🔄 ОБРАБОТКА ХОДА {self.game_state['turn'] + 1}", 'system')
        self.log(f"{'='*60}", 'system')

        ships = self.game_state['ships']
        self.game_state['last_hits'] = []

        # ==== ФАЗА 1: ПЕРЕМЕЩЕНИЯ ====
        self.log("\n📦 ПЕРЕМЕЩЕНИЯ:", 'info')
        for team, actions in self.actions_received.items():
            for action in actions:
                if action.action_type != ActionType.MOVE:
                    continue
                ship = ships.get(action.ship_id)
                if not ship or not ship.alive or ship.team != team:
                    continue
                if ship.move_range <= 0:
                    self.log(f"   ⚠️ {ship.name}: не может двигаться", 'warning')
                    continue

                # Коллизия: целевая клетка не должна быть занята другим
                # живым кораблём (ни своим, ни чужим). Порядок обработки
                # зависит от порядка actions_received — это задокументировано
                # поведение: если двое целятся в одну клетку, попадёт тот,
                # чьё действие обработано раньше.
                tx, ty, tz = action.target_x, action.target_y, action.target_z
                occupied = any(
                    other.alive and other.id != ship.id
                    and other.x == tx and other.y == ty and other.z == tz
                    for other in ships.values()
                )
                if occupied:
                    self.log(f"   ⚠️ {ship.name}: клетка ({tx},{ty},{tz}) занята", 'warning')
                    continue

                old_pos = (ship.x, ship.y, ship.z)
                if ship.move(tx, ty, tz):
                    self.log(f"   {ship.name}: {old_pos} → ({ship.x},{ship.y},{ship.z})", 'info')
                else:
                    self.log(f"   ⚠️ {ship.name}: недопустимое перемещение", 'warning')

        # ==== ФАЗА 2: ВЫСТРЕЛЫ (симультанно) ====
        # Сначала для каждого выстрела определяем, в кого он попадает (если
        # вообще попадает). Урон применяем только после обработки всех выстрелов.
        self.log("\n🎯 ВЫСТРЕЛЫ:", 'info')
        hit_records = []  # список (attacker_ship, target_ship, position_tuple)
        missiles_fired = 0

        for team, actions in self.actions_received.items():
            for action in actions:
                if action.action_type != ActionType.SHOOT:
                    continue
                ship = ships.get(action.ship_id)
                if not ship or not ship.alive or ship.team != team:
                    continue
                if not ship.can_shoot:
                    self.log(f"   ⚠️ {ship.name} не может стрелять", 'warning')
                    continue
                if not ship.can_shoot_at(action.target_x, action.target_y, action.target_z):
                    self.log(f"   ⚠️ {ship.name}: недопустимая цель", 'warning')
                    continue

                missiles_fired += 1
                target_ship, position = self._resolve_shot(ship, action)
                if target_ship is not None:
                    hit_records.append((ship, target_ship, position))

        # Применяем урон одним залпом — корабль мог погибнуть, но он всё равно
        # должен был успеть выстрелить в этот же ход.
        for attacker, target, pos in hit_records:
            already_dead = not target.alive
            if already_dead:
                # Несколько попаданий в уже мёртвый корабль — всё равно лог.
                self.log(f"   💀 {attacker.name} добивает {target.name}", 'info')
            target.take_hit()
            killed = (not target.alive) and not already_dead
            hit_info = {
                'turn': self.game_state['turn'] + 1,
                'attacker': attacker.team.value,
                'attacker_name': attacker.name,
                'target': target.team.value,
                'target_name': target.name,
                'position': f"({pos[0]},{pos[1]},{pos[2]})",
                'killed': killed,
            }
            self.game_state['last_hits'].append(hit_info)
            self.game_state['hit_history'].append(hit_info)
            self.log(f"   ✅ {attacker.name} поразил {target.name}!", 'success')

        hits = [
            f"{a.name} ({a.team.value}) → {t.name} ({t.team.value})"
            for (a, t, _) in hit_records
        ]

        self.log(f"   Выпущено ракет: {missiles_fired}", 'info')

        # Результаты
        self.log(f"\n📊 РЕЗУЛЬТАТЫ ХОДА {self.game_state['turn'] + 1}:", 'system')
        
        if hits:
            self.log("💥 ПОПАДАНИЯ:", 'success')
            for hit in hits:
                self.log(f"   {hit}", 'success')
        else:
            self.log("🎯 Попаданий нет", 'info')
        
        # Проверяем конец игры
        alive_teams = 0
        winner = None
        for team in [Team.TEAM_A, Team.TEAM_B, Team.TEAM_C]:
            team_ships = [s for s in ships.values() if s.team == team]
            if any(s.alive for s in team_ships):
                alive_teams += 1
                winner = team
        
        if alive_teams <= 1:
            self.game_state['game_over'] = True
            self.game_state['winner'] = winner.value if winner else "Ничья"
            self.log(f"\n{'🎮'*20}", 'system')
            self.log(f"        ИГРА ОКОНЧЕНА!", 'system')
            self.log(f"{'🎮'*20}", 'system')
            if winner:
                self.log(f"        🏆 ПОБЕДИТЕЛЬ: {winner.value}", 'success')
            else:
                self.log(f"        🤝 НИЧЬЯ!", 'info')
            return False
        
        self.game_state['turn'] += 1
        return True

    def _resolve_shot(self, attacker, action):
        """Определяет, в кого попадает выстрел.

        Возвращает (target_ship, (x,y,z)) или (None, None).

        - Артиллерия: точечный удар в клетку (attacker уже прошёл can_shoot_at).
          Поражает любой живой корабль команды-противника в этой клетке.
        - Обычный выстрел: пуля летит по прямой по одной оси. Блокируется
          ПЕРВЫМ живым кораблём на линии (своим или чужим). Засчитывается
          попадание, только если этот корабль — из команды противника.
        """
        ships = self.game_state['ships']
        tx, ty, tz = action.target_x, action.target_y, action.target_z

        if attacker.ship_type == ShipType.ARTILLERY:
            for target in ships.values():
                if (target.alive and target.team != attacker.team
                        and target.x == tx and target.y == ty and target.z == tz):
                    return target, (tx, ty, tz)
            return None, None

        # Определяем ось и шаг
        if tx != attacker.x:
            axis = 'x'
            step = 1 if tx > attacker.x else -1
            distance = min(attacker.shoot_range, abs(tx - attacker.x))
        elif ty != attacker.y:
            axis = 'y'
            step = 1 if ty > attacker.y else -1
            distance = min(attacker.shoot_range, abs(ty - attacker.y))
        elif tz != attacker.z:
            axis = 'z'
            step = 1 if tz > attacker.z else -1
            distance = min(attacker.shoot_range, abs(tz - attacker.z))
        else:
            return None, None

        for i in range(1, distance + 1):
            if axis == 'x':
                cell = (attacker.x + i * step, attacker.y, attacker.z)
            elif axis == 'y':
                cell = (attacker.x, attacker.y + i * step, attacker.z)
            else:
                cell = (attacker.x, attacker.y, attacker.z + i * step)

            blocker = next(
                (s for s in ships.values()
                 if s.alive and s.id != attacker.id
                 and (s.x, s.y, s.z) == cell),
                None,
            )
            if blocker is None:
                continue
            # Первый корабль на линии огня блокирует выстрел.
            if blocker.team != attacker.team:
                return blocker, cell
            # Союзник загородил цель — выстрел гасится, попадания нет.
            self.log(
                f"   🛡️ Выстрел {attacker.name} заблокирован союзником {blocker.name} в {cell}",
                'warning',
            )
            return None, None

        return None, None

    def main_loop(self):
        self.log("\n⏳ ОЖИДАНИЕ ПОДКЛЮЧЕНИЙ...", 'system')
        while (len(self.clients) < 3 or self.game_master_framed is None) and self.running:
            time.sleep(1)

        if not self.running:
            return

        self.log(f"\n{'✅'*20}", 'success')
        self.log(f"     ВСЕ ПОДКЛЮЧЕНЫ!", 'success')
        self.log(f"     ИГРА НАЧИНАЕТСЯ!", 'success')
        self.log(f"{'✅'*20}\n", 'success')

        while self.running and not self.game_state['game_over']:
            # Ждём команды «start_turn» от GM (первая итерация = старт игры,
            # следующие = подтверждение перехода к следующему ходу). Это даёт
            # GM контроль темпа, паузы и арбитража.
            self.game_state['phase'] = 'waiting_for_gm'
            self.log("\n⏳ Ожидание старта хода от гейммастера...", 'info')
            self.send_state_to_all()

            # wait даёт блокирующее ожидание с возможностью проснуться
            # по stop_event (stop / разрыв с GM).
            while self.running and not self.gm_start_event.wait(timeout=0.5):
                if self.gm_stop_event.is_set():
                    break
            self.gm_start_event.clear()

            if self.gm_stop_event.is_set() or not self.running:
                break

            self.game_state['phase'] = 'planning'
            self.log(f"\n{'='*60}", 'system')
            self.log(f"🎯 ХОД {self.game_state['turn'] + 1} - ФАЗА ПЛАНИРОВАНИЯ", 'system')
            self.log(f"{'='*60}", 'system')

            self.receive_actions()

            if self.gm_stop_event.is_set() or not self.running:
                break

            continue_game = self.process_turn()

            self.game_state['phase'] = 'results'
            self.send_state_to_all()

            if not continue_game:
                break

            if not self.game_state['game_over']:
                self.log(f"\n{'─'*40}", 'system')
                self.log("⏭️  Ожидание следующего хода...", 'info')

        self.log("\n🎮 Игра завершена!", 'system')
    
    def stop(self):
        self.running = False
        for framed in list(self.clients.values()):
            try:
                framed.close()
            except Exception:
                pass
        if self.game_master_framed is not None:
            try:
                self.game_master_framed.close()
            except Exception:
                pass
            self.game_master_framed = None
        try:
            self.server.close()
        except Exception:
            pass
        self.log("\n🛑 Сервер остановлен", 'warning')

if __name__ == "__main__":
    app = GameServerGUI()
    app.run()