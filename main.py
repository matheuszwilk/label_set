import os
import json
import csv
import re
import logging
import time
from datetime import datetime
from typing import Any, Dict, Tuple, Set
import serial
import requests
from label_convert import process_zpl
from modbusclient import write_modbus_register
import threading
from queue import Queue

class ExcludeDynamicWorkOrderLogFilter(logging.Filter):
    """
    Esse filtro exclui logs que contenham informações dinâmicas referentes a registros do WorkOrder.
    Se a mensagem contiver 'Registro' e 'WorkOrder:' (padrões fixos), ela será filtrada.
    """
    def filter(self, record):
        message = record.getMessage()
        if 'Registro' in message and 'WorkOrder:' in message:
            return False
        return True

# Configuração básica do logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("app.log", mode="a")
file_handler.addFilter(ExcludeDynamicWorkOrderLogFilter())
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso, seja ele executado como script
    ou a partir da aplicação congelada pelo PyInstaller.
    """
    import sys
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def configure_session_with_retries():
    session = requests.Session()
    return session


class LabelManager:
    # Imagem padrão (ZPL) para pré-carga na impressora.
    STANDARD_IMAGE_ZPL = """~DG13006430,3286,31,\r\n0000"""
    
    def __init__(self,
             serial_port: str = None,
             scanner_port: str = None,
             scanner_port2: str = None,  # Nova porta para o segundo scanner
             baud_rate: int = 9600,
             scanner_baud_rate: int = 9600,
             scanner_baud_rate2: int = 9600,  # Baud rate para o segundo scanner
             csv_file: str = None,
             org_code: str = 'NW7',
             api_serial_url: str = "http://150.150.251.243:3000/api/prod/serialnumberinfo/get",
             api_workorder_url: str = "http://150.150.251.243:3000/api/prod/labelworkorder/get") -> None:
    
        # Inicializa os locks antes de qualquer operação
        self.lock_file = threading.Lock()
        self.lock_csv = threading.Lock()
        self.lock_printed_serials = threading.Lock()
        # Carrega dados de configuração a partir do arquivo config.json
        config_path = resource_path("config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
            except Exception as ex:
                logging.error(f"Erro ao carregar config.json: {ex}")
                config = {}
        else:
            config = {}

        # Leia a porta serial e a porta do scanner também do config.json
        if serial_port is None:
            serial_port = config.get("serial_port", "COM12")
        if scanner_port is None:
            scanner_port = config.get("scanner_port", "COM6")
        if scanner_port2 is None:
            scanner_port2 = config.get("scanner_port2", "COM7")  # Valor padrão para a segunda porta

        # Leia os baud rates do config.json, definindo 9600 como valor padrão
        baud_rate = config.get("baud_rate", baud_rate)
        scanner_baud_rate = config.get("scanner_baud_rate", scanner_baud_rate)
        scanner_baud_rate2 = config.get("scanner_baud_rate2", scanner_baud_rate2)  # Baud rate para o segundo scanner

        # Carregando configurações do Modbus do config.json
        modbus_host = config.get("modbus_host", "127.0.0.1")
        modbus_port = config.get("modbus_port", 502)
        modbus_address = config.get("modbus_address", 0)
        modbus_address_to_monitor = config.get("modbus_address_to_monitor", 1)
        modbus_address_to_write = config.get("modbus_address_to_write", 2)
        modbus_address_read_confirmation = config.get("modbus_address_read_confirmation", 3)

        # Caso não exista caminho CSV informado, use um arquivo CSV padrão
        if csv_file is None:
            csv_file = "impressoes.csv"

        self.theme = config.get("theme", "light")
        # Aqui lemos o zpl_scale e outras configurações
        self.zpl_scale = config.get("zpl_scale", 2)
        self.novo_darkness = config.get("novo_darkness", 10)
        self.desired_move_x = config.get("desired_move_x", 36)
        self.desired_move_y = config.get("desired_move_y", 0)

        self.label_type_for_workorder = config.get("label_type_for_workorder")

        # Atribuindo finalmente para nosso objeto
        self.serial_port = serial_port
        self.scanner_port = scanner_port
        self.scanner_port2 = scanner_port2  # Atribuição da segunda porta de scanner
        self.baud_rate = baud_rate
        self.scanner_baud_rate = scanner_baud_rate
        self.scanner_baud_rate2 = scanner_baud_rate2  # Atribuição do baud rate do segundo scanner
        self.modbus_host = modbus_host
        self.modbus_port = modbus_port
        self.modbus_address = modbus_address
        self.modbus_address_to_monitor = modbus_address_to_monitor
        self.modbus_address_to_write = modbus_address_to_write
        self.modbus_address_read_confirmation = modbus_address_read_confirmation
        self.csv_file = resource_path(csv_file)
        self.org_code = org_code
        self.api_serial_url = api_serial_url
        self.api_workorder_url = api_workorder_url
        self.session = configure_session_with_retries()

        # Caches em memória
        self.workorder_cache: Dict[str, Any] = {}
        self.workorder_count: Dict[str, int] = {}
        self.printed_serials: Set[str] = set()
        self.api1_cache: Dict[str, Tuple[str, str]] = {}
        self.images_printed: Set[str] = set()

        # Caminhos para arquivos de cache
        self.api1_cache_file = resource_path("api1_cache.json")
        self.workorder_cache_file = resource_path("workorder_cache.json")
        self.printed_serials_file = resource_path("printed_serials.json")

        # Pré-carrega do dia as workorders na API de WO e grava no workorder_cache.json
        self.preload_workorder_cache_from_daily_api()

        # Carrega caches (se existirem)
        self._load_api1_cache()
        self._load_workorder_cache()
        self._load_printed_serials()

        # Pré-carrega imagem padrão na impressora
        self._preload_standard_image()

        # Inicializa fila de impressão e locks para acesso thread-safe
        self.print_queue = Queue()
        self.lock_file = threading.Lock()
        self.lock_csv = threading.Lock()
        self.lock_printed_serials = threading.Lock()
        self._start_print_worker()

    def _start_print_worker(self) -> None:
        """Inicia a thread que fica responsável por processar os jobs de impressão."""
        self.print_worker = threading.Thread(target=self._print_worker, daemon=True)
        self.print_worker.start()

    def _print_worker(self) -> None:
        """
        Worker de impressão: fica em loop aguardando jobs na fila.
        Cada job deve conter (no mínimo) o comando ZPL, dados do registro e informações do serial.
        Ao enviar o comando para a impressora, o worker aguarda a confirmação e registra os dados.
        """
        while True:
            job = self.print_queue.get()
            if job is None:
                break
            try:
                if not self.is_printer_ready():
                    logging.warning("A impressora não está pronta para impressão. Re-enfileirando o job.")
                    self.print_queue.put(job)
                    time.sleep(1)
                    continue
                logging.info("Enviando comando ZPL para impressão (job enfileirado).")
                with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as printer:
                    printer.write(job["zpl"].encode())
                    printer.flush()
                time.sleep(0.5)  # Aguarda brevemente para assegurar o envio completo
                if self._check_printing_status():
                    logging.info("Impressão confirmada para serial: %s", job["serial_number"])
                    serial_no = job["registro"].get("SerialNo", "")
                    with self.lock_csv:
                        self.save_to_csv(job["serial_number"],
                                         job["workorder_code_api1"],
                                         job["model_suffix_api1"],
                                         serial_no)
                    with self.lock_printed_serials:
                        self.printed_serials.add(job["serial_number"])
                        self._append_printed_serial(job["serial_number"],
                                                    job["model_suffix_api1"],
                                                    serial_no)
                else:
                    logging.warning("A impressão não foi confirmada para serial: %s", job["serial_number"])
            except Exception as e:
                logging.error("Erro no worker de impressão: %s", e)
            finally:
                self.print_queue.task_done()

    def preload_workorder_cache_from_daily_api(self) -> None:
        """
        Consulta a API de WO para obter as WorkOrderCode do dia atual e, para cada uma,
        consulta a API de workorder para obter os dados completos, gravando-os em workorder_cache.json.
        """
        logging.info("Carregando WorkOrders do dia atual da API de WO...")
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            url = "http://150.150.251.243:3000/api/prod/wo/get"
            params = {
                "parameters.orgCode": self.org_code,
                "parameters.fromScheduleDate": current_date,
                "parameters.toScheduleDate": current_date
            }
            response = self.session.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                logging.error("Formato inesperado dos dados da API de WO.")
                return

            filtered = [
                record for record in data
                if record.get("LineCode") == "AA1" and record.get("StatusTypeDesc") == "Released"
            ]
            work_order_codes = [
                record.get("WorkOrderCode") for record in filtered if record.get("WorkOrderCode")
            ]
            logging.info("WorkOrderCodes encontrados: %s", work_order_codes)

            cached_workorder_codes = set()
            if os.path.isfile(self.workorder_cache_file):
                try:
                    with open(self.workorder_cache_file, mode='r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                        if isinstance(cached_data, list):
                            for entry in cached_data:
                                workorder = entry.get("workorder")
                                if workorder:
                                    cached_workorder_codes.add(workorder)
                except Exception as ex:
                    logging.error("Erro ao ler o arquivo %s: %s", self.workorder_cache_file, ex)

            if set(work_order_codes).issubset(cached_workorder_codes) and len(cached_workorder_codes) > 0:
                logging.info("Arquivo workorder_cache.json já possui todas as work orders necessárias. Pulando pré-carregamento.")
                return

            for workorder_code in work_order_codes:
                if workorder_code in self.workorder_cache:
                    logging.info("WorkOrder %s já possui dados no cache, pulando.", workorder_code)
                    continue

                params_label = {
                    "parameters.orgCode": self.org_code,
                    "parameters.workOrderCode": workorder_code,
                    "parameters.labelType": self.label_type_for_workorder
                }
                workorder_data = self._get_json(self.api_workorder_url, params_label)
                if workorder_data is None:
                    logging.warning("Nenhum dado retornado para WorkOrderCode: %s", workorder_code)
                else:
                    self.workorder_cache[workorder_code] = workorder_data
                    if isinstance(workorder_data, list):
                        self.workorder_count[workorder_code] = len(workorder_data)
                    self._append_to_json_file(self.workorder_cache_file, {
                        "workorder": workorder_code,
                        "data": workorder_data
                    })
                    logging.info("WorkOrder %s carregada com sucesso.", workorder_code)
                
                time.sleep(1)  # Delay para evitar sobrecarga na API...
        except Exception as ex:
            logging.error("Erro ao carregar WorkOrders da API: %s", ex)

    def _preload_standard_image(self) -> None:
        """
        Pré-carrega a imagem padrão na impressora para agilizar impressões futuras.
        """
        logging.info("Pré-carregando a imagem padrão no cache da impressora...")
        try:
            self.print_zpl(self.STANDARD_IMAGE_ZPL)
            logging.info("Imagem padrão pré-carregada com sucesso.")
        except Exception as ex:
            logging.error(f"Erro ao pré-carregar a imagem padrão: {ex}")

    def _load_api1_cache(self) -> None:
        if os.path.isfile(self.api1_cache_file):
            try:
                with open(self.api1_cache_file, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            workorder = entry.get("workorder")
                            workorder_code = entry.get("WorkOrderCode", "")
                            model_suffix = entry.get("ModelSuffix", "")
                            if workorder:
                                self.api1_cache[workorder] = (workorder_code, model_suffix)
                logging.info("Cache API1 carregado com sucesso.")
            except Exception as ex:
                logging.error(f"Erro ao carregar cache API1: {ex}")

    def _load_workorder_cache(self) -> None:
        if os.path.isfile(self.workorder_cache_file):
            try:
                with open(self.workorder_cache_file, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            workorder = entry.get("workorder")
                            workorder_data = entry.get("data")
                            if workorder and workorder_data:
                                self.workorder_cache[workorder] = workorder_data
                                if isinstance(workorder_data, list):
                                    self.workorder_count[workorder] = len(workorder_data)
                                else:
                                    self.workorder_count[workorder] = 1
                logging.info("Cache de workorders carregado com sucesso.")
            except Exception as ex:
                logging.error(f"Erro ao carregar cache de workorders: {ex}")

    def _load_printed_serials(self) -> None:
        if os.path.isfile(self.printed_serials_file):
            try:
                with open(self.printed_serials_file, mode='r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for record in data:
                            if record.get("printed", False):
                                serial = record.get("serial")
                                if serial:
                                    self.printed_serials.add(serial)
                logging.info("Seriais impressos carregados com sucesso.")
            except Exception as ex:
                logging.error(f"Erro ao carregar os seriais impressos: {ex}")

    def _remove_images_from_data(self, data: Any) -> Any:
        """
        Remove a chave 'Images' ou 'images' dos dados.
        """
        if isinstance(data, list):
            for record in data:
                if isinstance(record, dict):
                    record.pop("Images", None)
                    record.pop("images", None)
        elif isinstance(data, dict):
            data.pop("Images", None)
            data.pop("images", None)
        return data

    def _append_to_json_file(self, file_path: str, data: dict) -> None:
        """
        Acrescenta uma nova entrada no arquivo JSON especificado, garantindo acesso thread-safe.
        """
        try:
            with self.lock_file:
                if file_path == self.workorder_cache_file and "data" in data:
                    data["data"] = self._remove_images_from_data(data["data"])
                if os.path.isfile(file_path):
                    with open(file_path, mode='r', encoding='utf-8') as f:
                        try:
                            existing_data = json.load(f)
                            if not isinstance(existing_data, list):
                                existing_data = []
                        except json.JSONDecodeError:
                            existing_data = []
                else:
                    existing_data = []
                if file_path == self.api1_cache_file:
                    for record in existing_data:
                        if record.get("workorder") == data.get("workorder"):
                            logging.info(f"Registro com workorder '{data.get('workorder')}' já existe em {file_path}.")
                            return
                existing_data.append(data)
                with open(file_path, mode='w', encoding='utf-8') as f:
                    json.dump(existing_data, f, indent=4)
        except Exception as ex:
            logging.error(f"Erro ao escrever no arquivo {file_path}: {ex}")

    def _append_printed_serial(self, serial_number: str, model_suffix: str, serial_no: str) -> None:
        """
        Adiciona o serial impresso ao arquivo printed_serials.json, de forma thread-safe.
        """
        try:
            with self.lock_file:
                if os.path.isfile(self.printed_serials_file):
                    with open(self.printed_serials_file, mode='r', encoding='utf-8') as f:
                        try:
                            records = json.load(f)
                            if not isinstance(records, list):
                                records = []
                        except json.JSONDecodeError:
                            records = []
                else:
                    records = []
                if not any(record.get("serial") == serial_number for record in records):
                    record = {
                        "serial": serial_number,
                        "printed": True,
                        "print_timestamp": datetime.now().isoformat(),
                        "ModelSuffix": model_suffix,
                        "SerialNo": serial_no
                    }
                    records.append(record)
                    with open(self.printed_serials_file, mode='w', encoding='utf-8') as f:
                        json.dump(records, f, indent=4)
                    logging.info(f"Serial {serial_number} registrada como impressa.")
        except Exception as ex:
            logging.error(f"Erro ao atualizar o arquivo de seriais impressos: {ex}")

    def consulta_api(self, serial_number: str) -> Tuple[str, str]:
        """
        Consulta a API de serial number e, se houver comando ZPL, envia-o para impressão.
        Retorna (WorkOrderCode, ModelSuffix).
        """
        params = {
            "parameters.serialNumber": serial_number,
            "parameters.labelType": "WIP"
        }
        data = self._get_json(self.api_serial_url, params)
        if data is None:
            return "", ""
        logging.info(f"Resposta da API Serial Number ({serial_number}): {data}")
        if isinstance(data, list) and data:
            item = data[0]
        elif isinstance(data, dict):
            item = data
        else:
            item = {}
        workorder_code = item.get("WorkOrderCode", "")
        model_suffix = item.get("ModelSuffix", "")
        zpl_code = item.get("ZPL", "")
        if zpl_code:
            logging.info("Imprimindo etiqueta da primeira API...")
            self.print_zpl(zpl_code)
        return workorder_code, model_suffix

    def _get_json(self, url: str, params: dict, max_attempts: int = 5, delay: int = 5) -> Any:
        """
        Executa um GET na URL e retorna o JSON da resposta, re-tentando em caso de erro ou timeout.
        """
        attempt = 0
        while attempt < max_attempts:
            try:
                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.ReadTimeout as e:
                attempt += 1
                logging.warning(
                    f"Timeout na requisição a {url}. Tentativa {attempt}/{max_attempts}. Aguardando {delay} segundos..."
                )
                time.sleep(delay)
            except Exception as ex:
                attempt += 1
                logging.error(
                    f"Erro na requisição a {url}: {ex}. Tentativa {attempt}/{max_attempts}. Aguardando {delay} segundos..."
                )
                time.sleep(delay)
        logging.error(f"Falha ao carregar dados da API {url} após {max_attempts} tentativas.")
        return None

    def is_printer_ready(self) -> bool:
        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as printer:
                printer.reset_input_buffer()
                logging.info("Verificando status da impressora antes de enviar a impressão...")
                printer.write(b"~HS")
                time.sleep(0.2)
                
                response_lines = []
                for _ in range(3):
                    line = printer.readline()
                    if line:
                        response_lines.append(line)
                if len(response_lines) < 2:
                    logging.error("Resposta insuficiente da impressora para verificação de status.")
                    return False
                decoded_line1 = response_lines[0].decode('ascii', errors='replace')
                if decoded_line1.startswith('\x02'):
                    decoded_line1 = decoded_line1[1:]
                if '\x03' in decoded_line1:
                    decoded_line1 = decoded_line1.split('\x03')[0]
                decoded_line1 = decoded_line1.strip()
                fields1 = decoded_line1.split(',')
                if len(fields1) < 3:
                    logging.error("Formato inesperado na resposta de status (linha 1)!")
                    return False
                paper_flag = fields1[1] if len(fields1) > 1 else "0"
                pause_flag = fields1[2] if len(fields1) > 2 else "0"
                paper_status = "Papel OK" if paper_flag != "1" else "Falta de Papel"
                pause_status = "Pause (OFF)" if pause_flag != "1" else "Pause (ON)"
                decoded_line2 = response_lines[1].decode('ascii', errors='replace')
                if decoded_line2.startswith('\x02'):
                    decoded_line2 = decoded_line2[1:]
                if '\x03' in decoded_line2:
                    decoded_line2 = decoded_line2.split('\x03')[0]
                decoded_line2 = decoded_line2.strip()
                fields2 = decoded_line2.split(',')
                if len(fields2) < 4:
                    logging.error("Formato inesperado na resposta de status (linha 2)!")
                    return False
                ribbon_flag = fields2[3] if len(fields2) > 3 else "0"
                ribbon_status = "Ribbon OK" if ribbon_flag != "1" else "Ribbon OUT"
                logging.info("Status da impressora - Papel: %s, Pausa: %s, Ribbon: %s", 
                            paper_status, pause_status, ribbon_status)
                printer_ready = (paper_status == "Papel OK" and
                                pause_status == "Pause (OFF)" and
                                ribbon_status == "Ribbon OK")
                if printer_ready:
                    write_modbus_register('OK')
                else:
                    write_modbus_register('NG')
                return printer_ready
        except Exception as ex:
            logging.error("Erro ao verificar status da impressora: %s", ex)
            return False

    def print_zpl(self, zpl_code: str) -> None:
        if not self.is_printer_ready():
            logging.warning("A impressora não está no estado correto para impressão. Impressão cancelada.")
            return
        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as printer:
                printer.write(zpl_code.encode())
            logging.info("Etiqueta enviada para impressão com sucesso.")
        except PermissionError as pe:
            logging.warning("Ignorando erro de permissão ao enviar ZPL: %s", pe)
        except Exception as ex:
            logging.info("Tentando acessar a porta serial... %s", ex)

    def send_test_print(self) -> None:
        """
        Envia uma impressão de teste utilizando uma string de ZPL pré-definida.
        """
        test_zpl = """^XA
                    ^PON
                    ^MD1^FS
                    ^PRD^FS
                    ^LH78,18^FS
                    ^CWM,E:MYRIADAS.FNT^FS
                    ^FO180,3160^A0N,60,60^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,760^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,852^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,952^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1046^A0N,50,44^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1134^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1340^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1818^A0N,50,32^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1880^A0N,50,32^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1972^A0N,50,48^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,2066^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1198^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1580^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1640^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1726^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO686,1196^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO520,1196^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO856,928^A0B,60,60^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO856,134^A0B,60,60^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,1612^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,1418^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,1276^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,1058^A0B,46,48^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,916^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,632^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,326^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1116,88^A0B,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1424^A0N,50,44^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO42,1484^A0N,50,44^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO106,1484^A0N,50,44^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO44,1258^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO734,1580^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO734,1726^A0N,50,50^FH^CT`^CC}}FD}FS}CT~}CC^
                    ^FO22,36^FR^GB810,3230,10,B,2^FS
                    ^FO32,814^FR^GB790,6,8,B,0^FS
                    ^FO32,726^FR^GB790,2,8,B,0^FS
                    ^FO32,910^FR^GB790,4,8,B,0^FS
                    ^FO32,1008^FR^GB790,4,8,B,0^FS
                    ^FO32,1104^FR^GB790,4,8,B,0^FS
                    ^FO32,1546^FR^GB790,4,8,B,0^FS
                    ^FO32,1936^FR^GB790,4,8,B,0^FS
                    ^FO32,2032^FR^GB790,4,8,B,0^FS
                    ^FO32,2126^FR^GB790,4,8,B,0^FS
                    ^FO32,1782^FR^GB790,4,8,B,0^FS
                    ^FO476,734^FR^GB2,80,8,B,0^FS
                    ^FO476,822^FR^GB2,88,8,B,0^FS
                    ^FO476,918^FR^GB2,90,8,B,0^FS
                    ^FO476,1112^FR^GB2,282,8,B,0^FS
                    ^FO476,1554^FR^GB0,228,8,B,0^FS
                    ^FO476,1790^FR^GB2,146,8,B,0^FS
                    ^FO476,1944^FR^GB2,88,8,B,0^FS
                    ^FO476,2040^FR^GB2,86,8,B,0^FS
                    ^FO32,1394^FR^GB790,4,8,B,0^FS
                    ^FO476,1016^FR^GB2,88,8,B,0^FS
                    ^FO476,1402^FR^GB2,144,8,B,0^FS
                    ^FO112,430^A0N,110,110^CT`^CC}}FD}FS}CT~}CC^
                    ^FO922,124^BY6^BCR,120,N,N,^FD^FS
                    ^FO1056,1702^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,1474^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,1300^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,1080^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,916^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,670^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1052,378^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO1056,172^A0B,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO856,1182^A0B,60,60^CT`^CC}}FD}FS}CT~}CC^
                    ^FO528,1196^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO162,568^A0N,80,80^CT`^CC}}FD}FS}CT~}CC^
                    ^FO720,760^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO642,852^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO692,950^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO712,1046^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO620,1134^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO632,1340^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO642,1818^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO642,1880^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO524,1972^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO524,2066^A0N,50,50^CT`^CC}}FD}FS}CT~}CC^
                    ^FO758,744^FR^XG13002577,2,2^FS
                    ^FO494,1484^A0N,50,32^CT`^CC}}FD}FS}CT~}CC^
                    ^FO564,1424^A0N,50,32^CT`^CC}}FD}FS}CT~}CC^
                    ^FO162,122^FR^XG13006430,2,2^FS
                    ^FO52,2352^FR^XG13008550,2,2^FS
                    ^FO864,1974^FR^XG13008590,2,2^FS
                    ^XZ
                    """
        try:
            config_path = resource_path("config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
                self.novo_darkness = config.get("novo_darkness", self.novo_darkness)
                self.desired_move_x = config.get("desired_move_x", self.desired_move_x)
                self.desired_move_y = config.get("desired_move_y", self.desired_move_y)
            from label_convert import set_darkness, set_move_x_token, set_move_y_token
            zpl_with_darkness = set_darkness(test_zpl, self.novo_darkness)
            tokens = zpl_with_darkness.split('^')
            new_tokens = []
            for token in tokens:
                if token.startswith("LH"):
                    try:
                        new_token = set_move_x_token(token, self.desired_move_x)
                        new_token = set_move_y_token(new_token, self.desired_move_y)
                    except ValueError as ve:
                        logging.error("Erro ao aplicar move_x: %s", ve)
                        new_token = token
                    new_tokens.append(new_token)
                else:
                    new_tokens.append(token)
            zpl_converted = '^'.join(new_tokens)
            logging.info("Teste de impressão utilizando: novo_darkness=%s, desired_move_x=%s",
                        self.novo_darkness, self.desired_move_x)
            with serial.Serial(self.serial_port, self.baud_rate, timeout=5) as printer:
                printer.write(zpl_converted.encode())
                printer.flush()
                time.sleep(0.5)
            logging.info("Teste de impressão enviado para a impressora com sucesso.")
        except PermissionError as pe:
            logging.warning("Ignorando erro de permissão ao enviar o Teste de Impressão: %s", pe)
        except Exception as ex:
            logging.error("Erro ao enviar impressão de teste: %s", ex)

    def save_to_csv(self, serial_number: str, workorder_code_api1: str, model_suffix_api1: str, serial_no: str) -> None:
        """
        Salva as informações da impressão em um arquivo CSV.
        """
        try:
            with open(self.csv_file, mode='a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([datetime.now().isoformat(), serial_number, workorder_code_api1, model_suffix_api1, serial_no])
            logging.info("Dados salvos em CSV com sucesso.")
        except Exception as ex:
            logging.error(f"Erro ao salvar dados em CSV: {ex}")

    @staticmethod
    def get_workorder_from_serial(serial: str) -> str:
        """
        Extrai a workorder a partir do serial (antes do hífen).
        """
        parts = serial.split('-')
        return parts[0] if parts else ""
    
    def get_total_labels(self, workorder_code: str) -> int:
        data = self.workorder_cache.get(workorder_code)
        if isinstance(data, list):
            return len(data)
        return 1

    def get_printed_count_for_workorder(self, workorder_code: str) -> int:
        return sum(1 for sn in self.printed_serials if self.get_workorder_from_serial(sn) == workorder_code)

    def get_remaining_labels(self, workorder_code: str) -> int:
        return self.get_total_labels(workorder_code) - self.get_printed_count_for_workorder(workorder_code)

    def _check_printing_status(self) -> bool:
        try:
            with serial.Serial(self.serial_port, self.baud_rate, timeout=2) as printer:
                printer.reset_input_buffer()
                logging.info("Enviando comando ~HS para verificar status da impressora.")
                printer.write(b"~HS")
                time.sleep(0.5)
                response_lines = []
                for _ in range(3):
                    line = printer.readline()
                    if line:
                        response_lines.append(line)
                if len(response_lines) < 2:
                    logging.error("Resposta insuficiente da impressora para verificação de status.")
                    return False
                decoded_line1 = response_lines[0].decode('ascii', errors='replace')
                if decoded_line1.startswith('\x02'):
                    decoded_line1 = decoded_line1[1:]
                if '\x03' in decoded_line1:
                    decoded_line1 = decoded_line1.split('\x03')[0]
                decoded_line1 = decoded_line1.strip()
                fields1 = decoded_line1.split(',')
                logging.info("Campos extraídos (Linha 1): %s", fields1)
                if len(fields1) < 5:
                    logging.error("Formato inesperado na resposta de status (String 1)!")
                    return False
                try:
                    num_formats = int(fields1[4])
                except ValueError:
                    num_formats = 0
                paper_flag = fields1[1] if len(fields1) > 1 else "0"
                pause_flag = fields1[2] if len(fields1) > 2 else "0"
                paper_status = "Papel OK" if paper_flag == "0" else "Falta de Papel"
                pause_status = "Pause (OFF)" if pause_flag == "0" else "Pause (ON)"
                decoded_line2 = response_lines[1].decode('ascii', errors='replace')
                if decoded_line2.startswith('\x02'):
                    decoded_line2 = decoded_line2[1:]
                if '\x03' in decoded_line2:
                    decoded_line2 = decoded_line2.split('\x03')[0]
                decoded_line2 = decoded_line2.strip()
                fields2 = decoded_line2.split(',')
                if len(fields2) < 8:
                    logging.error("Formato inesperado na resposta de status (String 2)!")
                    ribbon_flag = "0"
                    label_waiting = ""
                else:
                    ribbon_flag = fields2[3]
                    label_waiting = fields2[7]
                ribbon_status = "Ribbon OK" if ribbon_flag == "0" else "Ribbon OUT"
                logging.info("Status da impressora - Papel: %s, Pausa: %s, Ribbon: %s, Label Waiting: %s, Formatos no Buffer: %d",
                            paper_status, pause_status, ribbon_status, label_waiting, num_formats)
                if num_formats > 0 and paper_flag == "0" and pause_flag == "0" and ribbon_flag == "0":
                    return True
                else:
                    logging.warning("A impressão não foi confirmada: Status esperado [Papel OK, Pause (OFF), Ribbon OK] mas obtido - Papel: %s, Pausa: %s, Ribbon: %s",
                                    paper_status, pause_status, ribbon_status)
                    return False
        except Exception as e:
            logging.error(f"Erro ao consultar status da impressora: {e}")
            return False

    def consulta_workorder(self,
                           sequence_number: int,
                           serial_number: str,
                           workorder_code_api1: str,
                           model_suffix_api1: str,
                           allow_duplicate: bool = False) -> None:
        """
        Consulta a API de workorder e prepara o job para impressão.
        Em vez de enviar o ZPL diretamente, o job é enfileirado 
        para ser processado pelo worker de impressão.
        """
        workorder_code = workorder_code_api1 if workorder_code_api1 else self.get_workorder_from_serial(serial_number)
        if not workorder_code:
            logging.error("Erro ao extrair workorder do serial.")
            return
        
        if not allow_duplicate and serial_number in self.printed_serials:
            logging.warning(f"O serial {serial_number} já foi impresso anteriormente!")
            remaining = self.get_remaining_labels(workorder_code)
            logging.info(f"Total de etiquetas restantes para {workorder_code}: {remaining}")
            return

        # Use self.label_type_for_workorder read from config
        params_label = {
            "parameters.orgCode": self.org_code,
            "parameters.workOrderCode": workorder_code,
            "parameters.labelType": self.label_type_for_workorder,
        }

        if workorder_code in self.workorder_cache and self.get_total_labels(workorder_code) > 0:
            data = self.workorder_cache[workorder_code]
            logging.info(f"Usando dados do cache para workorder {workorder_code}...")
        else:
            data = self._get_json(self.api_workorder_url, params_label)
            if data is None:
                return
            self.workorder_cache[workorder_code] = data
            if isinstance(data, list):
                self.workorder_count[workorder_code] = len(data)
            logging.info(f"Dados obtidos da API para {workorder_code} e armazenados em cache.")
            logging.info(f"Total de etiquetas disponíveis: {self.get_total_labels(workorder_code)}")
            self._append_to_json_file(self.workorder_cache_file, {"workorder": workorder_code, "data": data})

        if isinstance(data, list) and len(data) >= sequence_number:
            registro = data[sequence_number - 1]
            logging.info(f"Registro {sequence_number} do WorkOrder: {registro}")
            zpl_set = registro.get("ZPL", "")
            if zpl_set:
                zpl_converted = process_zpl(
                    zpl_set,
                    scale=self.zpl_scale,
                    darkness=self.novo_darkness,
                    move_x=self.desired_move_x,
                    move_y=self.desired_move_y
                )
                logging.info("ZPL convertido para 600 DPI, enfileirando job de impressão...")
                job = {
                    "zpl": zpl_converted,
                    "registro": registro,
                    "serial_number": serial_number,
                    "workorder_code_api1": workorder_code_api1,
                    "model_suffix_api1": model_suffix_api1
                }
                self.print_queue.put(job)
            else:
                logging.warning("Código ZPL não encontrado no registro.")
        else:
            logging.warning(f"Não foi encontrado o registro {sequence_number} no WorkOrder.")

        logging.info(f"Total de etiquetas restantes para {workorder_code}: {self.get_remaining_labels(workorder_code)}")

    @staticmethod
    def get_sequence_number(serial: str) -> int:
        """
        Extrai e retorna o número sequencial presente no serial.
        Retorna 1 em caso de erro.
        """
        try:
            parts = serial.split('-')
            if len(parts) > 1:
                return int(parts[1])
        except Exception as ex:
            logging.warning(f"Falha ao extrair sequencial do serial {serial}: {ex}")
        return 1

    def validate_serial(self, serial_number: str) -> bool:
        """
        Valida se o serial está no formato esperado (ex.: 5BPR0559-00001).
        """
        pattern = r'^[A-Za-z0-9]+-\d+$'
        if re.match(pattern, serial_number):
            return True
        write_modbus_register('NG')
        logging.error("Formato de serial inválido!")
        return False

    def process_serial(self, serial_number: str, allow_duplicate: bool = False) -> None:
        """
        Processa o serial: consulta as APIs, atualiza caches e enfileira o job de impressão.
        """
        if not self.validate_serial(serial_number):
            return
            
        # Registra valor 1 no endereço 3 do Modbus para indicar que uma leitura foi realizada
        try:
            from modbusclient import write_modbus_register_address
            write_modbus_register_address(self.modbus_address_read_confirmation, 1)
            logging.info("Registro de leitura: valor 1 escrito no endereço 3 do Modbus")
        except Exception as ex:
            logging.error(f"Erro ao registrar leitura no Modbus: {ex}")
            
        if allow_duplicate:
            if serial_number in self.printed_serials:
                logging.info("Reimpressão manual solicitada para o serial: %s", serial_number)
            else:
                logging.info("Impressão solicitada para o serial: %s", serial_number)
        workorder_from_serial = self.get_workorder_from_serial(serial_number)
        sequence_number = self.get_sequence_number(serial_number)
        
        if sequence_number == 1 or workorder_from_serial not in self.api1_cache:
            logging.info("Consultando API para dados do serial...")
            workorder_code_api1, model_suffix_api1 = self.consulta_api(serial_number)
            self.api1_cache[workorder_from_serial] = (workorder_code_api1, model_suffix_api1)
            self._append_to_json_file(self.api1_cache_file, {
                "workorder": workorder_from_serial,
                "WorkOrderCode": workorder_code_api1,
                "ModelSuffix": model_suffix_api1
            })
        else:
            logging.info("WorkOrder encontrada no cache. Utilizando dados em cache para a consulta.")
            workorder_code_api1, model_suffix_api1 = self.api1_cache[workorder_from_serial]
        
        self.consulta_workorder(sequence_number, serial_number, workorder_code_api1, model_suffix_api1, allow_duplicate=allow_duplicate)

    def read_barcode_from_scanner(self) -> str:
        """
        Lê o código de barras do scanner.
        """
        try:
            config_path = resource_path("config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    new_scanner_port = config.get("scanner_port", self.scanner_port)
                    if new_scanner_port != self.scanner_port:
                        logging.info("Atualizando a porta do scanner de %s para %s...",
                                    self.scanner_port, new_scanner_port)
                        self.scanner_port = new_scanner_port
            
            with serial.Serial(self.scanner_port, self.scanner_baud_rate, timeout=0.3) as scanner:
                logging.info("Aguardando leitura do scanner na porta %s...", self.scanner_port)
                barcode = scanner.readline().decode().strip()
                logging.info("Código de barras lido: %s", barcode)
                return barcode
        except Exception as exc:
            # logging.error("Erro ao ler do scanner na porta %s: %s", self.scanner_port, exc)
            return ""
        
    def read_barcode_from_scanner2(self) -> str:
        """
        Lê o código de barras do scanner secundário.
        """
        try:
            config_path = resource_path("config.json")
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    new_scanner_port = config.get("scanner_port2", self.scanner_port2)
                    if new_scanner_port != self.scanner_port2:
                        logging.info("Atualizando a porta do scanner secundário de %s para %s...",
                                    self.scanner_port2, new_scanner_port)
                        self.scanner_port2 = new_scanner_port
            
            with serial.Serial(self.scanner_port2, self.scanner_baud_rate2, timeout=0.3) as scanner:
                logging.info("Aguardando leitura do scanner secundário na porta %s...", self.scanner_port2)
                barcode = scanner.readline().decode().strip()
                logging.info("Código de barras lido do scanner secundário: %s", barcode)
                return barcode
        except Exception as exc:
            # logging.error("Erro ao ler do scanner secundário na porta %s: %s", self.scanner_port2, exc)
            return ""

def main() -> None:
    """
    Função principal que instancia o LabelManager e inicia o loop de leitura dos scanners.
    """
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    label_manager = LabelManager()
    logging.info("Iniciando a leitura contínua dos scanners nas portas %s e %s...", 
                 label_manager.scanner_port, label_manager.scanner_port2)
    
    def scanner1_worker():
        """Thread worker para o scanner principal"""
        try:
            while True:
                serial_number = label_manager.read_barcode_from_scanner()
                if serial_number:
                    logging.info("Código de barras recebido do scanner principal: %s", serial_number)
                    label_manager.process_serial(serial_number)
        except Exception as e:
            logging.error(f"Erro no scanner principal: {e}")
    
    def scanner2_worker():
        """Thread worker para o scanner secundário"""
        try:
            while True:
                serial_number = label_manager.read_barcode_from_scanner2()
                if serial_number:
                    logging.info("Código de barras recebido do scanner secundário: %s", serial_number)
                    label_manager.process_serial(serial_number)
        except Exception as e:
            logging.error(f"Erro no scanner secundário: {e}")
    
    try:
        # Criar e iniciar as threads para os scanners
        scanner1_thread = threading.Thread(target=scanner1_worker, daemon=True)
        scanner2_thread = threading.Thread(target=scanner2_worker, daemon=True)
        
        # Iniciar o monitoramento Modbus em uma thread separada
        from modbusclient import monitor_modbus_input
        modbus_monitor_thread = threading.Thread(target=monitor_modbus_input, daemon=True)
        
        scanner1_thread.start()
        scanner2_thread.start()
        modbus_monitor_thread.start()  # Inicia o monitoramento Modbus
        
        # Aguardar indefinidamente (até Ctrl+C)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Programa encerrado via interrupção do usuário.")
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")

if __name__ == "__main__":
    main()