import pandas as pd
from typing import Dict, List, Tuple
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain, SequentialChain
from OprFuncs import *
#from langchain.schema.runnable import RunnableSequence
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
#from langchain.agents import AgentExecutor, Tool, create_react_agent
#from langchain import hub
import re
#from modelEXT.PygalCodeComponents import PygalCodeComponents
#from langchain.output_parsers import PydanticOutputParser
from DatabaseManager import DatabaseManager
from langchain_experimental.agents import create_pandas_dataframe_agent

class DataAnalyzer:
    def __init__(self,dataframe,llm,user_id=None):
        self.dataframe = dataframe
        self.llm = llm
        self.data_info = data_infer(dataframe)
        self.data_description = data_describer(dataframe)
        self.data_sample = dataframe.head().to_string()
        self.data_cols = ", ".join(dataframe.columns)
        self.db = DatabaseManager()
        self.report_id = None
        self.memory = []
        self.user_id = user_id

    def analysis_data(self):
        data_info = self.data_info
        data_sample = self.data_sample
        data_description = self.data_description

        analysis_template = '''
        You are a world-class data analyst.

        You are provided with:
        1. Dataset metadata: {data_info}
        2. Dataset sample: {data_sample}
        3. Dataset summary: {data_description}

        Your task is to provide a clear, comprehensive, and insightful **summary of the actual dataset provided**. 
        - **Do not invent or assume any additional data.**
        - **Do not generate code , hypothetical examples, or reference data not present.**
        - Focus only on the real data and its characteristics.
        - Summarize the most important findings, patterns, and statistics present in the dataset.
        - Highlight any interesting trends, outliers, or relationships you observe.
        - If the data is limited, mention this and only summarize what is actually present.
        
        Respond with a professional, business-oriented summary suitable for decision-makers.
        '''

        analysis_prompt = PromptTemplate(
            input_variables=["data_info", "data_sample", "data_description"],
            template=analysis_template
        )
        
        analysis_chain = analysis_prompt | self.llm

        formatted_analysis_prompt = analysis_template.format(data_info=data_info,data_sample=data_sample,
                                                             data_description=data_description)

        self.analysis = self.llm.invoke(formatted_analysis_prompt)

        self.memory.append(HumanMessage(content=formatted_analysis_prompt))
        self.memory.append(AIMessage(content=self.analysis))
        self.db.saveMemory(reportID=self.report_id,
                           llm=self.db.llm_id_by_name(self.llm.model),
                           prompet=formatted_analysis_prompt,
                           response=self.analysis,
                           chat=False)
        return self.analysis        

    def questions_gen(self, num):
        data_info = self.data_info
        data_sample = self.data_sample
        data_description = self.data_description
        

        question_prompt = f"""
        You are a senior data analyst hired by a company to extract meaningful, high-level, and actionable business insights from the following dataset.

        Your job is to generate advanced **strategic questions** that:
        - Are deeply rooted in the data structure and semantics.
        - Reflect important **business objectives**, patterns, risks, or growth opportunities.
        - Are **strong, insightful, and relevant** to decision-makers like company owners or managers.
        - Can be **easily visualized** using bar charts, line plots, histograms, scatter plots, or pie charts.

        **DO NOT generate general or surface-level questions. Instead, focus on questions that:**
        - Quantify change over time or between groups.
        - Explore distribution, frequency, or correlation.
        - Investigate trends, seasonality, or anomalies.
        - Provide guidance for optimizing business performance or identifying risks.

        You MUST generate exactly {num} chartable, insightful questions.

        ### INPUTS:
        1. Dataset Overview: {data_info}
        2. Dataset Sample: {data_sample}
        3. Data Summary: {data_description}

        ### OUTPUT FORMAT:
        Write {num} powerful analytical questions that:
        - Could be visualized with a chart.
        - Have clear business relevance.
        - Reflect advanced reasoning.

        Each question should be written on a separate line.
        """

        question_template = PromptTemplate(
            input_variables=["num", "data_info", "data_sample", "data_description"],
            template=question_prompt
        )

        question_chain = question_template | self.llm

        try:
            generated_questions = question_chain.invoke({
                "num": num,
                "data_info": data_info,
                "data_sample": data_sample,
                "data_description": data_description
            })

            # Ensure the response is properly encoded
            if isinstance(generated_questions, str):
                generated_questions = generated_questions.encode('utf-8', 'replace').decode('utf-8')

            print("Raw LLM Output:", repr(generated_questions))

            if not generated_questions.strip():
                print("Warning: LLM did not generate any questions.")
                return []

            # Use the improved extraction function
            questions_list = extract_questions(generated_questions)

            print("Extracted Questions List:", questions_list)

            # Trim or handle missing questions
            if len(questions_list) > num:
                questions_list = questions_list[:num]
            elif len(questions_list) < num:
                print(f"Warning: Expected {num} questions, but got {len(questions_list)}")

            # Store in memory
            formatted_question_prompt = question_template.format(
                num=num,
                data_info=data_info,
                data_sample=data_sample,
                data_description=data_description
            )
            self.memory.append(HumanMessage(content=formatted_question_prompt))
            self.memory.append(AIMessage(content="\n".join(questions_list)))
            self.db.saveMemory(reportID=self.report_id,
                           llm=self.db.llm_id_by_name(self.llm.model),
                           prompet=formatted_question_prompt,
                           response="\n".join(questions_list),
                           chat=False)

            return questions_list

        except Exception as e:
            print(f"Error generating questions: {str(e)}")
            return []

    
    def chat(self,question):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a data analyst.",
                    ),
                    MessagesPlaceholder(variable_name="memory"),
                    ("human", "{input}"),
                    ]
                    )
        chain = prompt_template | self.llm

        response = chain.invoke({"input": question, "memory":self.memory})
        self.db.saveMemory(reportID=self.report_id,
                           llm=self.db.llm_id_by_name(self.llm.model),
                           prompet=question,
                           response=response,
                           chat=True)

        self.memory.append(HumanMessage(content=question))
        self.memory.append(AIMessage(content=response))
        return response
    

    def select_chart_type(self, question: str) -> str:
        self.chart_type_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at selecting chart types for data visualization. Strictly follow these rules:
            
            1. CHART SELECTION GUIDE:
            - For comparing categories: Bar 
            - For trends over time: Line
            - For parts of a whole: Pie (few categories)
            - For relationships: Scatter
            - For the distribution of a numirecal variable: Histogram
            
            3. OUTPUT FORMAT (EXACTLY):
            chart_type: [Bar|Line|Pie|Scatter|Histogram]
            
            Data Description: {data_description}
            Available Columns: {columns}
            Sample Data: {sample_data}
            Question: {question}
            
            Respond ONLY with:
            chart_type: [chart_type]""")
        ])

        """Select only the chart type based on the question and data."""
        self.llm.temperature = 0.3
        chain = self.chart_type_prompt | self.llm
        response = chain.invoke({
            "data_description": self.data_description,
            "columns": self.data_cols,
            "sample_data": self.data_sample,
            "question": question
        })
        self.llm.temperature = 0.7
        # Parse response
        chart_match = re.search(r'chart_type:\s*([a-zA-Z]+)', response, re.IGNORECASE)
        chart_type = chart_match.group(1) if chart_match else None
        
        # Validate
        allowed_charts =  {
            'Bar', 'Line', 'Histogram', 
            'Pie', 'Scatter'
        }
        return chart_type if chart_type in allowed_charts else 'Bar'
    
    def select_columns(self, question: str) -> List[str]:
        self.columns_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at selecting relevant columns for data visualization. Strictly follow:
            
            1. COLUMN SELECTION RULES:
            - Focus on columns mentioned in the question
            - What is being measured (numerical columns)
            - What is being compared/grouped by (categorical columns)
            - Any time dimensions for trends
            - Never suggest columns not in Available Columns
            
            2. OUTPUT FORMAT (EXACTLY):
            columns: [exact_column_name1, exact_column_name2]
            
            Data Description: {data_description}
            Available Columns: {columns}
            Sample Data: {sample_data}
            Question: {question}
            
            Respond ONLY with:
            columns: [column1, column2]""")
        ])

        """"Select only the relevant columns based on the question and data."""
        self.llm.temperature = 0.3
        chain = self.columns_prompt | self.llm
        response = chain.invoke({
            "data_description": self.data_description,
            "columns":self.data_cols,
            "sample_data": self.data_sample,
            "question": question
        })
        self.llm.temperature = 0.7
        # Parse response
        cols_match = re.search(r'columns:\s*\[([^\]]+)\]', response)
        if cols_match:
            columns = [col.strip() for col in cols_match.group(1).split(',')]
        else:
            # Fallback parsing
            cols_line = next((line for line in response.split('\n') if line.startswith('columns:')), '')
            columns = [col.strip() for col in cols_line.replace('columns:', '').split(',') if col.strip()]
        
        # Validate columns exist in data
        available_cols = self.dataframe.columns.tolist()
        return [col for col in columns if col in available_cols]
    
    def get_chart_recommendation(self, question: str) -> Tuple[str, List[str]]:
        """Combined recommendation (maintaining original interface)"""
        chart_type = self.select_chart_type(question)
        columns = self.select_columns(question)
        return chart_type, columns
    

    
    def generate_recommendations(self, num_recommendations: int = 5):
        data_info = self.data_info
        data_sample = self.data_sample
        data_description = self.data_description
        analysis = self.analysis  # التحليل الذي تم عمله سابقاً

        recommendation_prompt = '''
        You are a world-class business consultant and data analyst.

        You have analyzed the following:
        - Dataset metadata: {data_info}
        - Dataset sample: {data_sample}
        - Dataset summary: {data_description}
        - Detailed business analysis: {analysis}

        Based on your deep understanding of the data and analysis:
        Your task is to generate {num_recommendations} highly actionable, strategic recommendations for the business.

        Your recommendations must:
        - Be directly based on the analysis and insights.
        - Address clear business actions (e.g., optimize processes, launch new products, reduce risks, target specific segments, etc.)
        - Be specific, impactful, and feasible.
        - Cover both short-term quick wins and long-term strategic moves.
        - Include estimated expected outcome in percentage (%) where appropriate.
        - Include any potential risks or challenges for each recommendation.
        - Reference relevant metrics or insights from the analysis if possible.
        - Use professional, executive-level language.
        - Add an appropriate emoji based on risk level:
            - ✅ for Low risk
            - ⚠️ for Medium risk
            - ❗for High risk

        Output Format:

        ### 📋 Full Recommendation Details

        1. **[Recommendation Title]** [Emoji]
        - **Details:** Explain clearly what should be done and why.
        - **Expected Impact:** [e.g., Increase attendance by 10%]
        - **Metrics Reference:** [Reference specific metric if available, e.g., matches with <50% attendance]
        - **Potential Risks:** [Possible challenges or risks involved]
        - **Timeline:** [Short-term or Long-term]

        Repeat similarly for each recommendation.
        '''

        
        rec_template = PromptTemplate(
            input_variables=["data_info", "data_sample", "data_description", "analysis", "num_recommendations"],
            template=recommendation_prompt
        )

        rec_chain = LLMChain(llm=self.llm, prompt=rec_template)

        rec_response = rec_chain.run(
            data_info=data_info,
            data_sample=data_sample,
            data_description=data_description,
            analysis=analysis,
            num_recommendations=num_recommendations
        )

        formatted_rec_prompt = recommendation_prompt.format(
            data_info=data_info,
            data_sample=data_sample,
            data_description=data_description,
            analysis=analysis,
            num_recommendations=num_recommendations
        )
        self.memory.append(HumanMessage(content=formatted_rec_prompt))
        self.memory.append(AIMessage(content=rec_response))
        self.db.saveMemory(reportID=self.report_id,
                        llm=self.db.llm_id_by_name(self.llm.model),
                        prompet=formatted_rec_prompt,
                        response=rec_response,
                        chat=False)

        return rec_response