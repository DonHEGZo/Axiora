import sys
import os
import platform
import ctypes
import matplotlib.pyplot as plt
import uuid
import markdown
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Import Qt modules first
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QHeaderView, QLabel, 
    QVBoxLayout, QSizePolicy, QPushButton, QGridLayout, QWidget, QFrame, QCheckBox, QTableWidget, QTableWidgetItem, QScrollArea, QHBoxLayout, QMessageBox, QTabWidget, QFileDialog
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QCursor
from PySide6.QtCore import Qt, QSize
import selenium

# Import our modules
from modules.app_settings import Settings
from modules.ui_functions import UIFunctions
from Functions import GuiFunctions
from uiEXT.login.LoginWindow import LoginWindow
from langchain_core.messages import HumanMessage, AIMessage
from OprFuncs import read_file
from modules.ui_main import Ui_MainWindow
from uiEXT.ColDialog import ColDialog
from time_series_forecaster import time_series_forecaster
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

def resizeEvent(self, event):
    new_size = max(10, self.width() // 100)  
    self.adjust_font_size(new_size)
    event.accept()

# IMPORT / GUI AND MODULES AND WIDGETS
# ///////////////////////////////////////////////////////////////
os.environ["QT_FONT_DPI"] = "110" # FIX Problem for High DPI and Scale above 100%

# SET AS GLOBAL WIDGETS
# ///////////////////////////////////////////////////////////////
widgets = None

class MainWindow(QMainWindow):
    def __init__(self, user_id):
        QMainWindow.__init__(self)
        self.user_id = uuid.UUID(user_id)  # Convert string back to UUID
        # SET AS GLOBAL WIDGETS
        # ///////////////////////////////////////////////////////////////
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        global widgets
        widgets = self.ui
        
        # Initialize app functions after UI setup
        self.app_functions = GuiFunctions(self, self.user_id)
        self.load_oldreports()
        
        # Fix path separators for Windows - use forward slashes
        self.report_logo = "images/icons/cil-report-colored-1.png"
        
        # USE CUSTOM TITLE BAR | USE AS "False" FOR MAC OR LINUX
        # ///////////////////////////////////////////////////////////////
        if platform.system() == "Windows":
            Settings.ENABLE_CUSTOM_TITLE_BAR = True
        else:
            Settings.ENABLE_CUSTOM_TITLE_BAR = False

        # APP NAME
        # ///////////////////////////////////////////////////////////////
        title = "Axiora"
        description = "Axiora - Automated BI Analysis"
        # APPLY TEXTS
        self.setWindowTitle(title)
        widgets.titleRightInfo.setText(description)

        # TOGGLE MENU
        # ///////////////////////////////////////////////////////////////
        widgets.toggleButton.clicked.connect(lambda: UIFunctions.toggleMenu(self, True))

        # SET UI DEFINITIONS
        # ///////////////////////////////////////////////////////////////
        UIFunctions.uiDefinitions(self)

        # Set icons for buttons
        #widgets.btn_chat.setIcon(QIcon(r"images\icons\chat.png"))
        
        # Set the logo
        logo_path = os.path.join(os.path.dirname(__file__), "images", "images", "IMG_20250226_011441_442.jpg")
        logo_pixmap = QPixmap(logo_path)
        if not logo_pixmap.isNull():
            scaled_pixmap = logo_pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Create a QLabel for the logo in the topLogoInfo frame
            logo_label = QLabel()
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignCenter)
            # Add the label to the topLogoInfo frame
            layout = QVBoxLayout(widgets.topLogoInfo)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(logo_label)
            # Set the logo in the main label if it exists
            if hasattr(widgets, 'label'):
                widgets.label.setPixmap(scaled_pixmap)
        else:
            print(f"Could not load logo from {logo_path}")

        # QTableWidget PARAMETERS
        # ///////////////////////////////////////////////////////////////
        widgets.tableData.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # BUTTONS CLICK
        # ///////////////////////////////////////////////////////////////

        # LEFT MENUS
        widgets.btn_chat.clicked.connect(self.buttonClick)
        widgets.btn_data.clicked.connect(self.buttonClick)
        widgets.btn_anlysis.clicked.connect(self.buttonClick)
        widgets.btn_new.clicked.connect(self.buttonClick)
        widgets.btn_home.clicked.connect(self.buttonClick)
        widgets.btn_dashboard.clicked.connect(self.buttonClick)
        widgets.btn_predictions.clicked.connect(self.buttonClick)
        widgets.btn_print.clicked.connect(self.buttonClick)
        
        
        # Set icons for buttons
        #widgets.btn_home.setIcon(QIcon("images/icons/chat.png"))
        widgets.btn_data.setIcon(QIcon("images/icons/data_icon.png"))
        widgets.btn_anlysis.setIcon(QIcon("images/icons/new_icon.png"))

        # EXTRA LEFT BOX
        def openCloseLeftBox():
            UIFunctions.toggleLeftBox(self, True)
        widgets.toggleLeftBox.clicked.connect(openCloseLeftBox)
        widgets.extraCloseColumnBtn.clicked.connect(openCloseLeftBox)

        # EXTRA RIGHT BOX
        def openCloseRightBox():
            UIFunctions.toggleRightBox(self, True)
        widgets.optionsTopBtn.clicked.connect(openCloseRightBox)

        # SHOW APP
        # ///////////////////////////////////////////////////////////////
        self.show()

        # SET CUSTOM THEME
        # ///////////////////////////////////////////////////////////////
        useCustomTheme = True
        themeFile = "themes/py_dracula_light.qss"

        # SET THEME AND HACKS
        if useCustomTheme:
            # LOAD AND APPLY STYLE
            self.applyTheme(themeFile)

            # SET HACKS
            #AppFunctions.setThemeHack(self)

        # SET HOME PAGE AND SELECT MENU
        # ///////////////////////////////////////////////////////////////
        widgets.stackedWidget.setCurrentWidget(widgets.home_2)
        username = self.app_functions.db.get_user_name(self.user_id)
        widgets.btn_home.setStyleSheet(UIFunctions.selectMenu(widgets.btn_home.styleSheet()))

        # Connect column header click event
        widgets.tableData.horizontalHeader().sectionClicked.connect(self.show_column_dialog)

    def load_oldreports(self):
        # Create a grid layout for the home page
        if hasattr(self.ui, 'home_2'):
            # Clear existing layout if any
            if self.ui.home_2.layout():
                QWidget().setLayout(self.ui.home_2.layout())
            
            # Create new grid layout
            grid_layout = QGridLayout(self.ui.home_2)
            grid_layout.setSpacing(20)
            grid_layout.setContentsMargins(20, 20, 20, 20)

            # Create welcome section (top left)
            welcome_widget = QFrame()
            welcome_widget.setStyleSheet("""
                QFrame {
                    background-color: #2c313c;
                    border: 2px solid #3d4451;
                    border-radius: 10px;
                }
            """)
            welcome_layout = QVBoxLayout(welcome_widget)
            welcome_layout.setContentsMargins(20, 20, 20, 20)
            welcome_layout.setSpacing(15)

            # Add welcome message
            username = self.app_functions.db.get_user_name(self.user_id)
            welcome_title = QLabel(f"Welcome back, {username}!")
            welcome_title.setStyleSheet("""
                QLabel {
                    color: #00a6fb;
                    font-size: 24px;
                    font-weight: bold;
                }
            """)
            welcome_layout.addWidget(welcome_title)

            # Add date and time
            from datetime import datetime
            current_time = datetime.now().strftime("%B %d, %Y %H:%M")
            time_label = QLabel(current_time)
            time_label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
            """)
            welcome_layout.addWidget(time_label)

            # Add app description
            description_frame = QFrame()
            description_frame.setStyleSheet("""
                QFrame {
                    background-color: #1b1e23;
                    border-radius: 8px;
                    padding: 15px;
                }
            """)
            description_layout = QVBoxLayout(description_frame)
            description_layout.setSpacing(10)

            # Title
            desc_title = QLabel("About Axiora")
            desc_title.setStyleSheet("""
                QLabel {
                    color: #00a6fb;
                    font-size: 18px;
                    font-weight: bold;
                }
            """)
            desc_title.setAlignment(Qt.AlignCenter)
            description_layout.addWidget(desc_title)

            # Description text
            desc_text = QLabel(
                "Axiora is an advanced Business Intelligence and Analytics platform that helps you:\n\n"
                "• Analyze and visualize your data with powerful tools\n"
                "• Generate automated insights and reports\n"
                "• Create accurate predictions and forecasts\n"
                "• Make data-driven decisions with confidence\n\n"
                "Get started by creating a new report or exploring your existing analyses."
            )
            desc_text.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                    line-height: 1.5;
                }
            """)
            desc_text.setWordWrap(True)
            description_layout.addWidget(desc_text)

            welcome_layout.addWidget(description_frame)

            # Add quick stats
            stats_frame = QFrame()
            stats_frame.setStyleSheet("""
                QFrame {
                    background-color: #1b1e23;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            stats_layout = QHBoxLayout(stats_frame)
            stats_layout.setSpacing(20)

            # Get total reports count
            total_reports = len(self.app_functions.db.get_user_reports(self.user_id))
            
            # Create stat boxes
            stats = [
                ("Total Reports", str(total_reports), "📊"),
                ("Active Projects", "3", "📈"),
                ("Recent Analysis", "5", "📉")
            ]

            for title, value, icon in stats:
                stat_box = QFrame()
                stat_box.setStyleSheet("""
                    QFrame {
                        background-color: #2c313c;
                        border-radius: 8px;
                        padding: 15px;
                    }
                """)
                stat_layout = QVBoxLayout(stat_box)
                
                # Icon and value
                value_label = QLabel(f"{icon} {value}")
                value_label.setStyleSheet("""
                    QLabel {
                        color: #00a6fb;
                        font-size: 24px;
                        font-weight: bold;
                    }
                """)
                value_label.setAlignment(Qt.AlignCenter)
                stat_layout.addWidget(value_label)
                
                # Title
                title_label = QLabel(title)
                title_label.setStyleSheet("""
                    QLabel {
                        color: #ffffff;
                        font-size: 14px;
                    }
                """)
                title_label.setAlignment(Qt.AlignCenter)
                stat_layout.addWidget(title_label)
                
                stats_layout.addWidget(stat_box)

            welcome_layout.addWidget(stats_frame)
            welcome_layout.addStretch()

            # Add welcome widget to top left
            grid_layout.addWidget(welcome_widget, 0, 0)

            # Create reports container for top right
            reports_container = QFrame()
            reports_container.setStyleSheet("""
                QFrame {
                    background-color: #2c313c;
                    border: 2px solid #3d4451;
                    border-radius: 10px;
                }
            """)
            reports_layout = QVBoxLayout(reports_container)
            reports_layout.setSpacing(15)
            reports_layout.setContentsMargins(20, 20, 20, 20)

            # Add title
            title_label = QLabel("Your Reports")
            title_label.setStyleSheet("""
                QLabel {
                    color: #00a6fb;
                    font-size: 20px;
                    font-weight: bold;
                }
            """)
            title_label.setAlignment(Qt.AlignCenter)
            reports_layout.addWidget(title_label)

            # Add reports scroll area
            reports_scroll = QScrollArea()
            reports_scroll.setWidgetResizable(True)
            reports_scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: transparent;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #1b1e23;
                    width: 8px;
                    margin: 0;
                }
                QScrollBar::handle:vertical {
                    background-color: #3d4451;
                    min-height: 30px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #00a6fb;
                }
            """)
            
            reports_widget = QWidget()
            reports_widget_layout = QVBoxLayout(reports_widget)
            reports_widget_layout.setSpacing(10)
            reports_widget_layout.setContentsMargins(0, 0, 0, 0)

            reports = self.app_functions.db.get_user_reports(self.user_id)
            for report in reports:
                report_btn = QPushButton()
                report_btn.setObjectName(report['name'])
                report_btn.setMinimumHeight(40)
                report_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                report_btn.setText(report['name'])
                report_btn.setProperty("report_id", report['id'])
                report_btn.setProperty("report_name", report['name'])
                
                # Set button style to match dark theme
                report_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2c313c;
                        color: #ffffff;
                        border: 2px solid #3d4451;
                        border-radius: 4px;
                        padding: 5px 10px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #1b1e23;
                        border-color: #00a6fb;
                        color: #00a6fb;
                    }
                """)
                
                # Add icon
                report_logo = "images/icons/cil-report-colored-1.png"
                pixmap_report_logo = QPixmap(report_logo)
                if not pixmap_report_logo.isNull():
                    scaled_pixmap = pixmap_report_logo.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    report_btn.setIcon(QIcon(scaled_pixmap))
                    report_btn.setIconSize(QSize(24, 24))
                
                report_btn.clicked.connect(self.report_button_clicked)
                reports_widget_layout.addWidget(report_btn)

            reports_widget_layout.addStretch()
            reports_scroll.setWidget(reports_widget)
            reports_layout.addWidget(reports_scroll)

            # Add reports container to top right
            grid_layout.addWidget(reports_container, 0, 1)

            # Set row and column stretch factors
            grid_layout.setRowStretch(0, 1)  # Top row
            grid_layout.setColumnStretch(0, 1)  # Left column
            grid_layout.setColumnStretch(1, 1)  # Right column

    def report_button_clicked(self):
        btn = self.sender()
        report_id = btn.property("report_id")
        report_name = btn.property("report_name")
        print(f"Report '{report_name}' (ID: {report_id}) clicked!")
        self.load_report(report_id)
    
    def load_report(self,report_id):
        self._clear_chat_display()
        self._clear_questions()
        self.app_functions.reportID = report_id
        report_dataset = self.app_functions.db.get_report_dataset(report_id)
        self.app_functions.datasetID = report_dataset
        self.app_functions.dname = os.path.basename(report_dataset)
        self.app_functions.rname = os.path.splitext(os.path.basename(report_dataset))[0]
        self.app_functions.df = read_file(report_dataset)
        self.app_functions._analyzer_attributes()
        self.app_functions._show_df()
        summary = self.app_functions.db.get_report_summary(report_id)
        if summary:
            self.app_functions._update_summary_text(summary)
        else: 
            self.ui.summary_text.setText("")
        questions = self.app_functions.db.get_report_questions(report_id)
        if questions:
            self.app_functions.g_questions = questions
            self.app_functions._ques_add()
        chat_history = self.app_functions.db.get_report_chat(report_id)
        if chat_history:
            for prompt, response, _ in chat_history:
                if prompt:
                    self.app_functions._add_user_message(prompt)
                    if response:
                        self.app_functions._add_ai_message(response)
        report_memory = self.app_functions.db.get_report_memory(report_id)
        if report_memory:
            for prompt, response, _ in report_memory:
                if prompt:
                    self.app_functions.analyzer.memory.append(HumanMessage(content=prompt))
                    if response:
                        self.app_functions.analyzer.memory.append(AIMessage(content=response))
        
        # Get and display charts
        chart_paths = self.app_functions.db.get_report_charts(report_id)
        if chart_paths:
            self.app_functions.chart_paths = chart_paths
            self.app_functions.display_current_chart()

        # Load and display forecasting data if it exists
        forecasting_data = self.app_functions.db.get_forecasting(report_id)
        if forecasting_data:
            # Create a container for the predictions page content
            content_container = QWidget()
            content_layout = QVBoxLayout(content_container)
            content_layout.setSpacing(20)
            content_layout.setContentsMargins(20, 20, 20, 20)
            
            # Create and add the feature DataFrame table
            feature_table = QTableWidget()
            feature_table.setColumnCount(len(forecasting_data['predicted_df'].columns))
            feature_table.setRowCount(len(forecasting_data['predicted_df']))
            feature_table.setHorizontalHeaderLabels(forecasting_data['predicted_df'].columns)
            
            # Fill the table with data
            for i in range(len(forecasting_data['predicted_df'])):
                for j in range(len(forecasting_data['predicted_df'].columns)):
                    item = QTableWidgetItem(str(forecasting_data['predicted_df'].iloc[i, j]))
                    feature_table.setItem(i, j, item)
            
            # Set table properties
            feature_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            feature_table.setMinimumHeight(200)
            feature_table.setMaximumHeight(400)
            feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            feature_table.setAlternatingRowColors(True)
            feature_table.setStyleSheet("""
                QTableWidget {
                    background-color: #2c313c;
                    alternate-background-color: #1b1e23;
                    gridline-color: #3d4451;
                    border: 1px solid #3d4451;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #1b1e23;
                    color: #00a6fb;
                    padding: 4px;
                    border: 1px solid #3d4451;
                    font-weight: bold;
                }
                QTableWidget::item {
                    padding: 5px;
                }
                QTableWidget::item:selected {
                    background-color: #00a6fb;
                    color: #ffffff;
                }
            """)
            
            # Add table to content layout
            content_layout.addWidget(feature_table)
            
            # Create a container for the plots with proper styling
            plot_container = QFrame()
            plot_container.setStyleSheet("""
                QFrame {
                    background-color: #2c313c;
                    border: 2px solid #3d4451;
                    border-radius: 10px;
                }
            """)
            plot_layout = QGridLayout(plot_container)
            plot_layout.setSpacing(20)
            plot_layout.setContentsMargins(20, 20, 20, 20)
            
            # Get forecasting data from database
            if hasattr(self.app_functions, 'reportID'):
                forecasting_data = self.app_functions.db.get_forecasting(self.app_functions.reportID)
                if forecasting_data and 'charts_path' in forecasting_data:
                    # Load and display charts from the charts directory
                    charts_dir = forecasting_data['charts_path']
                    if os.path.exists(charts_dir):
                        chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
                        for i, chart_file in enumerate(chart_files):
                            chart_path = os.path.join(charts_dir, chart_file)
                            if os.path.exists(chart_path):
                                # Create a frame for each chart section
                                chart_section = QFrame()
                                chart_section.setStyleSheet("""
                                    QFrame {
                                        background-color: #1b1e23;
                                        border: 2px solid #3d4451;
                                        border-radius: 10px;
                                    }
                                """)
                                chart_section.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                                chart_section.setMinimumSize(800, 600)
                                chart_section_layout = QVBoxLayout(chart_section)
                                chart_section_layout.setContentsMargins(0, 0, 0, 0)
                                chart_section_layout.setSpacing(0)

                                # Add title label
                                title = QLabel()
                                if i == 0:
                                    title.setText("1. Time Series Overview")
                                elif i == 1:
                                    title.setText("2. Feature Importance Analysis")
                                elif i == 2:
                                    title.setText("3. Actual vs Predicted Values")
                                elif i == 3:
                                    title.setText("4. Model Performance (R² Plot)")
                                
                                title.setStyleSheet("""
                                    QLabel {
                                        color: #00a6fb;
                                        font-size: 16px;
                                        font-weight: bold;
                                        padding: 15px;
                                        background-color: #2c313c;
                                        border-top-left-radius: 8px;
                                        border-top-right-radius: 8px;
                                        border-bottom: 2px solid #3d4451;
                                    }
                                """)
                                title.setAlignment(Qt.AlignCenter)
                                title.setFixedHeight(50)
                                chart_section_layout.addWidget(title)

                                # Create chart content widget with dark background
                                chart_content = QWidget()
                                chart_content.setStyleSheet("background-color: #1b1e23;")
                                chart_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                                chart_content_layout = QVBoxLayout(chart_content)
                                chart_content_layout.setContentsMargins(0, 0, 0, 0)
                                chart_content_layout.setSpacing(0)

                                # Chart image using QLabel for scaling
                                chart_label = QLabel()
                                chart_label.setAlignment(Qt.AlignCenter)
                                chart_label.setStyleSheet("background-color: #1b1e23; border: none;")
                                chart_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                                chart_pixmap = QPixmap(chart_path)
                                chart_label.setPixmap(chart_pixmap)
                                chart_label.setScaledContents(True)
                                chart_content_layout.addWidget(chart_label, stretch=1)

                                # Create scroll area with proper sizing
                                chart_scroll = QScrollArea()
                                chart_scroll.setStyleSheet("""
                                    QScrollArea {
                                        border: none;
                                        background-color: #1b1e23;
                                    }
                                    QScrollBar:vertical {
                                        border: none;
                                        background: #1b1e23;
                                        width: 8px;
                                        margin: 0;
                                    }
                                    QScrollBar::handle:vertical {
                                        background-color: #3d4451;
                                        min-height: 30px;
                                        border-radius: 4px;
                                    }
                                    QScrollBar::handle:vertical:hover {
                                        background-color: #00a6fb;
                                    }
                                    QScrollBar:horizontal {
                                        border: none;
                                        background: #1b1e23;
                                        height: 8px;
                                        margin: 0;
                                    }
                                    QScrollBar::handle:horizontal {
                                        background-color: #3d4451;
                                        min-width: 30px;
                                        border-radius: 4px;
                                    }
                                    QScrollBar::handle:horizontal:hover {
                                        background-color: #00a6fb;
                                    }
                                """)
                                chart_scroll.setWidget(chart_content)
                                chart_scroll.setWidgetResizable(True)
                                chart_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                                chart_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                                chart_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                                chart_section_layout.addWidget(chart_scroll)

                                # Position the chart sections in the grid with proper spacing
                                plot_layout.setSpacing(10)
                                plot_layout.setContentsMargins(10, 10, 10, 10)
                                if i == 0:  # Time Series Overview
                                    plot_layout.addWidget(chart_section, 0, 0)
                                elif i == 1:  # Feature Importance
                                    plot_layout.addWidget(chart_section, 0, 1)
                                elif i == 2:  # Actual vs Predicted
                                    plot_layout.addWidget(chart_section, 1, 0)
                                elif i == 3:  # R² Plot
                                    plot_layout.addWidget(chart_section, 1, 1)
                                    
                                    # Add metrics section after the last chart
                                    metrics_frame = QFrame()
                                    metrics_frame.setStyleSheet("""
                                        QFrame {
                                            background-color: #2c313c;
                                            border: 2px solid #3d4451;
                                            border-radius: 10px;
                                            margin-top: 10px;
                                        }
                                    """)
                                    metrics_layout = QVBoxLayout(metrics_frame)
                                    metrics_layout.setContentsMargins(20, 15, 20, 15)
                                    metrics_layout.setSpacing(10)

                                    # Title for metrics section
                                    metrics_title = QLabel("Final Model Performance Metrics")
                                    metrics_title.setStyleSheet("""
                                        QLabel {
                                            color: #00a6fb;
                                            font-size: 18px;
                                            font-weight: bold;
                                            padding: 5px;
                                        }
                                    """)
                                    metrics_title.setAlignment(Qt.AlignCenter)
                                    metrics_layout.addWidget(metrics_title)

                                    # R² Score Label
                                    r2_value = forecasting_data.get('r2')
                                    r2_text = f"R² Score on Test set: {r2_value:.4f}" if isinstance(r2_value, (int, float)) else "R² Score on Test set: N/A"
                                    r2_label = QLabel(r2_text)
                                    r2_label.setStyleSheet("""
                                        QLabel {
                                            color: #ffffff;
                                            font-size: 16px;
                                            font-weight: bold;
                                            padding: 5px;
                                        }
                                    """)
                                    r2_label.setAlignment(Qt.AlignCenter)
                                    metrics_layout.addWidget(r2_label)

                                    # RMSE Score Label
                                    rmse_value = forecasting_data.get('rmse')
                                    rmse_text = f"RMSE Score on Test set: {rmse_value:.2f}" if isinstance(rmse_value, (int, float)) else "RMSE Score on Test set: N/A"
                                    rmse_label = QLabel(rmse_text)
                                    rmse_label.setStyleSheet("""
                                        QLabel {
                                            color: #ffffff;
                                            font-size: 16px;
                                            font-weight: bold;
                                            padding: 5px;
                                        }
                                    """)
                                    rmse_label.setAlignment(Qt.AlignCenter)
                                    metrics_layout.addWidget(rmse_label)

                                    # Add metrics frame to layout
                                    plot_layout.addWidget(metrics_frame, 2, 0, 1, 2)

            # Create main scroll area for all charts
            main_scroll = QScrollArea()
            main_scroll.setWidget(plot_container)
            main_scroll.setWidgetResizable(True)
            main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            main_scroll.setStyleSheet("""
                QScrollArea {
                    border: none;
                    background-color: #2c313c;
                }
                QScrollBar:vertical {
                    border: none;
                    background: #1b1e23;
                    width: 14px;
                    margin: 15px 0 15px 0;
                    border-radius: 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: #3d4451;
                    min-height: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: #00a6fb;
                }
                QScrollBar:horizontal {
                    border: none;
                    background: #1b1e23;
                    height: 14px;
                    margin: 0px 15px 0 15px;
                    border-radius: 0px;
                }
                QScrollBar::handle:horizontal {
                    background-color: #3d4451;
                    min-width: 30px;
                    border-radius: 7px;
                }
                QScrollBar::handle:horizontal:hover {
                    background-color: #00a6fb;
                }
            """)
            
            # Add the main scroll area to the content layout
            content_layout.addWidget(main_scroll)
            
            # Add the content container to the predictions page
            if hasattr(widgets, 'predictions_page'):
                # Get the existing layout
                existing_layout = widgets.predictions_page.layout()
                if existing_layout is None:
                    existing_layout = QVBoxLayout(widgets.predictions_page)
                    existing_layout.setSpacing(20)
                    existing_layout.setContentsMargins(20, 20, 20, 20)
                
                # Create a scroll area for the entire page
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                scroll_area.setWidget(content_container)
                
                # Add the scroll area to the existing layout
                existing_layout.addWidget(scroll_area)

    def _clear_chat_display(self):
        while self.ui.chat_layout.count() > 0:
            item = self.ui.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            # If it's a layout or spacer, remove it
            elif item.layout():
                self.clear_layout(item.layout())

    def _clear_questions(self):
        scroll_contents = self.ui.scrollAreaWidgetContents
        if layout := scroll_contents.layout():  # Python 3.8+ (walrus operator)
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()


    # You can add more logic here, such as loading the report data, etc.
    def applyTheme(self, themeFile):
        with open(themeFile, "r") as file:
            self.setStyleSheet(file.read())

    # BUTTONS CLICK
    # Post here your functions for clicked buttons
    # ///////////////////////////////////////////////////////////////
    def buttonClick(self):
        # GET BUTTON CLICKED
        btn = self.sender()
        btnName = btn.objectName()

        print(f"Button clicked: {btnName}")  # Debug print

        if btnName == "btn_home":
            widgets.stackedWidget.setCurrentWidget(widgets.home_2)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_dashboard":
            widgets.stackedWidget.setCurrentWidget(widgets.page)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_predictions":
            print("Attempting to switch to predictions page...")  # Debug print
            try:
                widgets.stackedWidget.setCurrentWidget(widgets.predictions_page)
                print("Successfully switched to predictions page")  # Debug print
                UIFunctions.resetStyle(self, btnName)
                btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))
                
                # Update prediction controls with current dataset columns
                if hasattr(self.app_functions, 'df'):
                    print("Updating prediction controls with dataset columns")  # Debug print
                    df = self.app_functions.df
                    
                    # Update target column combo
                    widgets.target_col_combo.clear()
                    widgets.target_col_combo.addItems(df.columns)
                    
                    # Update date column combos
                    all_columns = list(df.columns)
                    
                    # Update single date column combo
                    widgets.date_col_combo.clear()
                    widgets.date_col_combo.addItems(all_columns)
                    # Try to select a date column by default
                    for i, col in enumerate(all_columns):
                        if 'date' in col.lower():
                            widgets.date_col_combo.setCurrentIndex(i)
                            break
                    
                    # Update year/month/day combos
                    widgets.year_combo.clear()
                    widgets.month_combo.clear()
                    widgets.day_combo.clear()
                    
                    widgets.year_combo.addItems(all_columns)
                    widgets.month_combo.addItems(all_columns)
                    widgets.day_combo.addItems(all_columns)
                    
                    # Try to select appropriate columns by default
                    for i, col in enumerate(all_columns):
                        col_lower = col.lower()
                        if 'year' in col_lower:
                            widgets.year_combo.setCurrentIndex(i)
                        elif 'month' in col_lower:
                            widgets.month_combo.setCurrentIndex(i)
                        elif 'day' in col_lower:
                            widgets.day_combo.setCurrentIndex(i)
                    
                    # Connect radio buttons to stack switching
                    widgets.single_date_radio.toggled.connect(lambda checked: 
                        widgets.date_stack.setCurrentWidget(widgets.single_date_page if checked 
                        else widgets.multi_date_page))
                    
                    # Connect predict button
                    try:
                        widgets.predict_btn.clicked.disconnect()
                    except:
                        pass
                    widgets.predict_btn.clicked.connect(self.generate_predictions)
            except Exception as e:
                print(f"Error switching to predictions page: {str(e)}")  # Debug print

        elif btnName == "btn_print":
            self.generate_pdf_report()
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_chat":
            widgets.stackedWidget.setCurrentWidget(widgets.home)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_data":
            widgets.stackedWidget.setCurrentWidget(widgets.data_page)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_anlysis":
            widgets.stackedWidget.setCurrentWidget(widgets.new_page)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        elif btnName == "btn_new":
            print("New Report BTN clicked!")
            # Clear all user output and start fresh
            self._clear_chat_display()
            self._clear_questions()
            
            # Clear the DataFrame and related attributes
            self.app_functions.df = None
            self.app_functions.datasetID = None
            self.app_functions.dname = None
            self.app_functions.rname = None
            self.app_functions.reportID = None
            
            # Clear the summary text
            self.ui.summary_text.setText("")
            
            # Clear the table data
            self.ui.tableData.clear()
            self.ui.tableData.setRowCount(0)
            self.ui.tableData.setColumnCount(0)
            
            # Clear any existing charts
            if hasattr(self.app_functions, 'chart_paths'):
                self.app_functions.chart_paths = []
            
            # Clear the predictions page if it exists
            if hasattr(widgets, 'predictions_page'):
                # Remove all widgets from the predictions page
                layout = widgets.predictions_page.layout()
                if layout:
                    while layout.count():
                        item = layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
            
            # Clear the analyzer memory
            if hasattr(self.app_functions, 'analyzer'):
                self.app_functions.analyzer.memory = []
            
            # Clear any stored questions
            if hasattr(self.app_functions, 'g_questions'):
                self.app_functions.g_questions = []
            
            # Switch to the data page for new report setup
            widgets.stackedWidget.setCurrentWidget(widgets.data_page)
            UIFunctions.resetStyle(self, btnName)
            btn.setStyleSheet(UIFunctions.selectMenu(btn.styleSheet()))

        # PRINT BTN NAME
        print(f'Button "{btnName}" pressed!')

    # RESIZE EVENTS
    # ///////////////////////////////////////////////////////////////
    def resizeEvent(self, event):
        # Update Size Grips
        UIFunctions.resize_grips(self)

    # MOUSE CLICK EVENTS
    # ///////////////////////////////////////////////////////////////
    def mousePressEvent(self, event):
        # SET DRAG POS WINDOW
        self.dragPos = event.scenePosition().toPoint()

        # PRINT MOUSE EVENTS
        if event.buttons() == Qt.LeftButton:
            print('Mouse click: LEFT CLICK')
        if event.buttons() == Qt.RightButton:
            print('Mouse click: RIGHT CLICK')

    def show_column_dialog(self, column_index):
        """Show the column dialog when a column header is clicked"""
        column_name = widgets.tableData.horizontalHeaderItem(column_index).text()
        dialog = ColDialog(self, self.app_functions.df, column_name)
        dialog.setWindowTitle(f"Column Options - {column_name}")
        dialog.exec_()

    def show_loading_indicator(self, message="Generating predictions..."):
        if hasattr(self, '_loading_label') and self._loading_label:
            self._loading_label.setText(message)
            self._loading_label.show()
        else:
            self._loading_label = QLabel(message)
            self._loading_label.setAlignment(Qt.AlignCenter)
            self._loading_label.setStyleSheet("color: #00a6fb; font-size: 18px; font-weight: bold; padding: 20px;")
            if hasattr(widgets, 'predictions_page'):
                layout = widgets.predictions_page.layout()
                if layout:
                    layout.insertWidget(1, self._loading_label)

    def hide_loading_indicator(self):
        if hasattr(self, '_loading_label') and self._loading_label:
            self._loading_label.hide()

    def show_error_message(self, message):
        if hasattr(self, '_error_label') and self._error_label:
            self._error_label.setText(message)
            self._error_label.show()
        else:
            self._error_label = QLabel(message)
            self._error_label.setAlignment(Qt.AlignCenter)
            self._error_label.setStyleSheet("color: #ff5555; font-size: 16px; font-weight: bold; padding: 20px;")
            if hasattr(widgets, 'predictions_page'):
                layout = widgets.predictions_page.layout()
                if layout:
                    layout.insertWidget(2, self._error_label)

    def hide_error_message(self):
        if hasattr(self, '_error_label') and self._error_label:
            self._error_label.hide()

    def export_forecast_table(self, table_widget):
        path, _ = QFileDialog.getSaveFileName(self, "Export Forecast Table", "forecast.csv", "CSV Files (*.csv)")
        if path:
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                headers = [table_widget.horizontalHeaderItem(i).text() for i in range(table_widget.columnCount())]
                writer.writerow(headers)
                for row in range(table_widget.rowCount()):
                    row_data = [table_widget.item(row, col).text() if table_widget.item(row, col) else '' for col in range(table_widget.columnCount())]
                    writer.writerow(row_data)

    def update_forecasting_results(self, predictions, plots, metrics, chart_paths, r2_score, rmse_score, charts_dir):
        # Remove previous results (except controls)
        if hasattr(widgets, 'predictions_page'):
            existing_layout = widgets.predictions_page.layout()
            if existing_layout:
                # Keep prediction_controls
                prediction_controls = None
                for i in range(existing_layout.count()):
                    widget = existing_layout.itemAt(i).widget()
                    if widget and widget.objectName() == "prediction_controls":
                        prediction_controls = widget
                        break
                # Remove all widgets except controls
                for i in reversed(range(existing_layout.count())):
                    widget = existing_layout.itemAt(i).widget()
                    if widget and widget != prediction_controls:
                        widget.deleteLater()
                if prediction_controls:
                    existing_layout.addWidget(prediction_controls)

        # Create forecast table
        feature_table = QTableWidget()
        feature_table.setColumnCount(len(predictions.columns))
        feature_table.setRowCount(len(predictions))
        feature_table.setHorizontalHeaderLabels(predictions.columns)
        for i in range(len(predictions)):
            for j in range(len(predictions.columns)):
                item = QTableWidgetItem(str(predictions.iloc[i, j]))
                feature_table.setItem(i, j, item)
        feature_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        feature_table.setMinimumHeight(200)
        feature_table.setMaximumHeight(400)
        feature_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        feature_table.setAlternatingRowColors(True)
        feature_table.setStyleSheet("""
            QTableWidget { background-color: #2c313c; alternate-background-color: #1b1e23; gridline-color: #3d4451; border: 1px solid #3d4451; color: #ffffff; }
            QHeaderView::section { background-color: #1b1e23; color: #00a6fb; padding: 4px; border: 1px solid #3d4451; font-weight: bold; }
            QTableWidget::item { padding: 5px; }
            QTableWidget::item:selected { background-color: #00a6fb; color: #ffffff; }
        """)
        # Add export button
        export_btn = QPushButton("Export Forecast Table")
        export_btn.setStyleSheet("background-color: #00a6fb; color: white; border-radius: 5px; padding: 6px 12px; font-weight: bold;")
        export_btn.clicked.connect(lambda: self.export_forecast_table(feature_table))
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)
        table_layout.addWidget(feature_table)
        table_layout.addWidget(export_btn, alignment=Qt.AlignRight)

        # --- Redesigned Charts & Metrics Tab ---
        charts_metrics_container = QWidget()
        charts_metrics_layout = QVBoxLayout(charts_metrics_container)
        charts_metrics_layout.setContentsMargins(20, 20, 20, 20)
        charts_metrics_layout.setSpacing(24)

        # Metrics Card Row
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(24)
        # Card for R2
        r2_card = QFrame()
        r2_card.setStyleSheet("""
            QFrame { background-color: #232733; border-radius: 14px; border: 1.5px solid #00a6fb; box-shadow: 0 2px 12px #00000033; }
        """)
        r2_card.setMinimumWidth(200)
        r2_layout = QVBoxLayout(r2_card)
        r2_layout.setContentsMargins(18, 18, 18, 18)
        r2_icon = QLabel("📈")
        r2_icon.setAlignment(Qt.AlignCenter)
        r2_icon.setStyleSheet("font-size: 32px;")
        r2_layout.addWidget(r2_icon)
        r2_title = QLabel("R² Score")
        r2_title.setAlignment(Qt.AlignCenter)
        r2_title.setStyleSheet("color: #00a6fb; font-size: 16px; font-weight: bold;")
        r2_layout.addWidget(r2_title)
        r2_value = QLabel(f"{r2_score:.4f}" if isinstance(r2_score, (int, float)) else "N/A")
        r2_value.setAlignment(Qt.AlignCenter)
        r2_value.setStyleSheet("color: #fff; font-size: 22px; font-weight: bold;")
        r2_layout.addWidget(r2_value)
        metrics_row.addWidget(r2_card)
        # Card for RMSE
        rmse_card = QFrame()
        rmse_card.setStyleSheet("""
            QFrame { background-color: #232733; border-radius: 14px; border: 1.5px solid #ffb347; box-shadow: 0 2px 12px #00000033; }
        """)
        rmse_card.setMinimumWidth(200)
        rmse_layout = QVBoxLayout(rmse_card)
        rmse_layout.setContentsMargins(18, 18, 18, 18)
        rmse_icon = QLabel("📉")
        rmse_icon.setAlignment(Qt.AlignCenter)
        rmse_icon.setStyleSheet("font-size: 32px;")
        rmse_layout.addWidget(rmse_icon)
        rmse_title = QLabel("RMSE")
        rmse_title.setAlignment(Qt.AlignCenter)
        rmse_title.setStyleSheet("color: #ffb347; font-size: 16px; font-weight: bold;")
        rmse_layout.addWidget(rmse_title)
        rmse_value = QLabel(f"{rmse_score:.2f}" if isinstance(rmse_score, (int, float)) else "N/A")
        rmse_value.setAlignment(Qt.AlignCenter)
        rmse_value.setStyleSheet("color: #fff; font-size: 22px; font-weight: bold;")
        rmse_layout.addWidget(rmse_value)
        metrics_row.addWidget(rmse_card)
        metrics_row.addStretch()
        charts_metrics_layout.addLayout(metrics_row)

        # Section Header
        charts_header = QLabel("Forecasting Charts")
        charts_header.setStyleSheet("color: #00a6fb; font-size: 20px; font-weight: bold; margin-top: 10px; margin-bottom: 10px;")
        charts_metrics_layout.addWidget(charts_header)

        # Charts Grid
        charts_grid = QGridLayout()
        charts_grid.setSpacing(24)
        charts_grid.setContentsMargins(0, 0, 0, 0)
        if charts_dir and os.path.exists(charts_dir):
            chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
            for i, chart_file in enumerate(chart_files):
                chart_path = os.path.join(charts_dir, chart_file)
                if os.path.exists(chart_path):
                    chart_card = QFrame()
                    chart_card.setStyleSheet("""
                        QFrame { background-color: #1b1e23; border-radius: 12px; border: 1.5px solid #3d4451; box-shadow: 0 2px 8px #00000022; }
                    """)
                    chart_card.setMinimumSize(400, 320)
                    chart_card_layout = QVBoxLayout(chart_card)
                    chart_card_layout.setContentsMargins(10, 10, 10, 10)
                    chart_card_layout.setSpacing(8)
                    # Chart title
                    chart_titles = [
                        "Time Series Overview",
                        "Feature Importance Analysis",
                        "Actual vs Predicted Values",
                        "Model Performance (R² Plot)"
                    ]
                    title = QLabel(chart_titles[i] if i < len(chart_titles) else f"Chart {i+1}")
                    title.setAlignment(Qt.AlignCenter)
                    title.setStyleSheet("color: #00a6fb; font-size: 15px; font-weight: bold; margin-bottom: 6px;")
                    chart_card_layout.addWidget(title)
                    # Chart image using QLabel for scaling
                    chart_label = QLabel()
                    chart_label.setAlignment(Qt.AlignCenter)
                    chart_label.setStyleSheet("background-color: #1b1e23; border: none;")
                    chart_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    chart_pixmap = QPixmap(chart_path)
                    chart_label.setPixmap(chart_pixmap)
                    chart_label.setScaledContents(True)
                    chart_card_layout.addWidget(chart_label, stretch=1)
                    chart_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    # Add to grid
                    row = i // 2
                    col = i % 2
                    charts_grid.addWidget(chart_card, row, col)
        charts_metrics_layout.addLayout(charts_grid)
        charts_metrics_layout.addStretch()

        # Create tab widget for results
        results_tabs = QTabWidget()
        results_tabs.addTab(table_container, "Forecast Table")

        # --- Add scroll area for Charts & Metrics tab ---
        charts_scroll_area = QScrollArea()
        charts_scroll_area.setWidgetResizable(True)
        charts_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        charts_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        charts_scroll_area.setWidget(charts_metrics_container)
        charts_scroll_area.setStyleSheet("background: transparent; border: none;")
        results_tabs.addTab(charts_scroll_area, "Charts & Metrics")

        # Add to predictions page
        if hasattr(widgets, 'predictions_page'):
            layout = widgets.predictions_page.layout()
            if layout:
                layout.addWidget(results_tabs)

    def generate_predictions(self):
        try:
            self.hide_error_message()
            self.show_loading_indicator()
            if not hasattr(self.app_functions, 'df'):
                self.show_error_message("No dataset loaded!")
                self.hide_loading_indicator()
                return
            # Clear previous predictions but keep the controls
            if hasattr(widgets, 'predictions_page'):
                existing_layout = widgets.predictions_page.layout()
                if existing_layout:
                    prediction_controls = None
                    for i in range(existing_layout.count()):
                        widget = existing_layout.itemAt(i).widget()
                        if widget and widget.objectName() == "prediction_controls":
                            prediction_controls = widget
                            break
                    while existing_layout.count():
                        item = existing_layout.takeAt(0)
                        if item.widget() and item.widget() != prediction_controls:
                            item.widget().deleteLater()
                    if prediction_controls:
                        existing_layout.addWidget(prediction_controls)
            df = self.app_functions.df
            target_col = widgets.target_col_combo.currentText()
            if widgets.single_date_radio.isChecked():
                date_cols = widgets.date_col_combo.currentText()
            else:
                date_cols = [widgets.year_combo.currentText(), widgets.month_combo.currentText(), widgets.day_combo.currentText()]
            horizon = widgets.horizon_spin.value()
            try:
                predictions, plots, metrics = time_series_forecaster(
                    dataframe=df,
                    target_col=target_col,
                    date_cols=date_cols,
                    forecast_horizon=horizon
                )
            except Exception as e:
                self.show_error_message(f"Prediction error: {str(e)}")
                self.hide_loading_indicator()
                return
            forecast_filename = f"forecast_{horizon}_{target_col}.csv"
            forecast_path = os.path.join(self.app_functions.rname, forecast_filename)
            predictions.to_csv(forecast_path, index=False)
            charts_folder = os.path.join(self.app_functions.rname, f"forecast_charts_{horizon}_{target_col}")
            os.makedirs(charts_folder, exist_ok=True)
            chart_paths = []
            for i, plot in enumerate(plots):
                if plot is not None:
                    chart_name = f"chart_{i+1}.png"
                    chart_path = os.path.join(charts_folder, chart_name)
                    plot.savefig(chart_path, bbox_inches='tight', dpi=300)
                    chart_paths.append(chart_path)
                    plt.close(plot)
            r2_score, rmse_score = metrics
            self.app_functions.db.saveForecasting(
                reportID=self.app_functions.reportID,
                target_column=target_col,
                predicted_df=forecast_path,
                rmse=rmse_score,
                r2=r2_score,
                charts_path=charts_folder
            )
            self.update_forecasting_results(predictions, plots, metrics, chart_paths, r2_score, rmse_score, charts_folder)
            self.hide_loading_indicator()
        except Exception as e:
            self.show_error_message(f"Error generating predictions: {str(e)}")
            self.hide_loading_indicator()
            import traceback
            traceback.print_exc()

    def generate_pdf_report(self):
        """Generate a PDF report containing summary, questions, charts, and forecasting data"""
        try:
            if not hasattr(self.app_functions, 'reportID'):
                print("No report loaded!")
                return

            # Create PDF document
            report_name = f"{self.app_functions.rname}_report.pdf"
            doc = SimpleDocTemplate(report_name, pagesize=letter)
            styles = getSampleStyleSheet()
            elements = []

            # Add title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30
            )
            elements.append(Paragraph(f"Report: {self.app_functions.rname}", title_style))
            elements.append(Spacer(1, 20))

            # Add summary section
            if hasattr(self.ui, 'summary_text'):
                summary = self.ui.summary_text.toPlainText()
                if summary:
                    elements.append(Paragraph("Summary", styles['Heading2']))
                    elements.append(Spacer(1, 10))
                    elements.append(Paragraph(summary, styles['Normal']))
                    elements.append(Spacer(1, 20))

            # Add questions section
            if hasattr(self.app_functions, 'g_questions') and self.app_functions.g_questions:
                elements.append(Paragraph("Questions", styles['Heading2']))
                elements.append(Spacer(1, 10))
                for i, question in enumerate(self.app_functions.g_questions, 1):
                    elements.append(Paragraph(f"{i}. {question}", styles['Normal']))
                elements.append(Spacer(1, 20))

            # Add charts section
            if hasattr(self.app_functions, 'chart_paths') and self.app_functions.chart_paths:
                elements.append(Paragraph("Charts", styles['Heading2']))
                elements.append(Spacer(1, 10))
                for chart_path in self.app_functions.chart_paths:
                    if os.path.exists(chart_path):
                        try:
                            # Convert HTML chart to PNG if needed
                            if chart_path.endswith('.html'):
                                # Create a temporary PNG file
                                temp_png = chart_path.replace('.html', '.png')
                                # Use a headless browser to capture the chart
                                from selenium import webdriver
                                from selenium.webdriver.chrome.options import Options
                                options = Options()
                                options.add_argument('--headless')
                                options.add_argument('--disable-gpu')
                                driver = webdriver.Chrome(options=options)
                                driver.get(f'file://{os.path.abspath(chart_path)}')
                                driver.save_screenshot(temp_png)
                                driver.quit()
                                chart_path = temp_png
                            
                            img = Image(chart_path, width=6*inch, height=4*inch)
                            elements.append(img)
                            elements.append(Spacer(1, 20))
                        except Exception as e:
                            print(f"Error adding chart {chart_path}: {str(e)}")
                            continue

            # Add forecasting section
            if hasattr(widgets, 'predictions_page'):
                elements.append(Paragraph("Forecasting", styles['Heading2']))
                elements.append(Spacer(1, 10))
                
                # Get forecasting data from the database
                forecasting_data = self.app_functions.db.get_forecasting(self.app_functions.reportID)
                if forecasting_data:
                    # Add RMSE and R2 scores if available
                    if 'rmse' in forecasting_data and forecasting_data['rmse']:
                        elements.append(Paragraph(f"RMSE Score: {forecasting_data['rmse']}", styles['Normal']))
                    if 'r2' in forecasting_data and forecasting_data['r2']:
                        elements.append(Paragraph(f"R2 Score: {forecasting_data['r2']}", styles['Normal']))
                    
                    # Add predicted DataFrame
                    if 'predicted_df' in forecasting_data and forecasting_data['predicted_df']:
                        try:
                            predicted_df = read_file(forecasting_data['predicted_df'])
                            # Create a table for the predicted DataFrame
                            table_data = [predicted_df.columns.tolist()] + predicted_df.values.tolist()
                            table = Table(table_data)
                            table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 14),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                                ('FONTSIZE', (0, 1), (-1, -1), 12),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black)
                            ]))
                            elements.append(table)
                            elements.append(Spacer(1, 20))
                        except Exception as e:
                            print(f"Error adding predicted DataFrame: {str(e)}")
                    
                    # Add forecasting charts
                    if 'charts_path' in forecasting_data:
                        charts_dir = forecasting_data['charts_path']
                        if os.path.exists(charts_dir):
                            chart_files = [f for f in os.listdir(charts_dir) if f.endswith('.png')]
                            for chart_file in chart_files:
                                chart_path = os.path.join(charts_dir, chart_file)
                                try:
                                    img = Image(chart_path, width=6*inch, height=4*inch)
                                    elements.append(img)
                                    elements.append(Spacer(1, 20))
                                except Exception as e:
                                    print(f"Error adding forecasting chart {chart_path}: {str(e)}")

            # Add recommendations section
            if hasattr(self.ui, 'recommendations_text'):
                recommendations = self.ui.recommendations_text.toPlainText()
                if recommendations:
                    elements.append(Paragraph("Recommendations", styles['Heading2']))
                    elements.append(Spacer(1, 10))
                    elements.append(Paragraph(recommendations, styles['Normal']))
                    elements.append(Spacer(1, 20))

            # Build the PDF
            doc.build(elements)
            print(f"PDF report generated: {report_name}")

        except Exception as e:
            print(f"Error generating PDF report: {str(e)}")
            import traceback
            traceback.print_exc()

def initialize_app():
    """Initialize the application and database"""
    try:
        # Initialize database
        from Axioradb import init_db
        init_db()
        return True
    except Exception as e:
        print(f"Error initializing application: {str(e)}")
        return False

if __name__ == "__main__":
    # Create QApplication instance
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    
    # Initialize application
    if not initialize_app():
        print("Failed to initialize application. Exiting...")
        sys.exit(1)
    
    # Set up the application ID for Windows
    if platform.system() == 'Windows':
        myappid = 'mycompany.axiora.version1'  # arbitrary string
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    # Set the application icon that will appear in taskbar
    # Try multiple icon formats
    icon_paths = [
        "images/images/IMG_20250226_011441_442.ico",  # First try .ico
        "images/images/IMG_20250226_011441_442.jpg",  # Then try .jpg
        "images/IMG_20250226_011441_442.ico",         # Try alternate paths
        "images/IMG_20250226_011441_442.jpg",
    ]
    
    icon = None
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            break
    
    if icon:
        app.setWindowIcon(icon)  # Set icon for the entire application
    else:
        print("Warning: Could not find icon file in any of the expected locations")
    
    # Set the font size for the entire application
    font = QFont("Segoe UI", 12)
    app.setFont(font)

    try:
        login_window = LoginWindow()
        if icon:
            login_window.setWindowIcon(icon)  # Set icon for login window

        def open_main(user_id):
            try:
                main_window = MainWindow(user_id)
                if icon:
                    main_window.setWindowIcon(icon)  # Set icon for main window
                main_window.show()
                login_window.close()
            except Exception as e:
                print(f"Error opening main window: {str(e)}")
                QMessageBox.critical(login_window, "Error", 
                    "Failed to open main window. Please check the application logs.")

        login_window.login_accepted.connect(open_main)
        login_window.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"Application error: {str(e)}")
        sys.exit(1)
