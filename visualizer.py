import os
import glob
import pandas as pd
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'csvs')
df_all = None

def load_data():
    global df_all
    print("Loading and processing CSV data...")
    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "**", "*.csv"), recursive=True))
    # Exclude combined.csv to prevent data duplication
    all_files = [f for f in all_files if not f.endswith('combined.csv')]
    
    df_list = []
    for f in all_files:
        try:
            df = pd.read_csv(f)
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {f}: {e}")
    
    if df_list:
        df_all = pd.concat(df_list, ignore_index=True)
        # Parse time and convert to UTC+8
        df_all['Time'] = pd.to_datetime(df_all['Time'], format='%Y%m%dT%H%M%SZ', errors='coerce')
        df_all.dropna(subset=['Time'], inplace=True)
        df_all['Time'] = df_all['Time'] + pd.Timedelta(hours=8)
        
        # Ensure correct types
        df_all['Temperature'] = pd.to_numeric(df_all['Temperature'], errors='coerce')
        df_all['Humidity'] = pd.to_numeric(df_all['Humidity'], errors='coerce')
        
        # Round values for cleanliness
        df_all['Temperature'] = df_all['Temperature'].round(1)
        df_all['Humidity'] = df_all['Humidity'].round(1)
        
        # Add useful columns
        df_all['Date'] = df_all['Time'].dt.date.astype(str)
        df_all['Hour'] = df_all['Time'].dt.hour
        
        # Set index for resampling
        df_all = df_all.set_index('Time')
        print(f"Loaded {len(df_all)} rows.")
    else:
        print("No CSV files found.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dates')
def get_dates():
    if df_all is None or df_all.empty:
        return jsonify([])
    dates = df_all['Date'].unique().tolist()
    return jsonify(dates)

@app.route('/api/data')
def get_data():
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    if df_all is None or df_all.empty:
        return jsonify([])
        
    mask = pd.Series(True, index=df_all.index)
    if start_date:
        try:
            start_ts = pd.to_datetime(start_date)
            mask = mask & (df_all.index >= start_ts)
        except:
            mask = mask & (df_all['Date'] >= start_date)
    if end_date:
        try:
            end_ts = pd.to_datetime(end_date)
            mask = mask & (df_all.index <= end_ts)
        except:
            mask = mask & (df_all['Date'] <= end_date)
            
    df_filtered = df_all.loc[mask]
    
    # Dynamic LOD Low-pass Filter and Gap Detection
    if not df_filtered.empty:
        df_filtered = df_filtered[['Temperature', 'Humidity']].dropna()
        span = df_filtered.index.max() - df_filtered.index.min()
        days = span.total_seconds() / 86400.0
        
        # Linear LOD: Target ~200 points total regardless of zoom span
        # total_minutes = days * 1440; rule = total_minutes / 200 = days * 7.2
        rule_minutes = int(days * 7.2)
        
        if rule_minutes > 1:
            rule = f'{rule_minutes}min'
            df_sampled = df_filtered.resample(rule).mean().dropna()
        else:
            rule = None
            df_sampled = df_filtered
            
        df_sampled = df_sampled.round(1)
        
        # Format for output and detect gaps
        result = []
        last_time = None
        
        # The gap threshold must be larger than the resampling interval.
        # Default is 3600 seconds (1 hour). If rule_minutes is large, use 1.5x the interval.
        gap_threshold_seconds = max(3600, rule_minutes * 60 * 1.5) if rule_minutes else 3600
        
        for time, row in df_sampled.iterrows():
            if last_time is not None:
                # If gap is larger than the dynamic threshold, insert a null point to break the line
                if (time - last_time).total_seconds() > gap_threshold_seconds:
                    gap_time = last_time + pd.Timedelta(seconds=1)
                    result.append({
                        'time': gap_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'temperature': None,
                        'humidity': None
                    })
            result.append({
                'time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'temperature': row['Temperature'],
                'humidity': row['Humidity']
            })
            last_time = time
            
        return jsonify(result)
    return jsonify([])

@app.route('/api/daily_stats')
def daily_stats():
    if df_all is None or df_all.empty:
        return jsonify({})
        
    stats = df_all.groupby('Date').agg({
        'Temperature': ['min', 'max', 'mean'],
        'Humidity': ['min', 'max', 'mean']
    }).round(1)
    
    # Flatten columns
    stats.columns = ['temp_min', 'temp_max', 'temp_avg', 'hum_min', 'hum_max', 'hum_avg']
    stats = stats.reset_index()
    
    return jsonify(stats.to_dict(orient='records'))

@app.route('/api/heatmap')
def heatmap():
    data_type = request.args.get('type', 'temperature') # 'temperature' or 'humidity'
    if data_type.lower() == 'humidity':
        col = 'Humidity'
    else:
        col = 'Temperature'
        
    if df_all is None or df_all.empty:
        return jsonify({})
        
    pivot = df_all.pivot_table(values=col, index='Hour', columns='Date', aggfunc='mean').round(1)
    
    # Format for heatmap: x=dates, y=hours, data=[[hour, date_idx, val], ...] or simply array of dicts
    dates = pivot.columns.tolist()
    hours = pivot.index.tolist()
    
    data = []
    for h_idx, h in enumerate(hours):
        for d_idx, d in enumerate(dates):
            val = pivot.iloc[h_idx, d_idx]
            if not pd.isna(val):
                data.append({
                    'x': d,
                    'y': h,
                    'v': val
                })
                
    return jsonify({
        'dates': dates,
        'hours': hours,
        'data': data
    })

if __name__ == '__main__':
    load_data()
    # allow running over local network as well
    app.run(debug=True, host='0.0.0.0', port=5000)
