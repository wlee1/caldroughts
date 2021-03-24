
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px
import pandas as pd
import json
import datetime
import plotly.graph_objects as go
from dash.dependencies import Input, Output
from flask_caching.backends import FileSystemCache
from dash_extensions.callback import CallbackCache, Trigger
from os import walk
app = dash.Dash(prevent_initial_callbacks=True)

app.title = 'California Drought'

# Create (server side) disk cache.
cc = CallbackCache(cache=FileSystemCache(cache_dir="server_cache_dir"))

# Load counties FIPS file from local json
def geojson():
    f = open('geojson-counties-fips.json',)
    return json.load(f)

# Load drought dataframe for heatmap
def droughts():
    return pd.read_csv("dm_export_20100101_20200901.csv", dtype={"FIPS": str})

# Drought intensity level for drop down
def getDroughtIntensityLevel():
    return [
            {'value': 'NONE', 'name': 'Drought %'},
            {'value': 'D0', 'name': 'Abnormally Dry %'},
            {'value': 'D1', 'name': 'Moderate Drought %'},
            {'value': 'D2', 'name': 'Severe Drought %'},
            {'value': 'D3', 'name': 'Extreme Drought %'},
            {'value': 'D4', 'name': 'Exceptional Drought %'}
        ]

def getSelectedRecord(df, year, month, day):
    date = datetime.datetime(year, month, day)
    qDateStr = date.strftime('%Y%m%d')
    return df.query('releaseDate == @qDateStr')[['FIPS','Value']]

# Get drought table for selected county
def getDroughtTable(data):
    return go.Figure(data=[go.Table(
        header=dict(
            values=['Release Date','County','State','Drought %','Abnormally Dry %','Moderate Drought %','Severe Drought %','Extreme Drought %','Exceptional Drought %','Valid Start','Valid End'],
            line_color='darkslategray',
            fill_color='grey',
            align='left',
            font=dict(color='white', size=14)),
        cells=dict(
            values=[data.releaseDate, data.county, data.state, data.NONE, data.D0, data.D1, data.D2, data.D3, data.D4, data.validStart, data.validEnd],
            line_color='darkslategray',
            align = ['left', 'center'],
            font = dict(color = 'darkslategray', size = 12)
        ))
    ])

# Get heat map for selected date and intensity
def getHeatMap(df, selectedDate, intensityLevel):

    # Create a new colume Value
    df['Value'] = (100 - df[intensityLevel]) if intensityLevel == 'NONE' else df[intensityLevel]
    selected_heatmap_data = getSelectedRecord(df,selectedDate.year, selectedDate.month, selectedDate.day)
    fig = go.Figure(go.Choroplethmapbox(geojson=counties, locations=selected_heatmap_data['FIPS'], z=selected_heatmap_data['Value'],
                                        colorscale="OrRd",
                                        zmin=0,
                                        zmax=100,
                                        marker_opacity=0.5,
                                        marker_line_width=0.1
                                        ))
    fig.update_layout(mapbox_style="carto-positron",
                      mapbox_zoom=3, mapbox_center = {"lat": 37.0902, "lon": -95.7129})
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    return fig

def getUniqueCounties():
    return sorted(drought_data['county'].unique())

def getSliderMarkerObject():
    datemarker = {}
    for idx,d in enumerate(all_dates):
        if idx % 70 == 0 or idx == len(all_dates) - 1:
            markervalue = {}
            markervalue['label'] = d.strftime('%Y-%m-%d')
            markervalue['style'] = {'color': '#FFFFFF'}
            datemarker[f'{idx}'] = markervalue
    return datemarker

def getStateFromFilesInFolder(filepath):
    state = []
    files = []
    for (dirpath, dirnames, filenames) in walk(filepath):
        files.extend(filenames)
        break
    for file in files:
        state.append(file.partition("_")[0])
    return sorted(set(state))

# Set county FIPS as global variable
counties = geojson()

# Set drought data as global variable
drought_data = droughts()

# Get drought intensity level as global variable
intensity_dropdown = getDroughtIntensityLevel()

# Get unique counties from drought data as global variable
all_counties = getUniqueCounties()

# Select the default first county data as global variable
county_data = drought_data.query('county==@all_counties[0]')

# Build table chart for county as global variable
county_table = getDroughtTable(county_data)

# Build all drought data dates for slider
all_dates = sorted(pd.DatetimeIndex(pd.to_datetime(drought_data['releaseDate'].astype(str), format='%Y%m%d')).unique())

slider_selected_date = all_dates[len(all_dates) - 1].strftime('%Y-%m-%d')

heatmap = getHeatMap(drought_data, all_dates[len(all_dates) - 1], 'D0')

states_dropdown = getStateFromFilesInFolder('states')

backtesting_data = pd.read_csv(f"states/{states_dropdown[0]}_pre.csv")
backtesting_data['ValidStart'] = pd.to_datetime(backtesting_data['ValidStart'])
backtesting_data = backtesting_data.sort_values(by=['ValidStart'], ascending=True)
backtesting_trend = px.line(backtesting_data, x='ValidStart', y='value', color='type', title=f'Training and back-testing')

states_future_dropdown = getStateFromFilesInFolder('states_future')

