import re
import ast
import json

def parse_json(response):
    response = re.sub('`', '', response)
    response = ast.literal_eval(response)
    return response