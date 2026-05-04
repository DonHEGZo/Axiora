import bcrypt
import uuid
from sqlalchemy import (
    create_engine, ForeignKey,
    Column, String, Integer, SmallInteger,
    Text, DateTime, Boolean, Float
)
from sqlalchemy import func
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID
import os

engine = create_engine("sqlite:///axioradb.db")
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    email = Column(String)
    preferred_llm = Column(UUID(as_uuid=True), ForeignKey('llm.llm_id'), nullable=True)
    
    reports = relationship("Report", back_populates="user")
    llm = relationship("LLM", back_populates="users")

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password) 

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username='{self.username}', email='{self.email}')>"

# 2. LLM Table
class LLM(Base):
    __tablename__ = "llm"
    llm_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    llm_name = Column(String(255), nullable=False)
    parameters = Column(SmallInteger)
    install_llm_code = Column(String)
    
    # Relationships
    reports = relationship("Report", back_populates="llm")
    report_memories = relationship("ReportMemory", back_populates="llm")
    users = relationship("User", back_populates="llm")  

    def __init__(self, llm_name, parameters=None, install_llm_code=None):
        self.llm_name = llm_name
        self.parameters = parameters
        self.install_llm_code = install_llm_code

    def __repr__(self):
        return f"<LLM(llm_id={self.llm_id}, llm_name='{self.llm_name}')>"


# 3. Dataset Table
class Dataset(Base):
    __tablename__ = "dataset"
    dataset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_name = Column(Text, nullable=False)
    raw_data = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=func.now())
    data_info = Column(Text)
    data_description = Column(Text)
    data_sample = Column(Text)
    data_columns = Column(Text)
    
    # Relationships
    reports = relationship("Report", back_populates="dataset")
    clean_datasets = relationship("CleanDataset", back_populates="original_dataset")

    def __init__(self, dataset_name, raw_data, data_info=None, data_description=None, data_sample=None, data_columns=None):
        self.dataset_name = dataset_name
        self.raw_data = raw_data
        self.data_info = data_info
        self.data_description = data_description
        self.data_sample = data_sample
        self.data_columns = data_columns

    def __repr__(self):
        return f"<Dataset(dataset_id={self.dataset_id}, dataset_name='{self.dataset_name}')>"


# 4. CleanDataset Table
class CleanDataset(Base):
    __tablename__ = "cleanDataset"
    clean_dataset_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_name = Column(Text, nullable=False)
    raw_data = Column(Text, nullable=False)
    original_dataset_id = Column(UUID(as_uuid=True), ForeignKey("dataset.dataset_id"))
    cleaned_at = Column(DateTime, default=func.now())
    data_info = Column(Text)
    data_description = Column(Text)
    data_sample = Column(Text)
    data_columns = Column(Text)
    
    # Relationships
    original_dataset = relationship("Dataset", back_populates="clean_datasets")
    reports = relationship("Report", back_populates="clean_dataset")

    def __init__(self, dataset_name, raw_data, original_dataset_id, data_info=None, data_description=None, data_sample=None, data_columns=None):
        self.dataset_name = dataset_name
        self.raw_data = raw_data
        self.original_dataset_id = original_dataset_id
        self.data_info = data_info
        self.data_description = data_description
        self.data_sample = data_sample
        self.data_columns = data_columns

    def __repr__(self):
        return f"<CleanDataset(clean_dataset_id={self.clean_dataset_id}, dataset_name='{self.dataset_name}')>"


