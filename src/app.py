import pandas as pd
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import folium
from folium.plugins import HeatMap

# Add the specified path
data_path = r'C:/Users/Biu9/OneDrive - CDC/Python files/Colombia/Data/Suicidios_Colombia_2016_2019_merged.xlsx'

# Load the dataset
df = pd.read_excel(data_path)

# Ensure the latitude and longitude columns are properly named and exist
assert 'LATITUD' in df.columns and 'LONGITUD' in df.columns, "Latitude and Longitude columns are required"

# Normalize the 'Dia del hecho' column to have consistent capitalization and fix misspellings
df['Dia del hecho'] = df['Dia del hecho'].str.capitalize()
df['Dia del hecho'] = df['Dia del hecho'].replace({
    'Miercoles': 'Miércoles',
    'jueves': 'Jueves',
    'sabado': 'Sábado',
    'viernes': 'Viernes',
    'lunes': 'Lunes',
    'martes': 'Martes',
    'domingo': 'Domingo',
    'miercoles': 'Miércoles'
})

# Sort the days of the week in the correct Spanish order
spanish_days_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
df['Dia del hecho'] = pd.Categorical(df['Dia del hecho'], categories=spanish_days_order, ordered=True)

# Exclude age groups '05 a 09' and '10 a 14', and groups less than 5 years old
exclude_age_groups = ['Menor de 1 año', '1 a 4', '05 a 09', '10 a 14']
df = df[~df['Grupo de edad de la victima'].isin(exclude_age_groups)]

# Filter the dataframe to get only the necessary columns and drop rows with missing values
df = df[['LATITUD', 'LONGITUD', 'DEPARTAMENTO', 'Sexo de la victima', 'Dia del hecho', 'Grupo de edad de la victima']].dropna()

# Initialize the Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.SOLAR])
server = app.server

app.layout = html.Div([
    html.H1("Mapa de Calor para Casos de Suicidio en Colombia entre 2016 y 2019", style={'color': '#FFFFE0'}),  # Title color adjusted to light yellow
    html.A("Datos Abiertos: Suicidio", href="https://www.datos.gov.co/Justicia-y-Derecho/Suicidios-Colombia-a-os-2016-a-2019/f75u-mirk/about_data",
           style={'color': '#FFFFE0', 'float': 'right', 'fontSize': '12px', 'margin': '10px'}),
    dbc.Row([
        dbc.Col([
            html.Label('Departamento', style={'color': '#FFFFE0'}),
            dcc.Dropdown(
                id='departamento-dropdown',
                options=[{'label': departamento, 'value': departamento} for departamento in df['DEPARTAMENTO'].unique()] + [{'label': 'All', 'value': 'All'}],
                value=['All'],
                multi=True,
                style={'width': '100%'}
            ),
        ], width=6),
        dbc.Col([
            html.Label('Sexo de la victima', style={'color': '#FFFFE0'}),
            dcc.Dropdown(
                id='sexo-dropdown',
                options=[{'label': sexo, 'value': sexo} for sexo in df['Sexo de la victima'].unique()] + [{'label': 'All', 'value': 'All'}],
                value=['All'],
                multi=True,
                style={'width': '60%'}  # Adjusted width to fit content
            ),
        ], width=6),
    ]),
    html.Div([
        html.Label('Día del hecho', style={'marginTop': '10px', 'color': '#FFFFE0'}),
        dbc.Checklist(
            id='dia-toggle',
            options=[{'label': dia, 'value': dia} for dia in spanish_days_order],
            value=[],  # Initially turn off all toggle options
            inline=True,
            switch=True,
            style={'color': '#FFFFE0'}  # Added light yellow color for labels
        ),
    ], style={'marginBottom': '20px'}),  # Increased margin between rows
    html.Div([
        html.Label('Grupo de edad de la victima', style={'marginTop': '10px', 'color': '#FFFFE0'}),
        dbc.Checklist(
            id='edad-toggle',
            options=[{'label': edad, 'value': edad} for edad in df['Grupo de edad de la victima'].unique()],
            value=[],  # Initially turn off all toggle options
            inline=True,
            switch=True,
            style={'color': '#FFFFE0'}  # Added light yellow color for labels
        ),
    ], style={'marginBottom': '20px'}),  # Increased margin between rows
    html.Div(id='map-container', style={'marginTop': '30px', 'width': '70%', 'height': '630px', 'margin': 'auto', 'float': 'left'})
])

@app.callback(
    Output('map-container', 'children'),
    [Input('departamento-dropdown', 'value'),
     Input('sexo-dropdown', 'value'),
     Input('dia-toggle', 'value'),
     Input('edad-toggle', 'value')]
)
def update_map(selected_departamentos, selected_sexos, selected_dias, selected_edades):
    # Set default values for inputs if they are None
    selected_departamentos = selected_departamentos or []
    selected_sexos = selected_sexos or []
    selected_dias = selected_dias or []
    selected_edades = selected_edades or []

    filtered_df = df
    if 'All' not in selected_departamentos:
        filtered_df = filtered_df[filtered_df['DEPARTAMENTO'].isin(selected_departamentos)]
    if 'All' not in selected_sexos:
        filtered_df = filtered_df[filtered_df['Sexo de la victima'].isin(selected_sexos)]
    if selected_dias:
        filtered_df = filtered_df[filtered_df['Dia del hecho'].isin(selected_dias)]
    if selected_edades:
        filtered_df = filtered_df[filtered_df['Grupo de edad de la victima'].isin(selected_edades)]

    if 'All' in selected_departamentos:
        center_lat = 4.5709
        center_lon = -74.2973
    else:
        center_lat = filtered_df['LATITUD'].mean()
        center_lon = filtered_df['LONGITUD'].mean()

    # Create a base map centered on selected departamentos or Colombia
    colombia_map = folium.Map(location=[center_lat, center_lon], zoom_start=6)

    # Create a list of locations for the heat map
    heat_data = [[row['LATITUD'], row['LONGITUD']] for index, row in filtered_df.iterrows()]

    # Define a regular gradient for the heat map
    gradient = {
        0.0: 'blue',
        0.4: 'lime',
        0.6: 'yellow',
        0.8: 'orange',
        1.0: 'red'
    }

    # Add the heat map layer with adjusted parameters and custom gradient
    HeatMap(heat_data, radius=15, blur=10, max_zoom=12, gradient=gradient).add_to(colombia_map)

    # Ensure the map fits the canvas properly
    map_html = colombia_map.get_root().render()

    return html.Iframe(srcDoc=map_html, width='100%', height='100%')

if __name__ == '__main__':
    app.run_server(debug=False)
