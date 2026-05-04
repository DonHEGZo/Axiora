import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.model_selection import train_test_split

def time_series_forecaster(dataframe, target_col, date_cols=None, test_size=0.2, forecast_horizon=None):

    # Load data
    df = dataframe.copy()
    
    # Validate target column exists
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in DataFrame. Available columns: {df.columns.tolist()}")
    
    # Handle date columns
    if date_cols is None:
        raise ValueError("Either date_col or date_cols must be specified")
    
    if isinstance(date_cols, str):
        # Single datetime column case
        df[date_cols] = pd.to_datetime(df[date_cols])
        df = df.set_index(date_cols)
        df.sort_index(inplace=True)
        
        # Create features from datetime index - only using the specified date_col
        def create_features(df):
            df = df.copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                return df
            # Only create features from the specified date column
            df[date_cols] = df.index
            return df
        
        has_datetime_index = True
    else:
        # Multiple columns case (year, month, etc.)
        # Create a datetime index from the date columns
        date_cols_str = [str(col) for col in date_cols]
        df['date'] = pd.to_datetime(df[date_cols_str].astype(str).agg('-'.join, axis=1))
        df = df.set_index('date')
        df.sort_index(inplace=True)
        
        def create_features(df):
            df = df.copy()
            if not isinstance(df.index, pd.DatetimeIndex):
                return df
            
            # Create temporal features
            df['year'] = df.index.year
            df['month'] = df.index.month
            df['day'] = df.index.day
            df['dayofweek'] = df.index.dayofweek
            df['dayofyear'] = df.index.dayofyear
            df['quarter'] = df.index.quarter
            df['weekofyear'] = df.index.isocalendar().week
            df['is_month_start'] = df.index.is_month_start.astype(int)
            df['is_month_end'] = df.index.is_month_end.astype(int)
            
            # Create lag features if target column exists
            if target_col in df.columns:
                for lag in [1, 2, 3, 7, 14, 30]:  # Daily, weekly, and monthly lags
                    df[f'lag_{lag}'] = df[target_col].shift(lag)
                
                # Create rolling statistics
                for window in [7, 14, 30]:  # Weekly, bi-weekly, and monthly windows
                    df[f'rolling_mean_{window}'] = df[target_col].rolling(window=window).mean()
                    df[f'rolling_std_{window}'] = df[target_col].rolling(window=window).std()
            
            # Create seasonal features
            df['sin_month'] = np.sin(2 * np.pi * df['month'] / 12)
            df['cos_month'] = np.cos(2 * np.pi * df['month'] / 12)
            df['sin_day'] = np.sin(2 * np.pi * df['day'] / 31)
            df['cos_day'] = np.cos(2 * np.pi * df['day'] / 31)
            
            return df
        
        has_datetime_index = True
    
    # Create initial visualization figure if we have a datetime index
    initial_plot = None
    if has_datetime_index:
        fig, ax = plt.subplots(figsize=(15, 5))
        df[target_col].plot(style='.', title=f'{target_col} Time Series', ax=ax)
        plt.tight_layout()
        initial_plot = fig
    
    # Create features for the entire dataset
    df = create_features(df)
    
    # Drop rows with NaN values from lag features
    df = df.dropna()
    
    # Convert categorical columns to numeric codes
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    for col in categorical_cols:
        if col != target_col:  # Don't encode the target variable
            df[col] = pd.Categorical(df[col]).codes
    
    # Convert datetime columns to numeric features
    datetime_cols = df.select_dtypes(include=['datetime64']).columns
    for col in datetime_cols:
        if col != target_col:  # Don't convert the target variable
            df[f'{col}_year'] = df[col].dt.year
            df[f'{col}_month'] = df[col].dt.month
            df[f'{col}_day'] = df[col].dt.day
            df[f'{col}_dayofweek'] = df[col].dt.dayofweek
            df = df.drop(columns=[col])
    
    # Feature selection based on correlation
    if target_col in df.columns:
        correlations = df.corr()[target_col].abs()
        FEATURES = correlations[correlations > 0.1].index.tolist()
        FEATURES = [f for f in FEATURES if f != target_col]
    else:
        FEATURES = [col for col in df.columns if col != target_col]
    
    if not FEATURES:
        warning_no_features = "Warning: No features found with significant correlation. Using all features."
        print(warning_no_features)
        FEATURES = [col for col in df.columns if col != target_col]
    
    print(f"Selected features: {FEATURES}")
    
    # Train-test split
    if isinstance(test_size, float):
        # Random split
        train, test = train_test_split(df, test_size=test_size, shuffle=False)
    else:
        if has_datetime_index:
            # Date-based split
            train = df.loc[df.index < pd.to_datetime(test_size)]
            test = df.loc[df.index >= pd.to_datetime(test_size)]
        else:
            # For non-datetime data, use a simple fraction split
            split_idx = int(len(df) * (1 - test_size))
            train = df.iloc[:split_idx]
            test = df.iloc[split_idx:]
    
    TARGET = target_col
    
    X_train = train[FEATURES]
    y_train = train[TARGET]
    X_test = test[FEATURES]
    y_test = test[TARGET]
    
    # Model training with updated parameters
    reg = xgb.XGBRegressor(
        base_score=0.5,
        booster='gbtree',
        n_estimators=2000,
        early_stopping_rounds=100,
        max_depth=8,
        learning_rate=0.1,
        min_child_weight=3,
        subsample=0.9,
        colsample_bytree=0.9,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective='reg:squarederror',
        enable_categorical=True,
        random_state=42,
        tree_method='hist',
        scale_pos_weight=1,
        max_delta_step=0
    )

    reg.fit(X_train, y_train,
           eval_set=[(X_train, y_train), (X_test, y_test)],
           verbose=100)
    
    # Create feature importance plot
    fi = pd.DataFrame(data=reg.feature_importances_,
                     index=reg.feature_names_in_,
                     columns=['importance'])
    importance_fig, importance_ax = plt.subplots(figsize=(10, 6))
    fi.sort_values('importance').plot(kind='barh', title='Feature Importance', ax=importance_ax)
    plt.tight_layout()
    
    # Predictions with proper feature handling
    test['prediction'] = reg.predict(X_test)
    
    # Ensure we're using all features for prediction
    df = df.merge(test[['prediction']], how='left', left_index=True, right_index=True)
    
    # Create actual vs predicted plot
    prediction_fig = None
    if has_datetime_index:
        prediction_fig, ax = plt.subplots(figsize=(15, 5), facecolor='#2c313c')
        ax.set_facecolor('#2c313c')
        df[[target_col]].plot(ax=ax, color='#00a6fb')
        df['prediction'].plot(ax=ax, style='.', color='#ff6b6b')
        plt.legend(['Actual Data', 'Predictions'], facecolor='#2c313c', labelcolor='white')
        ax.set_title('Actual vs Predicted', color='white')
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['right'].set_color('white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        plt.tight_layout()
    
    # Evaluation
    r2 = r2_score(test[target_col], test['prediction'])
    rmse = np.sqrt(mean_squared_error(test[target_col], test['prediction']))
    print(f'R² Score on Test set: {r2:0.4f}')
    print(f'RMSE Score on Test set: {rmse:0.2f}')
    
    # Create R² visualization
    r2_fig, r2_ax = plt.subplots(figsize=(8, 8), facecolor='#2c313c')
    r2_ax.set_facecolor('#2c313c')
    r2_ax.scatter(test[target_col], test['prediction'], alpha=0.5, color='#00a6fb')
    r2_ax.plot([test[target_col].min(), test[target_col].max()], 
             [test[target_col].min(), test[target_col].max()], 
             'r--', lw=2, color='#ff6b6b')
    r2_ax.set_xlabel('Actual Values', color='white')
    r2_ax.set_ylabel('Predicted Values', color='white')
    r2_ax.set_title(f'Fit line, R² = {r2:0.4f}', color='white')
    r2_ax.grid(True, color='#3d4451')
    r2_ax.tick_params(colors='white')
    r2_ax.spines['bottom'].set_color('white')
    r2_ax.spines['top'].set_color('white')
    r2_ax.spines['left'].set_color('white')
    r2_ax.spines['right'].set_color('white')
    plt.tight_layout()
    
    # Future forecasting (if requested)
    if forecast_horizon:
        if not has_datetime_index:
            warning_no_datetime = "Warning: Future forecasting requires datetime index. Skipping..."
            print(warning_no_datetime)
            return test['prediction'], [initial_plot, importance_fig, prediction_fig, r2_fig]
        
        last_date = df.index.max()
        future_dates = pd.date_range(start=last_date, periods=forecast_horizon+1, freq='D')[1:]
        future_df = pd.DataFrame(index=future_dates)
        
        # Create all temporal features for future dates
        future_df = create_features(future_df)
        
        # Fill in lag features using the last known values
        if target_col in df.columns:
            for lag in [1, 2, 3, 7, 14, 30]:
                if f'lag_{lag}' in FEATURES:
                    future_df[f'lag_{lag}'] = df[target_col].iloc[-lag]
            
            # Fill in rolling statistics
            for window in [7, 14, 30]:
                if f'rolling_mean_{window}' in FEATURES:
                    future_df[f'rolling_mean_{window}'] = df[target_col].rolling(window=window).mean().iloc[-1]
                if f'rolling_std_{window}' in FEATURES:
                    future_df[f'rolling_std_{window}'] = df[target_col].rolling(window=window).std().iloc[-1]
        
        # Add any missing features from the original dataset
        for feature in FEATURES:
            if feature not in future_df.columns:
                if feature in df.columns:
                    if pd.api.types.is_numeric_dtype(df[feature]):
                        # For numerical features, use the last known value
                        future_df[feature] = df[feature].iloc[-1]
                    else:
                        # For categoricals, use the most common value
                        future_df[feature] = df[feature].mode()[0]
                else:
                    # If feature doesn't exist in original data, set to 0
                    future_df[feature] = 0
        
        # Ensure all features are in the correct order and exist
        missing_features = [f for f in FEATURES if f not in future_df.columns]
        if missing_features:
            warning_missing_features = f"Warning: The following features are missing in future predictions: {missing_features}"
            print(warning_missing_features)
            for feature in missing_features:
                future_df[feature] = 0
        
        # Make predictions
        future_df['prediction'] = reg.predict(future_df[FEATURES])        
        return future_df, [initial_plot, importance_fig, prediction_fig, r2_fig],[r2,rmse]
    
    return test, [initial_plot, importance_fig, prediction_fig, r2_fig]