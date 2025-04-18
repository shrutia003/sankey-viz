import pandas as pd
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State
import dash_bootstrap_components as dbc

sankey_df = pd.read_csv("data/Preprocessed_Sankey_Data.csv")
merged_df = pd.read_csv("data/Merged_Reviews_With_Features.csv.gz", compression="gzip", parse_dates=["Date", "Release Date"])
features_df = pd.read_csv("data/Features1.csv", encoding='latin1', parse_dates=["Release Date"])

def truncate_label(text, length=40):
    return text if len(text) <= length else text[:length] + '...'

feature_titles = sankey_df['Feature Title'].unique().tolist()
clusters = sankey_df['Cluster'].unique().tolist()

truncated_features = [truncate_label(t) for t in feature_titles]
label_map = {truncate_label(t): t for t in feature_titles}

all_labels = truncated_features + clusters
label_to_index = {label: idx for idx, label in enumerate(all_labels)}
index_to_label = {idx: label for label, idx in label_to_index.items()}

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.layout = dbc.Container([
    html.H2("Feature ↔ Review Cluster Sankey Diagram"),
    dcc.Dropdown(
        id="filter-dropdown",
        options=[
            {"label": f, "value": f}
            for f in sorted(sankey_df['Filter'].unique())
            if f not in ["All Time", "Within 2 Weeks"]
        ],
        value=["All Time"],
        multi=True,
        placeholder="Select time period(s)..."
    ),
    html.Br(),
    dbc.Row([
        dbc.Col(dcc.Graph(id="sankey-graph"), width=8),
        dbc.Col([
            html.Div(id="feature-card", children=[
                html.H5("Feature Details", className="card-title"),
                html.H4(id="feature-title", className="mt-2"),
                html.P(id="feature-app", style={"fontStyle": "italic"}),
                html.P(id="release-date"),
                dcc.Graph(id="trend-graph", config={"displayModeBar": False}, style={"height": "200px"}),
                html.P(id="within-2wk-summary", style={"fontWeight": "bold"})
            ], className="p-3 border rounded")
        ], width=4)
    ])
], fluid=True)

def get_sankey_data(df):
    source_ids = df['Feature Title'].map(lambda x: label_to_index[truncate_label(x)]).tolist()
    target_ids = df['Cluster'].map(lambda x: label_to_index[x]).tolist()
    values = df['Value'].tolist()
    customdata = df['Feature Title'].tolist()
    return dict(source=source_ids, target=target_ids, value=values, customdata=customdata)

@app.callback(
    Output("sankey-graph", "figure"),
    Input("filter-dropdown", "value"),
    prevent_initial_call=False
)
def update_sankey(selected_filters):
    filtered = sankey_df[sankey_df["Filter"].isin(selected_filters)]
    sankey_data = get_sankey_data(filtered)

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            label=all_labels,
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5)
        ),
        link=dict(
            source=sankey_data['source'],
            target=sankey_data['target'],
            value=sankey_data['value'],
            customdata=sankey_data['customdata'],
            hovertemplate="Feature: %{customdata}<extra></extra>"
        )
    )])

    fig.update_layout(transition=dict(duration=0), margin=dict(t=20, l=10, r=10, b=10))
    return fig

@app.callback(
    Output("feature-title", "children"),
    Output("feature-app", "children"),
    Output("release-date", "children"),
    Output("within-2wk-summary", "children"),
    Output("trend-graph", "figure"),
    Input("sankey-graph", "clickData"),
    State("filter-dropdown", "value"),
    prevent_initial_call=True
)
def update_feature_card(clickData, selected_filters):
    if not clickData or "points" not in clickData or "customdata" not in clickData["points"][0]:
        return "Click a feature node to see details", "", go.Figure()

    full_feature = clickData["points"][0]["customdata"]

    if isinstance(selected_filters, list):
        filtered = merged_df[merged_df["Review Period"].isin(selected_filters)]
    else:
        filtered = merged_df.copy() if selected_filters == "All Time" else (
            merged_df[merged_df["Within2Weeks"]] if selected_filters == "Within 2 Weeks" else merged_df[merged_df["Review Period"] == selected_filters]
        )

    df = filtered[filtered["Feature Title"] == full_feature]
    
    if df.empty:
        return f"No review data for {full_feature}", "", go.Figure()
    
    app_name = df["App_x"].iloc[0] if "App_x" in df.columns else "Unknown App"
    rel_date_row = features_df[features_df['Feature Title'] == full_feature]
    release_date = rel_date_row.iloc[0]['Release Date'] if not rel_date_row.empty else pd.NaT
    app_name = f"App: {app_name}"
    release_str = f"Release Date: {release_date.strftime('%b %d, %Y')}" if pd.notnull(release_date) else "Release Date: Unknown"
    
    total = df.shape[0]
    two_weeks = df["Within2Weeks"].sum()
    percent = (two_weeks / total) * 100 if total > 0 else 0
    percent_str = f"{two_weeks}/{total} reviews ({percent:.1f}%) within 2 weeks"

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    trend_data = df.groupby(df["Date"].dt.to_period("W")).size().reset_index(name="Reviews")
    trend_data["Date"] = trend_data["Date"].dt.start_time

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=trend_data["Date"],
        y=trend_data["Reviews"],
        mode="lines+markers",
        name="Reviews"
    ))
    fig.update_layout(title="Reviews Over Time", margin=dict(t=30, l=10, r=10, b=30), height=200)

    return full_feature, app_name, release_str, percent_str, fig

server = app.server
