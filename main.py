import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import time
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import nltk
from nltk.corpus import stopwords
from fpdf import FPDF
import markdown  # Para converter Markdown em HTML
from weasyprint import HTML


# #############################################################################################################
# CONFIGURAÇÕES STREAMLIT
# #############################################################################################################

# Configurar o streamlit pra wide
st.set_page_config(layout="wide")



# #############################################################################################################
# CONFIGURAÇÕES CONEXÃO MONGO
# #############################################################################################################

# Configuração da conexão com o MongoDB
@st.cache_resource
def baixar_colecao_textos():

    string_conexao = st.secrets.senhas.string_conexao
    client = MongoClient(string_conexao)
    mongo_db = client['bibl_don_saw']
    collection = mongo_db['textos']
    return collection

collection = baixar_colecao_textos()


# #############################################################################################################
# FUNÇÕES AUXILIARES
# #############################################################################################################


# CADASTRAR -------------------------------------------------
# Função para cadastrar texto no MongoDB
def cadastrar_texto(titulo, data, texto):
    texto_markdown = texto.replace('\n', '  \n')  # Adicionar quebras de linha explícitas para Markdown
    documento = {
        'titulo': titulo,
        'data': data.strftime('%d-%m-%Y'),
        'texto': texto_markdown
    }
    result = collection.insert_one(documento)
    return result.inserted_id

# Diálogo para cadastrar novo texto
@st.dialog("Cadastrar novo texto", width="large")
def cadastrar():
    with st.form('form_cadastro'):
        titulo = st.text_input('Título:')
        data = st.date_input('Data:', datetime.today(), min_value=datetime(1990, 1, 1), format='DD/MM/YYYY')
        texto = st.text_area('Texto em formato **markdown**:')
        submit = st.form_submit_button('Salvar', icon=':material/save:')

        if submit:
            if titulo and texto:
                texto_id = cadastrar_texto(titulo, data, texto)
                st.success('Texto cadastrado com sucesso!')
                time.sleep(2)  # Pausa para feedback visual
                st.rerun()
            else:
                st.error('Por favor, preencha todos os campos antes de cadastrar.')


# EDITAR ----------------------------------------------------

# Função para editar texto no MongoDB
def editar_texto(doc_id, novo_titulo, nova_data, novo_texto):
    novo_texto_markdown = novo_texto.replace('\n', '  \n')
    collection.update_one(
        {'_id': doc_id},
        {'$set': {
            'titulo': novo_titulo,
            'data': nova_data.strftime('%d-%m-%Y'),
            'texto': novo_texto_markdown
        }}
    )

# Diálogo para editar texto
@st.dialog("Editar Texto", width="large")
def editar(doc_id):
    doc = collection.find_one({'_id': doc_id})
    if doc:
        with st.form(f'form_edicao_{doc_id}'):
            novo_titulo = st.text_input('Título', value=doc['titulo'])
            nova_data = st.date_input('Data', value=datetime.strptime(doc['data'], '%d-%m-%Y'), format='DD/MM/YYYY')
            novo_texto = st.text_area('Texto', height=400, value=doc['texto'].replace('  \n', '\n'))
            salvar = st.form_submit_button('Salvar Alterações', icon=':material/save:')

            if salvar:
                editar_texto(doc_id, novo_titulo, nova_data, novo_texto)
                st.success('Texto atualizado com sucesso!')
                time.sleep(2)
                st.rerun()


# DELETAR ---------------------------------------------------
# Função para deletar textos no MongoDB
def deletar_textos(doc_ids):
    collection.delete_many({'_id': {'$in': doc_ids}})


# Baixar o conjunto de stopwords
@st.cache_data
def baixar_stopwords():
    nltk.download('stopwords')

baixar_stopwords()


