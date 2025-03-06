from pyModbusTCP.client import ModbusClient
import logging
import os
import json

_modbus_config = None
_last_config_time = 0

def resource_path(relative_path: str) -> str:
    """
    Retorna o caminho absoluto para um recurso, seja ele executado como script
    ou a partir da aplicação congelada pelo PyInstaller.
    """
    import sys
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_modbus_config():
    """
    Carrega a configuração do Modbus a partir do arquivo config.json.
    
    Retorna:
        tuple: (host (str), port (int), address (int), address_to_monitor (int),
                address_to_write (int), address_read_confirmation (int))
    
    Observação:
        Essa função espera que o arquivo config.json contenha as chaves relacionadas ao Modbus.
    """
    config_file = resource_path("config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    host = config["modbus_host"]
    port = config["modbus_port"]
    address = config.get("modbus_address", 0)  # Caso a chave não exista, usa 0
    
    # Novos endereços para monitoramento
    address_to_monitor = config.get("modbus_address_to_monitor", 1)  # Padrão: 1
    address_to_write = config.get("modbus_address_to_write", 2)  # Padrão: 2
    address_read_confirmation = config.get("modbus_address_read_confirmation", 3)  # Padrão: 3
    
    return host, port, address, address_to_monitor, address_to_write, address_read_confirmation

def write_modbus_register(status):
    """
    Escreve um valor de status em um registrador Modbus.

    Parâmetros:
        status (str): Deve ser 'OK' ou 'NG'.
                      'OK' atribui o valor 0 ao registrador;
                      'NG' atribui o valor 1 ao registrador.

    Retorna:
        bool: True se a operação foi bem-sucedida, False caso contrário.

    Exceções:
        ValueError: Se o status informado não for 'OK' ou 'NG'.
    """
    status = status.upper()
    if status == 'OK':
        value = 0
    elif status == 'NG':
        value = 1
    else:
        raise ValueError("O parâmetro 'status' deve ser 'OK' ou 'NG'.")
    
    logging.basicConfig(level=logging.DEBUG)
    
    # Carrega as configurações do Modbus (host, port e address) a partir do arquivo JSON
    host, port, address, _, _, _ = load_modbus_config()
    
    # Cria e configura o cliente Modbus TCP
    client = ModbusClient(host=host, port=port, unit_id=1, auto_open=True)
    
    if not client.is_open:
        if not client.open():
            logging.error("Falha ao conectar no servidor Modbus TCP")
            return False

    # Usa o endereço configurado a partir do config.json
    if not client.write_single_register(address, value):
        logging.error("Erro ao escrever no registrador!")
        client.close()
        return False
    else:
        logging.info(f"Valor {value} escrito com sucesso no endereço {address}.")
    
    client.close()
    return True

def read_modbus_register(address):
    """
    Lê o valor de um registrador Modbus.

    Parâmetros:
        address (int): Endereço do registrador a ser lido.

    Retorna:
        int: Valor lido do registrador ou None em caso de erro.
    """
    logging.basicConfig(level=logging.DEBUG)
    
    # Carrega as configurações do Modbus (host, port) a partir do arquivo JSON
    host, port, _, _, _, _ = load_modbus_config()
    
    # Cria e configura o cliente Modbus TCP
    client = ModbusClient(host=host, port=port, unit_id=1, auto_open=True)
    
    if not client.is_open:
        if not client.open():
            logging.error("Falha ao conectar no servidor Modbus TCP")
            return None

    # Tenta ler o registrador
    value = client.read_holding_registers(address, 1)
    client.close()
    
    if value is None:
        logging.error(f"Erro ao ler o registrador do endereço {address}!")
        return None
    
    logging.info(f"Valor {value[0]} lido com sucesso do endereço {address}.")
    return value[0]

def write_modbus_register_address(address, value):
    """
    Escreve um valor específico em um endereço de registrador Modbus.

    Parâmetros:
        address (int): Endereço do registrador.
        value (int): Valor a ser escrito.

    Retorna:
        bool: True se a operação foi bem-sucedida, False caso contrário.
    """
    logging.basicConfig(level=logging.DEBUG)
    
    # Carrega as configurações do Modbus (host, port) a partir do arquivo JSON
    host, port, _, _, _, _ = load_modbus_config()
    
    # Cria e configura o cliente Modbus TCP
    client = ModbusClient(host=host, port=port, unit_id=1, auto_open=True)
    
    if not client.is_open:
        if not client.open():
            logging.error("Falha ao conectar no servidor Modbus TCP")
            return False

    if not client.write_single_register(address, value):
        logging.error(f"Erro ao escrever o valor {value} no registrador {address}!")
        client.close()
        return False
    else:
        logging.info(f"Valor {value} escrito com sucesso no endereço {address}.")
    
    client.close()
    return True

def monitor_modbus_input(**kwargs):
    """
    Monitora continuamente um endereço Modbus e executa ações com base na mudança de estado.
    Registra no log apenas mudanças de estado e eventos importantes.
    
    NOVA LÓGICA:
    - Quando o endereço de monitoramento muda para valor 1: começa a verificar o endereço de confirmação
    - Se o endereço de confirmação tiver valor 1: significa que foi feita uma leitura, então escreve 0 no endereço de escrita
    - Se o endereço de monitoramento voltar para 0 e o endereço de confirmação não tiver valor 1: escreve 1 no endereço de escrita
    - Sempre que o endereço de monitoramento mudar para 0: resetar o endereço de confirmação para 0
    
    Os endereços são carregados do arquivo config.json.
    
    Parâmetros (ignorados, mantidos para compatibilidade):
        **kwargs: Quaisquer parâmetros nomeados são ignorados, pois os valores são carregados da configuração.
    """
    import time
    
    # Carrega os endereços a partir do arquivo de configuração
    _, _, _, address_to_monitor, address_to_write, address_read_confirmation = load_modbus_config()
    
    logging.info(f"Monitorando Modbus: Endereço de sensor: {address_to_monitor}, "
                 f"Endereço de escrita: {address_to_write}, "
                 f"Endereço de confirmação: {address_read_confirmation}")
    
    last_value = None  # Inicializa como None para forçar leitura inicial sem log
    first_run = True
    read_confirmed = False  # Flag para controlar se a leitura foi confirmada
    
    while True:
        try:
            # Lê o registrador do sensor (sem logar a cada leitura)
            current_value = read_modbus_register_silent(address_to_monitor)
            
            # Na primeira execução, apenas atualiza o valor sem logar
            if first_run and current_value is not None:
                last_value = current_value
                first_run = False
                continue
            
            # Se o valor mudou de 0 para 1, inicia o processo de monitoramento do endereço de confirmação
            if current_value is not None and current_value == 1 and last_value == 0:
                logging.info(f"Mudança detectada no endereço {address_to_monitor}: valor mudou para 1 (ativo)")
                
                # Reinicia a flag para nova tentativa
                read_confirmed = False
            
            # Enquanto o sensor estiver ativo (valor 1), verifica o endereço de confirmação de leitura
            if current_value is not None and current_value == 1:
                # Verifica se já houve confirmação de leitura no endereço de confirmação
                if not read_confirmed:
                    read_status = read_modbus_register_silent(address_read_confirmation)
                    if read_status == 1:
                        read_confirmed = True
                        # Se a leitura foi confirmada, escreve 0 no endereço de resultado
                        write_modbus_register_silent(address_to_write, 0)
                        logging.info(f"Leitura confirmada no endereço {address_read_confirmation}. Escrito 0 no endereço {address_to_write}.")
            
            # Se o valor mudou de 1 para 0, verifica se houve confirmação de leitura
            elif current_value is not None and current_value == 0 and last_value == 1:
                logging.info(f"Mudança detectada no endereço {address_to_monitor}: valor voltou para 0 (inativo)")
                
                # Se não houve confirmação de leitura, escreve 1 no endereço de resultado
                if not read_confirmed:
                    write_modbus_register_silent(address_to_write, 1)
                    logging.info(f"Nenhuma leitura confirmada enquanto o sensor estava ativo. Escrito 1 no endereço {address_to_write}.")
                
                # SEMPRE após o sensor desativar, reseta o endereço de confirmação de leitura para 0
                reset_result = write_modbus_register_silent(address_read_confirmation, 0)
                if reset_result:
                    logging.info(f"Resetado endereço {address_read_confirmation} para 0 após sensor desativar.")
                else:
                    logging.error(f"Falha ao resetar endereço {address_read_confirmation} para 0.")
            
            # Atualiza o último valor lido
            if current_value is not None:
                last_value = current_value
            
            # Pausa de 200ms entre leituras para não sobrecarregar o CLP
            time.sleep(0.2)
            
        except Exception as e:
            logging.error(f"Erro durante o monitoramento Modbus: {e}")
            time.sleep(1)  # Espera um pouco antes de tentar novamente

def read_modbus_register_silent(address):
    """
    Lê o valor de um registrador Modbus sem gerar logs a cada leitura.
    Retorna o valor lido ou None em caso de erro.
    """
    # Carrega as configurações do Modbus (host, port) a partir do arquivo JSON
    host, port, _, _, _, _ = load_modbus_config()
    
    try:
        # Cria e configura o cliente Modbus TCP
        client = ModbusClient(host=host, port=port, unit_id=1, auto_open=True)
        
        if not client.is_open:
            if not client.open():
                return None

        # Tenta ler o registrador
        value = client.read_holding_registers(address, 1)
        client.close()
        
        if value is None:
            return None
        
        return value[0]
    except Exception:
        return None

def write_modbus_register_silent(address, value):
    """
    Escreve um valor específico em um endereço de registrador Modbus sem logs verbosos.
    Retorna True se a operação foi bem-sucedida, False caso contrário.
    """
    # Carrega as configurações do Modbus (host, port) a partir do arquivo JSON
    host, port, _, _, _, _ = load_modbus_config()
    
    try:
        # Cria e configura o cliente Modbus TCP
        client = ModbusClient(host=host, port=port, unit_id=1, auto_open=True)
        
        if not client.is_open:
            if not client.open():
                return False

        result = client.write_single_register(address, value)
        client.close()
        return result
    except Exception:
        return False

if __name__ == "__main__":
    # Exemplo de uso quando o módulo é executado diretamente
    resultado = write_modbus_register('NG')  # Utilize 'NG' ou 'OK'
    if resultado:
        print("Operação concluída com sucesso.")
    else:
        print("Operação falhou.")