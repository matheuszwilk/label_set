<!DOCTYPE html>
<html>

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>test</title>
  <link rel="stylesheet" href="https://stackedit.io/style.css" />
</head>

<body class="stackedit">
  <div class="stackedit__html"><h1 id="rpa-automation-suite">RPA Automation Suite</h1>
<h2 id="📌-introdução">📌 Introdução</h2>
<p>A <strong>RPA Automation Suite</strong> é uma ferramenta completa para criação de automação de processos robotizados (<strong>RPA</strong>). Com ela, é possível interagir com:</p>
<ul>
<li><strong>Páginas Web</strong>: Automatize tarefas repetitivas em sites.</li>
<li><strong>Elementos Visuais na Tela</strong>: Capture e interaja com elementos gráficos usando OCR.</li>
<li><strong>Aplicativos Windows</strong>: Controle programas e janelas do sistema.</li>
</ul>
<h2 id="📋-requisitos">📋 Requisitos</h2>
<p>Antes de iniciar, certifique-se de ter os seguintes requisitos instalados:</p>
<h3 id="🖥️-software-necessário">🖥️ Software Necessário</h3>
<ul>
<li><strong>Python</strong> 3.6+</li>
<li><strong>Drivers de Navegadores</strong>:
<ul>
<li>Edge: <code>msedgedriver.exe</code></li>
<li>Chrome: <code>chromedriver.exe</code></li>
<li>Firefox: <code>geckodriver.exe</code></li>
<li>Internet Explorer (Opcional): <code>IEDriverServer.exe</code></li>
</ul>
</li>
<li><strong>Bibliotecas Python</strong>:
<ul>
<li><code>BotCity</code></li>
<li><code>Selenium</code></li>
<li><code>PIL</code></li>
<li><code>pyautogui</code></li>
<li><code>keyboard</code></li>
<li><code>tkinter</code></li>
</ul>
</li>
<li><strong>OCR</strong>:
<ul>
<li><strong>Tesseract OCR</strong> para reconhecimento de texto em imagens</li>
</ul>
</li>
</ul>
<h2 id="🚀-instalação">🚀 Instalação</h2>
<ol>
<li>Instale o Python e as bibliotecas necessárias:<pre class=" language-sh"><code class="prism  language-sh">pip install -r requirements.txt
</code></pre>
</li>
<li>Instale o <strong>Tesseract OCR</strong> e configure o caminho corretamente.</li>
<li>Baixe os drivers dos navegadores compatíveis e configure no sistema.</li>
</ol>
<h2 id="🌐-web-automation">🌐 Web Automation</h2>
<h3 id="funcionalidades">Funcionalidades</h3>
<p>✅ Captura elementos HTML em páginas web<br>
✅ Suporte para frames e iframes<br>
✅ Identifica propriedades (ID, classe, XPath, etc.)<br>
✅ Monitora mudanças de URL automaticamente</p>
<h3 id="tipos-de-interação">Tipos de Interação</h3>
<ul>
<li><strong>Click</strong>: Clique em botões e links.</li>
<li><strong>Input</strong>: Inserção de texto em formulários.</li>
<li><strong>Copy</strong>: Extração de texto de elementos.</li>
<li><strong>OCR</strong>: Extração de texto de imagens.</li>
</ul>
<h3 id="como-usar">Como Usar</h3>
<ol>
<li>Inicie a ferramenta e selecione <strong>“Web Automation”</strong>.</li>
<li>Digite a URL e escolha o navegador.</li>
<li>Clique em <strong>“Start Capture”</strong>.</li>
<li>Posicione o mouse sobre o elemento e pressione <code>HOME</code>.</li>
<li>Configure o nome e a interação desejada.</li>
<li>Gere o código com <strong>“Generate BotCity Code”</strong>.</li>
</ol>
<h2 id="👁️-vision-automation">👁️ Vision Automation</h2>
<h3 id="funcionalidades-1">Funcionalidades</h3>
<p>✅ Captura regiões da tela independente da aplicação<br>
✅ Reconhece texto e imagens na tela<br>
✅ Suporta múltiplos monitores</p>
<h3 id="como-usar-1">Como Usar</h3>
<ol>
<li>Selecione a aba <strong>“Vision Automation”</strong>.</li>
<li>Clique em <strong>“Select Screen Area”</strong>.</li>
<li>Selecione a região da tela a ser capturada.</li>
<li>Configure o nome, tipo e opções.</li>
<li>Gere o código com <strong>“Generate Vision Code”</strong>.</li>
</ol>
<h2 id="🪟-windows-element-inspector">🪟 Windows Element Inspector</h2>
<h3 id="funcionalidades-2">Funcionalidades</h3>
<p>✅ Destaca elementos da UI do Windows<br>
✅ Captura informações de controles nativos<br>
✅ Gera código para automação de aplicativos Windows</p>
<h3 id="como-usar-2">Como Usar</h3>
<ol>
<li>Execute o <strong>Windows Element Inspector</strong>.</li>
<li>Passe o mouse sobre o elemento desejado.</li>
<li>Pressione <code>HOME</code> para capturar.</li>
<li>Selecione o tipo de ação (click, input, etc.).</li>
<li>Copie o código gerado.</li>
<li>Pressione <code>ESC</code> para sair.</li>
</ol>
<h2 id="⚙️-configurações">⚙️ Configurações</h2>
<ul>
<li><strong>Drivers de Navegadores</strong>: Configure os caminhos corretamente.</li>
<li><strong>OCR</strong>: Defina a pasta do <strong>Tesseract OCR</strong>.</li>
<li><strong>Imagens</strong>: Configure a pasta para salvar screenshots.</li>
</ul>
<h2 id="📝-exemplo-de-código">📝 Exemplo de Código</h2>
<p><img src="https://github.com/user-attachments/assets/72278dd4-1791-419a-8479-cb6cb8cf1955" alt="image"></p>
<p><img src="https://github.com/user-attachments/assets/2176cc13-6225-47c9-aa95-b1cb72d8e917" alt="image"></p>
<pre class=" language-python"><code class="prism  language-python"><span class="token keyword">from</span> botcity<span class="token punctuation">.</span>web <span class="token keyword">import</span> By<span class="token punctuation">,</span> WebBot
<span class="token keyword">import</span> time
<span class="token keyword">import</span> os
<span class="token keyword">import</span> pytesseract
<span class="token keyword">from</span> PIL <span class="token keyword">import</span> Image
pytesseract<span class="token punctuation">.</span>pytesseract<span class="token punctuation">.</span>tesseract_cmd <span class="token operator">=</span> r<span class="token string">"C:\Program Files\Tesseract-OCR\tesseract.exe"</span>

