# server_full_visibility.py
import socket
import threading
import json
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font
from shared_simple import *

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
        
        ships = self.game_server.game_state['ships']
        
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
        
        gm_status = "✅" if self.game_server.game_master_socket else "❌"
        gm_color = self.colors['accent3'] if self.game_server.game_master_socket else 'red'
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
        self.clients = {}  # team -> socket
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
        
        # Для гейммастера
        self.game_master_socket = None
        self.game_master_thread = None
        
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
            
            # Команда A
            ships["A_1"] = Ship("A_1", "Крейсер A1", Team.TEAM_A, 0, 0, 0, ShipType.CRUISER)
            ships["A_2"] = Ship("A_2", "Артиллерия A2", Team.TEAM_A, 0, 2, 0, ShipType.ARTILLERY)
            ships["A_3"] = Ship("A_3", "Радиовышка A3", Team.TEAM_A, 0, 4, 0, ShipType.RADIO)
            ships["A_4"] = Ship("A_4", "Базовый A4", Team.TEAM_A, 0, 6, 0, ShipType.BASE)
            ships["A_5"] = Ship("A_5", "Базовый A5", Team.TEAM_A, 0, 8, 0, ShipType.BASE)
            
            # Команда B
            ships["B_1"] = Ship("B_1", "Крейсер B1", Team.TEAM_B, 9, 9, 9, ShipType.CRUISER)
            ships["B_2"] = Ship("B_2", "Артиллерия B2", Team.TEAM_B, 9, 7, 9, ShipType.ARTILLERY)
            ships["B_3"] = Ship("B_3", "Радиовышка B3", Team.TEAM_B, 9, 5, 9, ShipType.RADIO)
            ships["B_4"] = Ship("B_4", "Базовый B4", Team.TEAM_B, 9, 3, 9, ShipType.BASE)
            ships["B_5"] = Ship("B_5", "Базовый B5", Team.TEAM_B, 9, 1, 9, ShipType.BASE)
            
            # Команда C
            ships["C_1"] = Ship("C_1", "Крейсер C1", Team.TEAM_C, 4, 9, 4, ShipType.CRUISER)
            ships["C_2"] = Ship("C_2", "Артиллерия C2", Team.TEAM_C, 5, 9, 4, ShipType.ARTILLERY)
            ships["C_3"] = Ship("C_3", "Радиовышка C3", Team.TEAM_C, 6, 9, 4, ShipType.RADIO)
            ships["C_4"] = Ship("C_4", "Базовый C4", Team.TEAM_C, 7, 9, 4, ShipType.BASE)
            ships["C_5"] = Ship("C_5", "Базовый C5", Team.TEAM_C, 8, 9, 4, ShipType.BASE)
        
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
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                return
            
            info = json.loads(data)
            client_type = info.get('type', 'player')
            
            if client_type == 'game_master':
                # Подключение гейммастера
                self.game_master_socket = client_socket
                self.game_master_thread = threading.current_thread()
                self.log(f"🎮 Подключился ГЕЙММАСТЕР", 'success')
                
                # Отправляем полную карту гейммастеру
                self.send_full_state_to_game_master()
                
                while self.running and not self.game_state['game_over']:
                    time.sleep(0.5)
                    
            else:
                # Подключение игрока
                team_name = info.get('team')
                player_name = info.get('player_name', 'Неизвестный')
                
                if team_name == "Team A":
                    team = Team.TEAM_A
                elif team_name == "Team B":
                    team = Team.TEAM_B
                elif team_name == "Team C":
                    team = Team.TEAM_C
                else:
                    self.log(f"❌ Неизвестная команда: {team_name}", 'error')
                    client_socket.close()
                    return
                
                if team in self.clients:
                    self.log(f"⚠️ Команда {team.value} уже подключена", 'warning')
                    client_socket.close()
                    return
                
                self.clients[team] = client_socket
                self.client_threads[team] = threading.current_thread()
                self.log(f"✅ Подключился {player_name} как {team.value}", 'success')
                self.log(f"   Всего игроков: {len(self.clients)}/3", 'info')
                
                # Отправляем начальное состояние игроку
                self.send_state_to_team(team)
                
                while self.running and not self.game_state['game_over']:
                    time.sleep(0.5)
                
        except Exception as e:
            self.log(f"❌ Ошибка в обработке клиента {address}: {e}", 'error')
    
    def send_state_to_team(self, team):
        """Отправляет состояние команде"""
        if team in self.clients:
            try:
                my_ships = {}
                visible_enemies = self.get_visible_enemies(team)
                
                for ship_id, ship in self.game_state['ships'].items():
                    if ship.team == team:
                        my_ships[ship_id] = ship.to_dict()
                
                state = {
                    'turn': self.game_state['turn'],
                    'my_ships': my_ships,
                    'visible_enemies': visible_enemies,
                    'team': team.value,
                    'phase': self.game_state['phase'],
                    'message': 'Планируйте ход' if self.game_state['phase'] == 'planning' else 'Результаты хода',
                    'game_over': self.game_state['game_over'],
                    'winner': self.game_state['winner'],
                    'game_mode': self.game_state['game_mode']
                }
                
                self.clients[team].send(json.dumps(state).encode('utf-8'))
                
            except Exception as e:
                self.log(f"❌ Ошибка отправки состояния команде {team.value}: {e}", 'error')
                try:
                    del self.clients[team]
                    del self.client_threads[team]
                except:
                    pass
    
    def send_full_state_to_game_master(self):
        """Отправляет полное состояние гейммастеру"""
        if self.game_master_socket:
            try:
                all_ships = self.get_full_map_for_game_master()
                
                state = {
                    'type': 'game_master',
                    'turn': self.game_state['turn'],
                    'all_ships': all_ships,
                    'phase': self.game_state['phase'],
                    'game_over': self.game_state['game_over'],
                    'winner': self.game_state['winner'],
                    'last_hits': self.game_state['last_hits'],
                    'message': f'Ход {self.game_state["turn"] + 1} - {self.game_state["phase"]}',
                    'game_mode': self.game_state['game_mode']
                }
                
                self.game_master_socket.send(json.dumps(state).encode('utf-8'))
                self.log(f"📊 Отправлена полная карта гейммастеру", 'info')
                
            except Exception as e:
                self.log(f"❌ Ошибка отправки состояния гейммастеру: {e}", 'error')
    
    def send_state_to_all(self):
        """Отправляет состояние всем подключенным"""
        for team in list(self.clients.keys()):
            self.send_state_to_team(team)
        
        if self.game_master_socket:
            self.send_full_state_to_game_master()
    
    def receive_actions(self, timeout=60):
        self.log(f"\n{'='*60}", 'system')
        self.log(f"⏳ СБОР ДЕЙСТВИЙ (таймаут: {timeout} сек)", 'system')
        self.log(f"{'='*60}", 'system')
        
        self.actions_received.clear()
        start_time = time.time()
        
        while time.time() - start_time < timeout and self.running:
            for team, client in list(self.clients.items()):
                if team not in self.actions_received:
                    try:
                        client.settimeout(0.5)
                        data = client.recv(65536)
                        if data:
                            actions_data = json.loads(data.decode('utf-8'))
                            actions = []
                            for action_dict in actions_data:
                                action = Action(
                                    ship_id=action_dict['ship_id'],
                                    action_type=ActionType(action_dict['action_type']),
                                    target_x=action_dict.get('target_x'),
                                    target_y=action_dict.get('target_y'),
                                    target_z=action_dict.get('target_z')
                                )
                                actions.append(action)
                            
                            self.actions_received[team] = actions
                            self.log(f"✅ Получено {len(actions)} действий от {team.value}", 'success')
                    except socket.timeout:
                        continue
                    except Exception as e:
                        self.log(f"❌ Ошибка от {team.value}: {e}", 'error')
            
            connected_teams = list(self.clients.keys())
            if connected_teams and all(team in self.actions_received for team in connected_teams):
                self.log(f"\n✅ Все команды отправили действия!", 'success')
                return True
            
            time.sleep(0.1)
        
        self.log(f"\n⏰ Время вышло!", 'warning')
        
        for team in self.clients.keys():
            if team not in self.actions_received:
                self.actions_received[team] = []
                self.log(f"⚠️ {team.value} не ответила", 'warning')
        
        return True
    
    def process_turn(self):
        self.log(f"\n{'='*60}", 'system')
        self.log(f"🔄 ОБРАБОТКА ХОДА {self.game_state['turn'] + 1}", 'system')
        self.log(f"{'='*60}", 'system')
        
        ships = self.game_state['ships']
        self.game_state['last_hits'] = []
        
        # Обработка перемещений
        self.log("\n📦 ПЕРЕМЕЩЕНИЯ:", 'info')
        for team, actions in self.actions_received.items():
            for action in actions:
                if action.action_type == ActionType.MOVE:
                    ship = ships.get(action.ship_id)
                    if ship and ship.alive and ship.team == team:
                        if ship.move_range > 0:
                            old_pos = f"({ship.x},{ship.y},{ship.z})"
                            if ship.move(action.target_x, action.target_y, action.target_z):
                                new_pos = f"({ship.x},{ship.y},{ship.z})"
                                self.log(f"   {ship.name}: {old_pos} → {new_pos}", 'info')
                            else:
                                self.log(f"   ⚠️ {ship.name}: недопустимое перемещение", 'warning')
                        else:
                            self.log(f"   ⚠️ {ship.name}: не может двигаться", 'warning')
        
        # Обработка выстрелов
        self.log("\n🎯 ВЫСТРЕЛЫ:", 'info')
        hits = []
        missiles_fired = 0
        
        for team, actions in self.actions_received.items():
            for action in actions:
                if action.action_type == ActionType.SHOOT:
                    ship = ships.get(action.ship_id)
                    if ship and ship.alive and ship.team == team:
                        if not ship.can_shoot:
                            self.log(f"   ⚠️ {ship.name} не может стрелять", 'warning')
                            continue
                        
                        if not ship.can_shoot_at(action.target_x, action.target_y, action.target_z):
                            self.log(f"   ⚠️ {ship.name}: недопустимая цель", 'warning')
                            continue
                        
                        missiles_fired += 1
                        
                        # Для артиллерии - прямая стрельба
                        if ship.ship_type == ShipType.ARTILLERY:
                            for target_ship in ships.values():
                                if (target_ship.alive and 
                                    target_ship.team != team and
                                    target_ship.x == action.target_x and
                                    target_ship.y == action.target_y and
                                    target_ship.z == action.target_z):
                                    
                                    target_ship.take_hit()
                                    hit_info = {
                                        'attacker': ship.team.value,
                                        'attacker_name': ship.name,
                                        'target': target_ship.team.value,
                                        'target_name': target_ship.name,
                                        'position': f"({action.target_x},{action.target_y},{action.target_z})"
                                    }
                                    self.game_state['last_hits'].append(hit_info)
                                    hits.append(f"{ship.name} ({ship.team.value}) → {target_ship.name} ({target_ship.team.value})")
                                    self.log(f"   ✅ {ship.name} поразил {target_ship.name}!", 'success')
                                    break
                        
                        else:
                            # Обычная стрельба по прямой
                            if action.target_x != ship.x:
                                step = 1 if action.target_x > ship.x else -1
                                distance = min(5, abs(action.target_x - ship.x))
                                for i in range(1, distance + 1):
                                    x = ship.x + i * step
                                    for target_ship in ships.values():
                                        if (target_ship.alive and 
                                            target_ship.team != team and
                                            target_ship.x == x and 
                                            target_ship.y == ship.y and 
                                            target_ship.z == ship.z):
                                            target_ship.take_hit()
                                            hit_info = {
                                                'attacker': ship.team.value,
                                                'attacker_name': ship.name,
                                                'target': target_ship.team.value,
                                                'target_name': target_ship.name,
                                                'position': f"({x},{ship.y},{ship.z})"
                                            }
                                            self.game_state['last_hits'].append(hit_info)
                                            hits.append(f"{ship.name} ({ship.team.value}) → {target_ship.name} ({target_ship.team.value})")
                                            self.log(f"   ✅ {ship.name} поразил {target_ship.name}!", 'success')
                                            break
                            
                            elif action.target_y != ship.y:
                                step = 1 if action.target_y > ship.y else -1
                                distance = min(5, abs(action.target_y - ship.y))
                                for i in range(1, distance + 1):
                                    y = ship.y + i * step
                                    for target_ship in ships.values():
                                        if (target_ship.alive and 
                                            target_ship.team != team and
                                            target_ship.x == ship.x and 
                                            target_ship.y == y and 
                                            target_ship.z == ship.z):
                                            target_ship.take_hit()
                                            hit_info = {
                                                'attacker': ship.team.value,
                                                'attacker_name': ship.name,
                                                'target': target_ship.team.value,
                                                'target_name': target_ship.name,
                                                'position': f"({ship.x},{y},{ship.z})"
                                            }
                                            self.game_state['last_hits'].append(hit_info)
                                            hits.append(f"{ship.name} ({ship.team.value}) → {target_ship.name} ({target_ship.team.value})")
                                            self.log(f"   ✅ {ship.name} поразил {target_ship.name}!", 'success')
                                            break
                            
                            elif action.target_z != ship.z:
                                step = 1 if action.target_z > ship.z else -1
                                distance = min(5, abs(action.target_z - ship.z))
                                for i in range(1, distance + 1):
                                    z = ship.z + i * step
                                    for target_ship in ships.values():
                                        if (target_ship.alive and 
                                            target_ship.team != team and
                                            target_ship.x == ship.x and 
                                            target_ship.y == ship.y and 
                                            target_ship.z == z):
                                            target_ship.take_hit()
                                            hit_info = {
                                                'attacker': ship.team.value,
                                                'attacker_name': ship.name,
                                                'target': target_ship.team.value,
                                                'target_name': target_ship.name,
                                                'position': f"({ship.x},{ship.y},{z})"
                                            }
                                            self.game_state['last_hits'].append(hit_info)
                                            hits.append(f"{ship.name} ({ship.team.value}) → {target_ship.name} ({target_ship.team.value})")
                                            self.log(f"   ✅ {ship.name} поразил {target_ship.name}!", 'success')
                                            break
        
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
    
    def main_loop(self):
        self.log("\n⏳ ОЖИДАНИЕ ПОДКЛЮЧЕНИЙ...", 'system')
        while (len(self.clients) < 3 or not self.game_master_socket) and self.running:
            time.sleep(1)
        
        if not self.running:
            return
        
        self.log(f"\n{'✅'*20}", 'success')
        self.log(f"     ВСЕ ПОДКЛЮЧЕНЫ!", 'success')
        self.log(f"     ИГРА НАЧИНАЕТСЯ!", 'success')
        self.log(f"{'✅'*20}\n", 'success')
        
        # Ждём команды от гейммастера
        self.log("⏳ Ожидание команды гейммастера для начала игры...", 'info')
        
        while self.running and not self.game_state['game_over']:
            self.game_state['phase'] = 'planning'
            self.log(f"\n{'='*60}", 'system')
            self.log(f"🎯 ХОД {self.game_state['turn'] + 1} - ФАЗА ПЛАНИРОВАНИЯ", 'system')
            self.log(f"{'='*60}", 'system')
            
            self.send_state_to_all()
            
            self.log("\n⏳ Команды планируют свои ходы...", 'info')
            self.log("📥 Гейммастер должен нажать Enter для сбора действий...", 'info')
            
            # Здесь сервер ждёт, пока гейммастер нажмёт Enter
            # В реальном коде нужно добавить механизм ожидания команды от гейммастера
            
            self.receive_actions()
            
            continue_game = self.process_turn()
            
            self.game_state['phase'] = 'results'
            self.send_state_to_all()
            
            if not continue_game:
                self.send_state_to_all()
                break
            
            if not self.game_state['game_over']:
                self.log(f"\n{'─'*40}", 'system')
                self.log("⏭️  Ожидание следующего хода...", 'info')
        
        self.log("\n🎮 Игра завершена!", 'system')
    
    def stop(self):
        self.running = False
        for client in self.clients.values():
            try:
                client.close()
            except:
                pass
        if self.game_master_socket:
            try:
                self.game_master_socket.close()
            except:
                pass
        try:
            self.server.close()
        except:
            pass
        self.log("\n🛑 Сервер остановлен", 'warning')

if __name__ == "__main__":
    app = GameServerGUI()
    app.run()