# Função para gerar a nuvem de palavras ----------------------
def gerar_nuvem_de_palavras(documentos):  # Recebe uma lista de textos
    
    textos = [doc["texto"] for doc in documentos if "texto" in doc]

    # Concatenar todos os textos da lista em uma única string
    texto_concatenado = " ".join(textos)

    # Obter a lista de stop words em português
    stop_words = set(stopwords.words('portuguese'))

    # Adicionar palavras customizadas à lista de stopwords
    palavras_personalizadas = {"se", "têm", "irá", "além disso", "além", "maior", "menor", "menos", "mais", "todo", "sobre", "apenas", "poderia", "poderiam", "outro", "outra", "outros", "outras", "vez", "parte"}
    stop_words.update(palavras_personalizadas)

    if texto_concatenado.strip():  # Verifica se há texto para gerar a nuvem

        # Lista para armazenar palavras filtradas
        palavras_filtradas = []

        # Iterar sobre cada palavra do texto concatenado
        for palavra in texto_concatenado.split():
            # Remover caracteres que não sejam letras ou números
            palavra_limpa = re.sub(r'[^a-zA-Z0-9á-úÁ-Ú]', '', palavra)

            # Verificar se a palavra não está vazia e não é uma stopword
            if palavra_limpa and palavra_limpa.lower() not in stop_words:
                palavras_filtradas.append(palavra_limpa)

        # Concatenar as palavras filtradas de volta em uma string
        texto_filtrado = " ".join(palavras_filtradas)

        # Gerar a nuvem de palavras
        wordcloud = WordCloud(
            width=2000, height=500,
            background_color='white',
            max_words=200,
            contour_color='steelblue',
            # collocations=True,
        ).generate(texto_filtrado)

        # Renderizar a nuvem como imagem
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("Nenhum texto encontrado.")


# Função para buscar documentos com base nos anos selecionados -----------------
def buscar_documentos_por_ano(anos_selecionados):

    documentos_filtrados = []

    if anos_selecionados:

        for texto in textos:
            data_str = texto['data']  # A data vem como uma string no formato "dd-mm-yyyy"

            # Converter a string da data para um objeto datetime
            data = datetime.strptime(data_str, "%d-%m-%Y")  # Usando o formato correto
            ano_documento = data.year  # Extrai o ano

            # Verificar se o ano está na lista de anos selecionados
            if str(ano_documento) in anos_selecionados:
                documentos_filtrados.append(texto)

    else:
        # query = {}  # Sem filtro, pega todos os documentos

        # Consultar no banco de dados
        # documentos = collection.find(query, {"_id": 0})  # Retorna todos os campos, exceto "_id"
        documentos_filtrados = textos

    return documentos_filtrados


# Função para buscar documentos com base nos termos selecionados -----------------
def buscar_documentos_por_palavra(termo, docs):

    # verificar se há um termo
    termo = termo.lower()  # Remover espaços extras e normalizar para lowercase

    resultado = []

    # Percorrer os documentos para aplicar o filtro de termo-chave
    for documento in docs:

        # Garantir que o campo "titulo" e "texto" existam e estejam em lowercase
        titulo = documento.get("titulo", "").lower()
        texto = documento.get("texto", "").lower()

        # Verificar se a termo aparece no título ou no texto
        if termo in titulo or termo in texto:
            resultado.append(documento)

    return resultado


