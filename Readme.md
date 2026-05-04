# Axiora

Axiora is a comprehensive Business Intelligence (BI) and data analytics platform that bridges the gap between complex data analysis and user-friendly interfaces. It empowers users of all technical backgrounds to analyze, visualize, and forecast data, generate automated reports, and make data-driven decisions with confidence.

## Features

- **Modern, Intuitive UI**: Built with PySide6, featuring responsive layouts, theming (dark/light modes), and reusable widgets.
- **Data Analysis & Visualization**:
  - Time series forecasting
  - Statistical analysis
  - Pattern recognition
  - Interactive charts and dashboards
- **Automated Reporting**:
  - PDF report generation
  - Customizable templates
  - Scheduled and on-demand exports
- **Data Management**:
  - Centralized, secure storage using SQLite
  - Efficient data import/export
  - Data validation and consistency
- **User Management**:
  - Secure authentication
  - Role-based access control
  - User preferences and activity logging
- **Extensibility**:
  - Modular architecture for easy feature addition
  - Plugin and theme support

## System Architecture

Axiora follows a modular, MVC-inspired architecture:

```
User Input → UI Layer → Controller → Model → Database
Database → Model → Controller → UI Layer → Visualization
```

- **Core**: `Axiora.py`, `DatabaseManager.py`, `DataAnalyzer.py`, `Visualizer.py`
- **UI**: `main_ui.py`, `uiEXT/`, `widgets/`, `themes/`
- **Data Processing**: `time_series_forecaster.py`, `Functions.py`, `Axioradb.py`

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd Axiora
   ```

2. **Set up a virtual environment (recommended)**:
   ```bash
   python -m venv my_env
   my_env\Scripts\activate  # On Windows
   # Or
   source my_env/bin/activate  # On macOS/Linux
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirments.txt
   ```

4. **Run the application**:
   ```bash
   python Axiora.py
   ```

## Usage

- **Login**: Start the app and log in with your credentials.
- **Data Import**: Import datasets (CSV, Excel, etc.) via the UI.
- **Analysis**: Use built-in tools for forecasting, statistical analysis, and visualization.
- **Reporting**: Generate and export reports in PDF or other formats.
- **Customization**: Switch between light/dark themes and configure user preferences.

## File Structure

- `Axiora.py` – Main application entry point
- `modules/` – Core modules (settings, UI functions, dialogs, etc.)
- `uiEXT/` – Extended UI components and dialogs
- `widgets/` – Custom widgets
- `themes/` – Theme files (QSS)
- `images/` – Icons and images
- `axioradb.db` – Local SQLite database
- `test/` – (Recommended) Unit and UI tests

## Development Guidelines

- Follow the code organization and naming conventions in `.cursorrules`.
- Write docstrings for all functions and modules.
- Use feature branches and pull requests for new features.
- Add unit/UI tests for new functionality.

## Requirements

- Python 3.8+
- PySide6
- matplotlib
- pandas
- reportlab
- selenium
- langchain-core
- (See `requirments.txt` for full list)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes
4. Open a pull request

## License

[MIT License](LICENSE)

## Acknowledgments

- Inspired by modern BI and analytics platforms
- Uses open-source Python libraries for data science and UI 