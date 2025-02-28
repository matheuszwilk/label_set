import re

# Comandos cujos parâmetros numéricos (coordenadas, tamanhos, larguras, etc.) deverão ser escalados.
# Adicionamos "BQN" para que o fator de magnificação do QR Code seja escalado.
SCALE_COMMANDS = (
    "LH",   # Label Home (posição, onde aplicaremos o ajuste de move_x/move_y ou escalonamento)
    "FO",   # Field Origin
    "A0N",  # Fonte normal (pode ser A0B também)
    "A0B",
    "GB",   # Graphic Box
    "BY",   # Barcode Field Default – parâmetros: módulo, ratio e altura
    "BCR",  # Barcode 128 (exemplo)
    "BQN",  # QR Code
    "XG"    # Recall Graphic (imagem armazenada) – tratado separadamente
)

def scale_numbers_in_token(token, scale=2):
    """
    Para um token (parte de um comando ZPL) multiplica todos os números (inteiros ou decimais)
    pelo fator de escala dado.
    """
    def repl(match):
        num_str = match.group(0)
        if '.' in num_str:
            num = float(num_str) * scale
            return str(int(num)) if num.is_integer() else str(num)
        else:
            return str(int(num_str) * scale)
    return re.sub(r'\d+(?:\.\d+)?', repl, token)

def scale_xg_token(token, scale=2):
    """
    Essa função é específica para os tokens do comando ^XG.
    
    O formato esperado é: "XG<filename>,<xscale>,<yscale>".
    O parâmetro <filename> (que pode conter apenas dígitos) não deve ser alterado,
    e os parâmetros de escala devem ser fixados para "2" e "2".
    """
    code = "XG"
    rest = token[len(code):]  # Exemplo: "13006430,1,1"
    if not rest:
        return token
    parts = rest.split(',')
    # Se o token não tiver ao menos o nome do arquivo, escala X e escala Y, retorna inalterado.
    if len(parts) < 3:
        return token
    # Mantém o nome do arquivo e força os parâmetros de escala para "2" e "2".
    new_parts = [parts[0], "2", "2"]
    # Caso haja outros parâmetros, estes são mantidos inalterados.
    if len(parts) > 3:
        new_parts.extend(parts[3:])
    return code + ','.join(new_parts)

def set_darkness(zpl, darkness_value):
    """
    Atualiza o nível de "dark" (densidade de impressão) em todo o código ZPL.
    
    Esta função procura por todas as ocorrências do comando ^MD seguido de um valor numérico
    e substitui esse valor pelo darkness_value informado.
    Por exemplo:
       Se o ZPL contiver "^MD11" e darkness_value for 20, o comando será alterado para "^MD20".
    """
    def replacement(match):
        return match.group(1) + str(darkness_value)
    # O re.sub atualizará todas as ocorrências na string
    return re.sub(r'(\^MD)(\d+)', replacement, zpl)

def set_move_x_token(token, move_x):
    """
    Atualiza o comando de movimento horizontal (LH) sobrescrevendo a coordenada X.
    O token esperado tem o formato "LH<valor_x>,<valor_y>[...]".
    O valor move_x deve estar entre 0 e 100.
    
    Exemplo:
       Para token "LH39,9" e move_x=50, retornará "LH50,9".
    """
    if not (0 <= move_x <= 100):
        raise ValueError("move_x deve estar entre 0 e 100")
    m = re.match(r'(LH)(\d+)(.*)', token)
    if m:
        return m.group(1) + str(move_x) + m.group(3)
    return token

def set_move_y_token(token, move_y):
    """
    Atualiza o segundo parâmetro (coordenada Y) do comando ^LH.
    O token esperado tem o formato "LH<valor_x>,<valor_y>[...]".
    O valor move_y deve estar entre 0 e 100.
    
    Exemplo:
        Para token "LH39,9" e move_y=70, retornará "LH39,70".
    """
    if not (0 <= move_y <= 100):
        raise ValueError("move_y deve estar entre 0 e 100")
    # Captura LH, depois algum número (X), depois vírgula, depois algum número (Y), e o restante.
    m = re.match(r'(LH)(\d+)(,)(\d+)(.*)', token)
    if m:
        # Exemplo de grupos:
        #  group(1) -> "LH"
        #  group(2) -> "39" (valor de X)
        #  group(3) -> ","
        #  group(4) -> "9"  (valor de Y)
        #  group(5) -> ""   (resto, se houver)
        return f"{m.group(1)}{m.group(2)},{move_y}{m.group(5)}"
    return token

