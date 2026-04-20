# game_master_gui.py
import socket
import json
import threading
import time
from tkinter import *
from tkinter import ttk, messagebox, font
from shared_simple import *

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
            
            # Отправляем информацию о гейммастере
            game_master_info = {
                'type': 'game_master',
                'player_name': player_name
            }
            self.socket.send(json.dumps(game_master_info).encode('utf-8'))
            
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
        """Цикл получения данных от сервера"""
        while self.connected:
            try:
                self.socket.settimeout(1)
                data = self.socket.recv(65536)
                
                if not data:
                    self.connected = False
                    self.root.after(0, lambda: messagebox.showinfo("Соединение", "Сервер закрыл соединение"))
                    break
                
                state = json.loads(data.decode('utf-8'))
                self.current_state = state
                
                # Обновляем интерфейс в основном потоке
                self.root.after(0, self.update_interface, state)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.connected:
                    print(f"Ошибка получения данных: {e}")
    
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
        else:
            self.phase_label.config(text=phase.upper(), fg='gray')
        
        if game_over:
            winner = state.get('winner', 'Не определен')
            self.game_status_label.config(text=f"Окончена. Победитель: {winner}", fg='red')
            self.message_label.config(text=f"🏆 ИГРА ОКОНЧЕНА! Победитель: {winner}", fg=self.colors['accent4'])
        else:
            self.game_status_label.config(text="Идет", fg=self.colors['accent3'])
            self.message_label.config(text=message, fg='white')
        
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
        """Обновляет информацию о попаданиях"""
        self.hits_text.delete(1.0, END)
        
        last_hits = state.get('last_hits', [])
        
        if not last_hits:
            self.hits_text.insert(END, "В последнем ходу попаданий не было\n", 'info')
        else:
            self.hits_text.insert(END, f"💥 ПОПАДАНИЯ В ХОДУ {state.get('turn', 0) + 1}:\n\n", 'info')
            for hit in last_hits:
                attacker = hit.get('attacker', 'Неизвестно')
                attacker_name = hit.get('attacker_name', 'Неизвестно')
                target = hit.get('target', 'Неизвестно')
                target_name = hit.get('target_name', 'Неизвестно')
                position = hit.get('position', 'Неизвестно')
                
                self.hits_text.insert(END, f"🎯 {attacker}: {attacker_name}\n", 'hit')
                self.hits_text.insert(END, f"   → {target}: {target_name}\n", 'hit')
                self.hits_text.insert(END, f"   📍 Позиция: {position}\n", 'hit')
                self.hits_text.insert(END, "-" * 30 + "\n", 'info')
    
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
    
    def run(self):
        """Запускает приложение"""
        self.root.mainloop()

if __name__ == "__main__":
    app = GameMasterGUI()
    app.run()