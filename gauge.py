# import plotly.plotly as py
import plotly.graph_objs as go

base_chart = {
    "values": [14, 14, 14, 14, 14, 30],
    "labels": ["Very poor", "Poor", "Avrage", "Good", "Excellent", " "],
    # "domain": {"x": [0, .48]},
    "marker": {
        "colors": [
            "rgb(229, 60, 26)",
            "rgb(229, 128, 26)",
            "rgb(229, 161, 26)",
            "rgb(183, 210, 45)",
            "rgb(72, 210, 45)",
            'rgba(255, 255, 255, 0)'
        ],
        "line": {
            "width": 1,
            "color": "black"
        }
    },
    "name": "Gauge",
    "hole": .75,
    "type": "pie",
    "direction": "clockwise",
    "rotation": -126,
    # "rotation": 108,
    "sort": False,
    "showlegend": False,
    "hoverinfo": "none",
    "textinfo": "none",
    "textposition": "outside"
}

meter_chart = {
    "values": [50, 10, 10, 10, 10, 10],
    "labels": ["Log Level", "Debug", "Info", "Warn", "Error", "Fatal"],
    "marker": {
        'colors': [
            'rgb(255, 255, 255)',
            'rgb(232,226,202)',
            'rgb(226,210,172)',
            'rgb(223,189,139)',
            'rgb(223,162,103)',
            'rgb(226,126,64)'
        ]
    },
    "domain": {"x": [0, 0.48]},
    "name": "Gauge",
    "hole": .8,
    "type": "pie",
    "direction": "clockwise",
    "rotation": 90,
    "showlegend": False,
    "textinfo": "label",
    "textposition": "inside",
    "hoverinfo": "none"
}

layout = {
    'xaxis': {
        'showticklabels': False,
        'showgrid': False,
        'zeroline': False,
        "visible": True,
        "range": [-1.1, 1.1]
    },
    'yaxis': {
        'showticklabels': False,
        'showgrid': False,
        'zeroline': False,
        "visible": True,
        "range": [-1.1, 1.1]
    },
    'shapes': [
        {
            'type': 'line',
            'x0': 0,
            'y0': 0,
            'x1': -10,
            'y1': 0,
            'fillcolor': 'red'

        }
    ]
    # 'annotations': [
    #     {
    #         'xref': 'paper',
    #         'yref': 'paper',
    #         'x': 0.23,
    #         'y': 0.45,
    #         'text': '50',
    #         'showarrow': False
    #     }
    # ]
}

# base_chart['marker']['line']['width'] = 0

fig = go.Figure({"data": [base_chart],
       "layout": layout})

fig.show()
