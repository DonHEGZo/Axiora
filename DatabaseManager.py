from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy import create_engine, event
from sqlalchemy.pool import QueuePool
from Axioradb import (engine,Dataset,CleanDataset,Report,Summary,LLM,Questions,
                       Dashboards, Charts, ReportMemory,User, FinalReport, Forecasting, init_db)
from sqlalchemy import func
import functools
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class DatabaseManager:
    _instance = None
    _cache: Dict[str, Dict[str, Any]] = {}
    _cache_timeout = 300  # 5 minutes
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            # Initialize database
            init_db()
            # Configure connection pooling
            cls._instance.engine = create_engine(
                "sqlite:///axioradb.db",
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=1800
            )
            # Create session factory
            session_factory = sessionmaker(bind=cls._instance.engine)
            cls._instance.Session = scoped_session(session_factory)
        return cls._instance

    def __init__(self):
        try:
            self.session = self.Session()
        except Exception as e:
            print(f"Error initializing database session: {str(e)}")
            raise
    
    def __del__(self):
        try:
            self.Session.remove()
        except:
            pass

    def _ensure_session(self):
        """Ensure we have a valid session"""
        if not self.session or not self.session.is_active:
            self.session = self.Session()

    def _handle_error(self, e: Exception, operation: str):
        """Handle database errors consistently"""
        print(f"Database error during {operation}: {str(e)}")
        if self.session:
            self.session.rollback()
        raise

    def _cache_key(self, prefix: str, *args) -> str:
        return f"{prefix}:{'_'.join(str(arg) for arg in args)}"
    
    def _get_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self._cache_timeout):
                return data
            del self._cache[key]
        return None
    
    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (value, datetime.now())
        # Clean old cache entries
        now = datetime.now()
        self._cache = {
            k: (v, t) for k, (v, t) in self._cache.items()
            if now - t < timedelta(seconds=self._cache_timeout)
        }
    
    def cache_decorator(prefix: str):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(self, *args, **kwargs):
                cache_key = self._cache_key(prefix, *args)
                result = self._get_cache(cache_key)
                if result is not None:
                    return result
                result = func(self, *args, **kwargs)
                self._set_cache(cache_key, result)
                return result
            return wrapper
        return decorator

    @cache_decorator("dataset")
    def saveDataSet(self,path,name,info,description,sample,cols):
        #dataSet = self.Base.classes.dataset
        newDataSet = Dataset(raw_data=path,
                             dataset_name = name,
                             data_info=info,
                             data_description=description,
                             data_sample=sample,
                             data_columns=cols)
        self.session.add(newDataSet)
        self.session.flush()
        dataset_id = newDataSet.dataset_id
        self.session.commit()
        return dataset_id
    @cache_decorator("clean_dataset")
    def saveCleanDataset(self,ogID,path,name,info,description,sample,cols):
        #cleandataset = self.Base.classes.cleanDataset
        newCleanDataset = CleanDataset(original_dataset_id=ogID,
                            raw_data=path,
                            #uploaded_at=datetime.now(),
                             dataset_name = name,
                             data_info=info,
                             data_description=description,
                             data_sample=sample,
                             data_columns=cols)
        self.session.add(newCleanDataset)
        self.session.flush()
        clean_dataset_id = newCleanDataset.clean_dataset_id
        self.session.commit()
        return clean_dataset_id

    @cache_decorator("report")
    def saveReport(self,rname,user,llm,dataset):
        #sessionTable = self.Base.classes.session
        newReport = Report(user_id=user,
                             llm_id=llm,
                             dataset_id=dataset,
                             report_name=rname)
        self.session.add(newReport)
        self.session.flush()
        report_id = newReport.report_id  
        self.session.commit()
        return report_id
    
    def saveCleanDatasetReport(self, reportId, cleandataset):
        #sessionTable = self.Base.classes.session
        reportRow = self.session.query(Report).filter(Report.report_id == reportId).first()
        if reportRow:
            reportRow.clean_dataset_id = cleandataset
            self.session.commit()
            # Invalidate cache
            cache_key = self._cache_key("report", reportId)
            if cache_key in self._cache:
                del self._cache[cache_key]

    def saveSummary(self, reportID, summary_content):
        try:
            # Check if a summary already exists for this reportID
            summary = self.session.query(Summary).filter(Summary.report_id == reportID).first()
            if summary:
                summary.summary_content = summary_content
            else:
                newSummary = Summary(report_id=reportID, summary_content=summary_content)
                self.session.add(newSummary)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise

    @cache_decorator("llm_id")
    def llm_id_by_name(self, llmName: str) -> int:
        #llmTable = self.Base.classes.llm 
        result = self.session.query(LLM.llm_id).filter(LLM.llm_name == llmName).first()
        return result[0] if result else None
    
    @cache_decorator("llm_code")
    def llm_installtion_code(self,llmName: str) -> int:
        llm = self.session.query(LLM).filter_by(llm_name=llmName).first()
        return llm.install_llm_code

    
    def saveQuestion(self,reportID, question):
        max_question_num = self.session.query(func.max(Questions.question_num)).filter(Questions.report_id == reportID).scalar()
        if max_question_num is None:
            max_question_num = 0
        new_question_num = max_question_num + 1
        newQu = Questions(question_num = new_question_num, report_id=reportID, question=question)
        self.session.add(newQu)
        self.session.commit()

    def addDashboard(self,reportID):
        newDash = Dashboards(report_id=reportID)
        self.session.add(newDash)
        self.session.flush()
        dashboard_id = newDash.dashboard_id  
        self.session.commit()
       #DashFinalReport = FinalReport(report_id=reportID,dashboard_id=dashboard_id)
        #self.session.add(DashFinalReport)
        self.session.commit()

        return dashboard_id
    
    def saveCharts(self,dashID,path):
        newChart = Charts(dashboard_id=dashID,chart_path=path)
        self.session.add(newChart)
        self.session.commit()

    def saveMemory(self,reportID,llm,prompet,response,chat):
        newMessage = ReportMemory(report_id=reportID,
                                   llm_id=llm,
                                   prompt=prompet,
                                   response=response,
                                   chat=chat)
        self.session.add(newMessage)
        self.session.commit()

    @cache_decorator("user_reports")
    def get_user_reports(self, user_id):
       reports = self.session.query(Report).filter(Report.user_id == user_id).all()
       return [{'id': report.report_id, 'name': report.report_name} for report in reports]
    
    @cache_decorator("report_dataset")
    def get_report_dataset(self, reportID):
        clean_data_set = self.session.query(CleanDataset.raw_data)\
        .join(Report, Report.clean_dataset_id == CleanDataset.clean_dataset_id)\
        .filter(Report.report_id == reportID)\
        .first()
        
        if clean_data_set:
            return clean_data_set[0]
        
        data_set = self.session.query(Dataset.raw_data)\
        .join(Report, Report.dataset_id == Dataset.dataset_id)\
        .filter(Report.report_id == reportID)\
        .first()
        return data_set[0] if data_set else None
    
    def get_report_summary(self, reportID):
        summary = self.session.query(Summary.summary_content).filter(Summary.report_id == reportID).first()
        summary = summary[0] if summary else None
        return summary
    def get_report_questions(self, reportID):
        questions = self.session.query(Questions.question).filter(Questions.report_id == reportID).order_by(Questions.question_num).all()
        return [qu[0] for qu in questions] if questions else None
    
    def get_report_chat(self, reportID):
        chat_history = self.session.query(
            ReportMemory.prompt,
            ReportMemory.response,
            ReportMemory.message_date
        ).filter(
            ReportMemory.report_id == reportID,
            ReportMemory.chat == True
        ).order_by(ReportMemory.message_date).all()
        return chat_history if chat_history else None
    
    def get_report_memory(self, reportID):
        memory = self.session.query(
            ReportMemory.prompt,
            ReportMemory.response,
            ReportMemory.message_date
        ).filter(
            ReportMemory.report_id == reportID,
            ReportMemory.chat == False
        ).order_by(ReportMemory.message_date).all()
        return memory if memory else None
    def get_user_name(self,userID):
        user_name = self.session.query(User.username).filter(User.user_id == userID).first()
        return user_name if user_name else None

    def get_report_charts(self, reportID):
        charts = self.session.query(Charts.chart_path)\
            .join(Dashboards, Charts.dashboard_id == Dashboards.dashboard_id)\
            .join(Report, Dashboards.report_id == Report.report_id)\
            .filter(Report.report_id == reportID)\
            .all()
        return [chart[0] for chart in charts] if charts else None
    def saveRecommendation(self, reportID, recommendation, dashboard_id):
        """Save a recommendation with its associated dashboard."""
        try:
            self._ensure_session()
            
            # Create new final report
            new_report = FinalReport(
                report_id=reportID,
                recommendation=recommendation,
                dashboard_id=dashboard_id
            )
            
            self.session.add(new_report)
            self.session.commit()
            
            # Invalidate cache if needed
            cache_key = self._cache_key("recommendation", reportID)
            if cache_key in self._cache:
                del self._cache[cache_key]
            
        except Exception as e:
            self._handle_error(e, "saving recommendation")
    def saveForecasting(self,reportID,target_column,predicted_df,rmse,r2,charts_path):
        newForecasting = Forecasting(report_id=reportID,target_column=target_column,
                                     predicted_df=predicted_df,
                                     rmse=rmse,
                                     r2=r2,
                                     charts_path=charts_path)
        self.session.add(newForecasting)
        self.session.commit()
    def get_forecasting(self, reportID):
        """Get all forecasting data for a given report ID"""
        forecasting_data = self.session.query(
            Forecasting.target_column,
            Forecasting.predicted_df,
            Forecasting.rmse,
            Forecasting.r2,
            Forecasting.charts_path
        ).filter(
            Forecasting.report_id == reportID
        ).first()
        
        if forecasting_data:
            return {
                'target_column': forecasting_data[0],
                'predicted_df': forecasting_data[1],
                'rmse': forecasting_data[2],
                'r2': forecasting_data[3],
                'charts_path': forecasting_data[4]
            }
        return None

