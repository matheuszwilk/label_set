import os
import json
import threading
import tkinter as tk
from tkinter import ttk, filedialog
import serial
from tkinter.scrolledtext import ScrolledText
import logging
import csv
import re

# Importa a classe LabelManager e a função resource_path definidas em main_top
from main import LabelManager, resource_path
import modbusclient
from importlib import reload
# Limpa o cache de configuração antes de recarregar o módulo
modbusclient._modbus_config = None
modbusclient._last_config_time = 0
reload(modbusclient)

# Forçar a recarga das configurações
modbusclient.load_modbus_config()

# ---------------------------------------------------------------------------
# Custom Logging Classes
# ---------------------------------------------------------------------------
class GuiLogFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        # Exclui mensagens que contenham "api" (case-insensitive)
        if "api" in msg.lower():
            return False
        # Exclui mensagens que contenham "registro <número> do workorder:" (case-insensitive)
        if re.search(r'registro\s+\d+\s+do workorder:', msg, re.IGNORECASE):
            return False
        return True

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # Configura a tag para mensagens de warning (texto em vermelho)
        self.text_widget.tag_configure("warning", foreground="red")
        # Configura a tag para negrito (ajuste a fonte conforme necessário)
        self.text_widget.tag_configure("bold", font=("Helvetica", 10, "bold"))

    def emit(self, record):
        msg = self.format(record) + "\n"

        def append():
            self.text_widget.configure(state="normal")
            # Obtém o índice onde a nova mensagem será inserida
            start_index = self.text_widget.index("end-1c")
            self.text_widget.insert("end", msg)
            end_index = self.text_widget.index("end-1c")

            if record.levelno == logging.WARNING:
                self.text_widget.tag_add("warning", start_index, end_index)

            # Padrões para encontrar os elementos que devem ficar em bold
            serial_pattern = re.compile(r"\b[0-9A-Z]+-[0-9]+\b", re.I)
            quantity_pattern = re.compile(r"(?<=:\s)(\d+)")
            timestamp_pattern = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3}")

            for m in serial_pattern.finditer(msg):
                tag_start = f"{start_index}+{m.start()}c"
                tag_end = f"{start_index}+{m.end()}c"
                self.text_widget.tag_add("bold", tag_start, tag_end)
            
            for m in quantity_pattern.finditer(msg):
                tag_start = f"{start_index}+{m.start(1)}c"
                tag_end = f"{start_index}+{m.end(1)}c"
                self.text_widget.tag_add("bold", tag_start, tag_end)
            
            for m in timestamp_pattern.finditer(msg):
                tag_start = f"{start_index}+{m.start()}c"
                tag_end = f"{start_index}+{m.end()}c"
                self.text_widget.tag_add("bold", tag_start, tag_end)

            self.text_widget.configure(state="disabled")
            # Garante que a view desça para mostrar a nova mensagem
            self.text_widget.yview("end")

        self.text_widget.after(0, append)

# ---------------------------------------------------------------------------
# Configurações de leitura e gravação de JSON
# ---------------------------------------------------------------------------
def load_config():
    config_file = resource_path("config.json")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config
        except Exception as e:
            print("Erro ao carregar config:", e)
    return {}

def save_config(config):
    config_file = resource_path("config.json")
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print("Erro ao salvar config:", e)