def criar_pdf(titulo, data, texto_markdown):
    # Converter o Markdown em HTML
    texto_html = markdown.markdown(texto_markdown)

    # Construir o HTML completo para o PDF
    html_completo = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>{titulo}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 20px;
            }}
            h1, h2, h3 {{
                color: #333;
            }}
            p, li {{
                font-size: 14px;
                line-height: 1.6;
            }}
            .titulo {{
                text-align: center;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }}
            .data {{
                font-size: 12px;
                text-align: right;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="titulo">{titulo}</div>
        <div class="data">Data: {data}</div>
        {texto_html}  <!-- Insere o conteúdo convertido do Markdown -->
    </body>
    </html>
    """

    # Gerar o PDF usando WeasyPrint
    pdf = HTML(string=html_completo).write_pdf()

    # Retornar o PDF como bytes
    return pdf



# Função do diálogo para ver um texto completo e baixar como PDF
@st.dialog("Texto completo", width="large")
def ver_texto(documento):

    # Criar o PDF
    pdf_bytes = criar_pdf(documento['titulo'], documento['data'], documento['texto'])

    # Botão para baixar o PDF
    st.download_button(
        label="Baixar PDF",
        data=pdf_bytes,
        file_name=f"{documento['titulo'].replace(' ', '_')}.pdf",
        mime="application/pdf",
        icon=":material/file_download:"
    )

    st.header(documento['titulo'])
    st.write(f'**{documento["data"]}**')
  
    # Mostrar o texto
    st.markdown(documento['texto'])


# Função para agrupar documentos por ano e ordenar os textos
def agrupar_e_ordenar_documentos(documentos):
    agrupados = {}
    for doc in documentos:
        # Converter a data para um objeto datetime
        data_datetime = datetime.strptime(doc['data'], "%d-%m-%Y")  # Exemplo de formato "dd-mm-yyyy"
        doc['data_datetime'] = data_datetime  # Adicionar a data datetime ao documento

        # Extrair o ano do objeto datetime
        ano = data_datetime.year

        # Agrupar por ano
        if ano not in agrupados:
            agrupados[ano] = []
        agrupados[ano].append(doc)

    # Ordenar os textos em cada ano (mais recentes primeiro)
    for ano in agrupados:
        agrupados[ano].sort(key=lambda x: x['data_datetime'], reverse=True)

    return agrupados

# Função para exibir os documentos no Streamlit
def exibir_documentos_ordenados(documentos):
    # Agrupar e ordenar os documentos
    documentos_por_ano = agrupar_e_ordenar_documentos(documentos)

    # Ordenar os anos em ordem decrescente
    anos_ordenados = sorted(documentos_por_ano.keys(), reverse=True)

    # Exibir os blocos de documentos no Streamlit
    for ano in anos_ordenados:
        st.markdown(f"<h2 style='color: #277f8e '>{ano}</h2>", unsafe_allow_html=True)
        for doc in documentos_por_ano[ano]:
            st.subheader(doc['titulo'])
            # st.write(f"**{doc['data']}**")
            st.markdown(f"<p style='font-size:20px; '>{doc['data']}</p>", unsafe_allow_html=True)

            # PREVIEW
            st.markdown(doc['texto'][:800] + '...')


            st.button(
                "Ver texto completo",
                key=f"ver_texto_{doc['titulo']}",
                on_click=ver_texto,
                args=(doc,),
                icon=":material/open_in_new:",
                type="primary"
            )

            st.markdown("---")  # Linha de separação entre documentos
            


# ###################################################################################
# TRATAMENTO DE TEXTO
# ###################################################################################

textos_raw = list(collection.find())

# Criar um conjunto de caracteres suportados
supported_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?@#$%^&*ºª()_+-=~[]}{|;:'\"<>/? áéíóúàèìòùâêîôûãõäëïöüñçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÄËÏÖÜÑÇ \n")

# Função para substituir caracteres não suportados por ' '
def replace_unsupported_chars(text):
    return ''.join(char if char in supported_characters else ' ' for char in text)

# Processar cada texto na estrutura de textos_raw
textos = []

for item in textos_raw:
    processed_item = {
        "_id": item["_id"],
        "titulo": replace_unsupported_chars(item["titulo"]) if "titulo" in item else " ",
        "data": item["data"],  # Data não precisa de processamento
        "texto": replace_unsupported_chars(item["texto"]) if "texto" in item else " "
    }
    textos.append(processed_item)


# ###################################################################################
# INTERFACE
# ###################################################################################

# Iniciando a variável pra guardar a busca do usuário, caso ela não exista
if 'busca_usuario' not in st.session_state:
    st.session_state.busca_usuario = None


# Barra lateral ---------------------------------

with st.sidebar:

    st.write("")
    st.write("")
    st.write("")
    st.write("")

    st.subheader('Filtros')

    st.write("")

    # Campo de texto para a busca
    busca_usuario = st.text_input("Digite uma palavra:", placeholder="Digite uma palavra", label_visibility="collapsed")

    # Capta a busca se a pessoa apertar enter
    st.session_state.busca_usuario = busca_usuario

    # Capta a busca se a pessoa apertar o botão
    if st.button("Pesquisar", type="primary", use_container_width=True, icon=":material/search:"):
        # Buscar documentos (com ou sem palavra-chave)
        if busca_usuario.strip():  # Garantir que não seja vazio
            st.session_state['busca_usuario'] = busca_usuario
        else:
            st.session_state['busca_usuario'] = None


    # Pílulas dos ANOS
    # Obter todas as datas dos documentos no banco
    datas_raw = list(collection.find({}, {"_id": 0, "data": 1}))  # Buscar apenas as datas

    # Converter datas para datetime
    datas = [datetime.strptime(doc['data'], '%d-%m-%Y') for doc in datas_raw]

    # Extrair os anos (ignorando o mês)
    anos = sorted(set(d.year for d in datas))

    # Criar labels como "Ano" para os intervalos
    labels = [str(ano) for ano in anos]

    st.write('')

    # Usar o st.pills para permitir a seleção de múltiplos anos
    anos_selecionados = st.pills(
        "Anos:",
        options=labels,
        selection_mode="multi",  # Permitir múltiplas seleções
        default=None,
    )

    # Pular linhas
    for _ in range(10):
        st.write('')


    with st.popover("Adm", icon=":material/settings:", use_container_width=True):

        # Espaço reservado para a entrada da senha
        container_senha_titulo = st.empty()

        # Entrada de senha permanece visível até ser validada
        senha = container_senha_titulo.text_input("Senha", type="password")

        if senha:  # Verifica se algo foi digitado
            if senha == st.secrets.senhas.senha:
                # Substitui o conteúdo do container apenas ao acertar a senha
                container_senha_titulo.empty()  # Remove o text_input
                st.subheader("Gerenciar textos")  # Mostra o gerenciador de textos

                # Tabs para as operações
                aba1, aba2, aba3 = st.tabs([
                    ":material/add: Cadastrar",
                    ":material/edit: Editar",
                    ":material/delete: Deletar"
                ])

                with aba1:
                    # Botão para diálogo de "Novo Texto"
                    if st.button("Novo Texto", use_container_width=True, icon=":material/add:"):
                        cadastrar()

                with aba2:
                    # Área para "Editar Texto"
                    texto_selecionado = st.selectbox(
                        'Selecione um texto para editar:',
                        options=[None] + textos,
                        format_func=lambda x: x['titulo'] if x else ""
                    )
                    if st.button('Editar Texto', icon=':material/edit:', use_container_width=True):
                        if texto_selecionado:
                            editar(texto_selecionado['_id'])
                        else:
                            st.warning('Nenhum texto selecionado para editar.')

                with aba3:
                    # Área para "Deletar Texto"
                    ids_para_deletar = st.multiselect(
                        'Selecione o(s) texto(s) para deletar:',
                        options=[str(doc['_id']) for doc in textos],
                        format_func=lambda x: next(doc['titulo'] for doc in textos if str(doc['_id']) == x),
                        placeholder=""
                    )
                    if st.button('Deletar Selecionados', icon=':material/delete:', use_container_width=True):
                        if ids_para_deletar:
                            doc_ids = [doc['_id'] for doc in textos if str(doc['_id']) in ids_para_deletar]
                            deletar_textos(doc_ids)
                            st.success(f'{len(doc_ids)} texto(s) deletado(s) com sucesso!')
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.warning('Nenhum texto selecionado para deletar.')
            else:
                # Mensagem de erro para senha incorreta
                st.error("Senha incorreta")



# INTERFACE PRINCIPAL ---------------------------


# TÍTULO
st.title("Biblioteca")

st.write("")

# Aplicando filtros

# Buscar os textos que correspondem aos anos selecionados
documentos_filtrados = buscar_documentos_por_ano(anos_selecionados)

# Buscar os textos que correspondem ao termo de busca
if st.session_state.busca_usuario:
    documentos_filtrados_final = buscar_documentos_por_palavra(st.session_state.busca_usuario, documentos_filtrados)
else:
    documentos_filtrados_final = documentos_filtrados


#  Nuvem de palavras -------------------------------

# Gerar a nuvem de palavras com os textos filtrados
gerar_nuvem_de_palavras(documentos_filtrados_final)


# Lista de documentos -------------------------------

# Contagem de textos
if len(documentos_filtrados_final) == 1:
    st.subheader(f'**{len(documentos_filtrados_final)} texto**')
else:
    st.subheader(f'**{len(documentos_filtrados_final)} textos**')


# Exibir os textos filtrados
exibir_documentos_ordenados(documentos_filtrados_final)

