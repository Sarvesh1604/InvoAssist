import sys
import yaml
import json
import streamlit as st
from pathlib import Path

sys.path.insert(0, f"{Path().absolute().parent.as_posix()}/utils")
from llm_calls import TriggerLLMCalls


st.set_page_config(page_title='InvoAssist', page_icon='', layout='centered')
st.title("InvoAssist")

def display_chat():
    if 'messages' in st.session_state:
        for dict_ in st.session_state.messages:
            if dict_['role'] == 'user':
                user_input = st.chat_message('user')
                user_input.write(dict_['content'])
            else:
                assistant_output = st.chat_message('assistant')
                assistant_output.write(dict_['content'])

if __name__=='__main__':

    if 'config' not in st.session_state:
        with open(Path().absolute().parent/'utils'/'config.yaml') as f:
            st.session_state.config = yaml.safe_load(f)

    if 'trigger_llm' not in st.session_state:
        st.session_state.trigger_llm = TriggerLLMCalls(st.session_state)
        st.session_state.trigger_llm.set_system_context()

    user_prompt = st.chat_input('ask questions')

    if user_prompt:
        st.session_state.trigger_llm.get_chat_response(user_prompt)
    
    sidebar = st.sidebar
    uploaded_image = sidebar.file_uploader(
                        label= 'upload your invoice',
                        type= ['jpg', 'png'],
                        accept_multiple_files= False,
                        key= 'file_uploader'
                    )
    if uploaded_image is not None and 'image' not in st.session_state:
        status = sidebar.empty()
        status.text('')

        with sidebar:
            with st.spinner('Analyzing Image'):
                st.session_state.image = uploaded_image.getvalue()
                st.session_state.trigger_llm.get_invoice_data()
            status.text('Invoice Analyzed Successfully!')

    if 'invoice_data_json' in st.session_state:
        with sidebar:
            st.download_button(
                label="Download Invoice Data",
                data=json.dumps(st.session_state.invoice_data_json),
                file_name="invoice_data.json",
                mime='application/json',
                icon=":material/download:",
            )
    display_chat()