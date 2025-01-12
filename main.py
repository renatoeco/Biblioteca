import streamlit as st
from pymongo import MongoClient
from datetime import datetime
import time
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
import nltk
from nltk.corpus import stopwords



# #############################################################################################################
# CONFIGURAÇÕES STREAMLIT
# #############################################################################################################

# Configurar o streamlit pra wide
st.set_page_config(layout="wide")



# #############################################################################################################
# CONFIGURAÇÕES CONEXÃO MONGO
# #############################################################################################################

# Configuração da conexão com o MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Substitua pela URI do seu MongoDB, se necessário
mongo_db = client['bibl_don_saw']
collection = mongo_db['textos']



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
        titulo = st.text_input('Título')
        data = st.date_input('Data', datetime.today(), min_value=datetime(1990, 1, 1), format='DD/MM/YYYY')
        texto = st.text_area('Texto')
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
            novo_texto = st.text_area('Texto', value=doc['texto'].replace('  \n', '\n'))
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


# Baixar o conjunto de stopwords se não tiver feito isso antes
nltk.download('stopwords')



# Função para gerar a nuvem de palavras ----------------------
def gerar_nuvem_de_palavras(documentos):  # Recebe uma lista de textos
    
    textos = [doc["texto"] for doc in documentos if "texto" in doc]

    # Concatenar todos os textos da lista em uma única string
    texto_concatenado = " ".join(textos)

    # Obter a lista de stop words em português
    stop_words = set(stopwords.words('portuguese'))

    # Adicionar palavras customizadas à lista de stopwords
    palavras_personalizadas = {"se", "têm", "irá", "além disso", "além"}
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
            width=2500, height=500,
            background_color='white',
            max_words=200,
            contour_color='steelblue',
            collocations=True
        ).generate(texto_filtrado)

        # Renderizar a nuvem como imagem
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("A lista de textos está vazia ou não contém palavras suficientes para gerar a nuvem de palavras.")



# Função para buscar documentos com base nos anos selecionados -----------------
def buscar_documentos_por_ano(anos_selecionados):
    if anos_selecionados:
        # Consultar todos os documentos, sem filtro de ano
        documentos = collection.find({}, {"_id": 0})  # Retorna todos os campos, exceto "_id"

        documentos_filtrados = []

        for doc in documentos:
            data_str = doc['data']  # A data vem como uma string no formato "dd-mm-yyyy"

            # Converter a string da data para um objeto datetime
            data = datetime.strptime(data_str, "%d-%m-%Y")  # Usando o formato correto
            ano_documento = data.year  # Extrai o ano

            # Verificar se o ano está na lista de anos selecionados
            if str(ano_documento) in anos_selecionados:
                documentos_filtrados.append(doc)

    else:
        query = {}  # Sem filtro, pega todos os documentos

        # Consultar no banco de dados
        documentos = collection.find(query, {"_id": 0})  # Retorna todos os campos, exceto "_id"
        documentos_filtrados = [doc for doc in documentos]

    return documentos_filtrados






# ###################################################################################
# INTERFACE
# ###################################################################################



# Barra lateral ---------------------------------

with st.sidebar:
    
    with st.expander("GERENCIAR TEXTOS", expanded=False, icon=":material/library_books:"):
        
        st.write('')

        st.write("**CADASTRAR**")
        # Butão para o diálogo para "Novo Texto"
        if st.button("Novo Texto",  use_container_width=True, icon=":material/add:"):
            cadastrar()

        st.write('')

        # Área para "Editar Texto"
        st.markdown("### EDITAR")
        textos = list(collection.find())
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

        st.write('')

        # Área para "Deletar Texto"
        st.markdown("### DELETAR")
        ids_para_deletar = st.multiselect(
            'Selecione o(s) texto(s) para deletar:',
            options=[str(doc['_id']) for doc in textos],
            format_func=lambda x: next(doc['titulo'] for doc in textos if str(doc['_id']) == x)
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



# Filtros ------------------------------------------------
st.subheader("Filtros")

# Obter todas as datas dos documentos no banco
datas_raw = list(collection.find({}, {"_id": 0, "data": 1}))  # Buscar apenas as datas

# Converter datas para datetime
datas = [datetime.strptime(doc['data'], '%d-%m-%Y') for doc in datas_raw]

# Extrair os anos (ignorando o mês)
anos = sorted(set(d.year for d in datas))

# Criar labels como "Ano" para os intervalos
labels = [str(ano) for ano in anos]

# Usar o st.pills para permitir a seleção de múltiplos anos
anos_selecionados = st.pills(
    "Anos:",
    options=labels,
    selection_mode="multi",  # Permitir múltiplas seleções
    default=None,
)

# Buscar os textos que correspondem aos anos selecionados
documentos_filtrados = buscar_documentos_por_ano(anos_selecionados)


#  Nuvem de palavras -------------------------------

# Gerar a nuvem de palavras com os textos filtrados
gerar_nuvem_de_palavras(documentos_filtrados)

st.divider()




# Lista de documentos -------------------------------

if len(documentos_filtrados) == 1:
    st.header(f'{len(documentos_filtrados)} texto')
else:
    st.header(f'{len(documentos_filtrados)} textos')

# Exibir os textos filtrados
for doc in documentos_filtrados:
    st.subheader(doc['titulo'])
    st.write(f"**Data: {doc['data']}**")
    st.markdown(doc['texto'])