<span class="token keyword">class</span> <span class="token class-name">PracticetestautomationFunctions</span><span class="token punctuation">:</span>
    <span class="token keyword">def</span> <span class="token function">__init__</span><span class="token punctuation">(</span>self<span class="token punctuation">,</span> webbot<span class="token punctuation">)</span><span class="token punctuation">:</span>
        self<span class="token punctuation">.</span>webbot <span class="token operator">=</span> webbot
        self<span class="token punctuation">.</span>max_attempts <span class="token operator">=</span> <span class="token number">3</span>
        <span class="token comment"># Variáveis para armazenar textos extraídos</span>
        self<span class="token punctuation">.</span><span class="token builtin">vars</span> <span class="token operator">=</span> <span class="token punctuation">{</span><span class="token punctuation">}</span>
        <span class="token comment"># Armazenar os handles das janelas/abas</span>
        self<span class="token punctuation">.</span>window_handles <span class="token operator">=</span> <span class="token punctuation">{</span><span class="token punctuation">}</span>
        <span class="token comment"># Pasta para salvar screenshots temporários</span>
        self<span class="token punctuation">.</span>screenshots_folder <span class="token operator">=</span> <span class="token string">"C:/Users/matheus/Documents/test"</span>

    <span class="token keyword">def</span> <span class="token function">start_navigation</span><span class="token punctuation">(</span>self<span class="token punctuation">)</span><span class="token punctuation">:</span>
        <span class="token triple-quoted-string string">"""Inicia a navegação e configura as janelas iniciais."""</span>
        self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>browse<span class="token punctuation">(</span><span class="token string">"https://practicetestautomation.com/practice-test-login/"</span><span class="token punctuation">)</span>
        <span class="token comment"># Armazenar o handle da janela principal</span>
        main_handle <span class="token operator">=</span> self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>driver<span class="token punctuation">.</span>current_window_handle
        self<span class="token punctuation">.</span>window_handles<span class="token punctuation">[</span><span class="token string">'main'</span><span class="token punctuation">]</span> <span class="token operator">=</span> main_handle
        <span class="token comment"># Aguardar carregamento da página</span>
        self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>wait<span class="token punctuation">(</span><span class="token number">2000</span><span class="token punctuation">)</span>

    <span class="token keyword">def</span> <span class="token function">create_or_activate_window</span><span class="token punctuation">(</span>self<span class="token punctuation">,</span> window_key<span class="token punctuation">,</span> url<span class="token punctuation">)</span><span class="token punctuation">:</span>
        <span class="token triple-quoted-string string">"""Cria uma nova janela ou ativa uma existente."""</span>
        <span class="token keyword">if</span> window_key <span class="token keyword">in</span> self<span class="token punctuation">.</span>window_handles<span class="token punctuation">:</span>
            <span class="token comment"># Ativar janela existente</span>
            <span class="token keyword">try</span><span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Ativando janela: {window_key}"</span><span class="token punctuation">)</span>
                self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>driver<span class="token punctuation">.</span>switch_to<span class="token punctuation">.</span>window<span class="token punctuation">(</span>self<span class="token punctuation">.</span>window_handles<span class="token punctuation">[</span>window_key<span class="token punctuation">]</span><span class="token punctuation">)</span>
                <span class="token keyword">return</span> <span class="token boolean">True</span>
            <span class="token keyword">except</span> Exception <span class="token keyword">as</span> e<span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Erro ao ativar janela: {str(e)}"</span><span class="token punctuation">)</span>
                <span class="token comment"># Janela pode ter sido fechada, remover do dicionário</span>
                <span class="token keyword">del</span> self<span class="token punctuation">.</span>window_handles<span class="token punctuation">[</span>window_key<span class="token punctuation">]</span>
        
        <span class="token comment"># Criar nova janela</span>
        <span class="token keyword">try</span><span class="token punctuation">:</span>
            <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Criando nova janela: {window_key} com URL: {url}"</span><span class="token punctuation">)</span>
            <span class="token comment"># Abrir nova aba usando JavaScript</span>
            self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>execute_javascript<span class="token punctuation">(</span><span class="token string">"window.open()"</span><span class="token punctuation">)</span>
            <span class="token comment"># Obter todas as janelas</span>
            handles <span class="token operator">=</span> self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>driver<span class="token punctuation">.</span>window_handles
            <span class="token comment"># A nova janela é a última na lista</span>
            new_handle <span class="token operator">=</span> handles<span class="token punctuation">[</span><span class="token operator">-</span><span class="token number">1</span><span class="token punctuation">]</span>
            <span class="token comment"># Alternar para a nova janela</span>
            self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>driver<span class="token punctuation">.</span>switch_to<span class="token punctuation">.</span>window<span class="token punctuation">(</span>new_handle<span class="token punctuation">)</span>
            <span class="token comment"># Navegar para a URL desejada</span>
            self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>browse<span class="token punctuation">(</span>url<span class="token punctuation">)</span>
            <span class="token comment"># Armazenar o handle da nova janela</span>
            self<span class="token punctuation">.</span>window_handles<span class="token punctuation">[</span>window_key<span class="token punctuation">]</span> <span class="token operator">=</span> new_handle
            <span class="token comment"># Aguardar carregamento</span>
            self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>wait<span class="token punctuation">(</span><span class="token number">2000</span><span class="token punctuation">)</span>
            <span class="token keyword">return</span> <span class="token boolean">True</span>
        <span class="token keyword">except</span> Exception <span class="token keyword">as</span> e<span class="token punctuation">:</span>
            <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Erro ao criar nova janela: {str(e)}"</span><span class="token punctuation">)</span>
            <span class="token keyword">return</span> <span class="token boolean">False</span>

    <span class="token keyword">def</span> <span class="token function">ocr</span><span class="token punctuation">(</span>self<span class="token punctuation">)</span><span class="token punctuation">:</span>
        <span class="token triple-quoted-string string">"""Extrai texto do elemento ocr usando OCR."""</span>
        attempts <span class="token operator">=</span> <span class="token number">0</span>
        <span class="token keyword">while</span> attempts <span class="token operator">&lt;</span> self<span class="token punctuation">.</span>max_attempts<span class="token punctuation">:</span>
            <span class="token comment"># Lista de estratégias para encontrar o elemento</span>
            strategies <span class="token operator">=</span> <span class="token punctuation">[</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">'//*[@id="site-title"]/a[1]/img[1]'</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>XPATH<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"xpath"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">"//'img'"</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>XPATH<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"tag-fallback"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
            <span class="token punctuation">]</span>
            <span class="token comment"># Tenta cada estratégia</span>
            <span class="token keyword">for</span> strategy <span class="token keyword">in</span> strategies<span class="token punctuation">:</span>
                <span class="token keyword">try</span><span class="token punctuation">:</span>
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Tentando encontrar elemento por {strategy['desc']}..."</span><span class="token punctuation">)</span>
                    element <span class="token operator">=</span> self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>find_element<span class="token punctuation">(</span>strategy<span class="token punctuation">[</span><span class="token string">"selector"</span><span class="token punctuation">]</span><span class="token punctuation">,</span> strategy<span class="token punctuation">[</span><span class="token string">"by"</span><span class="token punctuation">]</span><span class="token punctuation">)</span>
                    <span class="token comment"># Capturar screenshot do elemento</span>
                    screenshot_path <span class="token operator">=</span> os<span class="token punctuation">.</span>path<span class="token punctuation">.</span>join<span class="token punctuation">(</span>self<span class="token punctuation">.</span>screenshots_folder<span class="token punctuation">,</span> f<span class="token string">'temp_ocr_screenshot.png'</span><span class="token punctuation">)</span>
                    element<span class="token punctuation">.</span>screenshot<span class="token punctuation">(</span>screenshot_path<span class="token punctuation">)</span>
                    <span class="token comment"># Executar OCR no screenshot</span>
                    extracted_text <span class="token operator">=</span> pytesseract<span class="token punctuation">.</span>image_to_string<span class="token punctuation">(</span>Image<span class="token punctuation">.</span><span class="token builtin">open</span><span class="token punctuation">(</span>screenshot_path<span class="token punctuation">)</span><span class="token punctuation">)</span><span class="token punctuation">.</span>strip<span class="token punctuation">(</span><span class="token punctuation">)</span>
                    self<span class="token punctuation">.</span><span class="token builtin">vars</span><span class="token punctuation">[</span><span class="token string">"ocr"</span><span class="token punctuation">]</span> <span class="token operator">=</span> extracted_text
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Texto extraído com OCR: '{extracted_text}', salvo na variável ocr"</span><span class="token punctuation">)</span>
                    <span class="token comment"># Remover arquivo temporário</span>
                    <span class="token keyword">if</span> os<span class="token punctuation">.</span>path<span class="token punctuation">.</span>exists<span class="token punctuation">(</span>screenshot_path<span class="token punctuation">)</span><span class="token punctuation">:</span>
                        os<span class="token punctuation">.</span>remove<span class="token punctuation">(</span>screenshot_path<span class="token punctuation">)</span>
                    <span class="token keyword">return</span> <span class="token boolean">True</span>
                <span class="token keyword">except</span> Exception <span class="token keyword">as</span> e<span class="token punctuation">:</span>
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Falha na estratégia {strategy['desc']}: {str(e)}"</span><span class="token punctuation">)</span>
                    <span class="token keyword">continue</span>  <span class="token comment"># Tentar próxima estratégia</span>

            <span class="token comment"># Se chegou aqui, nenhuma estratégia funcionou nesta tentativa</span>
            attempts <span class="token operator">+=</span> <span class="token number">1</span>
            <span class="token keyword">if</span> attempts <span class="token operator">&lt;</span> self<span class="token punctuation">.</span>max_attempts<span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Tentativa falhou. Tentando novamente após aguardar..."</span><span class="token punctuation">)</span>
                time<span class="token punctuation">.</span>sleep<span class="token punctuation">(</span><span class="token number">1</span><span class="token punctuation">)</span>  <span class="token comment"># Aguardar 1 segundo antes de tentar novamente</span>
            <span class="token keyword">else</span><span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Todas as tentativas falharam para o elemento."</span><span class="token punctuation">)</span>
                <span class="token keyword">return</span> <span class="token boolean">False</span>

    <span class="token keyword">def</span> <span class="token function">test</span><span class="token punctuation">(</span>self<span class="token punctuation">)</span><span class="token punctuation">:</span>
        <span class="token triple-quoted-string string">"""Insere texto no elemento test."""</span>
        attempts <span class="token operator">=</span> <span class="token number">0</span>
        <span class="token keyword">while</span> attempts <span class="token operator">&lt;</span> self<span class="token punctuation">.</span>max_attempts<span class="token punctuation">:</span>
            <span class="token comment"># Lista de estratégias para encontrar o elemento</span>
            strategies <span class="token operator">=</span> <span class="token punctuation">[</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">"username"</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>ID<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"id"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">"username"</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>NAME<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"name"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">'//*[@id="username"]'</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>XPATH<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"xpath"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">"input#username"</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>CSS_SELECTOR<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"css"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
                <span class="token punctuation">{</span><span class="token string">"selector"</span><span class="token punctuation">:</span> <span class="token string">"//'input'"</span><span class="token punctuation">,</span> <span class="token string">"by"</span><span class="token punctuation">:</span> By<span class="token punctuation">.</span>XPATH<span class="token punctuation">,</span> <span class="token string">"desc"</span><span class="token punctuation">:</span> <span class="token string">"tag-fallback"</span><span class="token punctuation">}</span><span class="token punctuation">,</span>
            <span class="token punctuation">]</span>
            <span class="token comment"># Tenta cada estratégia</span>
            <span class="token keyword">for</span> strategy <span class="token keyword">in</span> strategies<span class="token punctuation">:</span>
                <span class="token keyword">try</span><span class="token punctuation">:</span>
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Tentando encontrar elemento por {strategy['desc']}..."</span><span class="token punctuation">)</span>
                    element <span class="token operator">=</span> self<span class="token punctuation">.</span>webbot<span class="token punctuation">.</span>find_element<span class="token punctuation">(</span>strategy<span class="token punctuation">[</span><span class="token string">"selector"</span><span class="token punctuation">]</span><span class="token punctuation">,</span> strategy<span class="token punctuation">[</span><span class="token string">"by"</span><span class="token punctuation">]</span><span class="token punctuation">)</span>
                    element<span class="token punctuation">.</span>clear<span class="token punctuation">(</span><span class="token punctuation">)</span>
                    <span class="token comment"># Verificar se a variável OCR existe antes de tentar usá-la</span>
                    <span class="token keyword">if</span> <span class="token string">"ocr"</span> <span class="token keyword">in</span> self<span class="token punctuation">.</span><span class="token builtin">vars</span><span class="token punctuation">:</span>
                        <span class="token comment"># Usar o valor extraído diretamente</span>
                        extracted_text <span class="token operator">=</span> self<span class="token punctuation">.</span><span class="token builtin">vars</span><span class="token punctuation">[</span><span class="token string">"ocr"</span><span class="token punctuation">]</span>
                        <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Usando texto extraído por OCR: '{extracted_text}'"</span><span class="token punctuation">)</span>
                        element<span class="token punctuation">.</span>send_keys<span class="token punctuation">(</span>extracted_text<span class="token punctuation">)</span>
                    <span class="token keyword">else</span><span class="token punctuation">:</span>
                        <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"AVISO: Variável OCR não encontrada."</span><span class="token punctuation">)</span>
                        <span class="token comment"># Fallback para input vazio</span>
                        element<span class="token punctuation">.</span>send_keys<span class="token punctuation">(</span><span class="token string">""</span><span class="token punctuation">)</span>
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Texto inserido com sucesso em ({strategy['desc']})"</span><span class="token punctuation">)</span>
                    <span class="token keyword">return</span> <span class="token boolean">True</span>
                <span class="token keyword">except</span> Exception <span class="token keyword">as</span> e<span class="token punctuation">:</span>
                    <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Falha na estratégia {strategy['desc']}: {str(e)}"</span><span class="token punctuation">)</span>
                    <span class="token keyword">continue</span>  <span class="token comment"># Tentar próxima estratégia</span>

            <span class="token comment"># Se chegou aqui, nenhuma estratégia funcionou nesta tentativa</span>
            attempts <span class="token operator">+=</span> <span class="token number">1</span>
            <span class="token keyword">if</span> attempts <span class="token operator">&lt;</span> self<span class="token punctuation">.</span>max_attempts<span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Tentativa falhou. Tentando novamente após aguardar..."</span><span class="token punctuation">)</span>
                time<span class="token punctuation">.</span>sleep<span class="token punctuation">(</span><span class="token number">1</span><span class="token punctuation">)</span>  <span class="token comment"># Aguardar 1 segundo antes de tentar novamente</span>
            <span class="token keyword">else</span><span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Todas as tentativas falharam para o elemento."</span><span class="token punctuation">)</span>
                <span class="token keyword">return</span> <span class="token boolean">False</span>

    <span class="token keyword">def</span> <span class="token function">run</span><span class="token punctuation">(</span>self<span class="token punctuation">)</span><span class="token punctuation">:</span>
        <span class="token triple-quoted-string string">"""Executa todas as interações em sequência."""</span>
        <span class="token keyword">try</span><span class="token punctuation">:</span>
            <span class="token comment"># Iniciar navegação</span>
            self<span class="token punctuation">.</span>start_navigation<span class="token punctuation">(</span><span class="token punctuation">)</span>

            <span class="token comment"># Interagir</span>
            <span class="token keyword">if</span> <span class="token operator">not</span> self<span class="token punctuation">.</span>ocr<span class="token punctuation">(</span><span class="token punctuation">)</span><span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Falha ao interagir com elemento. Interrompendo sequência."</span><span class="token punctuation">)</span>
                <span class="token keyword">return</span> <span class="token boolean">False</span>
            <span class="token comment"># Aguardar um pouco após a interação</span>
            time<span class="token punctuation">.</span>sleep<span class="token punctuation">(</span><span class="token number">0.5</span><span class="token punctuation">)</span>

            <span class="token comment"># Interagir</span>
            <span class="token keyword">if</span> <span class="token operator">not</span> self<span class="token punctuation">.</span>test<span class="token punctuation">(</span><span class="token punctuation">)</span><span class="token punctuation">:</span>
                <span class="token keyword">print</span><span class="token punctuation">(</span><span class="token string">"Falha ao interagir com elemento. Interrompendo sequência."</span><span class="token punctuation">)</span>
                <span class="token keyword">return</span> <span class="token boolean">False</span>
            <span class="token comment"># Aguardar um pouco após a interação</span>
            time<span class="token punctuation">.</span>sleep<span class="token punctuation">(</span><span class="token number">0.5</span><span class="token punctuation">)</span>

            <span class="token keyword">return</span> <span class="token boolean">True</span>
        <span class="token keyword">except</span> Exception <span class="token keyword">as</span> e<span class="token punctuation">:</span>
            <span class="token keyword">print</span><span class="token punctuation">(</span>f<span class="token string">"Erro durante a execução: {str(e)}"</span><span class="token punctuation">)</span>
            <span class="token keyword">return</span> <span class="token boolean">False</span>
