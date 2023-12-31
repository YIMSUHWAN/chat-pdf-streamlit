import streamlit as st
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

# pdf
import os
import tempfile
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# db
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# gpt
from langchain.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA


# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

################################# 

st.title("Chat PDF")
st.write("---")

# openai key
openai_key = st.text_input('OPEN_AI_API_KEY', type="password")
st.write("---")

# file
uploaded_file = st.file_uploader("Upload PDF",type=['pdf'])
st.write("---")

def pdf_to_document(uploaded_file):
    temp_dir = tempfile.TemporaryDirectory()
    temp_filepath = os.path.join(temp_dir.name, uploaded_file.name)
    with open(temp_filepath, "wb") as f:
        f.write(uploaded_file.getvalue())
    loader = PyPDFLoader(temp_filepath)
    pages = loader.load_and_split()
    return pages

# uploaded
if uploaded_file is not None:
    pages = pdf_to_document(uploaded_file)

    # split
    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size = 300,
        chunk_overlap  = 20,
        length_function = len,
        is_separator_regex = False,
    )
    texts = text_splitter.split_documents(pages)

    # embedding
    embeddings_model = OpenAIEmbeddings(openai_api_key=openai_key)

    # load it into Chroma
    db = Chroma.from_documents(texts, embeddings_model)

    #
    from langchain.callbacks.base import BaseCallbackHandler
    class StreamHandler(BaseCallbackHandler):
        def __init__(self, container, initial_text=""):
            self.container = container
            self.text=initial_text
        def on_llm_new_token(self, token: str, **kwargs) -> None:
            self.text+=token
            self.container.markdown(self.text)

    # question
    st.header("ask about PDF")
    question = st.text_input('question')

    if st.button('submit'):
        with st.spinner('Wait for it...'):
            chat_box = st.empty()
            stream_hander = StreamHandler(chat_box)
            llm = ChatOpenAI(model_name="gpt-3.5-turbo", 
                             temperature=0, 
                             openai_api_key=openai_key, 
                             streaming=True, 
                             callbacks=[stream_hander])
            qa_chain = RetrievalQA.from_chain_type(llm,retriever=db.as_retriever())
            qa_chain({"query": question})