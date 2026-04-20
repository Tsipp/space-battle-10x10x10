# client_player_fixed.py
import socket
import threading
import time
from tkinter import *
from tkinter import ttk, messagebox, font
from shared_simple import *
from protocol import Framed, ProtocolError

class MapWindow:
    def __init__(self, parent, team_name, team_color):
        self.parent = parent
        self.team_name = team_name
        self.team_color = team_color
        self.window = Toplevel(parent)
        self.window.title(f"🗺️ Карта - {team_name}")
        self.window.geometry("900x700")
        self.window.configure(bg='#0a0e27')
        
        # Переменные
        self.current_layer = IntVar(value=0)
        self.ships_data = {}
        self.enemies_data = {}
        
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
        
        # Создаем интерфейс
        self.create_widgets()
        
    def create_widgets(self):
        # Верхняя панель с заголовком
        header_frame = Frame(self.window, bg='#000000', height=60)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)
        
        header_label = Label(header_frame, 
                            text=f"🗺️ КАРТА {self.team_name}",
                            bg='#000000', fg=self.team_color,
                            font=('Arial', 18, 'bold'))
        header_label.pack(expand=True)
        
        # Панель управления слоями
        control_frame = Frame(self.window, bg=self.colors['panel'], height=50)
        control_frame.pack(fill=X, padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        # Слайдер слоёв с красивым оформлением
        Label(control_frame, text="🔽 Слой (Z):", 
              bg=self.colors['panel'], fg=self.colors['text'],
              font=('Arial', 11)).pack(side=LEFT, padx=10)
        
        layer_scale = Scale(control_frame, from_=0, to=9, variable=self.current_layer,
                           orient=HORIZONTAL, length=300,
                           bg=self.colors['panel'], fg=self.colors['accent1'],
                           troughcolor=self.colors['bg2'],
                           activebackground=self.colors['accent1'],
                           highlightbackground=self.colors['panel'])
        layer_scale.pack(side=LEFT, padx=10)
        
        self.layer_label = Label(control_frame, text="Z = 0",
                                bg=self.colors['panel'], fg=self.colors['accent1'],
                                font=('Arial', 14, 'bold'))
        self.layer_label.pack(side=LEFT, padx=20)
        
        # Кнопка обновления
        update_btn = Button(control_frame, text="🔄 Обновить",
                           bg=self.colors['accent1'], fg='black',
                           font=('Arial', 10, 'bold'),
                           command=self.update_map)
        update_btn.pack(side=RIGHT, padx=10)
        
        # Карта
        map_container = Frame(self.window, bg=self.colors['bg2'], bd=2, relief=SUNKEN)
        map_container.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        self.map_frame = Frame(map_container, bg=self.colors['bg2'])
        self.map_frame.pack(expand=True)
        
        # Создаем сетку 10x10
        self.cells = []
        for row in range(10):
            row_cells = []
            for col in range(10):
                cell = Label(self.map_frame, text=" ", width=4, height=2,
                           relief=RAISED, borderwidth=2,
                           font=('Arial', 10, 'bold'),
                           bg=self.colors['bg2'], fg='white')
                cell.grid(row=row, column=col, padx=2, pady=2)
                row_cells.append(cell)
            self.cells.append(row_cells)
        
        # Легенда
        legend_frame = Frame(self.window, bg=self.colors['panel'])
        legend_frame.pack(fill=X, padx=10, pady=10)
        
        legend_title = Label(legend_frame, text="📖 ЛЕГЕНДА",
                            bg=self.colors['panel'], fg=self.colors['accent4'],
                            font=('Arial', 11, 'bold'))
        legend_title.pack(anchor=W, padx=10, pady=5)
        
        # Создаем сетку для легенды
        legend_grid = Frame(legend_frame, bg=self.colors['panel'])
        legend_grid.pack(fill=X, padx=10)
        
        # Ваши корабли
        your_frame = Frame(legend_grid, bg=self.colors['panel'])
        your_frame.grid(row=0, column=0, sticky=W, padx=20, pady=2)
        
        your_dot = Label(your_frame, text="■", bg=self.colors['panel'],
                        fg=self.team_color, font=('Arial', 14))
        your_dot.pack(side=LEFT)
        Label(your_frame, text="Ваш корабль", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Крейсер
        cruiser_frame = Frame(legend_grid, bg=self.colors['panel'])
        cruiser_frame.grid(row=0, column=1, sticky=W, padx=20, pady=2)
        
        Label(cruiser_frame, text="К", bg='green', fg='white',
             font=('Arial', 10, 'bold'), width=2).pack(side=LEFT)
        Label(cruiser_frame, text="Крейсер", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Артиллерия
        art_frame = Frame(legend_grid, bg=self.colors['panel'])
        art_frame.grid(row=1, column=0, sticky=W, padx=20, pady=2)
        
        Label(art_frame, text="А", bg='green', fg='white',
             font=('Arial', 10, 'bold'), width=2).pack(side=LEFT)
        Label(art_frame, text="Артиллерия", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Радиовышка
        radio_frame = Frame(legend_grid, bg=self.colors['panel'])
        radio_frame.grid(row=1, column=1, sticky=W, padx=20, pady=2)
        
        Label(radio_frame, text="Р", bg='green', fg='white',
             font=('Arial', 10, 'bold'), width=2).pack(side=LEFT)
        Label(radio_frame, text="Радиовышка", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Враги
        enemy_frame = Frame(legend_grid, bg=self.colors['panel'])
        enemy_frame.grid(row=2, column=0, sticky=W, padx=20, pady=2)
        
        enemy_dot = Label(enemy_frame, text="■", bg=self.colors['panel'],
                         fg='red', font=('Arial', 14))
        enemy_dot.pack(side=LEFT)
        Label(enemy_frame, text="Враг", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Попадания
        hit_frame = Frame(legend_grid, bg=self.colors['panel'])
        hit_frame.grid(row=2, column=1, sticky=W, padx=20, pady=2)
        
        Label(hit_frame, text="2", bg='orange', fg='black',
             font=('Arial', 10, 'bold'), width=2).pack(side=LEFT)
        Label(hit_frame, text="Попадания", bg=self.colors['panel'],
             fg='white').pack(side=LEFT, padx=5)
        
        # Статусная строка
        self.status_label = Label(self.window,
                                  text="🗺️ Карта загружается...",
                                  bg=self.colors['bg2'], fg=self.colors['accent1'],
                                  font=('Arial', 10), anchor=W)
        self.status_label.pack(fill=X, padx=10, pady=5)
        
        # Привязываем обновление к слайдеру
        self.current_layer.trace('w', self.update_map)
        
    def update_map(self, *args):
        """Обновляет отображение карты для текущего слоя"""
        layer = self.current_layer.get()
        self.layer_label.config(text=f"Z = {layer}")
        
        # Очищаем карту
        for row in range(10):
            for col in range(10):
                self.cells[row][col].config(text=" ", bg=self.colors['bg2'], fg="white")
        
        # Отображаем свои корабли
        your_ships_count = 0
        radio_ships_on_layer = []
        
        for ship_id, ship in self.ships_data.items():
            if ship['alive'] and ship['z'] == layer:
                x, y = ship['x'], ship['y']
                
                # Определяем символ для типа корабля
                ship_type = ship.get('type', 'Базовый')
                if ship['hits'] > 0:
                    # Если есть попадания, показываем их
                    bg_color = 'orange'
                    display_text = str(ship['hits'])
                else:
                    bg_color = self.team_color
                    if ship_type == 'Крейсер':
                        display_text = "К"
                    elif ship_type == 'Артиллерия':
                        display_text = "А"
                    elif ship_type == 'Радиовышка':
                        display_text = "Р"
                        radio_ships_on_layer.append(ship)
                    else:
                        display_text = "Б"
                
                self.cells[y][x].config(
                    text=display_text,
                    bg=bg_color,
                    fg='white',
                    font=('Arial', 10, 'bold')
                )
                your_ships_count += 1
        
        # Отображаем вражеские корабли
        enemy_ships_count = 0
        for ship_id, ship in self.enemies_data.items():
            if ship['alive'] and ship['z'] == layer:
                x, y = ship['x'], ship['y']
                
                # Определяем цвет команды врага
                if ship['team'] == 'Team A':
                    enemy_color = '#4169E1'  # Синий
                elif ship['team'] == 'Team B':
                    enemy_color = '#DC143C'  # Красный
                else:
                    enemy_color = '#228B22'  # Зелёный
                
                # Если есть попадания
                if ship['hits'] > 0:
                    bg_color = 'orange'
                    display_text = str(ship['hits'])
                else:
                    bg_color = enemy_color
                    ship_type = ship.get('type', 'Базовый')
                    if ship_type == 'Крейсер':
                        display_text = "К"
                    elif ship_type == 'Артиллерия':
                        display_text = "А"
                    elif ship_type == 'Радиовышка':
                        display_text = "Р"
                    else:
                        display_text = "Б"
                
                self.cells[y][x].config(
                    text=display_text,
                    bg=bg_color,
                    fg='white',
                    font=('Arial', 10, 'bold')
                )
                enemy_ships_count += 1
        
        # Обновляем статус
        status_text = f"📍 Слой Z={layer} | 🚀 Ваших: {your_ships_count} | 🎯 Врагов: {enemy_ships_count}"
        if radio_ships_on_layer:
            status_text += " | 📡 Радиовышка сканирует слой!"
        
        self.status_label.config(text=status_text)
    
    def update_data(self, ships_data, enemies_data):
        """Обновляет данные кораблей"""
        self.ships_data = ships_data
        self.enemies_data = enemies_data
        self.update_map()

class GameClientGUI:
    def __init__(self):
        self.socket = None
        self.team = None
        self.connected = False
        self.player_name = ""
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
        
        # Цвета команд
        self.team_colors = {
            'Team A': '#4169E1',
            'Team B': '#DC143C',
            'Team C': '#228B22'
        }
        
        # Создаем главное окно
        self.root = Tk()
        self.root.title("🚀 КОСМИЧЕСКИЙ БОЙ - ИГРОК")
        self.root.geometry("1000x800")
        self.root.configure(bg=self.colors['bg'])
        
        # Переменные
        self.actions = []
        self.map_window = None
        
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
                           text="🚀 КОСМИЧЕСКИЙ БОЙ 10x10x10",
                           bg='#000000', fg=self.colors['accent1'],
                           font=('Arial', 20, 'bold'))
        title_label.pack(expand=True)
        
        subtitle_label = Label(header_frame,
                              text="КЛИЕНТ ИГРОКА",
                              bg='#000000', fg='white',
                              font=('Arial', 12))
        subtitle_label.pack()
        
        # Статусная строка под заголовком
        status_bar = Frame(self.root, bg=self.colors['panel'], height=30)
        status_bar.pack(fill=X, padx=10, pady=5)
        status_bar.pack_propagate(False)
        
        self.status_label = Label(status_bar, text="⚫ Не подключен",
                                  bg=self.colors['panel'], fg='red',
                                  font=('Arial', 10, 'bold'))
        self.status_label.pack(side=LEFT, padx=10)
        
        # Панель информации
        self.create_info_panel()
        
        # Панель кораблей
        self.create_ships_panel()
        
        # Панель врагов
        self.create_enemies_panel()
        
        # Нижняя панель с кнопками
        self.create_button_panel()
    
    def create_info_panel(self):
        """Панель с информацией о ходе"""
        info_frame = LabelFrame(self.root, text="📊 ИНФОРМАЦИЯ О ХОДЕ",
                                bg=self.colors['panel'], fg=self.colors['accent1'],
                                font=('Arial', 12, 'bold'))
        info_frame.pack(fill=X, padx=10, pady=5)
        
        # Создаем сетку для информации
        info_grid = Frame(info_frame, bg=self.colors['panel'])
        info_grid.pack(fill=X, padx=10, pady=10)
        
        # Ход
        Label(info_grid, text="Текущий ход:", bg=self.colors['panel'],
              fg=self.colors['text']).grid(row=0, column=0, sticky=W, padx=5)
        self.turn_label = Label(info_grid, text="0", bg=self.colors['panel'],
                                fg=self.colors['accent4'], font=('Arial', 12, 'bold'))
        self.turn_label.grid(row=0, column=1, sticky=W, padx=10)
        
        # Фаза
        Label(info_grid, text="Фаза игры:", bg=self.colors['panel'],
              fg=self.colors['text']).grid(row=0, column=2, sticky=W, padx=20)
        self.phase_label = Label(info_grid, text="ожидание", bg=self.colors['panel'],
                                 fg='orange', font=('Arial', 12, 'bold'))
        self.phase_label.grid(row=0, column=3, sticky=W, padx=10)
        
        # Команда
        Label(info_grid, text="Ваша команда:", bg=self.colors['panel'],
              fg=self.colors['text']).grid(row=1, column=0, sticky=W, padx=5, pady=5)
        self.team_label = Label(info_grid, text="Не выбрана", bg=self.colors['panel'],
                                fg='red', font=('Arial', 11, 'bold'))
        self.team_label.grid(row=1, column=1, sticky=W, padx=10)
        
        # Игрок
        Label(info_grid, text="Имя игрока:", bg=self.colors['panel'],
              fg=self.colors['text']).grid(row=1, column=2, sticky=W, padx=20)
        self.player_label = Label(info_grid, text="Неизвестный", bg=self.colors['panel'],
                                   fg=self.colors['accent1'], font=('Arial', 11, 'bold'))
        self.player_label.grid(row=1, column=3, sticky=W, padx=10)
        
        # Примечание о видимости
        note_frame = Frame(info_frame, bg=self.colors['panel'])
        note_frame.pack(fill=X, padx=10, pady=5)
        
        note_text = "👁️ Враги видны: в радиусе 3 клеток + вся плоскость Z от радиовышки"
        Label(note_frame, text=note_text, bg=self.colors['panel'],
              fg=self.colors['accent3'], font=('Arial', 9)).pack()
    
    def create_ships_panel(self):
        """Панель со своими кораблями"""
        ships_frame = LabelFrame(self.root, text="🚀 ВАШИ КОРАБЛИ",
                                 bg=self.colors['panel'], fg=self.colors['accent3'],
                                 font=('Arial', 12, 'bold'))
        ships_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        # Создаем Treeview с прокруткой
        tree_frame = Frame(ships_frame, bg=self.colors['panel'])
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
        
        columns = ("name", "type", "position", "status", "hits", "id")
        self.ships_tree = ttk.Treeview(tree_frame, columns=columns,
                                        show="headings", height=6)
        
        # Настраиваем колонки
        self.ships_tree.heading("name", text="Название")
        self.ships_tree.heading("type", text="Тип")
        self.ships_tree.heading("position", text="Позиция")
        self.ships_tree.heading("status", text="Статус")
        self.ships_tree.heading("hits", text="Попадания")
        self.ships_tree.heading("id", text="ID")
        
        self.ships_tree.column("name", width=150)
        self.ships_tree.column("type", width=100)
        self.ships_tree.column("position", width=120)
        self.ships_tree.column("status", width=80)
        self.ships_tree.column("hits", width=80)
        self.ships_tree.column("id", width=80)
        
        # Добавляем прокрутку
        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL,
                                  command=self.ships_tree.yview)
        self.ships_tree.configure(yscrollcommand=scrollbar.set)
        
        self.ships_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
        
        # Цветные теги для статусов
        self.ships_tree.tag_configure('alive', foreground=self.colors['accent3'])
        self.ships_tree.tag_configure('dead', foreground='gray')
    
    def create_enemies_panel(self):
        """Панель с вражескими кораблями"""
        enemies_frame = LabelFrame(self.root, text="🎯 ОБНАРУЖЕННЫЕ ВРАГИ",
                                   bg=self.colors['panel'], fg=self.colors['accent2'],
                                   font=('Arial', 12, 'bold'))
        enemies_frame.pack(fill=BOTH, expand=True, padx=10, pady=5)
        
        tree_frame = Frame(enemies_frame, bg=self.colors['panel'])
        tree_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        columns = ("name", "type", "position", "hits", "team")
        self.enemies_tree = ttk.Treeview(tree_frame, columns=columns,
                                         show="headings", height=4)
        
        self.enemies_tree.heading("name", text="Название")
        self.enemies_tree.heading("type", text="Тип")
        self.enemies_tree.heading("position", text="Позиция")
        self.enemies_tree.heading("hits", text="Попадания")
        self.enemies_tree.heading("team", text="Команда")
        
        self.enemies_tree.column("name", width=150)
        self.enemies_tree.column("type", width=100)
        self.enemies_tree.column("position", width=120)
        self.enemies_tree.column("hits", width=80)
        self.enemies_tree.column("team", width=100)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=VERTICAL,
                                  command=self.enemies_tree.yview)
        self.enemies_tree.configure(yscrollcommand=scrollbar.set)
        
        self.enemies_tree.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
    
    def create_button_panel(self):
        """Панель с кнопками управления"""
        button_frame = Frame(self.root, bg=self.colors['panel'], height=60)
        button_frame.pack(fill=X, padx=10, pady=10)
        button_frame.pack_propagate(False)
        
        # Кнопки
        self.map_button = Button(button_frame, text="🗺️ КАРТА",
                                 bg=self.colors['accent1'], fg='black',
                                 font=('Arial', 11, 'bold'),
                                 command=self.show_map, state=DISABLED)
        self.map_button.pack(side=LEFT, padx=10)
        
        self.plan_button = Button(button_frame, text="📝 ПЛАНИРОВАТЬ",
                                  bg=self.colors['accent3'], fg='black',
                                  font=('Arial', 11, 'bold'),
                                  command=self.show_planning_window, state=DISABLED)
        self.plan_button.pack(side=LEFT, padx=10)
        
        self.send_button = Button(button_frame, text="🚀 ОТПРАВИТЬ",
                                   bg='orange', fg='black',
                                   font=('Arial', 11, 'bold'),
                                   command=self.send_actions, state=DISABLED)
        self.send_button.pack(side=LEFT, padx=10)
        
        Button(button_frame, text="🔄 ОБНОВИТЬ",
               bg='#9370DB', fg='white',
               font=('Arial', 11, 'bold'),
               command=self.request_update).pack(side=LEFT, padx=10)
        
        Button(button_frame, text="❌ ВЫХОД",
               bg='red', fg='white',
               font=('Arial', 11, 'bold'),
               command=self.root.quit).pack(side=RIGHT, padx=10)
        
        # Сообщения
        self.message_label = Label(button_frame, text="",
                                    bg=self.colors['panel'], fg=self.colors['accent1'],
                                    font=('Arial', 10))
        self.message_label.pack(side=RIGHT, padx=20)
    
    def show_connection_window(self):
        """Показывает окно подключения"""
        conn_window = Toplevel(self.root)
        conn_window.title("🚀 Подключение к игре")
        conn_window.geometry("500x500")
        conn_window.configure(bg=self.colors['bg'])
        conn_window.transient(self.root)
        conn_window.grab_set()
        
        # Заголовок
        title_font = font.Font(family='Arial', size=16, weight='bold')
        Label(conn_window, text="🚀 ПОДКЛЮЧЕНИЕ К СЕРВЕРУ",
              bg=self.colors['bg'], fg=self.colors['accent1'],
              font=title_font).pack(pady=20)
        
        # Рамка с полями
        input_frame = Frame(conn_window, bg=self.colors['panel'], bd=2, relief=RAISED)
        input_frame.pack(padx=30, pady=20, fill=BOTH, expand=True)
        
        # IP сервера
        Label(input_frame, text="🌐 IP сервера:",
              bg=self.colors['panel'], fg=self.colors['text'],
              font=('Arial', 11)).pack(anchor=W, padx=20, pady=(20,5))
        
        ip_entry = Entry(input_frame, width=30, font=('Arial', 11),
                         bg=self.colors['bg2'], fg='white',
                         insertbackground='white')
        ip_entry.insert(0, "localhost")
        ip_entry.pack(padx=20, pady=5, fill=X)
        
        # Имя игрока
        Label(input_frame, text="👤 Ваше имя:",
              bg=self.colors['panel'], fg=self.colors['text'],
              font=('Arial', 11)).pack(anchor=W, padx=20, pady=(20,5))
        
        name_entry = Entry(input_frame, width=30, font=('Arial', 11),
                           bg=self.colors['bg2'], fg='white',
                           insertbackground='white')
        default_name = f"Игрок_{int(time.time()) % 1000}"
        name_entry.insert(0, default_name)
        name_entry.pack(padx=20, pady=5, fill=X)
        
        # Выбор команды
        Label(input_frame, text="🎯 Выберите команду:",
              bg=self.colors['panel'], fg=self.colors['text'],
              font=('Arial', 11)).pack(anchor=W, padx=20, pady=(20,5))
        
        team_var = StringVar(value="1")
        
        # Команда A
        team_a_frame = Frame(input_frame, bg=self.colors['panel'])
        team_a_frame.pack(anchor=W, padx=30, pady=2)
        Radiobutton(team_a_frame, text="Team A (Синие)", variable=team_var, value="1",
                   bg=self.colors['panel'], fg='white',
                   selectcolor=self.colors['bg'],
                   activebackground=self.colors['panel']).pack(side=LEFT)
        Label(team_a_frame, text="🟦", bg=self.colors['panel'],
              fg='#4169E1', font=('Arial', 12)).pack(side=LEFT, padx=5)
        
        # Команда B
        team_b_frame = Frame(input_frame, bg=self.colors['panel'])
        team_b_frame.pack(anchor=W, padx=30, pady=2)
        Radiobutton(team_b_frame, text="Team B (Красные)", variable=team_var, value="2",
                   bg=self.colors['panel'], fg='white',
                   selectcolor=self.colors['bg'],
                   activebackground=self.colors['panel']).pack(side=LEFT)
        Label(team_b_frame, text="🟥", bg=self.colors['panel'],
              fg='#DC143C', font=('Arial', 12)).pack(side=LEFT, padx=5)
        
        # Команда C
        team_c_frame = Frame(input_frame, bg=self.colors['panel'])
        team_c_frame.pack(anchor=W, padx=30, pady=2)
        Radiobutton(team_c_frame, text="Team C (Зеленые)", variable=team_var, value="3",
                   bg=self.colors['panel'], fg='white',
                   selectcolor=self.colors['bg'],
                   activebackground=self.colors['panel']).pack(side=LEFT)
        Label(team_c_frame, text="🟩", bg=self.colors['panel'],
              fg='#228B22', font=('Arial', 12)).pack(side=LEFT, padx=5)
        
        # Кнопки
        button_frame = Frame(conn_window, bg=self.colors['bg'])
        button_frame.pack(pady=20)
        
        def connect():
            server_ip = ip_entry.get().strip()
            player_name = name_entry.get().strip()
            team_choice = team_var.get()
            
            if not server_ip:
                server_ip = "localhost"
            if not player_name:
                player_name = default_name
            
            if self.connect(server_ip, team_choice, player_name):
                conn_window.destroy()
                self.root.deiconify()
            else:
                messagebox.showerror("Ошибка", "Не удалось подключиться к серверу")
        
        Button(button_frame, text="🚀 ПОДКЛЮЧИТЬСЯ",
               bg=self.colors['accent3'], fg='black',
               font=('Arial', 12, 'bold'),
               command=connect).pack(side=LEFT, padx=10)
        
        Button(button_frame, text="❌ ОТМЕНА",
               bg='red', fg='white',
               font=('Arial', 12, 'bold'),
               command=self.root.quit).pack(side=LEFT, padx=10)
    
    def connect(self, server_ip, team_choice, player_name):
        try:
            self.player_name = player_name
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((server_ip, 5555))
            self.framed = Framed(self.socket)

            # Определяем команду
            if team_choice == "1":
                self.team = Team.TEAM_A
                team_display = "Team A (Синие)"
                team_color = self.team_colors['Team A']
            elif team_choice == "2":
                self.team = Team.TEAM_B
                team_display = "Team B (Красные)"
                team_color = self.team_colors['Team B']
            elif team_choice == "3":
                self.team = Team.TEAM_C
                team_display = "Team C (Зеленые)"
                team_color = self.team_colors['Team C']
            else:
                messagebox.showerror("Ошибка", "Неверный выбор команды")
                return False

            # Отправляем информацию о команде (явно указываем тип клиента).
            team_info = {
                'type': 'player',
                'team': self.team.value,
                'player_name': player_name,
            }
            self.framed.send(team_info)

            self.connected = True
            self.team_color = team_color
            
            # Обновляем интерфейс
            self.team_label.config(text=team_display, fg=team_color)
            self.player_label.config(text=player_name)
            self.status_label.config(text="✅ Подключен к серверу", fg=self.colors['accent3'])
            
            # Активируем кнопки
            self.map_button.config(state=NORMAL)
            self.plan_button.config(state=NORMAL)
            self.send_button.config(state=NORMAL)
            
            # Запускаем поток для получения данных
            self.receive_thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.receive_thread.start()
            
            return True
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться: {e}")
            return False
    
    def receive_loop(self):
        """Цикл получения данных от сервера. Использует framed-протокол,
        каждый вызов возвращает ровно одно сообщение или None по таймауту."""
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
                    # Не выводим в stdout — его пользователь не видит.
                    err_text = f"Ошибка получения данных: {e}"
                    self.root.after(
                        0,
                        lambda t=err_text: self.status_label.config(
                            text=t, fg=self.colors['accent2']
                        ),
                    )
                    time.sleep(1)
                continue

            if msg is None:
                continue

            # Сервер может прислать reject в handshake.
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
        
        # Обновляем заголовки
        self.turn_label.config(text=str(turn))
        
        # Цвет фазы
        if phase == 'planning':
            self.phase_label.config(text="📝 ПЛАНИРОВАНИЕ", fg=self.colors['accent3'])
        elif phase == 'results':
            self.phase_label.config(text="📊 РЕЗУЛЬТАТЫ", fg='orange')
        else:
            self.phase_label.config(text=phase.upper(), fg='gray')
        
        # Проверяем наличие радиовышек
        radio_ships = []
        for ship_id, ship in state.get('my_ships', {}).items():
            if ship.get('type') == 'Радиовышка' and ship.get('alive'):
                radio_ships.append(ship)
        
        if radio_ships:
            layers = [f"Z={ship['z']}" for ship in radio_ships]
            self.message_label.config(
                text=f"📡 Радиовышка сканирует: {', '.join(layers)}",
                fg=self.colors['accent1']
            )
        else:
            self.message_label.config(text=message, fg='white')
        
        if game_over:
            winner = state.get('winner', 'Не определен')
            if winner == self.team.value:
                self.message_label.config(text="🏆 ПОБЕДА! ВЫ ВЫИГРАЛИ!", fg=self.colors['accent4'])
            else:
                self.message_label.config(text=f"Игра окончена. Победитель: {winner}", fg='gray')
            self.plan_button.config(state=DISABLED)
            self.send_button.config(state=DISABLED)
        else:
            # Активируем кнопки в фазе планирования
            if phase == 'planning':
                self.plan_button.config(state=NORMAL, bg=self.colors['accent3'])
                self.send_button.config(state=NORMAL, bg='orange')
            else:
                self.plan_button.config(state=DISABLED, bg='gray')
                self.send_button.config(state=DISABLED, bg='gray')
        
        # Обновляем список кораблей
        self.update_ships_list(state)
        
        # Обновляем список врагов
        self.update_enemies_list(state)
        
        # Обновляем карту, если она открыта
        if self.map_window and self.map_window.window.winfo_exists():
            self.map_window.update_data(
                state.get('my_ships', {}),
                state.get('visible_enemies', {})
            )
    
    def update_ships_list(self, state):
        """Обновляет список своих кораблей"""
        # Очищаем список
        for item in self.ships_tree.get_children():
            self.ships_tree.delete(item)
        
        ships = state.get('my_ships', {})
        for ship_id, ship in ships.items():
            if ship['alive']:
                status = "✅ Жив"
                tags = ('alive',)
            else:
                status = "💀 Уничтожен"
                tags = ('dead',)
            
            hits_display = f"{ship['hits']}/{ship.get('max_hits', 2)}"
            position = f"({ship['x']},{ship['y']},{ship['z']})"
            ship_type = ship.get('type', 'Базовый')
            
            self.ships_tree.insert("", "end", values=(
                ship['name'],
                ship_type,
                position,
                status,
                hits_display,
                ship_id
            ), tags=tags)
    
    def update_enemies_list(self, state):
        """Обновляет список вражеских кораблей"""
        # Очищаем список
        for item in self.enemies_tree.get_children():
            self.enemies_tree.delete(item)
        
        enemies = state.get('visible_enemies', {})
        if enemies:
            for ship_id, ship in enemies.items():
                if ship['alive']:
                    hits_display = f"{ship['hits']}/{ship.get('max_hits', 2)}"
                    position = f"({ship['x']},{ship['y']},{ship['z']})"
                    ship_type = ship.get('type', 'Базовый')
                    
                    # Определяем цвет команды
                    if ship['team'] == 'Team A':
                        team_display = "🔵 Team A"
                    elif ship['team'] == 'Team B':
                        team_display = "🔴 Team B"
                    else:
                        team_display = "🟢 Team C"
                    
                    self.enemies_tree.insert("", "end", values=(
                        ship['name'],
                        ship_type,
                        position,
                        hits_display,
                        team_display
                    ))
        else:
            # Если врагов не видно
            self.enemies_tree.insert("", "end", values=(
                "👁️ Врагов не обнаружено",
                "---",
                "---",
                "---",
                "---"
            ))
    
    def show_map(self):
        """Показывает окно с картой"""
        if not self.current_state:
            messagebox.showinfo("Информация", "Нет данных для отображения карты")
            return
        
        if self.map_window and self.map_window.window.winfo_exists():
            self.map_window.window.lift()
            self.map_window.window.focus()
        else:
            self.map_window = MapWindow(self.root, self.team.value, self.team_color)
            self.map_window.update_data(
                self.current_state.get('my_ships', {}),
                self.current_state.get('visible_enemies', {})
            )
    
    def show_planning_window(self):
        """Показывает окно планирования действий"""
        if not self.current_state or self.current_state.get('phase') != 'planning':
            messagebox.showinfo("Информация", "Сейчас не фаза планирования")
            return
        
        ships = self.current_state.get('my_ships', {})
        alive_ships = [s for s in ships.values() if s['alive']]
        
        if not alive_ships:
            messagebox.showinfo("Информация", "У вас не осталось живых кораблей")
            return
        
        planning_window = Toplevel(self.root)
        planning_window.title("📝 Планирование действий")
        planning_window.geometry("700x800")
        planning_window.configure(bg=self.colors['bg'])
        planning_window.transient(self.root)
        
        # Заголовок
        title_frame = Frame(planning_window, bg='#000000', height=60)
        title_frame.pack(fill=X)
        title_frame.pack_propagate(False)
        
        Label(title_frame, text="📝 ПЛАНИРОВАНИЕ ДЕЙСТВИЙ",
              bg='#000000', fg=self.colors['accent4'],
              font=('Arial', 16, 'bold')).pack(expand=True)
        
        # Правила
        rules_frame = Frame(planning_window, bg=self.colors['panel'])
        rules_frame.pack(fill=X, padx=10, pady=10)
        
        Label(rules_frame, text="📋 ПРАВИЛА:",
              bg=self.colors['panel'], fg=self.colors['accent1'],
              font=('Arial', 11, 'bold')).pack(anchor=W, padx=10, pady=5)
        
        rules_text = """• 🚀 Перемещение: на 1 клетку в любом направлении
• 🎯 Стрельба: обычные корабли - по прямой до 5 клеток
• 💥 Артиллерия: не двигается, стреляет куда угодно
• 📡 Радиовышка: не стреляет, сканирует весь слой Z"""
        
        Label(rules_frame, text=rules_text, bg=self.colors['panel'],
              fg='white', font=('Arial', 9), justify=LEFT).pack(anchor=W, padx=20, pady=5)
        
        # Прокручиваемый фрейм для кораблей
        canvas = Canvas(planning_window, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = Scrollbar(planning_window, orient=VERTICAL, command=canvas.yview)
        scrollable_frame = Frame(canvas, bg=self.colors['bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Список действий
        self.actions = []
        
        # Для каждого корабля
        for i, ship in enumerate(alive_ships, 1):
            # Создаем фрейм для корабля
            ship_frame = LabelFrame(scrollable_frame,
                                    text=f"🚀 КОРАБЛЬ {i}: {ship['name']}",
                                    bg=self.colors['panel'], fg=self.team_color,
                                    font=('Arial', 11, 'bold'))
            ship_frame.pack(fill=X, padx=10, pady=5, ipady=5)
            
            # Информация о корабле
            info_frame = Frame(ship_frame, bg=self.colors['panel'])
            info_frame.pack(fill=X, padx=10, pady=5)
            
            pos_text = f"📍 Позиция: ({ship['x']}, {ship['y']}, {ship['z']})"
            hits_text = f"💥 Попадания: {ship['hits']}/{ship.get('max_hits', 2)}"
            
            Label(info_frame, text=pos_text, bg=self.colors['panel'],
                  fg='white').pack(anchor=W)
            Label(info_frame, text=hits_text, bg=self.colors['panel'],
                  fg='orange' if ship['hits'] > 0 else 'white').pack(anchor=W)
            
            # Проверяем тип корабля
            ship_type = ship.get('type', 'Базовый')
            can_move = ship_type != 'Артиллерия'
            can_shoot = ship_type != 'Радиовышка'
            
            # Выбор действия
            action_var = StringVar(value="none")
            
            # Пропустить ход
            none_frame = Frame(ship_frame, bg=self.colors['panel'])
            none_frame.pack(anchor=W, padx=20, pady=2)
            Radiobutton(none_frame, text="⏭️ Пропустить ход",
                       variable=action_var, value="none",
                       bg=self.colors['panel'], fg='white',
                       selectcolor=self.colors['bg'],
                       activebackground=self.colors['panel']).pack(side=LEFT)
            
            # Переменные для координат
            move_x_var = StringVar(value=str(ship['x']))
            move_y_var = StringVar(value=str(ship['y']))
            move_z_var = StringVar(value=str(ship['z']))
            
            shoot_x_var = StringVar(value=str(ship['x']))
            shoot_y_var = StringVar(value=str(ship['y']))
            shoot_z_var = StringVar(value=str(ship['z']))
            
            # Перемещение
            if can_move:
                move_frame = Frame(ship_frame, bg=self.colors['panel'])
                move_frame.pack(anchor=W, padx=20, pady=5, fill=X)
                
                Radiobutton(move_frame, text="🚀 Переместиться в:",
                           variable=action_var, value="move",
                           bg=self.colors['panel'], fg='white',
                           selectcolor=self.colors['bg'],
                           activebackground=self.colors['panel']).pack(side=LEFT)
                
                coord_frame = Frame(move_frame, bg=self.colors['panel'])
                coord_frame.pack(side=LEFT, padx=10)
                
                Entry(coord_frame, textvariable=move_x_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
                Entry(coord_frame, textvariable=move_y_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
                Entry(coord_frame, textvariable=move_z_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
            else:
                Label(ship_frame, text="⚠️ Артиллерия не может двигаться",
                     bg=self.colors['panel'], fg='orange',
                     font=('Arial', 9)).pack(anchor=W, padx=20, pady=2)
            
            # Выстрел
            if can_shoot:
                shoot_frame = Frame(ship_frame, bg=self.colors['panel'])
                shoot_frame.pack(anchor=W, padx=20, pady=5, fill=X)
                
                if ship_type == 'Артиллерия':
                    Radiobutton(shoot_frame, text="💥 Выстрелить в любую точку:",
                               variable=action_var, value="shoot",
                               bg=self.colors['panel'], fg='white',
                               selectcolor=self.colors['bg'],
                               activebackground=self.colors['panel']).pack(side=LEFT)
                else:
                    Radiobutton(shoot_frame, text="🎯 Выстрелить в:",
                               variable=action_var, value="shoot",
                               bg=self.colors['panel'], fg='white',
                               selectcolor=self.colors['bg'],
                               activebackground=self.colors['panel']).pack(side=LEFT)
                
                coord_frame = Frame(shoot_frame, bg=self.colors['panel'])
                coord_frame.pack(side=LEFT, padx=10)
                
                Entry(coord_frame, textvariable=shoot_x_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
                Entry(coord_frame, textvariable=shoot_y_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
                Entry(coord_frame, textvariable=shoot_z_var, width=3,
                      bg=self.colors['bg2'], fg='white',
                      insertbackground='white').pack(side=LEFT, padx=1)
            else:
                Label(ship_frame, text="📡 Радиовышка не может стрелять",
                     bg=self.colors['panel'], fg='#00d4ff',
                     font=('Arial', 9)).pack(anchor=W, padx=20, pady=2)
            
            # Сохраняем данные для этого корабля
            ship_data = {
                'ship_id': ship['id'],
                'ship_name': ship['name'],
                'ship_type': ship_type,
                'ship_x': ship['x'],
                'ship_y': ship['y'],
                'ship_z': ship['z'],
                'action_var': action_var,
                'move_x': move_x_var,
                'move_y': move_y_var,
                'move_z': move_z_var,
                'shoot_x': shoot_x_var if can_shoot else None,
                'shoot_y': shoot_y_var if can_shoot else None,
                'shoot_z': shoot_z_var if can_shoot else None,
                'can_move': can_move,
                'can_shoot': can_shoot
            }
            
            # Кнопка сохранения
            Button(ship_frame, text="💾 СОХРАНИТЬ ДЕЙСТВИЕ",
                   bg=self.colors['accent3'], fg='black',
                   font=('Arial', 10, 'bold'),
                   command=lambda data=ship_data: self.save_ship_action(data)).pack(pady=10)
        
        # Кнопки внизу
        button_frame = Frame(planning_window, bg=self.colors['bg'])
        button_frame.pack(fill=X, pady=10)
        
        def send_all_actions():
            if not self.actions:
                messagebox.showwarning("Внимание", "Не сохранено ни одного действия")
                return
            
            planning_window.destroy()
            self.send_actions()
        
        Button(button_frame, text="🚀 ОТПРАВИТЬ ВСЕ ДЕЙСТВИЯ",
               bg=self.colors['accent3'], fg='black',
               font=('Arial', 12, 'bold'),
               command=send_all_actions).pack(side=LEFT, padx=10)
        
        Button(button_frame, text="❌ ЗАКРЫТЬ",
               bg='red', fg='white',
               font=('Arial', 12, 'bold'),
               command=planning_window.destroy).pack(side=RIGHT, padx=10)
        
        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)
    
    def save_ship_action(self, ship_data):
        """Сохраняет действие для корабля"""
        try:
            action_type = ship_data['action_var'].get()
            ship_id = ship_data['ship_id']
            ship_name = ship_data['ship_name']
            
            if action_type == "none":
                # Удаляем существующее действие
                self.actions = [a for a in self.actions if a.ship_id != ship_id]
                self.status_label.config(
                    text=f"⏭️ Действие для {ship_name} удалено",
                    fg=self.colors['accent4'],
                )
                return
            
            if action_type == "move":
                # Проверяем, может ли корабль двигаться
                if not ship_data['can_move']:
                    messagebox.showerror("Ошибка", "Этот корабль не может двигаться!")
                    return
                
                x = int(ship_data['move_x'].get())
                y = int(ship_data['move_y'].get())
                z = int(ship_data['move_z'].get())
                
                # Проверка: можно двигаться только на 1 клетку
                dx = abs(x - ship_data['ship_x'])
                dy = abs(y - ship_data['ship_y'])
                dz = abs(z - ship_data['ship_z'])
                
                if max(dx, dy, dz) > 1:
                    messagebox.showerror("Ошибка", "Можно перемещаться только на 1 клетку!")
                    return
                
                # Проверка границ
                if x < 0 or x > 9 or y < 0 or y > 9 or z < 0 or z > 9:
                    messagebox.showerror("Ошибка", "Координаты должны быть от 0 до 9!")
                    return
                
                action = Action(
                    ship_id=ship_id,
                    action_type=ActionType.MOVE,
                    target_x=x,
                    target_y=y,
                    target_z=z
                )
            
            elif action_type == "shoot":
                # Проверяем, может ли корабль стрелять
                if not ship_data['can_shoot']:
                    messagebox.showerror("Ошибка", "Этот корабль не может стрелять!")
                    return
                
                # Получаем координаты выстрела
                if ship_data['shoot_x'] is not None:
                    x = int(ship_data['shoot_x'].get())
                else:
                    x = ship_data['ship_x']
                    
                if ship_data['shoot_y'] is not None:
                    y = int(ship_data['shoot_y'].get())
                else:
                    y = ship_data['ship_y']
                    
                if ship_data['shoot_z'] is not None:
                    z = int(ship_data['shoot_z'].get())
                else:
                    z = ship_data['ship_z']
                
                # Проверка границ
                if x < 0 or x > 9 or y < 0 or y > 9 or z < 0 or z > 9:
                    messagebox.showerror("Ошибка", "Координаты должны быть от 0 до 9!")
                    return
                
                # Для артиллерии - любые координаты
                if ship_data['ship_type'] == 'Артиллерия':
                    # Проверка дальности (макс 10 клеток)
                    dx = abs(x - ship_data['ship_x'])
                    dy = abs(y - ship_data['ship_y'])
                    dz = abs(z - ship_data['ship_z'])
                    
                    if dx > 10 or dy > 10 or dz > 10:
                        messagebox.showerror("Ошибка", "Дальность стрельбы не более 10 клеток!")
                        return
                else:
                    # Для обычных кораблей - только по одной оси
                    changed_axes = 0
                    if x != ship_data['ship_x']: changed_axes += 1
                    if y != ship_data['ship_y']: changed_axes += 1
                    if z != ship_data['ship_z']: changed_axes += 1
                    
                    if changed_axes != 1:
                        messagebox.showerror("Ошибка", "Можно стрелять только по одной оси!")
                        return
                    
                    # Проверка дальности (максимум 5 клеток)
                    distance = max(
                        abs(x - ship_data['ship_x']), 
                        abs(y - ship_data['ship_y']), 
                        abs(z - ship_data['ship_z'])
                    )
                    if distance > 5:
                        messagebox.showerror("Ошибка", "Дальность стрельбы не более 5 клеток!")
                        return
                
                action = Action(
                    ship_id=ship_id,
                    action_type=ActionType.SHOOT,
                    target_x=x,
                    target_y=y,
                    target_z=z
                )
            
            else:
                return
            
            # Удаляем старое действие и добавляем новое
            self.actions = [a for a in self.actions if a.ship_id != ship_id]
            self.actions.append(action)
            
            self.status_label.config(
                text=f"✅ Действие для {ship_name} сохранено",
                fg=self.colors['accent3'],
            )
            
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Неверный формат координат: {e}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при сохранении: {e}")
    
    def send_actions(self):
        """Отправляет действия на сервер"""
        if not self.actions:
            messagebox.showwarning("Внимание", "Нет действий для отправки")
            return
        
        try:
            actions_data = [a.to_dict() for a in self.actions]
            self.framed.send(actions_data)

            self.status_label.config(
                text=f"🚀 Отправлено действий: {len(self.actions)}",
                fg=self.colors['accent3'],
            )
            self.actions = []

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить действия: {e}")
    
    def request_update(self):
        """Запрашивает обновление состояния"""
        if self.current_state and self.connected:
            self.update_interface(self.current_state)
    
    def run(self):
        """Запускает приложение"""
        self.root.mainloop()

if __name__ == "__main__":
    app = GameClientGUI()
    app.run()