</code></pre>
<h2 id="🛠️-solução-de-problemas">🛠️ Solução de Problemas</h2>
<h3 id="web-automation">Web Automation</h3>
<p>❌ <strong>Navegador não inicia</strong>: Verifique a compatibilidade do driver.<br>
❌ <strong>Elementos não capturados</strong>: Verifique frames, iframes ou elementos dinâmicos.<br>
❌ <strong>Erro no código</strong>: Recapture os elementos se o site mudou.</p>
<h3 id="vision-automation">Vision Automation</h3>
<p>❌ <strong>Elementos não encontrados</strong>: Ajuste a precisão (<code>confidence</code>).<br>
❌ <strong>OCR impreciso</strong>: Expanda a região capturada e verifique a instalação do <strong>Tesseract</strong>.</p>
<h3 id="windows-automation">Windows Automation</h3>
<p>❌ <strong>Elementos não destacados</strong>: Execute como <strong>administrador</strong>.<br>
❌ <strong>Elementos não reconhecidos</strong>: Utilize identificadores mais específicos.</p>
<h2 id="📚-recursos-adicionais">📚 Recursos Adicionais</h2>
<ul>
<li>📖 <strong>Documentação do BotCity</strong>: <a href="https://documentation.botcity.dev/">Clique aqui</a></li>
<li>🖥️ <strong>Tesseract OCR</strong>: <a href="https://github.com/tesseract-ocr/tesseract">Repositório Oficial</a></li>
</ul>
<hr>
<p>A <strong>RPA Automation Suite</strong> oferece ferramentas intuitivas para automação de processos, permitindo que usuários de todos os níveis criem soluções robustas sem necessidade de programação avançada! 🚀</p>
</div>
</body>

</html>
