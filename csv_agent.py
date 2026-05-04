import pandas as pd
from LLM import llama3b
from DataAnalyzer import DataAnalyzer
df = pd.read_csv("Test_Datasets/laptop_price.csv", encoding='latin1')
analyzer = DataAnalyzer(dataframe=df,llm=llama3b)
analysis = analyzer.chat("What is the relation between the company and the price?")
print(analysis)