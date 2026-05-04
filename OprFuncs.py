import pandas as pd
import io
import re
import os

def data_infer(dataframe):   
    buffer = io.StringIO()
    dataframe.info(buf=buffer)
    data_info = buffer.getvalue()
    
    # Ensure output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  
    
    output_path = os.path.join(output_dir, "df_info.txt")
    with open(output_path, "w", encoding="utf-8") as f:  
        f.write(data_info)
    return data_info

def data_describer(dataframe):
    # Get the description of the dataframe
    description = dataframe.describe()
    
    # Convert the description to a string with column names
    description_str = "Data Description:\n"
    for col in description.columns:
        description_str += f"\nColumn: {col}\n"
        description_str += description[col].to_string() + "\n"
    
    # Ensure output directory exists
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Use os.path.join for path handling
    output_path = os.path.join(output_dir, "df_description.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(description_str)
    
    return description_str

def extract_code(input_text):
    result = re.search(r'```.*?\n(.*?)\n```', input_text, re.DOTALL)
    code = result.group(1) if result else input_text
    code_lines = code.splitlines()
    cleaned_code = "\n".join(line.strip() for line in code_lines)
    return cleaned_code.strip()

def read_file(path):
    _, extension = os.path.splitext(path)    
    if extension.lower() == ".csv":
        encodings_to_try = ['utf-8', 'latin1', 'cp1252', 'utf-16']
        for encoding in encodings_to_try:
            try:
                df = pd.read_csv(path, encoding=encoding)
                print(f"Successfully read CSV with encoding: {encoding}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error reading file: {e}")
                continue
    raise ValueError(f"Unsupported file extension: {extension}")

def extract_questions(generated_text):
    # Split the text by lines and filter out empty lines
    lines = [line.strip() for line in generated_text.split('\n') if line.strip()]
    
    # Extract questions (assuming each question starts with a number and a dot)
    questions = []
    for line in lines:
        if line[0].isdigit() and '.' in line:
            questions.append(line.split('. ', 1)[1])  # Split on the first occurrence of '. ' and take the second part
    
    return questions