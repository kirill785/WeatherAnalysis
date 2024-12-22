import streamlit as st
import pandas as pd
from analyze_weather import process_data
import plotly.express as px


def draw_chart(city_data, stat):
    city_data = city_data.copy()
    city_data['anomaly'] = stat['anomalies']
    
    fig = px.scatter(city_data, x='timestamp', y='temperature',
                     color='anomaly',
                     title=f'График температуры для города {stat["city"]}',
                     color_discrete_map={False: 'blue', True: 'red'})
    
    fig.add_scatter(x=city_data['timestamp'], y=city_data['temperature'],
                   mode='lines', line=dict(color='lightblue'),
                   showlegend=False)
    
    fig.update_xaxes(title_text='Дата')
    fig.update_yaxes(title_text='Температура (°C)')
    st.plotly_chart(fig)


st.title("Анализ температурных данных")

uploaded_file = st.file_uploader("Выберите CSV-файл", type=["csv"])

if uploaded_file is not None:
    data = pd.read_csv(uploaded_file)
    cities = sorted(data['city'].unique())
    selected_city = st.selectbox("Выберите город", cities)
    city_data = data[data['city'] == selected_city]
    
    api_key = st.text_input("Введите ваш API-ключ OpenWeatherMap", type="password")
    if api_key:
        try:
            stats = process_data(city_data, api_key)
            assert len(stats) == 1
            stat = stats[0]
            st.write(f"Средняя температура: {stat['global_mean']:.2f} °C")
            st.write(f"Минимальная температура: {stat['global_min']:.2f} °C")
            st.write(f"Максимальная температура: {stat['global_max']:.2f} °C")
            st.write(f"Тренд: {stat['trend']:.2f}")
            st.write(f"Сезон: {stat['current_season']}")
            st.write(f"Средняя температура в сезон: {stat['season_mean'][stat['current_season']]:.2f} °C")
            st.write(f"Стандартное отклонение в сезон: {stat['season_std'][stat['current_season']]:.2f} °C")
            st.markdown(f"### {stat['current_temp_status']}")

            draw_chart(city_data, stat)

        except Exception as e:
            st.error(f"Произошла ошибка: {e}")

else:
    st.write("Пожалуйста, загрузите CSV-файл.")