def process_zpl(zpl, scale=2, darkness=None, move_x=None, move_y=None):
    """
    Converte uma string contendo código ZPL (por exemplo, de 300 DPI) em um novo código
    escalado (por exemplo, para 600 DPI). Durante o processamento:
    
      - Se o parâmetro 'darkness' for fornecido, atualiza todas as ocorrências do comando ^MD
        com esse valor, alterando o nível de densidade (dark) da impressão;
      - Se o parâmetro 'move_x' for fornecido, ajusta a coordenada X no comando LH para esse valor
        (garantindo que esteja entre 0 e 100);
      - Se o parâmetro 'move_y' for fornecido, ajusta a coordenada Y no comando LH para esse valor
        (garantindo que esteja entre 0 e 100);
      - Os comandos que iniciam com "^FD" (campos de dados) não são alterados;
      - O comando ^XG é tratado de forma especial, mantendo o nome original do arquivo e
        fixando os parâmetros de escala para "2,2";
      - Os comandos ^BQN passam a ter seus valores numéricos (por exemplo "4" em BQN,,4) 
        multiplicados pelo fator de escala;
      - Os demais comandos listados em SCALE_COMMANDS terão seus valores numéricos 
        multiplicados pelo fator de escala.
    """
    # Atualiza o comando ^MD, se darkness for informado.
    if darkness is not None:
        zpl = set_darkness(zpl, darkness)
    
    tokens = zpl.split('^')
    new_tokens = []
    
    # Se a string iniciar com '^', o primeiro token será vazio.
    if tokens and tokens[0] == '':
        new_tokens.append('')
        tokens = tokens[1:]
    
    for token in tokens:
        if token.startswith("FD"):
            # Campos de dados não são alterados
            new_tokens.append(token)
        elif token.startswith("XG"):
            # Trata ^XG de maneira especial (força escala "2,2")
            new_tokens.append(scale_xg_token(token, scale))
        elif token.startswith("LH"):
            # Ajusta X e/ou Y se fornecidos
            if move_x is not None:
                token = set_move_x_token(token, move_x)
            if move_y is not None:
                token = set_move_y_token(token, move_y)
            # Se não foi fornecido move_x ou move_y, escalona normalmente
            if move_x is None and move_y is None:
                token = scale_numbers_in_token(token, scale)
            new_tokens.append(token)
        else:
            # Verifica se o token inicia com algum dos comandos de SCALE_COMMANDS
            m = re.match(r'([A-Z0-9]+)', token)
            if m:
                cmd_code = m.group(1)
                # Excluímos "XG" aqui, pois já é tratado separadamente acima.
                if any(cmd_code.startswith(prefix) for prefix in SCALE_COMMANDS if prefix != "XG"):
                    new_tokens.append(scale_numbers_in_token(token, scale))
                else:
                    new_tokens.append(token)
            else:
                new_tokens.append(token)
    
    return '^'.join(new_tokens)

if __name__ == "__main__":
    # Exemplo de código ZPL (300 DPI) com comandos ^MD, ^LH e ^XG, além de ^BQN
    zpl_code = (
        "^XA\r\n"
        "^PON\r\n"
        "^MD11^FS\r\n"
        "^PRD^FS\r\n"
        "^LH39,9^FS\r\n"
        "^CWM,E:MYRIADAS.FNT^FS\r\n"
        "^FO90,1580^A0N,30,30^FS\r\n"
        "^BQN,,4^FDMA,https://example.com^FS\r\n"
        "^XG13006430,1,1^FS\r\n"
        "^XZ"
    )

    # Configurações desejadas
    desired_darkness = 1
    desired_move_x = 50  # valor de move_x entre 0 e 100 
    desired_move_y = 20  # valor de move_y entre 0 e 100

    processed_zpl = process_zpl(
        zpl_code, 
        scale=2, 
        darkness=desired_darkness, 
        move_x=desired_move_x,
        move_y=desired_move_y
    )

    print("\nCódigo ZPL Processado com darkness, move_x, move_y e QR Code escalado:\n")
    print(processed_zpl)