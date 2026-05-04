#from Custom_Widgets import *
#from Custom_Widgets.QAppSettings import QAppSettings
#from Custom_Widgets.QCustomTipOverlay import QCustomTipOverlay
from PySide6.QtCore import (QSettings, QTimer, QThread, Signal, Qt, QUrl)
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QCursor, QIcon, QPixmap)
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect, QApplication, QMainWindow, 
                             QFileDialog, QPushButton, QLabel, QDialog, QVBoxLayout, 
    QTableWidget, QTableWidgetItem, QSizePolicy, QHBoxLayout,
    QFrame, QCheckBox, QWidget, QLineEdit, QGridLayout, QScrollArea,
    QProgressBar
)
from PySide6.QtSvg import QSvgRenderer
import random
from Visualizer import Visualizer
import shutil
from PySide6.QtCore import QFile
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineSettings
from PySide6 import QtCore
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (QApplication, QMainWindow, QLineEdit,
                               QPushButton, QVBoxLayout, QWidget, QLabel,
                               QScrollArea, QSizePolicy, QHBoxLayout,
                               QFileDialog, QTableWidgetItem, QFrame, QCheckBox)

#from PySide6 import uic
import os
import subprocess
from OprFuncs import read_file, data_infer
from DataAnalyzer import DataAnalyzer
from LLM import *
from markdown import markdown
from functools import partial
from uiEXT.ChatBubble import ChatBubble
from uiEXT.CleanDataDialog import CleanDataDialog
#from Axioradb import *
from docx import Document
from DatabaseManager import DatabaseManager
import sys
import platform
from datetime import datetime

# Add Shiboken path to sys.path if needed
shiboken_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Lib', 'site-packages', 'shiboken6')
if os.path.exists(shiboken_path) and shiboken_path not in sys.path:
    sys.path.append(shiboken_path)

class SummaryWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer

    def run(self):
        try:
            summary = self.analyzer.analysis_data()
            self.finished.emit(summary)
        except Exception as e:
            self.error.emit(str(e))

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        
        # Set up the overlay
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Create layout
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Create loading spinner
        self.spinner = QProgressBar()
        self.spinner.setRange(0, 0)  # Makes it an "infinite" progress bar
        self.spinner.setFixedSize(60, 60)
        self.spinner.setTextVisible(False)
        self.spinner.setStyleSheet("""
            QProgressBar {
                border: 2px solid #3498DB;
                border-radius: 30px;
                background-color: transparent;
            }
            QProgressBar::chunk {
                background-color: transparent;
            }
        """)
        
        # Create loading text
        self.label = QLabel("Loading...")
        self.label.setObjectName("loadingLabel")
        self.label.setAlignment(Qt.AlignCenter)
        
        # Add widgets to layout
        layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        layout.addWidget(self.label, alignment=Qt.AlignCenter)
        
        # Set up rotation animation
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.timer.start(80)
        
    def _rotate(self):
        self.angle = (self.angle + 30) % 360
        self.spinner.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #3498DB;
                border-radius: 30px;
                background-color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: transparent;
            }}
        """)
        
    def showEvent(self, event):
        self.resize(self.parent().size())
        
    def resizeEvent(self, event):
        self.resize(self.parent().size())

class QuestionWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, analyzer, num_questions):
        super().__init__()
        self.analyzer = analyzer
        self.num_questions = num_questions

    def run(self):
        try:
            questions = self.analyzer.questions_gen(self.num_questions)
            self.finished.emit(questions)
        except Exception as e:
            self.error.emit(str(e))

class RecommendationWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, analyzer):
        super().__init__()
        self.analyzer = analyzer

    def run(self):
        try:
            recommendations = self.analyzer.generate_recommendations()
            self.finished.emit(recommendations)
        except Exception as e:
            self.error.emit(str(e))

class ChartGenerationWorker(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, analyzer, visualizer, questions, rname, db, reportID):
        super().__init__()
        self.analyzer = analyzer
        self.visualizer = visualizer
        self.questions = questions
        self.rname = rname
        self.db = db
        self.reportID = reportID

    def run(self):
        try:
            chart_paths = []
            dashboardID = self.db.addDashboard(reportID=self.reportID)
            for question in self.questions:
                chart_type = self.analyzer.select_chart_type(question)
                chart_columns = self.analyzer.select_columns(question)
                chart_title = question[3:6] + str(random.randint(100, 2000))
                chart_path = f"{self.rname}/{chart_title}.html"
                self.visualizer.generate_visualization(
                    question=question,
                    output_path=chart_path,
                    columns=chart_columns,
                    chart_type=chart_type,
                    width=1200,
                    height=800
                )
                if chart_path and os.path.exists(chart_path):
                    self.db.saveCharts(dashID=dashboardID, path=chart_path)
                    chart_paths.append(chart_path)
            self.finished.emit(chart_paths)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class GuiFunctions():
    def __init__(self, MainWindow, user_id):
        self.main_window = MainWindow
        self.ui = MainWindow.ui
        self.user_id = user_id
        self.db = DatabaseManager()
        self.llm = llama3b  
        self.selected_qu_list = [] 
        self.setup_connections()
        self.summary_worker = None 
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_loading_animation)
        self.loading_dots = 0
        self.web_view = None  # Track web view instance
        
        # Connect LLM selection change
        self.ui.llm_combo.currentTextChanged.connect(self.handle_llm_change)
        
        # Initialize loading overlay
        self.loading_overlay = LoadingOverlay(MainWindow)
        self.loading_overlay.hide()
        
        # Update icons with modern versions
        self.setup_modern_icons()

    def setup_connections(self):
        self.main_window.ui.openfile_btn.clicked.connect(self.handle_data_button)
        self.main_window.ui.sum_btn.clicked.connect(self.handle_sum_btn)
       # self.main_window.ui.btn_LLMs.clicked.connect(self.handle_btn_LLMs)
        self.main_window.ui.clean_data_btn.clicked.connect(self.handle_clean_data_btn)
        self.main_window.ui.qu_num_list.currentIndexChanged.connect(self.handle_qu_num)
        self.main_window.ui.qu_btn.clicked.connect(self.handle_qu_btn)
        self.main_window.ui.save_qu_btn.clicked.connect(self.handle_save_qu_btn)
       # self.main_window.ui.chat_data_btn.clicked.connect(self.handle_chat_data_btn)
        self.main_window.ui.send_btn.clicked.connect(self.send_message)
        self.lineEdit_chat = self.main_window.ui.lineEdit_message
        self.main_window.ui.lineEdit_message.keyReleaseEvent = self.enter_return_release
        self.main_window.ui.qu_data_btn.clicked.connect(self.handle_word_btn)
        self.main_window.ui.btn_dashboard.clicked.connect(self.handle_dashboard_click)
        # Add done button connection
        self.main_window.ui.done_btn.clicked.connect(self.process_selected_questions)
        self.main_window.ui.rec_btn.clicked.connect(self.handle_rec_btn)

    def handle_word_btn(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self.main_window, "Open Word File", "", "Word Files (*.docx)"
        )
        if fpath:
            document = Document(fpath)
            full_text = []
            for para in document.paragraphs:
                full_text.append(para.text)
            word_content = '\n'.join(full_text)
            
            # Debug: Print the content of the Word file
            print("Word file content:")
            print(word_content)

            # Extract questions from the Word content
            questions = self.extract_questions(word_content)
            
            # Store the extracted questions for use by other functions
            self.g_questions = questions
            
            # Clear the selected questions list
            self.selected_qu_list = []
            
            # Debug: Print the extracted questions
            print("Extracted questions:")
            print(questions)

            # Get references to UI components
            scroll_area = self.main_window.ui.scrollArea
            scroll_contents = self.main_window.ui.scrollAreaWidgetContents

            # Ensure proper widget hierarchy
            if not scroll_contents.layout():
                scroll_contents.setLayout(QVBoxLayout())

            qu_layout = scroll_contents.layout()
            qu_layout.setAlignment(Qt.AlignTop)

            # Clear previous questions
            while qu_layout.count():
                item = qu_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Add new questions with proper parenting
            if questions:
                for i, question in enumerate(questions, 1):
                    question_frame = QFrame(scroll_contents)
                    question_frame.setFrameShape(QFrame.StyledPanel)

                    hbox = QHBoxLayout(question_frame)
                    hbox.setContentsMargins(0, 0, 0, 0)  # Reduce margins
                    hbox.setSpacing(2)  # Reduce spacing between widgets

                    number_label = QLabel(f"{i}.", question_frame)
                    number_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    hbox.addWidget(number_label)

                    question_label = QLabel(str(question), question_frame)
                    question_label.setWordWrap(True)
                    question_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    # Set font size for question text
                    font = question_label.font()
                    font.setPointSize(20)  # Adjust this value to change font size
                    question_label.setFont(font)
                    hbox.addWidget(question_label)

                    check_box = QCheckBox(question_frame)
                    check_box.setObjectName(f"checkbox_{i}")  # Set unique object name
                    check_box.setProperty("question", question)
                    
                    # Create a custom slot for this specific checkbox
                    def create_slot(q):
                        return lambda checked: self.handle_question_selection(q, checked)
                    
                    # Connect with the custom slot
                    slot = create_slot(question)
                    check_box.toggled.connect(slot)
                    
                    hbox.addWidget(check_box)

                    qu_layout.addWidget(question_frame)

                # Ensure proper layout update
                scroll_contents.adjustSize()
                scroll_area.updateGeometry()
                QApplication.processEvents()  # Force UI refresh
            else:
                error_label = QLabel("No questions extracted. Please check your Word file.", scroll_contents)
                error_label.setAlignment(Qt.AlignCenter)
                qu_layout.addWidget(error_label)

            # Set widget if not already set (should be done once during initialization)
            if scroll_area.widget() != scroll_contents:
                scroll_area.setWidget(scroll_contents)

    def handle_data_button(self):
        dpath, _ = QFileDialog.getOpenFileName(
            self.main_window, "Open File", "", "CSV Files (*.csv);;Excel Files (*.xls *.xlsx)"
        )
        if dpath:
            self.dpath = dpath
            self.dname = os.path.basename(dpath)
            self.rname = os.path.splitext(os.path.basename(dpath))[0]
            os.makedirs(self.rname, exist_ok=True)  
            self.datasetPath = os.path.join(self.rname, self.dname)
            shutil.copy(dpath, self.datasetPath) 
            self.location = self.main_window.ui.path_location
            self.location.setText(dpath)
            self.df = read_file(dpath)
            self._analyzer_attributes()
            self.datasetID = self.db.saveDataSet(path=self.datasetPath,
                                                 name=self.dname,
                                                 info=self.data_info,
                                                 description=self.data_description,
                                                 sample=self.data_sample,
                                                 cols=self.data_cols) 
            self.reportID = self.db.saveReport(user=self.user_id,
                                llm=self.db.llm_id_by_name(self.llm.model),
                                dataset=self.datasetID,
                                rname = self.rname)
            self._show_df()
            
    def _analyzer_attributes(self):
            self.analyzer = DataAnalyzer(dataframe=self.df, llm=self.llm, user_id=self.user_id)
            self.data_info = self.analyzer.data_info
            self.data_description = self.analyzer.data_description
            self.data_sample = self.analyzer.data_sample
            self.data_cols = self.analyzer.data_cols
    def _show_df(self):
        self.analyzer.report_id = self.reportID
        if "Index" not in self.df.columns:
            self.df.insert(0, "Index", self.df.index)
        
        # Configure table for virtual scrolling
        self.table = self.main_window.ui.tableData
        self.table.setRowCount(0)  # Clear existing rows
        self.table.setSortingEnabled(False)  # Disable sorting temporarily
        
        # Set up table dimensions
        self.table.setRowCount(self.df.shape[0])
        self.table.setColumnCount(self.df.shape[1])
        
        # Set headers
        self.table.setHorizontalHeaderLabels(self.df.columns.astype(str))
        self.table.horizontalHeader().setVisible(True)
        
        # Batch load data in chunks
        CHUNK_SIZE = 100
        total_rows = self.df.shape[0]
        
        self.table.setUpdatesEnabled(False)  # Disable updates during batch loading
        
        for start_row in range(0, total_rows, CHUNK_SIZE):
            end_row = min(start_row + CHUNK_SIZE, total_rows)
            for row in range(start_row, end_row):
                for col in range(self.df.shape[1]):
                    item = QTableWidgetItem(str(self.df.iat[row, col]))
                    self.table.setItem(row, col, item)
        
        self.table.setUpdatesEnabled(True)  # Re-enable updates
        self.table.setSortingEnabled(True)  # Re-enable sorting
        self.table.resizeColumnsToContents()

    def handle_rec_btn(self):
        # Show loading overlay
        self.show_loading("Generating Recommendations...")
        
        # Disable the recommendations button
        self.main_window.ui.rec_btn.setEnabled(False)
        
        try:
            # Create and start a worker thread for recommendations
            self.rec_worker = RecommendationWorker(self.analyzer)
            self.rec_worker.finished.connect(self.handle_rec_complete)
            self.rec_worker.error.connect(self.handle_rec_error)
            self.rec_worker.start()
        except Exception as e:
            print(f"Error starting recommendations generation: {str(e)}")
            self.hide_loading()
            self.main_window.ui.rec_btn.setEnabled(True)

    def handle_rec_complete(self, recommendations):
        try:
            # Save to database and update UI
            if hasattr(self, 'reportID'):
                # Create a new dashboard for recommendations if needed
                dashboard_id = self.db.addDashboard(reportID=self.reportID)
                
                # Save recommendation with the new dashboard
                self.db.saveRecommendation(
                    reportID=self.reportID,
                    recommendation=recommendations,
                    dashboard_id=dashboard_id
                )
                
                # Update UI
                # Create CSS styling for larger font size
                css_style = """
                <style>
                body { font-size: 20px; }
                p { font-size: 20px; }
                h1, h2, h3, h4, h5, h6 { font-size: 20px; }
                li { font-size: 20px; }
                table { font-size: 20px; }
                td, th { font-size: 20px; }
                </style>
                """
                recommendations_md = markdown(recommendations)
                # Combine CSS with markdown content
                styled_recommendations = css_style + recommendations_md
                self.main_window.ui.recommendations_text.setHtml(styled_recommendations)
            else:
                print("Error: No report ID available")
                self.main_window.ui.recommendations_text.setMarkdown(
                    "Error: Could not save recommendations. Please make sure a report is loaded."
                )
        except Exception as e:
            print(f"Error handling recommendations completion: {str(e)}")
            self.main_window.ui.recommendations_text.setMarkdown(
                f"Error generating recommendations: {str(e)}"
            )
        finally:
            # Reset UI state
            self.main_window.ui.rec_btn.setEnabled(True)
            self.hide_loading()
            if self.rec_worker:
                self.rec_worker.deleteLater()
                self.rec_worker = None

    def handle_rec_error(self, error_message):
        # Hide loading overlay
        self.hide_loading()
        
        # Reset button state
        self.main_window.ui.rec_btn.setEnabled(True)
        print(f"Error generating recommendations: {error_message}")
        
        if self.rec_worker:
            self.rec_worker.deleteLater()
            self.rec_worker = None

    def handle_sum_btn(self):
        # Show loading overlay
        self.show_loading("Generating Summary...")
        
        # Disable the summary button
        self.main_window.ui.sum_btn.setEnabled(False)
        
        # Create and configure the worker
        self.summary_worker = SummaryWorker(self.analyzer)
        self.summary_worker.finished.connect(self.handle_summary_complete)
        self.summary_worker.error.connect(self.handle_summary_error)
        self.summary_worker.start()

    def _update_summary_text(self,summary):
            # Create CSS styling for larger font size
            css_style = """
            <style>
            body { font-size: 20px; }
            p { font-size: 20px; }
            h1, h2, h3, h4, h5, h6 { font-size: 20px; }
            li { font-size: 20px; }
            table { font-size: 20px; }
            td, th { font-size: 20px; }
            </style>
            """
            summary_md = markdown(summary)
            # Combine CSS with markdown content
            styled_summary = css_style + summary_md
            self.main_window.ui.summary_text.setHtml(styled_summary)

    def handle_summary_complete(self, summary):
        try:
            # Save to database and update UI
            self.db.saveSummary(reportID=self.reportID, summary_content=summary)
            self._update_summary_text(summary)
        except Exception as e:
            print(f"Error handling summary completion: {str(e)}")
        finally:
            # Reset UI state
            self.main_window.ui.sum_btn.setEnabled(True)
            self.hide_loading()
            if self.summary_worker:
                self.summary_worker.deleteLater()
                self.summary_worker = None

    def handle_summary_error(self, error_message):
        # Hide loading overlay
        self.hide_loading()
        
        # Reset button state
        self.main_window.ui.sum_btn.setEnabled(True)
        print(f"Error generating summary: {error_message}")
        
        if self.summary_worker:
            self.summary_worker.deleteLater()
            self.summary_worker = None


    def handle_clean_data_btn(self):
        # Show loading overlay
        self.show_loading("Cleaning Data...")
        
        try:
            # Check if datasetID exists
            if not hasattr(self, 'datasetID'):
                self.main_window.ui.import_data_dialog.setText("Please load a dataset first.")
                return
            
            # Create and show the cleaning dialog
            clean_dialog = CleanDataDialog(parent=self.main_window, df=self.df)
            if clean_dialog.exec() == QDialog.Accepted:
                # Get the cleaned dataframe from the dialog
                self.cleaned_df = clean_dialog.cleaned_data
                
                # Update filename and path
                self.dname = f"cleaned_{self.dname}"
                self.cleaned_df_path = os.path.join(self.rname, self.dname)
                print(f"Saving cleaned data to: {self.cleaned_df_path}")
                
                # Save cleaned dataframe to CSV
                self.cleaned_df.to_csv(self.cleaned_df_path, index=False)
                
                # Update current dataframe
                self.df = self.cleaned_df
                
                # Update analyzer attributes with cleaned data
                self._analyzer_attributes()
                
                # Save cleaned dataset to database
                self.datasetID = self.db.saveCleanDataset(
                    ogID=self.datasetID,
                    path=self.cleaned_df_path,
                    name=self.dname,
                    info=self.data_info,
                    description=self.data_description,
                    sample=self.data_sample,
                    cols=self.data_cols
                )
                
                # Save clean dataset report
                self.db.saveCleanDatasetReport(reportId=self.reportID, cleandataset=self.datasetID)
                
                # Update table display
                self._show_df()
                
                # Show success message
                self.main_window.ui.import_data_dialog.setText("Data cleaned successfully!")
            else:
                # User cancelled the cleaning operation
                self.main_window.ui.import_data_dialog.setText("Data cleaning cancelled.")
            
        except Exception as e:
            print(f"Error cleaning data: {str(e)}")
            self.main_window.ui.import_data_dialog.setText(f"Error cleaning data: {str(e)}")
            
        finally:
            # Hide loading overlay
            self.hide_loading()

    def extract_questions(self, text):
        """Extracts questions from the text by splitting on newlines."""
        questions = [line.strip() for line in text.split('\n') if line.strip()]
        return questions

    def handle_qu_num(self, index):
        """Handles the selection of the number of questions."""
        self.ques_num_list = self.main_window.ui.qu_num_list  # Get the dropdown list
        self.num_qu = self.ques_num_list.currentText()  # Get text directly

        try:
            self.num_qu = int(self.ques_num_list.currentText().strip())
        except ValueError:
            print(f"⚠️ Invalid selection: {self.num_qu}. Defaulting to 1")
            self.num_qu = 1

        print(f"Number of questions to generate: {self.num_qu}")

    def handle_qu_btn(self):
        # Validate analyzer state
        if not hasattr(self, 'analyzer') or self.analyzer is None:
            print("Analyzer not initialized. Load data first.")
            return

        # Show loading overlay
        self.show_loading("Generating Questions...")
        
        # Disable the questions button
        self.main_window.ui.qu_btn.setEnabled(False)
        
        # Create and configure the worker
        self.question_worker = QuestionWorker(self.analyzer, self.num_qu)
        self.question_worker.finished.connect(self.handle_questions_complete)
        self.question_worker.error.connect(self.handle_questions_error)
        self.question_worker.start()

    def handle_questions_complete(self, questions):
        try:
            # Store the generated questions
            self.g_questions = questions
            # Clear the selected questions list
            self.selected_qu_list = []
            # Update the UI with new questions
            self._ques_add()
        except Exception as e:
            print(f"Error handling questions completion: {str(e)}")
        finally:
            # Reset UI state
            self.main_window.ui.qu_btn.setEnabled(True)
            self.hide_loading()
            if hasattr(self, 'question_worker'):
                self.question_worker.deleteLater()
                self.question_worker = None

    def handle_questions_error(self, error_message):
        # Hide loading overlay
        self.hide_loading()
        
        # Reset button state
        self.main_window.ui.qu_btn.setEnabled(True)
        
        # Handle Unicode characters in error message
        try:
            error_msg = str(error_message).encode('ascii', 'replace').decode('ascii')
            print(f"Error generating questions: {error_msg}")
        except Exception as e:
            print(f"Error handling questions: {str(e)}")
        
        if hasattr(self, 'question_worker'):
            self.question_worker.deleteLater()
            self.question_worker = None

    def _ques_add(self): # Get references to UI components
        scroll_area = self.main_window.ui.scrollArea
        scroll_contents = self.main_window.ui.scrollAreaWidgetContents

        # Ensure proper widget hierarchy
        if not scroll_contents.layout():
            scroll_contents.setLayout(QVBoxLayout())

        qu_layout = scroll_contents.layout()
        qu_layout.setAlignment(Qt.AlignTop)

        # Clear previous questions
        while qu_layout.count():
            item = qu_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new questions with proper parenting
        if self.g_questions:
            for i, question in enumerate(self.g_questions, 1):
                question_frame = QFrame(scroll_contents)
                question_frame.setFrameShape(QFrame.StyledPanel)

                hbox = QHBoxLayout(question_frame)
                hbox.setContentsMargins(0, 0, 0, 0)  # Reduce margins
                hbox.setSpacing(2)  # Reduce spacing between widgets

                number_label = QLabel(f"{i}.", question_frame)
                number_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                hbox.addWidget(number_label)

                question_label = QLabel(str(question), question_frame)
                question_label.setWordWrap(True)
                question_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                # Set font size for question text
                font = question_label.font()
                font.setPointSize(20)  # Adjust this value to change font size
                question_label.setFont(font)
                hbox.addWidget(question_label)

                # Create checkbox with the question
                check_box = QCheckBox(question_frame)
                check_box.setObjectName(f"checkbox_{i}")
                
                # Create a custom slot for this specific checkbox
                def create_slot(q):
                    return lambda checked: self.handle_question_selection(q, checked)
                
                # Connect with the custom slot
                slot = create_slot(question)
                check_box.toggled.connect(slot)
                
                hbox.addWidget(check_box)
                qu_layout.addWidget(question_frame)

            # Ensure proper layout update
            scroll_contents.adjustSize()
            scroll_area.updateGeometry()
            QApplication.processEvents()  # Force UI refresh
        else:
            error_label = QLabel("No questions generated. Please check your data.", scroll_contents)
            error_label.setAlignment(Qt.AlignCenter)
            qu_layout.addWidget(error_label)

        # Set widget if not already set (should be done once during initialization)
        if scroll_area.widget() != scroll_contents:
            scroll_area.setWidget(scroll_contents)

    def handle_question_selection(self, question, checked):
        if checked:
            if question not in self.selected_qu_list:
                self.selected_qu_list.append(question)
        else:
            if question in self.selected_qu_list:
                self.selected_qu_list.remove(question)
     
    def handle_save_qu_btn(self):
        self.saved_questions = set()
        for qu in self.selected_qu_list:
            if qu not in self.saved_questions:  
                self.db.saveQuestion(reportID=self.reportID, question=qu)
                self.saved_questions.add(qu) 
        self.qu_saved = True

#
    # def handle_chat_data_btn(self):
    #     cfpath, _ = QFileDialog.getOpenFileName(
    #         self.main_window, "Open File", "", "CSV Files (*.csv);;Excel Files (*.xls *.xlsx)"
    #     )
    #     if cfpath:
    #         chat_df = read_file()
    #         chat_analyzer = DataAnalyzer(dataframe=chat_df, llm=self.llm)
    #         chat_df_anlysis = chat_analyzer.analysis_data()
    #         return chat_df_anlysis

    def enter_return_release(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.send_message()
    def _add_user_message(self, user_input):
        user_msg = ChatBubble(user_input, True, "You")
        self.main_window.ui.chat_layout.addWidget(user_msg)
        self.lineEdit_chat.clear()
        
        # Show loading indicator for AI response
        loading_msg = ChatBubble("Thinking...", False, "AI")
        loading_msg.setStyleSheet("color: #666; font-style: italic;")
        self.main_window.ui.chat_layout.addWidget(loading_msg)
        return loading_msg

    def _add_ai_message(self, ai_response, loading_msg=None):
        if loading_msg:
            self.main_window.ui.chat_layout.removeWidget(loading_msg)
            loading_msg.deleteLater()
        
        ai_msg = ChatBubble(ai_response, False, "AI")
        self.main_window.ui.chat_layout.addWidget(ai_msg)

    def send_message(self):
        print("send_message called")  # Debugging statement
        user_input = self.lineEdit_chat.text()
        if user_input:
            loading_msg = self._add_user_message(user_input=user_input)
            
            if not hasattr(self, 'analyzer') or not self.analyzer:
                print("Analyzer not initialized!")
                self._add_ai_message("Upload a dataset first.", loading_msg)
            else:
                # Use QThread to process the message asynchronously
                class MessageWorker(QThread):
                    finished = Signal(str)
                    
                    def __init__(self, analyzer, message):
                        super().__init__()
                        self.analyzer = analyzer
                        self.message = message
                    
                    def run(self):
                        response = self.analyzer.chat(self.message)
                        self.finished.emit(response)
                
                self.worker = MessageWorker(self.analyzer, user_input)
                self.worker.finished.connect(lambda response: self._add_ai_message(response, loading_msg))
                self.worker.start()

    def process_selected_questions(self):
        """Process selected questions and generate charts in a grid layout (now threaded)"""
        if not self.selected_qu_list:
            print("No questions selected!")
            print("Debug: Current selections:", self.selected_qu_list)
            return

        print(f"Processing {len(self.selected_qu_list)} selected questions")
        print(f"Selected questions: {self.selected_qu_list}")

        # Save questions and create dashboard first (quick, so keep in main thread)
        for qu in self.selected_qu_list:
            if not hasattr(self, 'saved_questions'):
                self.saved_questions = set()
            if qu not in self.saved_questions:
                self.db.saveQuestion(reportID=self.reportID, question=qu)
                self.saved_questions.add(qu)

        # Prepare visualizer if needed
        self.visualizer = Visualizer(dataframe=self.df)

        # Show loading overlay
        self.show_loading("Generating charts...")

        # Start chart generation in a thread
        self.chart_worker = ChartGenerationWorker(
            analyzer=self.analyzer,
            visualizer=self.visualizer,
            questions=self.selected_qu_list,
            rname=self.rname,
            db=self.db,
            reportID=self.reportID
        )
        self.chart_worker.finished.connect(self._on_charts_generated)
        self.chart_worker.error.connect(self._on_charts_error)
        self.chart_worker.start()

    def _on_charts_generated(self, chart_paths):
        self.chart_paths = chart_paths
        self.hide_loading()
        # Configure the page widget
        page_widget = self.main_window.ui.page
        if page_widget.layout():
            QWidget().setLayout(page_widget.layout())
        page_layout = QVBoxLayout(page_widget)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        # Configure widget_3
        widget_3 = self.main_window.ui.widget_3
        widget_3.setMinimumSize(800, 600)
        widget_3.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page_layout.addWidget(widget_3)
        # Switch to the visualization page
        self.main_window.ui.stackedWidget.setCurrentWidget(self.main_window.ui.page)
        # Display all charts
        self.display_current_chart()

    def _on_charts_error(self, error_message):
        print(f"Error processing questions: {error_message}")
        self.hide_loading()

    def display_current_chart(self):
        """Display all charts in a scrollable layout with lazy loading"""
        try:
            # Switch to the visualization page first
            self.main_window.ui.stackedWidget.setCurrentWidget(self.main_window.ui.page)
            
            # Get or create the page layout
            page_widget = self.main_window.ui.page
            if not page_widget.layout():
                page_layout = QVBoxLayout(page_widget)
                page_layout.setContentsMargins(0, 0, 0, 0)
                page_layout.setSpacing(0)
            else:
                page_layout = page_widget.layout()
            
            # Clear existing widgets
            while page_layout.count():
                item = page_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
                    item.widget().deleteLater()
            
            # Create scroll area
            main_scroll = QScrollArea()
            main_scroll.setWidgetResizable(True)
            main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            # Create main container
            main_container = QWidget()
            main_layout = QVBoxLayout(main_container)
            main_layout.setSpacing(20)
            main_layout.setContentsMargins(20, 20, 20, 20)
            
            # Calculate grid dimensions
            num_charts = len(self.chart_paths)
            if num_charts == 0:
                return
            
            cols = 2  # Maximum 2 columns
            rows = (num_charts + 1) // 2  # Ceiling division
            
            # Create grid layout
            grid_layout = QGridLayout()
            grid_layout.setSpacing(20)
            
            # Create placeholder widgets for each chart
            self.chart_widgets = []
            for i, chart_path in enumerate(self.chart_paths):
                # Create container with border
                chart_container = QFrame()
                chart_container.setStyleSheet("""
                    QFrame {
                        background-color: #1b1e23;
                        border: 2px solid #3d4451;
                        border-radius: 10px;
                    }
                """)
                chart_container.setFixedSize(800, 600)  # Reduced from 1200x800
                chart_layout = QVBoxLayout(chart_container)
                chart_layout.setContentsMargins(10, 10, 10, 10)
                
                # Create loading label
                loading_label = QLabel("Loading chart...")
                loading_label.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                loading_label.setAlignment(Qt.AlignCenter)
                chart_layout.addWidget(loading_label)
                
                # Add to grid
                row = i // cols
                col = i % cols
                grid_layout.addWidget(chart_container, row, col)
                
                # Store for lazy loading
                self.chart_widgets.append({
                    'container': chart_container,
                    'path': chart_path,
                    'loaded': False
                })
            
            # Add grid layout
            main_layout.addLayout(grid_layout)
            main_layout.addStretch()
            
            # Set up scroll area
            main_scroll.setWidget(main_container)
            page_layout.addWidget(main_scroll)
            
            # Connect scroll signal for lazy loading
            main_scroll.verticalScrollBar().valueChanged.connect(
                lambda: self._lazy_load_visible_charts(main_scroll)
            )
            
            # Initial load of visible charts
            QTimer.singleShot(100, lambda: self._lazy_load_visible_charts(main_scroll))
            
        except Exception as e:
            print(f"Error displaying charts: {str(e)}")
            import traceback
            traceback.print_exc()

    def _lazy_load_visible_charts(self, scroll_area):
        """Load charts that are currently visible in the scroll area"""
        try:
            viewport = scroll_area.viewport()
            visible_rect = viewport.rect()
            visible_rect.translate(0, scroll_area.verticalScrollBar().value())
            
            for chart_data in self.chart_widgets:
                if not chart_data['loaded']:
                    container = chart_data['container']
                    container_rect = container.geometry()
                    
                    # Check if container is visible
                    if container_rect.intersects(visible_rect):
                        self._load_chart(chart_data)
        except Exception as e:
            print(f"Error in lazy loading: {str(e)}")

    def _load_chart(self, chart_data):
        """Load a single chart"""
        try:
            if chart_data['loaded']:
                return
            
            container = chart_data['container']
            chart_path = chart_data['path']
            
            # Clear loading label
            while container.layout().count():
                item = container.layout().takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            if os.path.exists(chart_path):
                # Create web view
                web_view = QWebEngineView()
                
                # Configure settings
                settings = web_view.settings()
                settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
                settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
                
                # Configure web view
                web_view.setFixedSize(780, 580)  # Reduced from 1180x780
                web_view.page().setBackgroundColor(Qt.transparent)
                web_view.setAttribute(Qt.WA_TranslucentBackground)
                web_view.setContextMenuPolicy(Qt.NoContextMenu)
                
                # Load chart
                file_url = QUrl.fromLocalFile(os.path.abspath(chart_path))
                web_view.loadFinished.connect(lambda ok, v=web_view: self._on_chart_load_finished(ok, v))
                web_view.load(file_url)
                
                # Add to container
                container.layout().addWidget(web_view)
                chart_data['loaded'] = True
                
        except Exception as e:
            print(f"Error loading chart: {str(e)}")

    def _on_chart_load_finished(self, ok, web_view):
        """Handle chart load finished event"""
        if ok:
            # Inject JavaScript to enhance chart interactivity
            js = """
            if (window.Plotly) {
                var gd = document.querySelector('.plotly-graph-div');
                if (gd) {
                    Plotly.relayout(gd, {
                        'showlink': false,
                        'modeBarButtonsToRemove': ['sendDataToCloud'],
                        'responsive': true,
                        'displayModeBar': true,
                        'scrollZoom': true,
                        'editable': true,
                        'dragmode': 'zoom'
                    });
                    
                    // Enable single-click interactions
                    gd.on('plotly_click', function(data) {
                        var point = data.points[0];
                        console.log('Clicked point:', point);
                    });
                    
                    // Make chart responsive
                    window.addEventListener('resize', function() {
                        Plotly.Plots.resize(gd);
                    });
                }
            }
            """
            web_view.page().runJavaScript(js)

    def show_previous_chart(self):
        """Show the previous chart"""
        if hasattr(self, 'current_chart_index') and self.current_chart_index > 0:
            self.current_chart_index -= 1
            self.display_current_chart()

    def show_next_chart(self):
        """Show the next chart"""
        if hasattr(self, 'current_chart_index') and hasattr(self, 'total_charts'):
            if self.current_chart_index < self.total_charts - 1:
                self.current_chart_index += 1
                self.display_current_chart()

    def create_navigation_controls(self):
        """Create navigation controls for multiple charts"""
        # Create navigation widget
        self.nav_widget = QWidget()
        nav_layout = QHBoxLayout(self.nav_widget)
        
        # Create navigation buttons
        self.prev_btn = QPushButton("Previous")
        self.next_btn = QPushButton("Next")
        self.chart_counter = QLabel()
        
        # Add buttons to layout
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.chart_counter)
        nav_layout.addWidget(self.next_btn)
        
        # Connect button signals
        self.prev_btn.clicked.connect(self.show_previous_chart)
        self.next_btn.clicked.connect(self.show_next_chart)
        
        # Add navigation widget to widget_3
        widget_3 = self.main_window.ui.widget_3
        if not widget_3.layout():
            widget_3.setLayout(QVBoxLayout())
        widget_3.layout().addWidget(self.nav_widget)

    def display_svg(self, svg_path=None):
        """Display an SVG file in widget_3"""
        try:
            # If no specific SVG path is provided, look for charts in the output directory
            if svg_path is None:
                output_dir = "output"
                if os.path.exists(output_dir):
                    html_files = sorted(
                        [f for f in os.listdir(output_dir) if f.endswith('.html')],
                        key=lambda x: os.path.getmtime(os.path.join(output_dir, x)),
                        reverse=True
                    )
                    if html_files:
                        # Display the most recent chart
                        self.display_current_chart()
                        return
                    else:
                        print("No charts found in output directory")
                        return
                else:
                    print(f"Output directory {output_dir} does not exist")
                    return
            
            # If a specific SVG path is provided, verify it exists
            if not isinstance(svg_path, str):
                raise ValueError("SVG path must be a string")
            
            if not os.path.exists(svg_path):
                print(f"SVG file not found: {svg_path}")
                return None
            
            # Create SVG widget
            self.svg_widget = QSvgWidget()
            self.svg_widget.load(svg_path)  # Load the SVG file
            
            # Configure widget
            self.svg_widget.setMinimumSize(400, 300)
            self.svg_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            
            # Get widget_3 and set up layout
            widget_3 = self.main_window.ui.widget_3
            if not widget_3.layout():
                widget_3.setLayout(QVBoxLayout())
            
            # Clear existing content
            layout = widget_3.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Add SVG widget
            layout.addWidget(self.svg_widget)
            
            # Show everything
            self.svg_widget.show()
            widget_3.show()
            
            print(f"Successfully displayed SVG from: {svg_path}")
            return self.svg_widget
            
        except Exception as e:
            print(f"Error displaying SVG: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def update_loading_animation(self):
        self.loading_dots = (self.loading_dots + 1) % 4
        self.main_window.ui.sum_btn.setText(f"Generating{'.' * self.loading_dots}")

    def handle_llm_change(self, model_name):
        """Handle LLM model selection change"""
        if model_name == "llama3b":
            llm = llama3b.model
            if not self.is_model_installed(llm):
                self.install_model(self.db.llm_installtion_code(llm.model))
            self.llm = llama3b
        elif model_name == "phi35":
            llm = phi35.model
            if not self.is_model_installed(llm):
                self.install_model(self.db.llm_installtion_code(llm.model))
            self.llm = phi35
            
        # Update analyzer if it exists
        if hasattr(self, 'analyzer'):
            self.analyzer.llm = self.llm
            
        print(f"LLM model changed to: {model_name}")


    def is_model_installed(self, model_name):
        # Run `ollama list` to check if the model is installed
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        return model_name in result.stdout

    def install_model(self, install_code):
        # Execute the installation code in the terminal
        process = subprocess.run(install_code, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            raise RuntimeError(f"Failed to install model: {process.stderr}")

    def handle_dashboard_click(self):
        """Handle dashboard button click by displaying the most recent chart"""
        print("Opening dashboard view...")
        # Switch to the visualization page
        self.main_window.ui.stackedWidget.setCurrentWidget(self.main_window.ui.page)
        # Display the most recent chart
        self.display_current_chart()

    def setup_modern_icons(self):
        # Update main icons
        self.main_window.ui.btn_home.setIcon(QIcon("images/icons/home.png"))
        self.main_window.ui.btn_dashboard.setIcon(QIcon("images/icons/dashboard.png"))
        self.main_window.ui.btn_data.setIcon(QIcon("images/icons/database.png"))
        self.main_window.ui.btn_anlysis.setIcon(QIcon("images/icons/analytics.png"))
        self.main_window.ui.btn_chat.setIcon(QIcon("images/icons/chat.png"))
        self.main_window.ui.btn_predictions.setIcon(QIcon("images/icons/chart-line.png"))
        
        # Update action icons
        self.main_window.ui.openfile_btn.setIcon(QIcon("images/icons/upload.png"))
        self.main_window.ui.clean_data_btn.setIcon(QIcon("images/icons/clean.png"))
        self.main_window.ui.send_btn.setIcon(QIcon("images/icons/send.png"))
        self.main_window.ui.predict_btn.setIcon(QIcon("images/icons/chart-line.png"))
        
    def show_loading(self, message="Loading..."):
        """Show loading overlay with custom message"""
        self.loading_overlay.label.setText(message)
        self.loading_overlay.show()
        
    def hide_loading(self):
        """Hide loading overlay"""
        self.loading_overlay.hide()
