import pandas as pd
import requests
import json
import datetime
import pytz
import folium
from flask import Flask

######################################################################

data_final = datetime.date.today() + datetime.timedelta(days = +1)

data_inicial = datetime.date.today() + datetime.timedelta(days = -1)

lista_ids_telemetricos_hc = '212643330,212943250,213043220,205442390,211742490,211443190,211743130,211843110,211943050,212143020,211842540,211842510,212442420,212742340,212642230,213242100,213742060,211642560,212842490,212742470'

url = f'https://www.snirh.gov.br/hidroweb/rest/api/documento/gerarTelemetricas?codigosEstacoes={lista_ids_telemetricos_hc}&tipoArquivo=3&periodoInicial={data_inicial}T03:00:00.000Z&periodoFinal={data_final}T03:00:00.000Z'
res = requests.get(url)
res_json = json.loads(res.text)

######################################################################

colunas_nivel_meta = ['codigoNome', 'latitude', 'longitude']

df_medicoes_completa = pd.json_normalize(res_json, record_path = 'medicoes', meta = colunas_nivel_meta)

df_medicoes_completa = df_medicoes_completa.rename(columns = {
    'id.horEstacao': 'id_horEstacao', 
    'id.horDataHora': 'id_horDataHora'
}).copy()

df_medicoes = df_medicoes_completa[['codigoNome', 'latitude', 'longitude', 'id_horDataHora', 'horChuva', 'horNivelAdotado', 'horVazao']].copy()

df_medicoes['id_horDataHora'] = pd.to_datetime(df_medicoes['id_horDataHora'], utc = True).map(lambda x: x.tz_convert('America/Sao_Paulo')).map(lambda x: x.strftime('%d/%m/%Y %H:%M:%S'))

df_medicoes = df_medicoes.sort_values('id_horDataHora', ascending = False).copy()

df_agrup = df_medicoes.groupby('codigoNome', as_index = False).first()

def define_cor_estacao(row):
  if row['horNivelAdotado'] >= 1000:
    return 'red'
  elif row['horNivelAdotado'] > 100 and row['horNivelAdotado'] < 1000:
    return 'orange'
  return 'blue'

df_agrup['cor_estacao'] = df_agrup.apply(define_cor_estacao, axis = 1)

######################################################################

m = folium.Map(
  location = [-21.3624184,-42.7126306], 
  zoom_start = 10
)

for idx, row in df_agrup.iterrows():
  folium.Marker(
    location = [row['latitude'], row['longitude']], 
    icon = folium.Icon(color = row['cor_estacao']), 
    # tooltip = row['codigoNome'], 
    popup = folium.Popup(
      f"""
      Estação: {row['codigoNome']} <br> 
      Atualizado em: {row['id_horDataHora']} <br> 
      Precipitação: {row['horChuva']} <br> 
      Nível: {row['horNivelAdotado']} <br> 
      Vazão: {row['horVazao']} <br> 
      """, 
      max_width = 500
    ),
  ).add_to(m)

######################################################################

app = Flask('app')

@app.route('/')
def index():
    return m._repr_html_()

@app.route('/mapa')
def mapa():
    return m._repr_html_()

app.run(host='0.0.0.0', port=8080)