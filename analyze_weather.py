from multiprocessing import Pool
import requests
from datetime import datetime
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
import aiohttp
import asyncio
from generate_data import month_to_season


def analyze_temperature(data: pd.DataFrame, city: str, window: int = 30):
    data_city = data[data['city'] == city].copy()
    data_city['rolling_mean'] = data_city['temperature'].rolling(window=window, center=True).mean()
    data_city['rolling_std'] = data_city['temperature'].rolling(window=window, center=True).std()
    data_city['anomalies'] = (data_city['temperature'] - data_city['rolling_mean']).abs() > 2 * data_city['rolling_std']
    
    # analyze by season
    season_mean = data_city['temperature'].groupby(data_city['season']).mean()
    season_std = data_city['temperature'].groupby(data_city['season']).std()
    season_mean_smoothed = data_city['rolling_mean'].groupby(data_city['season']).mean()
    season_std_smoothed = data_city['rolling_mean'].groupby(data_city['season']).std()
    
    # estimate trend
    data_city['days'] = (data_city['timestamp'] - data_city['timestamp'].min()).dt.days
    X = data_city['days'].values[window//2:-window//2].reshape(-1, 1)
    y = data_city['rolling_mean'].values[window//2:-window//2]
    model = LinearRegression()
    model.fit(X, y)
    trend = model.coef_[0]

    global_mean = data_city['temperature'].mean()
    global_min = data_city['temperature'].min()
    global_max = data_city['temperature'].max()

    output = {
        'city': city,
        'trend': trend,
        'global_mean': global_mean,
        'global_min': global_min,
        'global_max': global_max,
        'season_mean': season_mean,
        'season_std': season_std,
        'season_mean_smoothed': season_mean_smoothed,
        'season_std_smoothed': season_std_smoothed,
        'anomalies': data_city['anomalies'],
    }
    return output


def check_seasonal_anomaly(temperature: float, season: str, season_mean: pd.Series, season_std: pd.Series):
    mean = season_mean[season]
    std = season_std[season]
    return np.abs(temperature - mean) > 2 * std


async def get_temperature(session, city, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
    async with session.get(url) as response:
        data = await response.json()
        if data['cod'] == 200:
            return city, data['main']['temp']
        else:
            raise ValueError(str(data))


async def get_all_temperatures(cities, api_key):
    async with aiohttp.ClientSession() as session:
        tasks = [get_temperature(session, city, api_key) for city in cities]
        results = await asyncio.gather(*tasks)
        return dict(results)


def process_data(data: pd.DataFrame, api_key: str):
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    cities = data['city'].unique()
    window = 30
    args = [(data, city, window) for city in cities]
    with Pool() as pool:
        stats = pool.starmap(analyze_temperature, args)
    
    current_temperatures = asyncio.run(get_all_temperatures(cities, api_key))
    current_season = month_to_season[datetime.now().month]
    
    for city_stats in stats:
        is_anomaly = check_seasonal_anomaly(current_temperatures[city_stats['city']], current_season, city_stats['season_mean'], city_stats['season_std'])
        if is_anomaly:
            current_temp_status = f"Температура в {city_stats['city']} аномальна: {current_temperatures[city_stats['city']]} °C"
        else:
            current_temp_status = f"В {city_stats['city']} температура в норме: {current_temperatures[city_stats['city']]} °C"

        city_stats['current_temp_status'] = current_temp_status
        city_stats['current_season'] = current_season
    
    return stats
