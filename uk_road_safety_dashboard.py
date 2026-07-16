# -*- coding: utf-8 -*-
"""
UK 2016 Trafik Kazası Analizi - Dinamik İnteraktif Dashboard
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.colab import drive

# ── 1. GOOGLE DRIVE MOUNT ───────────────────────────────────────────────────
drive.mount('/content/drive')

# ── 2. VERİ YÜKLEME ──────────────────────────────────────────────────────────
accidents  = pd.read_csv('/content/drive/MyDrive/accidents_2016.csv',  low_memory=False)
vehicles   = pd.read_csv('/content/drive/MyDrive/vehicles_2016.csv',   low_memory=False)

# ── 3. ETİKETLEME VE VERİ DÖNÜŞTÜRME ───────────────────────────────────────
severity_map = {1: 'Ölümlü', 2: 'Ağır Yaralı', 3: 'Hafif Yaralı'}
accidents['Severity_Label'] = accidents['Accident_Severity'].map(severity_map)

hava_map = {
    1:'Açık', 2:'Yağmurlu', 3:'Karlı',
    4:'Açık (Rüzgarlı)', 5:'Yağmurlu (Rüzgarlı)',
    6:'Karlı (Rüzgarlı)', 7:'Sisli', 8:'Diğer', 9:'Bilinmiyor', -1:'Eksik'
}
accidents['Weather_Label'] = accidents['Weather_Conditions'].map(hava_map)

arac_map = {
    1:'Bisiklet', 2:'Motosiklet (≤50cc)', 3:'Motosiklet (≤125cc)',
    4:'Motosiklet (125-500cc)', 5:'Motosiklet (>500cc)',
    8:'Taksi', 9:'Otomobil', 10:'Minibüs', 11:'Otobüs',
    17:'Tarım Aracı', 19:'Hafif Ticari', 20:'Ağır Ticari (3.5-7.5t)',
    21:'Ağır Ticari (>7.5t)', 22:'Engelli Scooter', 90:'Diğer'
}
vehicles['Vehicle_Label'] = vehicles['Vehicle_Type'].map(arac_map)

# Tarih ve Saat İşlemleri
accidents['Date'] = pd.to_datetime(accidents['Date'], dayfirst=True)
accidents['Hour'] = pd.to_datetime(accidents['Time'], format='%H:%M', errors='coerce').dt.hour
accidents['Month'] = accidents['Date'].dt.month

ay_isimleri = {1:'Oca',2:'Şub',3:'Mar',4:'Nis',5:'May',6:'Haz',
               7:'Tem',8:'Ağu',9:'Eyl',10:'Eki',11:'Kas',12:'Ara'}

# ── 4. MERGE VE SABİT METRİKLERİN HAZIRLANMASI ──────────────────────────────
acc_veh = pd.merge(
    accidents,
    vehicles[['Accident_Index', 'Vehicle_Label']],
    on='Accident_Index', how='left'
)

# Panel 2: Hava x Şiddet Dağılımı (Sabit Panel)
hava_pct = (accidents
    .query("Weather_Label not in ['Bilinmiyor','Eksik','Diğer']")
    .groupby(['Weather_Label', 'Severity_Label'])
    .size()
    .reset_index(name='Adet'))
hava_toplam = hava_pct.groupby('Weather_Label')['Adet'].transform('sum')
hava_pct['Yuzde'] = (hava_pct['Adet'] / hava_toplam * 100).round(1)

# Panel 3: Araç Türüne Göre Ölümlü Oran (Sabit Panel)
veh_sev = (acc_veh
    .groupby('Vehicle_Label')['Accident_Severity']
    .agg(Toplam='count', Olumlu=lambda x: (x == 1).sum())
    .reset_index())
veh_sev['Olumlu_Oran'] = (veh_sev['Olumlu'] / veh_sev['Toplam'] * 100).round(2)
veh_sev = (veh_sev
    .dropna(subset=['Vehicle_Label'])
    .query('Toplam >= 200')
    .sort_values('Olumlu_Oran'))

ort = veh_sev['Olumlu_Oran'].mean()
renkler_arac = ['#e74c3c' if v > 2 else '#e67e22' if v > 1 else '#3498db' for v in veh_sev['Olumlu_Oran']]

col_sev = {'Ölümlü': '#e74c3c', 'Ağır Yaralı': '#e67e22', 'Hafif Yaralı': '#3498db'}

# ── 5. DASHBOARD KURULUMU (MAKE_SUBPLOTS) ───────────────────────────────────
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=[
        'Saate Göre Kaza Sayısı',
        'Hava Koşuluna Göre Kaza Şiddeti (%)',
        'Araç Türüne Göre Ölümlü Kaza Oranı (%)',
        'Aylık Kaza Trendi ve Ölümlü Oran'
    ],
    specs=[
        [{'type': 'bar'},  {'type': 'bar'}],
        [{'type': 'bar'},  {'secondary_y': True}]
    ],
    vertical_spacing=0.18,
    horizontal_spacing=0.12,
)

hava_listesi = [
    'Tümü', 'Açık', 'Yağmurlu', 'Sisli',
    'Karlı', 'Açık (Rüzgarlı)', 'Yağmurlu (Rüzgarlı)', 'Karlı (Rüzgarlı)'
]

panel1_trace_idx = []
panel4_bar_idx   = []
panel4_line_idx  = []

# ── Panel 1 & Panel 4 için Hava Koşuluna Göre Trace'lerin Eklenmesi ────────
for hava in hava_listesi:
    df_h = accidents if hava == 'Tümü' else accidents[accidents['Weather_Label'] == hava]

    # Panel 1: Saate Göre Kaza
    h_df = df_h['Hour'].value_counts().sort_index().reset_index()
    h_df.columns = ['Saat', 'Adet']

    fig.add_trace(go.Bar(
        x=h_df['Saat'], y=h_df['Adet'],
        marker_color='#3498db', marker_opacity=0.8,
        name=f'Kaza — {hava}',
        hovertemplate='<b>%{x}:00</b><br>Kaza: %{y:,}<extra></extra>',
        showlegend=False, visible=(hava == 'Tümü')
    ), row=1, col=1)
    panel1_trace_idx.append(len(fig.data) - 1)

    # Panel 4: Aylık Kaza + Ölümlü Oran
    m_df = (df_h.groupby('Month')
        .agg(Kaza=('Accident_Index','count'), Olumlu=('Accident_Severity', lambda x: (x==1).sum()))
        .reset_index())
    m_df['Olumlu_Oran'] = (m_df['Olumlu'] / m_df['Kaza'] * 100).round(2)
    m_df['Ay_Ad']       = m_df['Month'].map(ay_isimleri)

    fig.add_trace(go.Bar(
        x=m_df['Ay_Ad'], y=m_df['Kaza'],
        name=f'Aylık Kaza — {hava}',
        marker_color='#3498db', marker_opacity=0.7,
        hovertemplate='<b>%{x}</b><br>Kaza: %{y:,}<extra></extra>',
        showlegend=False, visible=(hava == 'Tümü')
    ), secondary_y=False, row=2, col=2)
    panel4_bar_idx.append(len(fig.data) - 1)

    fig.add_trace(go.Scatter(
        x=m_df['Ay_Ad'], y=m_df['Olumlu_Oran'],
        name=f'Ölümlü Oran — {hava}',
        mode='lines+markers',
        line=dict(color='#e74c3c', width=2.5),
        marker=dict(size=8, color='#e74c3c'),
        hovertemplate='<b>%{x}</b><br>Ölümlü Oran: %{y:.2f}%<extra></extra>',
        showlegend=False, visible=(hava == 'Tümü')
    ), secondary_y=True, row=2, col=2)
    panel4_line_idx.append(len(fig.data) - 1)

# ── Panel 2: Hava x Şiddet (Sabit Trace'ler) ─────────────────────────────────
panel2_trace_idx = []
for sev in ['Ölümlü', 'Ağır Yaralı', 'Hafif Yaralı']:
    veri = hava_pct[hava_pct['Severity_Label'] == sev]
    fig.add_trace(go.Bar(
        x=veri['Yuzde'], y=veri['Weather_Label'],
        name=sev, orientation='h',
        marker_color=col_sev[sev],
        hovertemplate=f'<b>%{{y}}</b><br>{sev}: %{{x:.1f}}%<extra></extra>',
        legendgroup=sev, showlegend=True, visible=True
    ), row=1, col=2)
    panel2_trace_idx.append(len(fig.data) - 1)

# ── Panel 3: Araç Türü x Ölümlü Oran (Sabit Trace) ──────────────────────────
fig.add_trace(go.Bar(
    x=veh_sev['Olumlu_Oran'], y=veh_sev['Vehicle_Label'],
    orientation='h', marker_color=renkler_arac,
    hovertemplate='<b>%{y}</b><br>Ölümlü Oran: %{x:.2f}%<extra></extra>',
    showlegend=False, visible=True
), row=2, col=1)
panel3_trace_idx = [len(fig.data) - 1]

# ── Referans Çizgileri ───────────────────────────────────────────────────────
for saat_val, etiket, renk in [(8, 'Sabah Rush', '#e74c3c'), (17, 'Akşam Rush', '#e67e22')]:
    fig.add_vline(x=saat_val, line_dash='dash', line_color=renk, line_width=1.5,
                  annotation_text=etiket, annotation_position='top right', row=1, col=1)

fig.add_vline(x=ort, line_dash='dot', line_color='black', line_width=1.2,
              annotation_text=f'Ort. {ort:.1f}%', annotation_position='top right', row=2, col=1)

# ── 6. DROPDOWN BUTONLARI VE LAYOUT ──────────────────────────────────────────
toplam_trace = len(fig.data)
butonlar = []

for i, hava in enumerate(hava_listesi):
    gorunurluk = [False] * toplam_trace
    gorunurluk[panel1_trace_idx[i]] = True
    gorunurluk[panel4_bar_idx[i]]   = True
    gorunurluk[panel4_line_idx[i]]  = True

    for idx in panel2_trace_idx + panel3_trace_idx:
        gorunurluk[idx] = True

    butonlar.append(dict(
        label=hava,
        method='update',
        args=[
            {'visible': gorunurluk},
            {'title': {'text': f'UK 2016 Trafik Kazası Analizi — {hava}', 'x': 0.5, 'font': {'size': 16}}}
        ]
    ))

fig.update_layout(
    title=dict(text='UK 2016 Trafik Kazası Analizi — Tümü', x=0.5, font=dict(size=16)),
    template='seaborn',
    height=850,
    barmode='relative', # Panel 2'nin stack olup bozulmasını engeller
    legend=dict(orientation='h', y=-0.12, x=0.5, xanchor='center', font=dict(size=10)),
    margin=dict(t=110, b=110, l=70, r=70),
    updatemenus=[dict(
        buttons=butonlar,
        direction='down',
        showactive=True,
        x=0.0, xanchor='left',
        y=1.14, yanchor='top',
        bgcolor='#ecf0f1',
        bordercolor='#bdc3c7',
        font=dict(size=11)
    )],
    annotations=[
        *[a for a in fig.layout.annotations],
        dict(text='Hava Koşulu:', x=0.0, y=1.18, xref='paper', yref='paper',
             showarrow=False, font=dict(size=11, color='#555'))
    ]
)

# Eksen Tanimlamalari
fig.update_xaxes(title_text='Saat', row=1, col=1)
fig.update_yaxes(title_text='Kaza Sayısı', row=1, col=1)
fig.update_xaxes(title_text='Yüzde (%)', range=[0, 100], row=1, col=2)
fig.update_xaxes(title_text='Ölümlü Oran (%)', row=2, col=1)
fig.update_xaxes(tickangle=-30, row=2, col=2)
fig.update_yaxes(title_text='Kaza Sayısı', secondary_y=False, row=2, col=2)
fig.update_yaxes(title_text='Ölümlü Oran (%)', secondary_y=True, row=2, col=2, range=[0, 3], showgrid=False)

for ann in fig.layout.annotations:
    ann.font.size = 11

# ── 7. GOSTERIM VE KAYIT ────────────────────────────────────────────────────
fig.show()

fig.write_html(
    '/content/drive/MyDrive/uk_road_safety_dashboard_v2.html',
    include_plotlyjs='cdn'
)
print('Dashboard başarıyla kaydedildi.')
