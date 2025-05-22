import json
import os
import boto3
from trp import Document
import pandas as pd

class ExtractOCRData:
    def __init__(self, image):
        self.image = image
    
    def id_to_text_map(self):
        id_to_text = {}

        for block in self.ocr_data['Blocks']:
            if block['BlockType'] in ['LINE', 'WORD']:
                id_to_text[block['Id']] = block['Text']

        return id_to_text

    def get_text_layout_data(self):
        text_str = ''
        all_layouts = [block for block in self.ocr_data['Blocks'] if block['BlockType'].startswith('LAYOUT_') and block['BlockType']!='LAYOUT_TABLE']

        all_layouts = sorted(all_layouts, key=lambda x: (x['Geometry']['BoundingBox']['Top'], x['Geometry']['BoundingBox']['Left']))

        for block in all_layouts:
            rel_ids = []
            for rel in block.get('Relationships', []):
                for id in rel['Ids']:
                    text_str += self.id_to_text.get(id, '') + '\n'
            text_str += '\n'
        
        return text_str

    def get_table_data(self, doc):
        '''
        extract table layout data and returns a pandas dataframe
        '''
        tables = []

        for page in doc.pages:
            for table in page.tables:
                temp_table = {}
                for col in table.rows[0].cells:
                    temp_table[col.text] = []
                for i in range(1, len(table.rows)):
                    for j in range(len(temp_table)):
                        temp_table[table.rows[0].cells[j].text].append(table.rows[i].cells[j].text)
                
                tables.append(pd.DataFrame(temp_table))
        return tables
    
    def extract_ocr_data(self):
        '''
        extract layout level text and table data separately
        Return a string appending each extracted data
        '''
        self.id_to_text = self.id_to_text_map()
        text_data = self.get_text_layout_data()

        ocr_data_doc = Document(self.ocr_data)
        table_data = self.get_table_data(ocr_data_doc)
        table_data_str = '\n\n'.join([f'TABLE {i+1} \n{table.to_markdown()}' for i, table in enumerate(table_data)])
        
        final_ocr_data_str = text_data + '\n\n' + table_data_str
        return final_ocr_data_str
    
    def analyze_image(self):
        '''self.image has to be in Bytes'''

        client = boto3.client('textract')
        response = client.analyze_document(
            Document={'Bytes': self.image},
            FeatureTypes=['TABLES', 'FORMS', 'LAYOUT']
        )
        self.ocr_data = response

    def print_data_temp(self):
        '''function for testing, delete later'''
        
        text_data, table_data = self.extract_ocr_data()

        print(f'\n====================================== Text Data ======================================\n')
        for line in text_data.split('\n'):
            print(line)
        print(f'\n====================================== Table Data ======================================\n')
        for table in table_data:
            print(table.to_markdown())

