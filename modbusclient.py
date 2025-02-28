from pyModbusTCP.client import ModbusClient
import logging
import os
import json

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
        tuple: (host (str), port (int), address (int))
    
    Observação:
        Essa função espera que o arquivo config.json contenha as chaves "modbus_host", "modbus_port" e "modbus_address".
    """
    config_file = resource_path("config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    host = config["modbus_host"]
    port = config["modbus_port"]
    address = config.get("modbus_address", 0)  # Caso a chave não exista, usa 0
    return host, port, address

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
    host, port, address = load_modbus_config()
    
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

if __name__ == "__main__":
    # Exemplo de uso quando o módulo é executado diretamente
    resultado = write_modbus_register('NG')  # Utilize 'NG' ou 'OK'
    if resultado:
        print("Operação concluída com sucesso.")
    else:
        print("Operação falhou.")