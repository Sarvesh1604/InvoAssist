import json
import yaml
from openai import OpenAI
from pydantic import Field
from json_handler import parse_json
from langchain.schema import Document
from langchain.vectorstores import FAISS
from extract_ocr_data import ExtractOCRData
from langchain.chains import ConversationChain
from langchain_core.language_models.llms import LLM
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.memory import ConversationSummaryBufferMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter

class custom_llm(LLM):
    config: dict = Field(...)
    max_tokens: int = Field(...)

    @property
    def _llm_type(self):
        return 'custom'
    
    def _call(
            self, 
            prompt, 
            stop=None
    ):
        auth_dict = self.config['authentication']
        model = self.config['llm_config']['model']
        max_tokens = self.max_tokens

        client = OpenAI(**auth_dict)

        response = client.chat.completions.create(
            model = model,
            messages = [
                {
                    'role': 'user',
                    'content': f'{prompt}'
                }
            ],
            max_tokens = max_tokens
        )

        return response.choices[0].message.content
    
class TriggerLLMCalls():
    def __init__(self, session_state):
        self.session_state = session_state
        self.max_tokens = session_state.config['llm_config']['max_tokens']
    
    def custom_llm_call(self, prompt, max_tokens, memory=None):
        llm = custom_llm.model_construct(
                config = self.session_state.config,
                max_tokens = max_tokens
            )
        if memory:
            conversation = ConversationChain(
                llm = llm,
                memory = memory
            )
        else:
            conversation = ConversationChain(
                llm = llm
            )

        return conversation.predict(input=prompt)

    def update_session_state(self, input, output):
        if 'messages' not in self.session_state:
            self.session_state.messages = [
                {'role': 'user', 'content': input},
                {'role': 'assistant', 'content': output}
            ]
        else:
            self.session_state.messages.extend([
                {'role': 'user', 'content': input},
                {'role': 'assistant', 'content': output}
            ])
        
        self.session_state.memory.save_context({'input': input}, {'output': output})

    def set_system_context(self):
        llm = custom_llm.model_construct(
                config = self.session_state.config,
                max_tokens = self.max_tokens
            )
        self.session_state.memory = ConversationSummaryBufferMemory(
                                        llm=llm,
                                        max_token_limit=50000
                                    )
        system_prompt = self.session_state.config['prompt_library']['system_prompt']
        response = self.custom_llm_call(prompt=system_prompt, max_tokens=20)

        self.session_state.memory.save_context({'input': system_prompt}, {'output': response})

    def get_chat_response(self, user_prompt):
        if 'invoice_data_str' in self.session_state:
            docs_list = [Document(page_content = self.session_state.invoice_data_str)]
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=50, chunk_overlap=5)
            docs = text_splitter.split_documents(docs_list)

            embeddings = HuggingFaceEmbeddings(
                            model = self.session_state.config['embed_config']['model'],
                            model_kwargs = self.session_state.config['embed_config']['model_kwargs'],
                            encode_kwargs = self.session_state.config['embed_config']['encode_kwargs']
                        ) 

            db = FAISS.from_documents(docs, embeddings)

            relevant_chunks = db.similarity_search_with_score(
                query = user_prompt,
                k = self.session_state.config['retrieval_config']['k']
            )

            score_threshold = self.session_state.config['retrieval_config']['score_threshold']
            relevant_chunks = [chunks for chunks, score in relevant_chunks if score <= score_threshold]

            if relevant_chunks:
                prompt = self.session_state.config['prompt_library']['user_query']['query_with_context']
                prompt = prompt.replace("{user_query}", user_prompt)
                prompt = prompt.replace("{context}", '\n'.join([chunk.page_content for chunk in relevant_chunks]))

                final_response = self.custom_llm_call(
                                    prompt=prompt,
                                    max_tokens=self.max_tokens,
                                    memory=self.session_state.memory
                                )
            else:
                prompt = self.session_state.config['prompt_library']['user_query']['general_query']
                prompt = prompt.replace("{user_query}", user_prompt)

                final_response = self.custom_llm_call(
                                prompt=user_prompt,
                                max_tokens=self.max_tokens,
                                memory=self.session_state.memory
                            )
        else:
            final_response = self.custom_llm_call(
                                prompt=user_prompt,
                                max_tokens=self.max_tokens,
                                memory=self.session_state.memory
                            )

        self.update_session_state(user_prompt, final_response)

    def get_invoice_data(self):
        '''
        function to extract invoice data in a predefined json structure
        considering only one image for now
        will be modifying to handle multiple images in the same session state  
        '''

        extract_ocr = ExtractOCRData(self.session_state.image)
        extract_ocr.analyze_image()
        self.session_state.invoice_data_str = extract_ocr.extract_ocr_data()
                
        prompt = self.session_state.config['prompt_library']['get_invoice_data']
        prompt = prompt.replace("{invoice_data}", self.session_state.invoice_data_str)
                
        response = self.custom_llm_call(prompt=prompt, max_tokens=self.max_tokens)
        self.session_state.invoice_data_json = parse_json(response)
        
        # for testing
        # with open('D:/Projects/InvoAssist/test_data/prompt.txt', 'a') as f:
        #     for line in prompt.split('\n'):
        #         f.write(line)

        # with open('D:/Projects/InvoAssist/test_data/llm_response_test_4_v3_before_postproc.json', 'w') as f:
        #     f.write(json.dumps(response))
        
        # try:
        #     self.session_state.invoice_data_json = parse_json(response)
        #     with open('D:/Projects/InvoAssist/test_data/llm_response_test_4_v3.json', 'w') as f:
        #         json.dump(self.session_state.invoice_data_json, f)
        #     print("PASSED")
        # except:
        #     print("FAILED")
        