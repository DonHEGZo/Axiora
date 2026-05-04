from langchain_ollama import OllamaLLM
llama3b = OllamaLLM(model="llama3.2:3b")
granite_code3b = OllamaLLM(model="granite-code:3b")
starcoder2 = OllamaLLM(model="starcoder2:3b")
deepseek = OllamaLLM(model="deepseek-r1:7b")
dsCoder = OllamaLLM(model="deepseek-coder:latest") 
phi35 = OllamaLLM(model="phi3.5:3.8b") 
class LLModels():
    def __init__(self, model_name, model):
        self.model_name = model_name
        self.model = model