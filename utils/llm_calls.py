import json
import yaml
from openai import OpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationSummaryBufferMemory
from langchain_core.language_models.llms import LLM
from extract_ocr_data import ExtractOCRData
from json_handler import parse_json

class custom_llm(LLM):
    @property
    def _llm_type(self):
        return 'custom'
    
    def _call(self, prompt, model='meta-llama/llama-3.3-8b-instruct:free', stop=None):

        auth_dict = {
            "base_url": '',
            "api_key": ''
        }
        client = OpenAI(**auth_dict) 

        response = client.chat.completions.create(
            model = model,
            messages = [
                {
                    'role': 'user',
                    'content': f'{prompt}'
                }
            ]
        )

        return response.choices[0].message.content
    
class TriggerLLMCalls():
    def __init__(self, session_state):
        self.session_state = session_state
        # self.auth_dict = session_state.config['authentication']
    
    def custom_llm_call(self, prompt, memory=None):

        if memory:
            conversation = ConversationChain(
                llm = custom_llm(),
                # memory = self.session_state.memory
                memory = memory
            )
        else:
            conversation = ConversationChain(
                llm = custom_llm()
            )

        return conversation.predict(input=prompt)

    def update_session_state(self, input, output):
        if 'messages' not in self.sesstion_state:
            self.sesstion_state.messages = [
                {'role': 'user', 'content': input},
                {'role': 'assistant', 'content': output}
            ]
        else:
            self.sesstion_state.messages.extend([
                {'role': 'user', 'content': input},
                {'role': 'assistant', 'content': output}
            ])
        
        self.session_state.memory.save_context({'input': input}, {'output': output})

    def set_system_context(self):
        self.session_state.memory = ConversationSummaryBufferMemory(
                                        llm=custom_llm(),
                                        max_token_limit=50000
                                    )
        system_prompt = self.session_state.config['prompt_library']['system_prompt']
        response = self.custom_llm_call(system_prompt)

        self.session_state.memory.save_context({'input': system_prompt}, {'output': response})

    def get_chat_response(self, user_prompt):
        if 'image' in self.session_state:
            prompt_1 = self.session_state.config['prompt_library']['user_query']['query_nature']
            prompt_1 = prompt_1.replace("{user_query}", user_prompt)
            response_1 = self.custom_llm_call(prompt_1, self.session_state.memory)
            response_1 = parse_json(response_1)

            if response_1['category'] in ['1', 1]:
                prompt_2 = self.session_state.config['prompt_library']['user_query']['data_filtering']
                prompt_2 = prompt_2.replace("{user_query}", user_prompt)

                key_list = '\n'.join([f'id{i+1}. {key}' for key in self.session_state.invoice_data_json.keys()])
                prompt_2 = prompt_2.replace("{key_list}", key_list)
                response_2 = self.custom_llm_call(prompt_2)
                response_2 = parse_json(response_2)

                keys_req = response_2['keys_required']
                filtered_data = '\n'.join([f'{self.session_state.invoice_data_json[key]}' for key in keys_req])

                prompt_3 = self.session_state.config['prompt_library']['user_query']['final_query']
                prompt_3 = prompt_3.replace("{user_query}", user_prompt).replace("{information}", filtered_data)
                final_response = self.custom_llm_call(prompt_3, self.session_state.memory)
                self.update_session_state(user_prompt, final_response)
            else:
                final_response = self.custom_llm_call(user_prompt, self.session_state.memory)
                self.update_session_state(user_prompt, final_response)
        else:
            final_response = self.custom_llm_call(
                prompt=user_prompt,
                memory=self.session_state.memory
            )

            self.update_session_state(user_prompt, final_response)

    def get_invoice_data(self):
        '''
        function to extract invoice data in a predefined json structure
        considering only one image for now
        will be modifying to handle multiple images in the same session state  
        '''
        # for testing - 
        # extract_ocr = ExtractOCRData([])
        # with open('D:/Projects/InvoAssist/test_data/response_test_2.json') as f:
        #     extract_ocr.ocr_data = json.load(f)
        # invoice_data_str = extract_ocr.extract_ocr_data()
        # with open('D:/Projects/InvoAssist/utils/config.yaml', 'r') as file:
        #     config = yaml.safe_load(file)
        # prompt = config['prompt_library']['get_invoice_data']
        # prompt = prompt.replace("{invoice_data}", invoice_data_str)
        # return response

        extract_ocr = ExtractOCRData(self.session_state.image)
        extract_ocr.analyze_image()
        self.session_state.invoice_data_str = extract_ocr.extract_ocr_data()
                
        prompt = self.session_state.config['prompt_library']['get_invoice_data']
        prompt = prompt.replace("{invoice_data}", self.session_state.invoice_data_str)
                
        response = self.custom_llm_call(prompt)
        self.session_state.invoice_data_json = parse_json(response)
        