# ---------------------------------------------------------------------------
# Classe Principal da Interface Gráfica
# ---------------------------------------------------------------------------
class LabelManagerGUI(tk.Tk):
    def __init__(self, label_manager=None):
        super().__init__()
        self.title("Label Manager GUI")
        self.geometry("950x650")
        self.minsize(800, 600)
        self.state("zoomed")

        # Propriedades para os tooltips dos indicadores
        self.printer_tooltip = None
        self.scanner_tooltip = None
        self.scanner2_tooltip = None  # NOVO: Tooltip para o scanner2

        # Define o diretório atual e seta o cwd
        current_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(current_dir)
        
        # Carrega o arquivo do tema azure via resource_path
        azure_path = resource_path("azure.tcl")
        if not os.path.exists(azure_path):
            raise FileNotFoundError(f"Arquivo azure.tcl não encontrado em {azure_path}")
        self.tk.call("source", azure_path)
        
        # Carrega configurações (tema, portas, etc.)
        self.config_data = load_config()
        self.current_theme = self.config_data.get("theme", "light")
        self.tk.call("set_theme", self.current_theme)
        
        # Configura estilos do tema
        self.style = ttk.Style(self)
        self.configure_theme_styles()
        
        # Configura estilos
        self.style = ttk.Style(self)
        default_font = ("Helvetica", 12)
        self.style.configure("TButton", font=default_font)
        self.style.configure("TLabel", font=default_font)
        self.style.configure("TEntry", font=default_font)
        self.style.configure("Treeview", font=default_font)
        self.style.configure("Header.TLabel", font=("Helvetica", 14, "bold"))
        self.configure(bg="#f0f0f0")
        self.style.configure("Card.TFrame",
                             background=self.cget("bg"),
                             relief="raised",
                             borderwidth=1)
        
        if label_manager:
            self.label_manager = label_manager
        else:
            serial_port = self.config_data.get("serial_port", "COM12")
            scanner_port = self.config_data.get("scanner_port", "COM6")
            scanner_port2 = self.config_data.get("scanner_port2", "COM7")
            scanner_baud_rate = self.config_data.get("scanner_baud_rate", 9600)
            scanner_baud_rate2 = self.config_data.get("scanner_baud_rate2", 9600)
            self.label_manager = LabelManager(
                serial_port=serial_port, 
                scanner_port=scanner_port,
                scanner_port2=scanner_port2,
                scanner_baud_rate=scanner_baud_rate,
                scanner_baud_rate2=scanner_baud_rate2
            )

        # Atributos para indicar se as conexões com os scanners foram estabelecidas com sucesso.
        self.scanner_connected = False
        self.scanner2_connected = False  # NOVO: Status de conexão do scanner2

        # Atributos para controlar as threads dos scanners
        self.scanner_stop_event = threading.Event()
        self.scanner_listener_thread = None
        self.scanner2_stop_event = threading.Event()  # NOVO: Evento para parar o scanner2
        self.scanner2_listener_thread = None  # NOVO: Thread para o scanner2

        # Cria o Notebook com abas
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        
        self.create_dashboard_tab()
        self.create_history_tab()
        self.create_config_tab()
        self.create_scanner_tab()  # Aba para o scanner

        # Inicia o listener contínuo do scanner
        self.start_scanner_listener()
        self.start_scanner2_listener()  # NOVO: Inicia o listener do scanner2
        self.auto_refresh_tables()
        self.start_modbus_monitor_thread()
        self.start_modbus_monitoring()

    def start_modbus_monitor_thread(self):
        """
        Inicia a thread que executa a função monitor_modbus_input.
        """
        try:
            from modbusclient import monitor_modbus_input
            self.modbus_monitor_thread = threading.Thread(target=monitor_modbus_input, daemon=True)
            self.modbus_monitor_thread.start()
            logging.info("Thread de monitoramento Modbus iniciada")
        except Exception as e:
            logging.error(f"Erro ao iniciar thread de monitoramento Modbus: {e}")

    def configure_theme_styles(self):
        """
        Configura os estilos do tema para todos os widgets
        """
        # Configurações básicas de fonte
        default_font = ("Helvetica", 10)
        header_font = ("Helvetica", 12, "bold")
        
        # Estilos gerais
        self.style.configure("TLabel", font=default_font)
        self.style.configure("TButton", font=default_font)
        self.style.configure("TEntry", font=default_font)
        self.style.configure("TCombobox", font=default_font)
        
        # Estilo para cabeçalhos
        self.style.configure("Header.TLabel", font=header_font)
        
        # Estilo para Treeview
        self.style.configure("Treeview", font=default_font)
        self.style.configure("Treeview.Heading", font=default_font)
        
        # Estilo para Frame com borda
        self.style.configure("Card.TFrame", relief="solid", borderwidth=1)
        
        # Estilo para ScrolledText (precisa ser configurado individualmente)
        self.option_add("*Text.font", default_font)
        
        # Configurações específicas para tooltips
        tooltip_bg = "#ffffff" if self.current_theme == "light" else "#333333"
        tooltip_fg = "#000000" if self.current_theme == "light" else "#ffffff"
        self.style.configure("Tooltip.TLabel", 
                           font=default_font,
                           background=tooltip_bg,
                           foreground=tooltip_fg)

    def create_dashboard_tab(self):
        """
        Cria a aba Dashboard com campo de serial, resumo, 
        indicadores de conexão das portas e painel para logs de processos.
        """
        self.dashboard_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        
        # Indicadores de conexão para Impressora e Scanner
        status_label = ttk.Label(self.dashboard_tab, text="Status das Portas:", font=("Helvetica", 12, "bold"))
        status_label.pack(anchor="w", padx=10, pady=(10, 5))
        indicator_frame = ttk.Frame(self.dashboard_tab)
        indicator_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Indicador para porta da Impressora
        printer_label = ttk.Label(indicator_frame, text="Impressora: ")
        printer_label.grid(row=0, column=0, sticky="w")
        self.printer_canvas = tk.Canvas(indicator_frame, width=20, height=20, bd=0, highlightthickness=0)
        self.printer_canvas.grid(row=0, column=1, padx=(0,20))
        initial_printer_color = "green" if self.is_printer_connected() else "red"
        self.printer_circle = self.printer_canvas.create_oval(2, 2, 18, 18, fill=initial_printer_color)
        self.printer_canvas.bind("<Enter>", self.show_printer_tooltip)
        self.printer_canvas.bind("<Leave>", self.hide_printer_tooltip)
        
        # Indicador para porta do Scanner 1
        scanner_label = ttk.Label(indicator_frame, text="Scanner 1: ")
        scanner_label.grid(row=0, column=2, sticky="w")
        self.scanner_canvas = tk.Canvas(indicator_frame, width=20, height=20, bd=0, highlightthickness=0)
        self.scanner_canvas.grid(row=0, column=3, padx=(0,20))
        initial_scanner_color = "green" if self.is_scanner_connected() else "red"
        self.scanner_circle = self.scanner_canvas.create_oval(2, 2, 18, 18, fill=initial_scanner_color)
        self.scanner_canvas.bind("<Enter>", self.show_scanner_tooltip)
        self.scanner_canvas.bind("<Leave>", self.hide_scanner_tooltip)
        
        # NOVO: Indicador para porta do Scanner 2
        scanner2_label = ttk.Label(indicator_frame, text="Scanner 2: ")
        scanner2_label.grid(row=0, column=4, sticky="w")
        self.scanner2_canvas = tk.Canvas(indicator_frame, width=20, height=20, bd=0, highlightthickness=0)
        self.scanner2_canvas.grid(row=0, column=5, padx=(0,20))
        initial_scanner2_color = "green" if self.is_scanner2_connected() else "red"
        self.scanner2_circle = self.scanner2_canvas.create_oval(2, 2, 18, 18, fill=initial_scanner2_color)
        self.scanner2_canvas.bind("<Enter>", self.show_scanner2_tooltip)
        self.scanner2_canvas.bind("<Leave>", self.hide_scanner2_tooltip)
        
        # Atualiza periodicamente os indicadores de conexão
        self.update_connection_indicators()
        
        # -------------------------------------------------------------------------------------
        # Campo de gerenciamento do serial e resumo
        # -------------------------------------------------------------------------------------
        process_frame = ttk.Frame(self.dashboard_tab, padding=10)
        process_frame.pack(side="top", fill="x")
        
        lbl_instrucoes = ttk.Label(
            process_frame,
            text="Digite o número serial (ex.: 5BPR0559-00001):"
        )
        lbl_instrucoes.grid(row=0, column=0, sticky="w", padx=5, pady=5)

        self.serial_entry = ttk.Entry(process_frame, width=30)
        self.serial_entry.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        process_button = ttk.Button(
            process_frame,
            text="Processar",
            command=self.on_process_serial
        )
        process_button.grid(row=0, column=2, padx=5, pady=5)

        self.process_status = ttk.Label(
            process_frame,
            text="",
            foreground="blue"
        )
        self.process_status.grid(row=1, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        separator = ttk.Separator(self.dashboard_tab, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=10)

        # -------------------------------------------------------------------------------------
        # Tabela de Resumo
        # -------------------------------------------------------------------------------------
        summary_frame = ttk.Frame(self.dashboard_tab, padding=10)
        summary_frame.pack(side="top", fill="both", expand=True)

        summary_label = ttk.Label(
            summary_frame,
            text="Resumo por Work Order",
            style="Header.TLabel"
        )
        summary_label.pack(pady=(0, 10))

        # Frame para conter a tabela e a barra de rolagem
        table_frame = ttk.Frame(summary_frame)
        table_frame.pack(fill="both", expand=True)

        # Configura as colunas
        columns = ("WorkOrder", "Total", "Impresso", "Restante", "Data")
        self.summary_tree = ttk.Treeview(
            table_frame, 
            columns=columns, 
            show="headings",
            height=15  # Limita a exibição inicial a 15 linhas
        )

        # Configura a barra de rolagem vertical
        scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=scrollbar_y.set)

        # Configura a barra de rolagem horizontal
        scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.summary_tree.xview)
        self.summary_tree.configure(xscrollcommand=scrollbar_x.set)

        # Configura as colunas da tabela
        for col in columns:
            self.summary_tree.heading(col, text=col)
            self.summary_tree.column(col, anchor="center", width=120, minwidth=100)

        # Posiciona os elementos usando grid
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        # Configura o grid para expandir corretamente
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)

        # Botões de controle
        button_frame = ttk.Frame(summary_frame)
        button_frame.pack(fill="x", pady=10)

        refresh_summary_btn = ttk.Button(
            button_frame,
            text="Atualizar Resumo",
            command=self.refresh_summary_table
        )
        refresh_summary_btn.pack(side="left", padx=5)

        download_summary_btn = ttk.Button(
            button_frame,
            text="Download CSV",
            command=self.download_summary_csv
        )
        download_summary_btn.pack(side="left", padx=5)

        self.refresh_summary_table()

        # -------------------------------------------------------------------------------------
        # Painel de Logs
        # -------------------------------------------------------------------------------------
        log_frame = ttk.Frame(self.dashboard_tab, padding=10)
        log_frame.pack(side="bottom", fill="both", expand=True)

        log_label = ttk.Label(log_frame, text="Process Logs", style="Header.TLabel")
        log_label.pack(anchor="w", pady=(0, 5))

        self.log_text = ScrolledText(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

        # Configura o handler de logging
        text_handler = TextHandler(self.log_text)
        text_handler.setLevel(logging.INFO)
        text_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        text_handler.addFilter(GuiLogFilter())
        logging.getLogger().addHandler(text_handler)

    def create_history_tab(self):
        """
        Cria a aba de Histórico de Impressões a partir de printed_serials.json.
        """
        self.history_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.history_tab, text="Histórico de Impressões")

        history_label = ttk.Label(
            self.history_tab,
            text="Histórico de Impressões",
            style="Header.TLabel"
        )
        history_label.pack(pady=10)

        # Add frame for treeview and scrollbar
        tree_frame = ttk.Frame(self.history_tab)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("serial", "printed", "print_timestamp", "ModelSuffix", "SerialNo")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        
        # Configure scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        scrollbar.pack(side="right", fill="y")
        
        self.history_tree.configure(yscrollcommand=self.on_history_scroll)
        self.history_tree.pack(side="left", fill="both", expand=True)

        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, anchor="center", width=150)

        refresh_history_btn = ttk.Button(
            self.history_tab,
            text="Atualizar Histórico",
            command=self.refresh_history_table
        )
        refresh_history_btn.pack(pady=10)
        
        download_history_btn = ttk.Button(
            self.history_tab,
            text="Download CSV",
            command=self.download_history_csv
        )
        download_history_btn.pack(pady=5)

        # Initialize pagination attributes
        self.records_per_page = 50
        self.current_page = 0
        self.all_records = []
        
        self.refresh_history_table()
    
    def on_history_scroll(self, *args):
        """
        Manipula eventos de rolagem na tabela de histórico.
        Verifica se os argumentos são válidos para o método yview.
        """
        if args and len(args) > 0:
            if args[0] in ('moveto', 'scroll'):
                return self.history_tree.yview(*args)
            else:
                # Se for um evento de rolagem do mouse
                delta = args[0].delta if hasattr(args[0], 'delta') else 0
                
                # Para diferentes sistemas operacionais
                if hasattr(args[0], 'num') and args[0].num in (4, 5):
                    # Linux
                    delta = 120 if args[0].num == 4 else -120
                
                # Rolar baseado no delta (direção da rolagem)
                if delta:
                    self.history_tree.yview_scroll(int(-1 * delta / 120), "units")
                return "break"  # Impede a propagação do evento
        return

    def load_more_records(self):
        """
        Loads next batch of records into the history table
        """
        start_idx = len(self.history_tree.get_children())
        end_idx = start_idx + self.records_per_page
        
        if start_idx < len(self.all_records):
            records_to_add = self.all_records[start_idx:end_idx]
            for record in records_to_add:
                values = (
                    record.get("serial", ""),
                    str(record.get("printed", "")),
                    record.get("print_timestamp", ""),
                    record.get("ModelSuffix", ""),
                    record.get("SerialNo", "")
                )
                self.history_tree.insert("", "end", values=values)

    def create_config_tab(self):
        """
        Cria a aba de Configuração para atualizar portas, tema,
        novo_darkness, desired_move_x, desired_move_y e parâmetros do Modbus.
        """
        self.config_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.config_tab, text="Configuração")

        main_frame = ttk.Frame(self.config_tab)
        main_frame.pack(fill="both", expand=True)

        header_label = ttk.Label(main_frame, text="Configurações", style="Header.TLabel")
        header_label.pack(anchor="w", pady=(0, 10))

        # Frame principal que conterá as 3 colunas
        columns_frame = ttk.Frame(main_frame)
        columns_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configurar as 3 colunas com pesos iguais
        columns_frame.columnconfigure(0, weight=1)
        columns_frame.columnconfigure(1, weight=1)
        columns_frame.columnconfigure(2, weight=1)

        # ===== COLUNA 1: Configurações de Conexão =====
        col1_frame = ttk.LabelFrame(columns_frame, text="Conexões", padding=10)
        col1_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configuração da coluna interna
        col1_frame.columnconfigure(1, weight=1)

        # Porta Printer
        port_label = ttk.Label(col1_frame, text="Porta Printer:")
        port_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.port_entry = ttk.Entry(col1_frame)
        self.port_entry.insert(0, self.config_data.get("serial_port", "COM12"))
        self.port_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Baud Rate (impressora)
        baud_rate_label = ttk.Label(col1_frame, text="Baud Rate (Printer):")
        baud_rate_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.baud_rate_entry = ttk.Entry(col1_frame)
        self.baud_rate_entry.insert(0, self.config_data.get("baud_rate", 9600))
        self.baud_rate_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Porta Scanner 1
        scanner_label = ttk.Label(col1_frame, text="Porta Scanner 1:")
        scanner_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.scanner_entry = ttk.Entry(col1_frame)
        self.scanner_entry.insert(0, self.config_data.get("scanner_port", "COM6"))
        self.scanner_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
        
        # Baud rate (scanner 1)
        scanner_baud_rate_label = ttk.Label(col1_frame, text="Baud Rate (Scanner 1):")
        scanner_baud_rate_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.scanner_baud_rate_entry = ttk.Entry(col1_frame)
        self.scanner_baud_rate_entry.insert(0, self.config_data.get("scanner_baud_rate", 9600))
        self.scanner_baud_rate_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # Porta Scanner 2
        scanner2_label = ttk.Label(col1_frame, text="Porta Scanner 2:")
        scanner2_label.grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.scanner2_entry = ttk.Entry(col1_frame)
        self.scanner2_entry.insert(0, self.config_data.get("scanner_port2", "COM7"))
        self.scanner2_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        # Baud rate (scanner 2)
        scanner2_baud_rate_label = ttk.Label(col1_frame, text="Baud Rate (Scanner 2):")
        scanner2_baud_rate_label.grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.scanner2_baud_rate_entry = ttk.Entry(col1_frame)
        self.scanner2_baud_rate_entry.insert(0, self.config_data.get("scanner_baud_rate2", 9600))
        self.scanner2_baud_rate_entry.grid(row=5, column=1, sticky="ew", padx=5, pady=5)

        # Tema
        tema_label = ttk.Label(col1_frame, text="Tema:")
        tema_label.grid(row=6, column=0, sticky="w", padx=5, pady=5)
        self.theme_var = tk.StringVar(value=self.config_data.get("theme", "light"))
        tema_combo = ttk.Combobox(col1_frame, textvariable=self.theme_var, values=["light", "dark"], state="readonly")
        tema_combo.grid(row=6, column=1, sticky="ew", padx=5, pady=5)

        # ===== COLUNA 2: Configurações de Impressão =====
        col2_frame = ttk.LabelFrame(columns_frame, text="Impressão", padding=10)
        col2_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        
        # Configuração da coluna interna
        col2_frame.columnconfigure(1, weight=1)

        # Novo Darkness
        novo_darkness_label = ttk.Label(col2_frame, text="Novo Darkness:")
        novo_darkness_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.novo_darkness_entry = ttk.Entry(col2_frame)
        self.novo_darkness_entry.insert(0, self.config_data.get("novo_darkness", 7))
        self.novo_darkness_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Desired Move X
        move_x_label = ttk.Label(col2_frame, text="Desired Move X:")
        move_x_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.move_x_entry = ttk.Entry(col2_frame)
        self.move_x_entry.insert(0, self.config_data.get("desired_move_x", 50))
        self.move_x_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Desired Move Y
        move_y_label = ttk.Label(col2_frame, text="Desired Move Y:")
        move_y_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.move_y_entry = ttk.Entry(col2_frame)
        self.move_y_entry.insert(0, self.config_data.get("desired_move_y", 0))
        self.move_y_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # zpl_scale
        zpl_scale_label = ttk.Label(col2_frame, text="ZPL Scale:")
        zpl_scale_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.zpl_scale_entry = ttk.Entry(col2_frame)
        self.zpl_scale_entry.insert(0, self.config_data.get("zpl_scale", 2))
        self.zpl_scale_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # label_type_for_workorder
        label_type_label = ttk.Label(col2_frame, text="Label Type (WorkOrder):")
        label_type_label.grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.label_type_entry = ttk.Entry(col2_frame)
        self.label_type_entry.insert(0, self.config_data.get("label_type_for_workorder", "SET"))
        self.label_type_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        # ===== COLUNA 3: Configurações do Modbus =====
        col3_frame = ttk.LabelFrame(columns_frame, text="Modbus", padding=10)
        col3_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=5)
        
        # Configuração da coluna interna
        col3_frame.columnconfigure(1, weight=1)

        # Modbus Host
        modbus_host_label = ttk.Label(col3_frame, text="Host:")
        modbus_host_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.modbus_host_entry = ttk.Entry(col3_frame)
        self.modbus_host_entry.insert(0, self.config_data.get("modbus_host", "127.0.0.1"))
        self.modbus_host_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        # Modbus Port
        modbus_port_label = ttk.Label(col3_frame, text="Port:")
        modbus_port_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.modbus_port_entry = ttk.Entry(col3_frame)
        self.modbus_port_entry.insert(0, self.config_data.get("modbus_port", 502))
        self.modbus_port_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=5)

        # Modbus Address
        modbus_address_label = ttk.Label(col3_frame, text="Address Status Impressora:")
        modbus_address_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.modbus_address_entry = ttk.Entry(col3_frame)
        self.modbus_address_entry.insert(0, self.config_data.get("modbus_address", 0))
        self.modbus_address_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=5)

        # Modbus Monitor Address (NOVO)
        modbus_monitor_label = ttk.Label(col3_frame, text="Address Sensor:")
        modbus_monitor_label.grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.modbus_monitor_entry = ttk.Entry(col3_frame)
        self.modbus_monitor_entry.insert(0, self.config_data.get("modbus_address_to_monitor", 5))
        self.modbus_monitor_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

        # Modbus Write Address (NOVO)
        modbus_write_label = ttk.Label(col3_frame, text="Address Stop/Start:")
        modbus_write_label.grid(row=4, column=0, sticky="w", padx=5, pady=5)
        self.modbus_write_entry = ttk.Entry(col3_frame)
        self.modbus_write_entry.insert(0, self.config_data.get("modbus_address_to_write", 6))
        self.modbus_write_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

        # Modbus Confirmation Address (NOVO)
        modbus_confirm_label = ttk.Label(col3_frame, text="Address Confirmação Scanner:")
        modbus_confirm_label.grid(row=5, column=0, sticky="w", padx=5, pady=5)
        self.modbus_confirm_entry = ttk.Entry(col3_frame)
        self.modbus_confirm_entry.insert(0, self.config_data.get("modbus_address_read_confirmation", 7))
        self.modbus_confirm_entry.grid(row=5, column=1, sticky="ew", padx=5, pady=5)

        # Botões (centralizados)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        # Container para centralizar os botões
        center_container = ttk.Frame(button_frame)
        center_container.pack(anchor="center")

        save_button = ttk.Button(center_container, text="Salvar Configurações", command=self.save_configuration)
        save_button.pack(side="left", padx=5)

        test_print_button = ttk.Button(center_container, text="Teste de Impressão", command=self.test_print_label)
        test_print_button.pack(side="left", padx=5)

        # Label de status (centralizada)
        self.config_status = ttk.Label(main_frame, text="", foreground="green", anchor="center", justify="center")
        self.config_status.pack(fill="x", padx=10, pady=5)
    
    def test_print_label(self):
        """
        Chama a função de teste de impressão definida em main.py (na classe LabelManager)
        """
        try:
            self.label_manager.send_test_print()
            self.config_status.config(text="Teste de impressão enviado com sucesso.")
        except Exception as e:
            self.config_status.config(text=f"Erro no teste de impressão: {str(e)}")

    def create_scanner_tab(self):
        """
        Cria a aba para exibir o status do scanner.
        """
        self.scanner_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.scanner_tab, text="Scanner")
        self.scanner_status_label = ttk.Label(
            self.scanner_tab,
            text="Scanner ativo, aguardando leitura...",
            foreground="blue"
        )
        self.scanner_status_label.pack(pady=10)

    def save_configuration(self):
        """
        Salva as configurações e atualiza o label_manager e o arquivo config.json.
        """
        new_port = self.port_entry.get().strip()
        new_scanner_port = self.scanner_entry.get().strip()
        new_scanner_port2 = self.scanner2_entry.get().strip()
        new_theme = self.theme_var.get().strip()
        
        # Darkness
        new_darkness = self.novo_darkness_entry.get().strip()
        try:
            new_darkness_value = int(new_darkness)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para o novo darkness.")
            return

        # Desired Move X
        new_move_x = self.move_x_entry.get().strip()
        try:
            new_move_x_value = int(new_move_x)
            if not (0 <= new_move_x_value <= 100):
                self.config_status.config(text="Digite um valor válido para Desired Move X (0-100).")
                return
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para Desired Move X.")
            return

        # Desired Move Y
        new_move_y = self.move_y_entry.get().strip()
        try:
            new_move_y_value = int(new_move_y)
            if not (0 <= new_move_y_value <= 100):
                self.config_status.config(text="Digite um valor válido para Desired Move Y (0-100).")
                return
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para Desired Move Y.")
            return

        # label_type_for_workorder
        new_label_type_for_workorder = self.label_type_entry.get().strip()

        # Baud Rate (impressora)
        new_baud_rate = self.baud_rate_entry.get().strip()
        try:
            new_baud_rate_value = int(new_baud_rate)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para o Baud Rate (Printer).")
            return

        # Scanner Baud Rate
        new_scanner_baud_rate = self.scanner_baud_rate_entry.get().strip()
        try:
            new_scanner_baud_rate_value = int(new_scanner_baud_rate)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para o Baud Rate (Scanner 1).")
            return
            
        # Scanner Baud Rate 2
        new_scanner_baud_rate2 = self.scanner2_baud_rate_entry.get().strip()
        try:
            new_scanner_baud_rate2_value = int(new_scanner_baud_rate2)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para o Baud Rate (Scanner 2).")
            return

        # ZPL Scale
        new_zpl_scale = self.zpl_scale_entry.get().strip()
        try:
            new_zpl_scale_value = int(new_zpl_scale)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para ZPL Scale.")
            return

        # Modbus Config
        new_modbus_host = self.modbus_host_entry.get().strip()
        new_modbus_port = self.modbus_port_entry.get().strip()
        try:
            new_modbus_port_value = int(new_modbus_port)
        except ValueError:
            self.config_status.config(text="Digite um valor numérico válido para o Modbus port.")
            return

        # Modbus Addresses
        new_modbus_address = self.modbus_address_entry.get().strip()
        new_modbus_monitor = self.modbus_monitor_entry.get().strip()  # NOVO
        new_modbus_write = self.modbus_write_entry.get().strip()  # NOVO
        new_modbus_confirm = self.modbus_confirm_entry.get().strip()  # NOVO
        
        try:
            new_modbus_address_value = int(new_modbus_address)
            new_modbus_monitor_value = int(new_modbus_monitor)  # NOVO
            new_modbus_write_value = int(new_modbus_write)  # NOVO
            new_modbus_confirm_value = int(new_modbus_confirm)  # NOVO
        except ValueError:
            self.config_status.config(text="Digite valores numéricos válidos para todos os endereços Modbus.")
            return

        if not new_port or not new_scanner_port or not new_scanner_port2 or not new_modbus_host:
            self.config_status.config(text="Digite portas e host válidos para as configurações.")
            return

        # Atualiza o dicionário config_data
        self.config_data["serial_port"] = new_port
        self.config_data["scanner_port"] = new_scanner_port
        self.config_data["scanner_port2"] = new_scanner_port2
        self.config_data["theme"] = new_theme
        self.config_data["novo_darkness"] = new_darkness_value
        self.config_data["desired_move_x"] = new_move_x_value
        self.config_data["desired_move_y"] = new_move_y_value
        self.config_data["label_type_for_workorder"] = new_label_type_for_workorder
        self.config_data["baud_rate"] = new_baud_rate_value
        self.config_data["scanner_baud_rate"] = new_scanner_baud_rate_value
        self.config_data["scanner_baud_rate2"] = new_scanner_baud_rate2_value
        self.config_data["zpl_scale"] = new_zpl_scale_value
        self.config_data["modbus_host"] = new_modbus_host
        self.config_data["modbus_port"] = new_modbus_port_value
        self.config_data["modbus_address"] = new_modbus_address_value
        # Novos campos Modbus
        self.config_data["modbus_address_to_monitor"] = new_modbus_monitor_value
        self.config_data["modbus_address_to_write"] = new_modbus_write_value
        self.config_data["modbus_address_read_confirmation"] = new_modbus_confirm_value

        # Salva no config.json
        save_config(self.config_data)

        # Atualiza atributos do LabelManager
        self.label_manager.serial_port = new_port
        self.label_manager.scanner_port = new_scanner_port
        self.label_manager.scanner_port2 = new_scanner_port2
        self.label_manager.novo_darkness = new_darkness_value
        self.label_manager.desired_move_x = new_move_x_value
        self.label_manager.desired_move_y = new_move_y_value
        self.label_manager.label_type_for_workorder = new_label_type_for_workorder
        self.label_manager.baud_rate = new_baud_rate_value
        self.label_manager.scanner_baud_rate = new_scanner_baud_rate_value
        self.label_manager.scanner_baud_rate2 = new_scanner_baud_rate2_value
        self.label_manager.zpl_scale = new_zpl_scale_value
        self.label_manager.modbus_host = new_modbus_host
        self.label_manager.modbus_port = new_modbus_port_value
        self.label_manager.modbus_address = new_modbus_address_value
        # Novos campos Modbus
        self.label_manager.modbus_address_to_monitor = new_modbus_monitor_value
        self.label_manager.modbus_address_to_write = new_modbus_write_value
        self.label_manager.modbus_address_read_confirmation = new_modbus_confirm_value

        # Reinicia os listeners dos scanners, se necessário
        self.restart_scanner_listener()
        self.restart_scanner2_listener()
        self.update_connection_indicators()

        # Se o tema mudou, aplica o novo
        if new_theme != self.current_theme:
            self.current_theme = new_theme
            self.tk.call("set_theme", self.current_theme)

        # Exemplo de recarregar o modbusclient (caso seu código já possua isso)
        import modbusclient
        from importlib import reload
        # Limpa o cache de configuração antes de recarregar
        if hasattr(modbusclient, "_modbus_config"):
            modbusclient._modbus_config = None
        reload(modbusclient)

        self.restart_modbus_monitor()

        # Exibe mensagem de sucesso
        self.config_status.config(text="Configurações atualizadas com sucesso!")

    def restart_modbus_monitor(self):
        """
        Reinicia a thread de monitoramento Modbus com as configurações atualizadas.
        """
        # Se já existe uma thread de monitoramento, para ela (não é possível realmente)
        # Uma nova thread será criada
        try:
            from modbusclient import monitor_modbus_input
            if hasattr(self, 'modbus_monitor_thread') and self.modbus_monitor_thread.is_alive():
                logging.info("Thread de monitoramento Modbus já está em execução")
            else:
                # Inicia uma nova thread de monitoramento
                self.modbus_monitor_thread = threading.Thread(target=monitor_modbus_input, daemon=True)
                self.modbus_monitor_thread.start()
                logging.info("Thread de monitoramento Modbus iniciada")
        except Exception as e:
            logging.error(f"Erro ao iniciar thread de monitoramento Modbus: {e}")

    def on_process_serial(self):
        """
        Processa o serial digitado, evitando a duplicidade.
        """
        serial_number = self.serial_entry.get().strip()
        if not serial_number:
            self.process_status.config(text="Por favor, insira um número serial.")
            return

        # if serial_number in self.label_manager.printed_serials:
        #     self.process_status.config(text="Erro: Serial já existe!")
        #     return

        self.process_status.config(text="Processando...")
        threading.Thread(
            target=self.process_serial_thread,
            args=(serial_number,),
            daemon=True
        ).start()

    def process_serial_thread(self, serial_number):
        try:
            # Para input manual, permite reimprimir mesmo que o serial já tenha sido processado.
            self.label_manager.process_serial(serial_number, allow_duplicate=True)
            self.after(0, self.process_status.config, {"text": f"Serial {serial_number} processada."})
            self.after(0, self.refresh_summary_table)
            self.after(0, self.refresh_history_table)
        except Exception as e:
            self.after(0, self.process_status.config, {"text": f"Erro: {str(e)}"})

    def auto_refresh_tables(self):
        """
        Atualiza automaticamente as tabelas de resumo e histórico a cada 5 segundos.
        Dessa forma, os dados serão carregados mesmo que o print esteja ocorrendo em fila.
        """
        self.refresh_summary_table()
        self.refresh_history_table()
        # Reagenda essa função para chamar novamente em 5000 milissegundos (5 segundos)
        self.after(1000, self.auto_refresh_tables)

    def refresh_summary_table(self):
        """
        Atualiza a tabela de resumo dos Work Orders.
        """
        for item in self.summary_tree.get_children():
            self.summary_tree.delete(item)

        last_print_dates = {}
        file_path = resource_path("printed_serials.json")
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                for record in records:
                    serial = record.get("serial", "")
                    workorder = self.label_manager.get_workorder_from_serial(serial)
                    timestamp = record.get("print_timestamp", "")
                    if workorder:
                        if workorder not in last_print_dates or timestamp > last_print_dates[workorder]:
                            last_print_dates[workorder] = timestamp
            except Exception as e:
                print("Erro ao ler arquivo de seriais impressos:", e)

        workorders = set(self.label_manager.workorder_cache.keys())
        for sn in self.label_manager.printed_serials:
            wo = self.label_manager.get_workorder_from_serial(sn)
            if wo:
                workorders.add(wo)
        
        # Ordena os workorders pela data do último print em ordem decrescente
        sorted_workorders = sorted(workorders, key=lambda wo: last_print_dates.get(wo, ""), reverse=True)

        # Insere os dados uma única vez
        for wo in sorted_workorders:
            total = self.label_manager.get_total_labels(wo)
            impresso = self.label_manager.get_printed_count_for_workorder(wo)
            restante = self.label_manager.get_remaining_labels(wo)
            data_str = last_print_dates.get(wo, "")
            if data_str:
                data_str = data_str.split("T")[0]
            self.summary_tree.insert("", "end", values=(wo, total, impresso, restante, data_str))

    def refresh_history_table(self):
        """
        Atualiza a tabela de histórico a partir de printed_serials.json,
        ordenando os registros do mais novo para o mais antigo com base no 'print_timestamp'.
        """
        # Clear existing entries
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Reset pagination
        self.current_page = 0
        self.all_records = []
        
        file_path = resource_path("printed_serials.json")
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    records = json.load(f)
                # Sort records by timestamp
                self.all_records = sorted(records, key=lambda rec: rec.get("print_timestamp", ""), reverse=True)
                
                # Load initial batch
                initial_records = self.all_records[:self.records_per_page]
                for record in initial_records:
                    values = (
                        record.get("serial", ""),
                        str(record.get("printed", "")),
                        record.get("print_timestamp", ""),
                        record.get("ModelSuffix", ""),
                        record.get("SerialNo", "")
                    )
                    self.history_tree.insert("", "end", values=values)
                    
            except Exception as e:
                print("Erro ao ler arquivo de seriais impressos:", e)

    # ---------------------------------------------------------------------------
    # Métodos para atualização dos indicadores de conexão
    # ---------------------------------------------------------------------------
    def is_printer_connected(self):
        """
        Tenta abrir a porta da impressora para verificar se está conectada.
        """
        try:
            s = serial.Serial(self.label_manager.serial_port, self.label_manager.baud_rate, timeout=1)
            s.close()
            return True
        except Exception:
            return False

    def is_scanner_connected(self):
        """
        Verifica se o scanner está operacional.
        Retorna True somente se a thread estiver ativa e a conexão com a porta foi estabelecida com sucesso.
        """
        return (self.scanner_listener_thread is not None and 
                self.scanner_listener_thread.is_alive() and 
                self.scanner_connected)
    
    def is_scanner2_connected(self):
        """
        Verifica se o scanner 2 está operacional.
        Retorna True somente se a thread estiver ativa e a conexão com a porta foi estabelecida com sucesso.
        """
        return (self.scanner2_listener_thread is not None and 
                self.scanner2_listener_thread.is_alive() and 
                self.scanner2_connected)

    def update_connection_indicators(self):
        """
        Atualiza os indicadores de conexão das portas da impressora e dos scanners.
        """
        printer_status = self.is_printer_connected()
        scanner_status = self.is_scanner_connected()
        scanner2_status = self.is_scanner2_connected()  # NOVO: Status do scanner 2
        printer_color = "green" if printer_status else "red"
        scanner_color = "green" if scanner_status else "red"
        scanner2_color = "green" if scanner2_status else "red"  # NOVO: Cor do scanner 2
        self.printer_canvas.itemconfig(self.printer_circle, fill=printer_color)
        self.scanner_canvas.itemconfig(self.scanner_circle, fill=scanner_color)
        self.scanner2_canvas.itemconfig(self.scanner2_circle, fill=scanner2_color)  # NOVO: Atualiza cor do scanner 2
        self.after(5000, self.update_connection_indicators)

    def show_printer_tooltip(self, event):
        """
        Exibe um tooltip com o status da porta da impressora.
        """
        status = "Conectada" if self.is_printer_connected() else "Desconectada"
        x = event.x_root + 10
        y = event.y_root + 10
        self.printer_tooltip = tk.Toplevel(self.printer_canvas)
        self.printer_tooltip.wm_overrideredirect(True)
        self.printer_tooltip.wm_geometry(f"+{x}+{y}")
        bg_color = self.printer_canvas.cget("bg")
        tk.Label(
            self.printer_tooltip,
            text=f"Impressora: {status}",
            bg=bg_color,
            font=("Helvetica", 10),
            borderwidth=1,
            relief="solid"
        ).pack(ipadx=5, ipady=2)

    def hide_printer_tooltip(self, event):
        """
        Remove o tooltip da impressora.
        """
        if self.printer_tooltip:
            self.printer_tooltip.destroy()
            self.printer_tooltip = None

    def show_scanner_tooltip(self, event):
        """
        Exibe um tooltip com o status da porta do scanner.
        """
        status = "Conectado" if self.is_scanner_connected() else "Desconectado"
        x = event.x_root + 10
        y = event.y_root + 10
        self.scanner_tooltip = tk.Toplevel(self.scanner_canvas)
        self.scanner_tooltip.wm_overrideredirect(True)
        self.scanner_tooltip.wm_geometry(f"+{x}+{y}")
        bg_color = self.scanner_canvas.cget("bg")
        tk.Label(
            self.scanner_tooltip,
            text=f"Scanner: {status}",
            bg=bg_color,
            font=("Helvetica", 10),
            borderwidth=1,
            relief="solid"
        ).pack(ipadx=5, ipady=2)
    
    def show_scanner2_tooltip(self, event):
        """
        Exibe um tooltip com o status da porta do scanner 2.
        """
        status = "Conectado" if self.is_scanner2_connected() else "Desconectado"
        x = event.x_root + 10
        y = event.y_root + 10
        self.scanner2_tooltip = tk.Toplevel(self.scanner2_canvas)
        self.scanner2_tooltip.wm_overrideredirect(True)
        self.scanner2_tooltip.wm_geometry(f"+{x}+{y}")
        bg_color = self.scanner2_canvas.cget("bg")
        tk.Label(
            self.scanner2_tooltip,
            text=f"Scanner 2: {status}",
            bg=bg_color,
            font=("Helvetica", 10),
            borderwidth=1,
            relief="solid"
        ).pack(ipadx=5, ipady=2)

    def hide_scanner_tooltip(self, event):
        """
        Remove o tooltip do scanner.
        """
        if self.scanner_tooltip:
            self.scanner_tooltip.destroy()
            self.scanner_tooltip = None

    def hide_scanner2_tooltip(self, event):
        """
        Remove o tooltip do scanner 2.
        """
        if self.scanner2_tooltip:
            self.scanner2_tooltip.destroy()
            self.scanner2_tooltip = None

    # ---------------------------------------------------------------------------
    # Métodos para controle da thread do scanner
    # ---------------------------------------------------------------------------
    def start_scanner_listener(self):
        """
        Inicia uma thread que mantém a porta do scanner aberta para leituras.
        """
        self.scanner_stop_event.clear()
        self.scanner_listener_thread = threading.Thread(target=self.scanner_listener, daemon=True)
        self.scanner_listener_thread.start()

    def start_scanner2_listener(self):
        """
        Inicia uma thread que mantém a porta do scanner 2 aberta para leituras.
        """
        self.scanner2_stop_event.clear()
        self.scanner2_listener_thread = threading.Thread(target=self.scanner2_listener, daemon=True)
        self.scanner2_listener_thread.start()

    def stop_scanner_listener(self):
        """
        Para a thread de leitura do scanner.
        """
        self.scanner_stop_event.set()
        if self.scanner_listener_thread:
            self.scanner_listener_thread.join(timeout=2)
            self.scanner_listener_thread = None

    def stop_scanner2_listener(self):
        """
        Para a thread de leitura do scanner 2.
        """
        self.scanner2_stop_event.set()
        if self.scanner2_listener_thread:
            self.scanner2_listener_thread.join(timeout=2)
            self.scanner2_listener_thread = None

    def restart_scanner_listener(self):
        """
        Reinicia a thread de leitura do scanner.
        """
        self.stop_scanner_listener()
        self.start_scanner_listener()

    def restart_scanner2_listener(self):
        """
        Reinicia a thread de leitura do scanner 2.
        """
        self.stop_scanner2_listener()
        self.start_scanner2_listener()

    def scanner_listener(self):
        """
        Lê continuamente a porta do scanner e processa cada código lido.
        Atualiza o status de conexão do scanner com base na tentativa de abrir a porta.
        """
        while not self.scanner_stop_event.is_set():
            try:
                with serial.Serial(self.label_manager.scanner_port,
                                   self.label_manager.scanner_baud_rate,
                                   timeout=1) as scanner:
                    self.scanner_connected = True
                    while not self.scanner_stop_event.is_set():
                        barcode_bytes = scanner.readline()
                        barcode = barcode_bytes.decode().strip() if barcode_bytes else ""
                        if barcode:
                            self.after(0, self.process_scanned_barcode, barcode)
            except Exception as e:
                self.scanner_connected = False
                self.after(0, self.scanner_status_label.config, {"text": f"Erro no scanner: {str(e)}"})
                # Aguarda um curto período antes de tentar reconectar
                self.scanner_stop_event.wait(2)

    def scanner2_listener(self):
        """
        Lê continuamente a porta do scanner 2 e processa cada código lido.
        Atualiza o status de conexão do scanner 2 com base na tentativa de abrir a porta.
        """
        while not self.scanner2_stop_event.is_set():
            try:
                with serial.Serial(self.label_manager.scanner_port2,
                                  self.label_manager.scanner_baud_rate2,
                                  timeout=1) as scanner:
                    self.scanner2_connected = True
                    while not self.scanner2_stop_event.is_set():
                        barcode_bytes = scanner.readline()
                        barcode = barcode_bytes.decode().strip() if barcode_bytes else ""
                        if barcode:
                            self.after(0, self.process_scanned_barcode, barcode)
            except Exception as e:
                self.scanner2_connected = False
                self.after(0, self.scanner_status_label.config, {"text": f"Erro no scanner 2: {str(e)}"})
                # Aguarda um curto período antes de tentar reconectar
                self.scanner2_stop_event.wait(2)
    
    def start_modbus_monitoring(self):
        """
        Inicia o monitoramento dos endereços Modbus em uma thread separada.
        """
        # Importa o módulo modbus e threading
        from modbusclient import monitor_modbus_input
        import threading
        
        # Inicia o monitoramento em uma thread separada
        self.modbus_monitor_thread = threading.Thread(
            target=monitor_modbus_input,
            kwargs={
                'address_to_monitor': 1,
                'address_to_write': 2,
                'address_read_confirmation': 3
            },
            daemon=True
        )
        self.modbus_monitor_thread.start()
        logging.info("Monitoramento Modbus iniciado nos endereços 1, 2 e 3.")

    def process_scanned_barcode(self, barcode):
        """
        Atualiza a aba do scanner e processa o código lido.
        """
        self.scanner_status_label.config(text=f"Código lido: {barcode}")
        threading.Thread(target=self.process_scanned_barcode_thread, args=(barcode,), daemon=True).start()

    def process_scanned_barcode_thread(self, barcode):
        try:
            self.label_manager.process_serial(barcode)
            # Atualiza o label de status para mostrar o processamento do serial
            self.after(0, self.process_status.config, {"text": f"Serial {barcode} processada."})
            self.after(0, self.refresh_summary_table)
            self.after(0, self.refresh_history_table)
        except Exception as e:
            print("Erro ao processar barcode:", e)
            self.after(0, self.process_status.config, {"text": f"Erro: {str(e)}"})

    def download_history_csv(self):
        """
        Exporta os dados da tabela de Histórico de Impressões em um arquivo CSV.
        """
        file_path = filedialog.asksaveasfilename(
            initialfile="history.csv",
            title="Salvar CSV do Histórico de Impressões",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if not file_path:
            return
        headers = ("serial", "printed", "print_timestamp", "ModelSuffix", "SerialNo")
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(headers)
                for item in self.history_tree.get_children():
                    row_data = self.history_tree.item(item)["values"]
                    csvwriter.writerow(row_data)
            self.process_status.config(text="Histórico exportado com sucesso!")
        except Exception as e:
            print("Erro ao exportar CSV do Histórico:", e)
            self.process_status.config(text=f"Erro ao salvar CSV: {str(e)}")

    def download_summary_csv(self):
        """
        Exporta os dados da tabela de Resumo por Work Order em um arquivo CSV.
        """
        file_path = filedialog.asksaveasfilename(
            initialfile="summary.csv",
            title="Salvar CSV do Resumo do Work Order",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*"))
        )
        if not file_path:
            return
        headers = ("WorkOrder", "Total", "Impresso", "Restante", "Data")
        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                csvwriter = csv.writer(csvfile)
                csvwriter.writerow(headers)
                for item in self.summary_tree.get_children():
                    row_data = self.summary_tree.item(item)["values"]
                    csvwriter.writerow(row_data)
            self.process_status.config(text="Resumo exportado com sucesso!")
        except Exception as e:
            print("Erro ao exportar CSV do Resumo:", e)
            self.process_status.config(text=f"Erro ao salvar CSV: {str(e)}")

    def start_modbus_monitoring(self):
        """
        Monitora os registradores Modbus para detectar erros e exibir alertas.
        Verifica periodicamente o status da impressora e do scanner via Modbus.
        """
        try:
            # Carrega os endereços dos registradores Modbus a partir da configuração
            modbus_address = self.config_data.get("modbus_address", 0)
            modbus_address_to_write = self.config_data.get("modbus_address_to_write", 6)
            
            # Lê o valor dos registradores
            from modbusclient import read_modbus_register_silent
            
            printer_status = read_modbus_register_silent(modbus_address)
            scanner_status = read_modbus_register_silent(modbus_address_to_write)
            
            # Verifica se há erro na impressora (valor 1 no endereço da impressora)
            if printer_status == 1:
                self.show_printer_error_alert()
            
            # Verifica se há erro no scanner (valor 1 no endereço do scanner)
            if scanner_status == 1:
                self.show_scanner_error_alert()
                
        except Exception as e:
            logging.error(f"Erro ao monitorar registradores Modbus: {e}")
        
        # Agenda a próxima verificação para daqui a 2 segundos
        self.after(2000, self.start_modbus_monitoring)
    
    def show_printer_error_alert(self):
        """
        Exibe um alerta sobre problemas na impressora com efeito piscante.
        """
        try:
            # Verifica se já existe uma janela de alerta aberta
            if hasattr(self, 'printer_alert_window') and self.printer_alert_window.winfo_exists():
                return  # Evita criar múltiplas janelas de alerta
            
            self.printer_alert_window = tk.Toplevel(self)
            self.printer_alert_window.title("ALERTA - IMPRESSORA")
            
            # Aumenta o tamanho da janela
            self.printer_alert_window.geometry("600x450")
            self.printer_alert_window.configure(bg="red")
            
            # Centraliza a janela na tela
            window_width = 600
            window_height = 450
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            self.printer_alert_window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
            
            # Configura para ficar sempre visível
            self.printer_alert_window.attributes('-topmost', True)
            
            # Cria uma borda visível ao redor da janela
            self.printer_alert_window.configure(highlightbackground="red", highlightcolor="red", 
                                               highlightthickness=5, bd=5)
            
            # Adiciona um frame para o conteúdo
            frame = ttk.Frame(self.printer_alert_window, padding=20)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Ícone de alerta
            alert_label = ttk.Label(frame, text="⚠️", font=("Helvetica", 60))
            alert_label.pack(pady=20)
            
            # Mensagem de erro
            error_label = ttk.Label(
                frame, 
                text="ERRO NA IMPRESSORA!\n\nVerifique se há falta de papel, ribbon ou se a impressora está em pausa.",
                font=("Helvetica", 16, "bold"),
                wraplength=500,
                justify="center"
            )
            error_label.pack(pady=20)
            
            # Botão para fechar o alerta
            close_button = ttk.Button(
                frame, 
                text="Entendi, verificar impressora", 
                command=self.printer_alert_window.destroy,
                style="Accent.TButton"
            )
            close_button.pack(pady=20)
            
            # Som de alerta
            self.bell()
            
            # Inicializa variáveis para controle do piscar
            self.printer_alert_window.blink_state = True
            self.printer_alert_window.blink_job = None
            
            # Inicia o efeito de piscar
            self._blink_window_border(self.printer_alert_window, "red")
            
            # Configura para parar o piscar quando a janela for fechada
            self.printer_alert_window.protocol("WM_DELETE_WINDOW", 
                                              lambda: self._stop_blinking_and_close(self.printer_alert_window))
            
        except Exception as e:
            logging.error(f"Erro ao exibir alerta da impressora: {e}")
    
    def show_scanner_error_alert(self):
        """
        Exibe um alerta sobre problemas no scanner com efeito piscante.
        """
        try:
            # Verifica se já existe uma janela de alerta aberta
            if hasattr(self, 'scanner_alert_window') and self.scanner_alert_window.winfo_exists():
                return  # Evita criar múltiplas janelas de alerta
            
            self.scanner_alert_window = tk.Toplevel(self)
            self.scanner_alert_window.title("ALERTA - SCANNER")
            
            # Aumenta o tamanho da janela
            self.scanner_alert_window.geometry("600x450")
            self.scanner_alert_window.configure(bg="orange")
            
            # Centraliza a janela na tela
            window_width = 600
            window_height = 450
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            center_x = int(screen_width/2 - window_width/2)
            center_y = int(screen_height/2 - window_height/2)
            self.scanner_alert_window.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
            
            # Configura para ficar sempre visível
            self.scanner_alert_window.attributes('-topmost', True)
            
            # Cria uma borda visível ao redor da janela
            self.scanner_alert_window.configure(highlightbackground="orange", highlightcolor="orange", 
                                               highlightthickness=5, bd=5)
            
            # Adiciona um frame para o conteúdo
            frame = ttk.Frame(self.scanner_alert_window, padding=20)
            frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Ícone de alerta
            alert_label = ttk.Label(frame, text="⚠️", font=("Helvetica", 60))
            alert_label.pack(pady=20)
            
            # Mensagem de erro
            error_label = ttk.Label(
                frame, 
                text="ERRO DE LEITURA!\n\nProduto passou pelo sensor mas não foi lido pelo scanner!",
                font=("Helvetica", 16, "bold"),
                wraplength=500,
                justify="center"
            )
            error_label.pack(pady=20)
            
            # Botão para fechar o alerta
            close_button = ttk.Button(
                frame, 
                text="Entendi, verificar scanner", 
                command=self.scanner_alert_window.destroy,
                style="Accent.TButton" 
            )
            close_button.pack(pady=20)
            
            # Som de alerta
            self.bell()
            
            # Inicializa variáveis para controle do piscar
            self.scanner_alert_window.blink_state = True
            self.scanner_alert_window.blink_job = None
            
            # Inicia o efeito de piscar
            self._blink_window_border(self.scanner_alert_window, "orange")
            
            # Configura para parar o piscar quando a janela for fechada
            self.scanner_alert_window.protocol("WM_DELETE_WINDOW", 
                                              lambda: self._stop_blinking_and_close(self.scanner_alert_window))
            
        except Exception as e:
            logging.error(f"Erro ao exibir alerta do scanner: {e}")
    
    def _blink_window_border(self, window, color):
        """
        Faz a borda da janela piscar alternando entre visível e invisível.
        
        Args:
            window: A janela de alerta
            color: A cor da borda quando visível
        """
        if not window.winfo_exists():
            return
        
        if window.blink_state:
            # Borda visível com cor de alerta
            window.configure(highlightbackground=color, highlightcolor=color, highlightthickness=2)
        else:
            # Borda invisível (usa a mesma cor do fundo para "esconder" a borda)
            window.configure(highlightbackground=window.cget("bg"), highlightcolor=window.cget("bg"), 
                             highlightthickness=2)
        
        # Alterna o estado
        window.blink_state = not window.blink_state
        
        # Agenda a próxima alternância
        window.blink_job = window.after(500, self._blink_window_border, window, color)
    
    def _stop_blinking_and_close(self, window):
        """
        Para o efeito de piscar e fecha a janela.
        
        Args:
            window: A janela de alerta
        """
        if hasattr(window, 'blink_job') and window.blink_job:
            window.after_cancel(window.blink_job)
        window.destroy()

# ---------------------------------------------------------------------------
# Bloco Principal
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import threading
    from tkinter import ttk
    from tkinter.scrolledtext import ScrolledText

    # Cria uma janela splash sem barra de título
    splash = tk.Tk()
    splash.overrideredirect(True)
    
    # Define dimensões da janela splash
    splash_width = 800
    splash_height = 400

    # Calcula a posição para centralizar a janela na tela
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width - splash_width) // 2
    y = (screen_height - splash_height) // 2

    # Define a geometria da splash centralizada
    splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")

    # Aplica o tema na splash screen
    splash.tk.call("source", resource_path("azure.tcl"))
    config = load_config()
    current_theme = config.get("theme", "light")
    splash.tk.call("set_theme", current_theme)
    
    # Configura os estilos do tema
    style = ttk.Style(splash)
    style.configure("TLabel", font=("Helvetica", 10))
    style.configure("Header.TLabel", font=("Helvetica", 12, "bold"))
    style.configure("TButton", font=("Helvetica", 10))
    style.configure("TProgressbar", background="#007fff")
    
    # Permite fechar a splash pressionando a tecla ESC
    splash.bind("<Escape>", lambda event: splash.destroy())

    # Frame principal da splash com o estilo do tema
    splash_frame = ttk.Frame(splash, padding=20)
    splash_frame.pack(expand=True, fill="both")

    # Mensagem de carregamento com estilo Header
    splash_label = ttk.Label(
        splash_frame, 
        text="Carregando, por favor aguarde...", 
        style="Header.TLabel"
    )
    splash_label.pack(pady=(0, 10))

    # Barra de progresso com o estilo do tema
    progress = ttk.Progressbar(
        splash_frame, 
        mode="indeterminate", 
        style="TProgressbar"
    )
    progress.pack(pady=10, fill="x")
    progress.start(10)

    # ScrolledText para logs com fonte consistente
    splash_log_text = ScrolledText(
        splash_frame, 
        height=8, 
        state="disabled", 
        wrap="word",
        font=("Helvetica", 10)
    )
    splash_log_text.pack(fill="both", expand=True, pady=(10, 0))

    # Botão de fechar com estilo do tema
    close_button = ttk.Button(
        splash_frame, 
        text="Fechar", 
        command=splash.destroy,
        style="TButton"
    )
    close_button.pack(pady=5)

    # Configura o handler dos logs para a splash screen
    splash_handler = TextHandler(splash_log_text)
    splash_handler.setLevel(logging.INFO)
    splash_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(splash_handler)

    def load_label_manager():
        """
        Instancia o LabelManager (pré-carregando a imagem padrão).
        """
        config = load_config()
        serial_port = config.get("serial_port", "COM12")
        scanner_port = config.get("scanner_port", "COM6")
        lm = LabelManager(serial_port=serial_port, scanner_port=scanner_port)
        return lm

    def finish_loading(label_manager_instance):
        # Remove o handler da splash para evitar logs duplicados na interface principal
        logging.getLogger().removeHandler(splash_handler)
        splash.destroy()
        app = LabelManagerGUI(label_manager=label_manager_instance)
        app.mainloop()

    def worker():
        lm = load_label_manager()
        splash.after(0, finish_loading, lm)

    # Inicia o thread de carregamento
    threading.Thread(target=worker, daemon=True).start()
    
    # Inicia o loop principal da splash screen
    splash.mainloop()