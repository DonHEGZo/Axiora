import plotly.graph_objects as go
import pandas as pd
from typing import List, Dict, Optional, Union
import re
import os
import numpy as np
import plotly.express as px

class Visualizer:
    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize with a pandas DataFrame
        
        Args:
            dataframe: Input data for visualization
        """
        self.df = dataframe
        self._valid_charts = {
            'Bar', 'Line', 'Histogram', 
            'Pie', 'Scatter', 'StackedBar'
        }
        
        # Default theme colors
        self._theme_colors = {
            'primary': '#2196F3',      # Bright blue
            'secondary': '#4CAF50',    # Green
            'accent': '#1976D2',       # Darker blue
            'accent2': '#388E3C',      # Darker green
            'background': '#111827',   # Dark background
            'text': '#E0E0E0',         # Light gray text
            'grid': '#1F2937'          # Dark grid lines
        }

    def generate_visualization(
        self,
        question: str,
        output_path: str,
        columns: List[str],
        chart_type: str,
        **chart_args
    ) -> Dict[str, Union[str, bool]]:
        """
        Generate and execute Plotly visualization
        
        Args:
            question: Chart title/description
            output_path: Where to save HTML (e.g., 'output/chart.html')
            columns: List of columns to visualize
            chart_type: Type of chart to generate
            chart_args: Additional chart configuration
            
        Returns:
            Dictionary with:
            - 'success': Execution status
            - 'message': Additional info
            - 'output_path': Path to generated chart
        """
        # Create output directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Validate inputs
            self._validate_columns(columns)
            self._validate_chart_type(chart_type)
            
            # Create the figure based on chart type
            fig = self._create_figure(chart_type, columns, question, chart_args)
            
            # Apply common layout settings
            self._apply_layout(fig, question)
            
            # Save to HTML
            fig.write_html(output_path)
            
            return {
                'success': True,
                'message': f"Chart saved to {output_path}",
                'output_path': output_path
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Error: {str(e)}",
                'output_path': None
            }

    def _validate_columns(self, columns: List[str]) -> None:
        """Ensure columns exist in DataFrame"""
        invalid = [col for col in columns if col not in self.df.columns]
        if invalid:
            raise ValueError(f"Columns not found: {invalid}")

    def _validate_chart_type(self, chart_type: str) -> None:
        """Ensure requested chart type is supported"""
        if chart_type not in self._valid_charts:
            raise ValueError(f"Invalid chart type. Choose from: {self._valid_charts}")

    def _create_figure(self, chart_type: str, columns: List[str], title: str, chart_args: dict) -> go.Figure:
        """Create appropriate Plotly figure based on chart type"""
        if chart_type == "Bar":
            return self._create_bar_chart(columns[0])
        elif chart_type == "Line":
            return self._create_line_chart(columns)
        elif chart_type == "Histogram":
            return self._create_histogram(columns[0])
        elif chart_type == "Pie":
            return self._create_pie_chart(columns[0])
        elif chart_type == "Scatter":
            return self._create_scatter_plot(columns[0], columns[1] if len(columns) > 1 else None)
        elif chart_type == "StackedBar":
            return self._create_stacked_bar(columns)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    def _create_bar_chart(self, column: str) -> go.Figure:
        """Create a bar chart"""
        data = self.df[column].value_counts()
        fig = go.Figure(data=[
            go.Bar(
                x=data.index,
                y=data.values,
                marker_color=self._theme_colors['primary'],
                marker_line_color=self._theme_colors['accent'],
                marker_line_width=1.5
            )
        ])
        return fig

    def _create_line_chart(self, columns: List[str]) -> go.Figure:
        """Create a line chart using value_counts for frequency aggregation, like bar/pie charts."""
        fig = go.Figure()
        if len(columns) == 1:
            # Use value_counts on the column
            data = self.df[columns[0]].value_counts().sort_index()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    name=columns[0],
                    mode='lines+markers',
                    line=dict(color=self._theme_colors['primary'])
                )
            )
        elif len(columns) >= 2:
            # Use value_counts on the x column
            x_col = columns[0]
            data = self.df[x_col].value_counts().sort_index()
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    name=x_col,
                    mode='lines+markers',
                    line=dict(color=self._theme_colors['primary'])
                )
            )
        else:
            raise ValueError("Line chart requires at least one column.")
        return fig

    def _create_histogram(self, column: str) -> go.Figure:
        """Create a histogram"""
        fig = go.Figure(data=[
            go.Histogram(
                x=self.df[column],
                marker_color=self._theme_colors['primary'],
                marker_line_color=self._theme_colors['accent'],
                marker_line_width=1
            )
        ])
        return fig

    def _create_pie_chart(self, column: str) -> go.Figure:
        """Create a pie chart"""
        data = self.df[column].value_counts()
        fig = go.Figure(data=[
            go.Pie(
                labels=data.index,
                values=data.values,
                marker=dict(
                    colors=[self._theme_colors[color] for color in ['primary', 'secondary', 'accent', 'accent2']]
                )
            )
        ])
        return fig

    def _create_scatter_plot(self, x_col: str, y_col: str) -> go.Figure:
        """Create a scatter plot using value_counts for (x, y) frequency aggregation, with color indicating frequency."""
        if y_col:
            # Count frequency of each (x, y) pair
            freq = self.df.groupby([x_col, y_col]).size().reset_index(name='count')
            fig = go.Figure(data=[
                go.Scatter(
                    x=freq[x_col],
                    y=freq[y_col],
                    mode='markers',
                    marker=dict(
                        size=freq['count'] * 5,  # scale marker size by count
                        color=freq['count'],     # color by frequency
                        colorscale='Blues',      # use a blue color scale
                        showscale=True,
                        colorbar=dict(title='Frequency'),
                        line=dict(color=self._theme_colors['accent'], width=1)
                    ),
                    text=freq['count'],
                    name=f"{x_col} vs {y_col} (freq)"
                )
            ])
        else:
            # Only x_col provided, use value_counts
            data = self.df[x_col].value_counts().sort_index()
            fig = go.Figure(data=[
                go.Scatter(
                    x=data.index,
                    y=data.values,
                    mode='markers',
                    marker=dict(
                        size=data.values * 5,
                        color=data.values,
                        colorscale='Blues',
                        showscale=True,
                        colorbar=dict(title='Frequency'),
                        line=dict(color=self._theme_colors['accent'], width=1)
                    ),
                    text=data.values,
                    name=f"{x_col} (freq)"
                )
            ])
        return fig

    def _create_stacked_bar(self, columns: List[str]) -> go.Figure:
        """Create a stacked bar chart"""
        fig = go.Figure()
        for i, col in enumerate(columns):
            data = self.df[col].value_counts()
            fig.add_trace(
                go.Bar(
                    name=col,
                    x=data.index,
                    y=data.values,
                    marker_color=self._theme_colors['primary' if i % 2 == 0 else 'secondary']
                )
            )
        fig.update_layout(barmode='stack')
        return fig

    def _apply_layout(self, fig: go.Figure, title: str) -> None:
        """Apply common layout settings to figure"""
        fig.update_layout(
            title=dict(
                text=self._clean_title(title),
                font=dict(
                    size=20,
                    color=self._theme_colors['text']
                )
            ),
            plot_bgcolor=self._theme_colors['background'],
            paper_bgcolor=self._theme_colors['background'],
            font=dict(
                family="Segoe UI",
                size=12,
                color=self._theme_colors['text']
            ),
            showlegend=True,
            legend=dict(
                bgcolor='rgba(17, 24, 39, 0.8)',
                font=dict(color=self._theme_colors['text'])
            ),
            xaxis=dict(
                gridcolor=self._theme_colors['grid'],
                tickcolor=self._theme_colors['text'],
                tickfont=dict(color=self._theme_colors['text'])
            ),
            yaxis=dict(
                gridcolor=self._theme_colors['grid'],
                tickcolor=self._theme_colors['text'],
                tickfont=dict(color=self._theme_colors['text'])
            ),
            margin=dict(t=100, l=80, r=80, b=80)
        )

    def _clean_title(self, text: str) -> str:
        """Clean and truncate chart title"""
        text = re.sub(r'[^\w\s-]', '', text.strip())[:60]
        return text + ('...' if len(text) >= 60 else '')