# 5. Report Table (previously Session)
class Report(Base):
    __tablename__ = "report"
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"))
    llm_id = Column(UUID(as_uuid=True), ForeignKey("llm.llm_id"))
    report_name = Column(Text, nullable=False)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("dataset.dataset_id"))
    clean_dataset_id = Column(UUID(as_uuid=True), ForeignKey("cleanDataset.clean_dataset_id"))
    creation_date = Column(DateTime, default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reports")
    llm = relationship("LLM", back_populates="reports")
    dataset = relationship("Dataset", back_populates="reports")
    clean_dataset = relationship("CleanDataset", back_populates="reports")
    report_memories = relationship("ReportMemory", back_populates="report", cascade="all, delete-orphan")
    summary = relationship("Summary", back_populates="report", uselist=False, cascade="all, delete-orphan")
    questions = relationship("Questions", back_populates="report", cascade="all, delete-orphan")
    dashboards = relationship("Dashboards", back_populates="report", cascade="all, delete-orphan")
    final_reports = relationship("FinalReport", back_populates="report", cascade="all, delete-orphan")
    forecasts = relationship("Forecasting", back_populates="report", cascade="all, delete-orphan")

    def __init__(self, report_name, user_id, llm_id, dataset_id, clean_dataset_id=None):
        self.user_id = user_id
        self.llm_id = llm_id
        self.dataset_id = dataset_id
        self.report_name = report_name
        self.clean_dataset_id = clean_dataset_id

    def __repr__(self):
        return f"<Report(report_id={self.report_id},report_name={self.report_name}, user_id={self.user_id})>"


# 6. ReportMemory Table (previously SessionMemory)
class ReportMemory(Base):
    __tablename__ = "report_memory"
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"))
    llm_id = Column(UUID(as_uuid=True), ForeignKey("llm.llm_id"))
    message_date = Column(DateTime, default=func.now(), nullable=False)
    prompt = Column(Text)
    response = Column(Text)
    additional_kwargs = Column(Text)
    response_metadata = Column(Text)
    chat = Column(Boolean)
    
    # Relationships
    report = relationship("Report", back_populates="report_memories")
    llm = relationship("LLM", back_populates="report_memories")

    def __init__(self, report_id, llm_id, prompt, response, additional_kwargs=None, response_metadata=None, chat=False):
        self.report_id = report_id
        self.llm_id = llm_id
        self.prompt = prompt
        self.response = response
        self.additional_kwargs = additional_kwargs
        self.response_metadata = response_metadata
        self.chat = chat

    def __repr__(self):
        return f"<ReportMemory(message_id={self.message_id}, report_id={self.report_id}, prompt={self.prompt}, response={self.response}, message_date={self.message_date})>"


# 7. Summary Table
class Summary(Base):
    __tablename__ = "summary"
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"), primary_key=True)
    summary_content = Column(Text)
    
    # Relationship
    report = relationship("Report", back_populates="summary")

    def __init__(self, report_id, summary_content=None):
        self.report_id = report_id
        self.summary_content = summary_content

    def __repr__(self):
        return f"<Summary(report_id={self.report_id})>"


# 8. Questions Table
class Questions(Base):
    __tablename__ = "questions"
    question_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"))
    question_num = Column(Integer)
    question = Column(Text)
    answer = Column(Text)
    
    # Relationship
    report = relationship("Report", back_populates="questions")

    def __init__(self, question_num, report_id, question, answer=None):
        self.question_num = question_num
        self.report_id = report_id
        self.question = question
        self.answer = answer

    def __repr__(self):
        return f"<Questions(question_id={self.question_id}, report_id={self.report_id})>"


# 9. Dashboards Table
class Dashboards(Base):
    __tablename__ = "dashboards"
    dashboard_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"))
    
    # Relationships
    report = relationship("Report", back_populates="dashboards")
    charts = relationship("Charts", back_populates="dashboard", cascade="all, delete-orphan")
    final_reports = relationship("FinalReport", back_populates="dashboard", cascade="all, delete-orphan")

    def __init__(self, report_id):
        self.report_id = report_id

    def __repr__(self):
        return f"<Dashboards(dashboard_id={self.dashboard_id}, report_id={self.report_id})>"


# 10. Charts Table
class Charts(Base):
    __tablename__ = "charts"
    chart_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chart_path = Column(String(255), nullable=False)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.dashboard_id", ondelete="CASCADE"))
    chart_style = Column(Text)
    chart_code = Column(Text)
    
    # Relationships
    dashboard = relationship("Dashboards", back_populates="charts")

    def __init__(self, chart_path, dashboard_id, chart_style=None, chart_code=None):
        self.chart_path = chart_path
        self.dashboard_id = dashboard_id
        self.chart_style = chart_style
        self.chart_code = chart_code

    def __repr__(self):
        return f"<Charts(chart_id={self.chart_id}, chart_type='{self.chart_type}')>"


# 11. Columns Table
"""class Columns(Base):
    __tablename__ = "columns"
    column_id = Column(Integer, primary_key=True, autoincrement=True)
    chart_id = Column(Integer, ForeignKey("charts.chart_id", ondelete="CASCADE"))
    column_name = Column(Text)
    
    # Relationship
    chart = relationship("Charts", back_populates="columns")

    def __init__(self, chart_id, column_name):
        self.chart_id = chart_id
        self.column_name = column_name

    def __repr__(self):
        return f"<Columns(column_id={self.column_id}, chart_id={self.chart_id})>"
        """


# 12. FinalReport Table
class FinalReport(Base):
    __tablename__ = "final_report"
    final_report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"), nullable=False)
    recommendation = Column(Text, nullable=False)
    dashboard_id = Column(UUID(as_uuid=True), ForeignKey("dashboards.dashboard_id", ondelete="CASCADE"), nullable=False)
    
    report = relationship("Report", back_populates="final_reports")
    dashboard = relationship("Dashboards", back_populates="final_reports")

    def __init__(self, report_id, recommendation, dashboard_id):
        self.report_id = report_id
        self.recommendation = recommendation
        self.dashboard_id = dashboard_id

    def __repr__(self):
        return f"<FinalReport(final_report_id={self.final_report_id}, report_id={self.report_id})>"


# 13. Forecasting Table
class Forecasting(Base):
    __tablename__ = "forecasting"
    forecast_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("report.report_id", ondelete="CASCADE"), nullable=False)
    target_column = Column(String(255), nullable=False)
    predicted_df = Column(Text, nullable=False)  # Store as JSON string
    rmse = Column(Float, nullable=True)
    r2 = Column(Float, nullable=True)
    charts_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    report = relationship("Report", back_populates="forecasts")

    def __init__(self, report_id, target_column, predicted_df, rmse=None, r2=None, charts_path=None):
        self.report_id = report_id
        self.target_column = target_column
        self.predicted_df = predicted_df
        self.rmse = rmse
        self.r2 = r2
        self.charts_path = charts_path

    def __repr__(self):
        return f"<Forecasting(forecast_id={self.forecast_id}, report_id={self.report_id}, target_column='{self.target_column}')>"

def init_db():
    """Initialize the database, creating all tables if they don't exist."""
    try:
        # Create database file if it doesn't exist
        db_path = "axioradb.db"
        if not os.path.exists(db_path):
            Base.metadata.create_all(engine)
            
            # Create a session to add initial data
            from sqlalchemy.orm import sessionmaker
            Session = sessionmaker(bind=engine)
            session = Session()
            
            try:
                # Add default LLM models
                llama = LLM(
                    llm_name="llama3b",
                    parameters=3,
                    install_llm_code="ollama pull llama2:3b"
                )
                phi = LLM(
                    llm_name="phi35",
                    parameters=3,
                    install_llm_code="ollama pull phi"
                )
                
                session.add(llama)
                session.add(phi)
                session.commit()
                
            except Exception as e:
                print(f"Error initializing database: {str(e)}")
                session.rollback()
            finally:
                session.close()
        else:
            # For existing database, try to update tables
            try:
                # Drop the final_report table if it exists
                Base.metadata.tables['final_report'].drop(engine, checkfirst=True)
                # Create tables that don't exist
                Base.metadata.create_all(engine)
            except Exception as e:
                print(f"Error updating database schema: {str(e)}")
                raise

    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        raise

# Initialize database when module is imported
init_db()