future_forecast_data = pd.read_csv(f"states_future/{states_future_dropdown[0]}_future.csv")
future_forecast_data['ValidStart'] = pd.to_datetime(future_forecast_data['ValidStart'])
future_forecast_data = future_forecast_data.sort_values(by=['ValidStart'], ascending=True)
future_forecast_trend = px.line(future_forecast_data, x='ValidStart', y='value', color='type', title=f'Future forecast')


colors = {
    'background': '#808080',
    'text': '#FFFFFF',
    'heatmap': '#FFFFFF',
    'headerColor' : 'FFFFFF',
    'rowEvenColor' : 'lightgrey',
    'rowOddColor' : 'white'
}


app.layout = html.Div(style={'backgroundColor': colors['background'],'box-sizing': 'border-box'}, children=[
    html.H1(
        children='US Droughts (2015 - 2020)',
        style={
            'textAlign': 'center',
            'color': colors['text']
        }
    ),
    html.Div(children=[
        html.H2(id='heatmap_selected_date',
                children=f'Heatmap on {slider_selected_date}',
                style={
                    'textAlign': 'center',
                    'color': colors['heatmap']
                }
                ),
        html.Div(children=[
            dcc.Slider(
                id='my-slider',
                min=0,
                max=len(all_dates) - 1,
                value=len(all_dates) - 1,
                marks=getSliderMarkerObject()
            ),
            dcc.Dropdown(
                id='DpercentDropdown',
                options=[{'label': intensity['name'], 'value': intensity['value']} for intensity in intensity_dropdown],
                value='D0'),
            html.Div(id='slider-output-container')]),
        html.Div(children=[
            dcc.Loading(
                id="loading-1",
                type="default",
                children=dcc.Graph(
                    id='drought_heatmap',
                    figure=heatmap
                )
            ),
            dcc.Store(id="heatmap")])

    ]),

    html.Div(children=[
        dcc.Dropdown(
            id='counties-dropdown',
            options=[{'label': county, 'value': county} for county in all_counties],
            value=all_counties[0])

    ]),

    html.Div(children=[
        dcc.Graph(
            id='county_table',
            figure=county_table
        ),
    ]),
    html.Div(children=[
        dcc.Dropdown(
            id='state_dropdown',
            options=[{'label': state, 'value': state} for state in states_dropdown],
            value='CA'),
        dcc.Graph(
            id='backtesting_trend',
            figure=backtesting_trend),
        dcc.Dropdown(
            id='states_future_dropdown',
            options=[{'label': state, 'value': state} for state in states_future_dropdown],
            value='CA'),
        dcc.Graph(
            id='forecast_trend',
            figure=future_forecast_trend)
    ]),
])

server = app.server

@app.callback(
    dash.dependencies.Output('heatmap_selected_date', 'children'),
    [dash.dependencies.Input('my-slider', 'value')])
def update_heatmap_date(value):
    selectDateStr = all_dates[value].strftime('%Y-%m-%d')
    return f'Heatmap on {selectDateStr}'

@cc.cached_callback(Output("heatmap", "data"),
                    [Input('my-slider', 'value'),
                     Input('DpercentDropdown', 'value'),
                     Trigger("my-slider", "value")])  # Trigger is like Input, but excluded from args
def query_data(value, value1):
    tempDate = all_dates[value]
    tempPercent = value1
    return getHeatMap(drought_data, tempDate, tempPercent)

@cc.callback(
    dash.dependencies.Output('drought_heatmap', 'figure'),
    [Input('heatmap', 'data'),
     dash.dependencies.Input('my-slider', 'value'),
     dash.dependencies.Input('DpercentDropdown', 'value')])
def update_heatmap_chart(heatmap, value, value1):
    return heatmap

@app.callback(
    dash.dependencies.Output('county_table', 'figure'),
    [dash.dependencies.Input('counties-dropdown', 'value')])
def update_county_table(value):
    new_county_data = drought_data.query('county==@value')
    return getDroughtTable(new_county_data)

@app.callback(
    dash.dependencies.Output('backtesting_trend', 'figure'),
    [dash.dependencies.Input('state_dropdown', 'value')])
def updatePred(value):
    selected_forecast_data = pd.read_csv(f"states/{value}_pre.csv")
    selected_forecast_data['ValidStart'] = pd.to_datetime(selected_forecast_data['ValidStart'])
    selected_forecast_data = selected_forecast_data.sort_values(by=['ValidStart'], ascending=True)
    return px.line(selected_forecast_data, x='ValidStart', y='value', color='type', title=f'Training and back-testing')

@app.callback(
    dash.dependencies.Output('forecast_trend', 'figure'),
    [dash.dependencies.Input('states_future_dropdown', 'value')])
def updateForecast(value):
    selected_forecast_data = pd.read_csv(f"states_future/{value}_future.csv")
    selected_forecast_data['ValidStart'] = pd.to_datetime(selected_forecast_data['ValidStart'])
    selected_forecast_data = selected_forecast_data.sort_values(by=['ValidStart'], ascending=True)
    return px.line(selected_forecast_data, x='ValidStart', y='value', color='type', title=f'Future forecast')


cc.register(app)

if __name__ == '__main__':
    app.run_server(debug=False)

