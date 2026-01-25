pip freeze > Requirements.txt

import folium
import streamlit as st
from streamlit_folium import st_folium
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib  # 日本語フォント対応
from folium import Element
import streamlit.components.v1 as components # これを使います

# -----------------------------------------
# 1. データ準備（Rのデータフレーム読み込みを想定）
# -----------------------------------------
# シェープファイルの読み込み
shp1 = gpd.read_file('rcom.shp')

# CSVデータの読み込みと結合
pop20 = pd.read_csv("SB0002_2020_2020_17.csv", skiprows=1, encoding='shift-jis')

# 両方の 'KEY' 列を強制的に「文字列」に変換して揃える
shp1['KEY'] = shp1['KEY'].astype(str)
pop20['KEY'] = pop20['KEY'].astype(str)
# ---------------------------

noto0 = shp1.merge(pop20, on='KEY', sort=False)

# Excelデータの読み込みとフィルタリング
noto = pd.read_excel("notofes.xlsx")

# noto <- noto %>% filter(fes<3)
noto = noto[noto['fes'] < 3]

# -----------------------------------------
# 2. データ加工ロジックの変換
# -----------------------------------------
def get_type(row):
    if pd.isna(row['FES0']):
        return 7
    elif row['FES0'] == "獅子舞":
        return 2
    elif row['FES0'] == "キリコ":
        return 4
    elif row['FES0'] == "キリコ獅子舞":
        return 3
    else:
        return 5

# 関数を適用して新しい列を作成
noto['type'] = noto.apply(get_type, axis=1)

noto0['log_pop'] = np.log10(noto0['pop14'] + noto0['pop9'] + 1)

# --- サイドバーによるフィルタリング ---
# 1. 市町村名の列を指定 (実際のデータに合わせて変更してください)
target_col = 'FES0'  # 例: 'CITY_NAME', '市町村名' など

# 2. 選択肢のリストを作成 (重複なし)
city_list = noto[target_col].unique()

# 3. サイドバーにマルチセレクトボックスを表示
# default=city_list とすることで、最初は「全て選択された状態」にします
selected_cities = st.sidebar.multiselect(
    '表示する祭りを選択してください',
    options=city_list,
    default=city_list
)

# 4. データを選択された祭りだけに絞り込む (サブセット作成)
if selected_cities:
    noto_p = noto[noto[target_col].isin(selected_cities)]
else:
    # 何も選択されていない場合は、データを空にするか、全て表示するか選べます
    # ここでは警告を出して処理を止める例です
    st.warning("市町村が選択されていません。")
    st.stop()

# 1. サイドバーにスライダーを表示
target_col2 = 'month' 
start,stop = st.sidebar.slider('月の範囲を選んでください(0:不明もしくは祭りなし)', 0, 12,(4,10))
months = list(range(start, stop + 1))

# 2. データを選択された月に絞り込む (サブセット作成)
noto_p = noto_p[noto_p[target_col2].isin(months)]
# str.containsではエラーがでる　月ごとに行を形成する必要

# --------------------------------------------------
# 1. 地図の初期化 (notoデータの中心に合わせる)
# --------------------------------------------------
center_lat = noto['lat'].mean()
center_lon = noto['lon'].mean()

print(center_lat)
print(center_lon)
# m = folium.Map(location=[37.3, 137.0], zoom_start=11)
m = folium.Map(location=[center_lat, center_lon], zoom_start=9)

# --------------------------------------------------
# 2. シェープファイルの追加 (ここをシンプルにしました)
# --------------------------------------------------
# 座標系変換 (必須)
if noto0.crs is not None and noto0.crs.to_string() != "EPSG:4326":
    noto0 = noto0.to_crs(epsg=4326)

# シンプルにGeoJsonとして追加 (lambda関数を使わない)
#folium.GeoJson(
#    noto0,
#    name='能登エリア',
#   tooltip=folium.GeoJsonTooltip(fields=['KEY'], aliases=['地域コード:'])
#).add_to(m)

# 色分け(Choropleth)
folium.Choropleth(
    geo_data=noto0,
    data=noto0,
    columns=['KEY', 'log_pop'],
    key_on='feature.properties.KEY',
    fill_color='YlGn',
    fill_opacity=0.5,
    line_weight=0,
    line_opacity=0,
    line_color='transparent',
    legend_name='Log Population'
).add_to(m)

# 凡例 (.legend) を 90度回転させ、位置を調整するCSS
# ※ top や right の数値を変えることで位置を微調整できます
css_style = """
<style>
.legend {
    transform: rotate(90deg);   /* 90度回転して縦にする */
    transform-origin: top right;/* 回転の基準点 */
    
    /* 位置の強制指定 (!important で上書き) */
    top: 50% !important;        /* 画面の縦真ん中あたり */
    right: 30px !important;     /* 右端からの距離 */
    
    /* 見た目の微調整 */
    background-color: white;
    opacity: 0.8;
    padding: 10px;
    border-radius: 5px;
}
/* 文字が回転してしまうので、読みづらい場合は調整が必要ですが、
   単純な回転だと文字も横を向きます */
</style>
"""

# 地図のHTMLヘッダーにCSSを追加
m.get_root().html.add_child(Element(css_style))
# --------------------------------------------------
# 3. マーカーの追加 (あなたの修正済みコード)
# --------------------------------------------------
# --------------------------------------------------
# 色を決める関数 (例: 種類によって色を変える)
# --------------------------------------------------
def get_color(type_value):
    if type_value == "獅子舞":
        return 'red'
    elif type_value == "キリコ":
        return 'blue'
    elif type_value == "キリコ獅子舞":
        return 'green'
    elif type_value == "枠旗":
        return 'yellow'
    else:
        return 'gray' # その他

# --------------------------------------------------
# マーカー追加ループ
# --------------------------------------------------
for index, row in noto_p.iterrows():
    if pd.notna(row['lat']) and pd.notna(row['lon']):
        
        # 1. 色の決定: ここで文字列 ('red'など) を作っておく
        # (例: 'type'列がある場合の例。なければ 'blue' と直接書いてください)
        marker_color = get_color(row.get('FES0', 0)) 
        
        # 2. サイズの決定: ここで数値を作っておく
        marker_radius = row['fes'] *3+2  # 適当な係数で調整
        
        # 名前などのテキスト処理
        name_text = str(row['district']) if pd.notna(row['district']) else ""
        url_text = str(row['Youtube']) if pd.notna(row['Youtube']) else ""

        # 3. CircleMarker (円/点) として追加
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=marker_radius,      # 半径 (ピクセル単位)
            color=marker_color,        # 枠線の色
            fill=True,                 # 塗りつぶしあり
            fill_color=marker_color,   # 塗りつぶしの色
            fill_opacity=0.7,          # 透明度 (0.0~1.0)
            weight=1,                  # 枠線の太さ (0にすると枠線なし)
            tooltip=name_text,
            popup=url_text
        ).add_to(m)

# --------------------------------------------------
# 4. Streamlitでの表示
# --------------------------------------------------
st.title("能登3市3町祭りマップ")
#st.write("能登3市3町祭りマップ")
st.write("〇をクリックし表示されたURLを左下の空欄にコピーしEnterを押すと動画が再生されます")
#st.write("ピンをクリックすると、サイドバーで動画が再生されます。")

# m_html = m._repr_html_()
# components.html(m_html, height=500, width=700)

map_event = st_folium(m, width=700, height=500)

# 7. クリックされた場所を特定して動画を表示
#    サイドバーの下の方にコンテナを作る
st.sidebar.markdown("---")
st.sidebar.subheader("🎥 祭り動画")
video_url = st.sidebar.text_input("URLをコピーしてください")
video_container = st.sidebar.empty()  # 表示領域を確保
st.sidebar.video(video_url)

#if map_event and map_event['last_object_clicked']:
    # クリックされたマーカーの座標を取得
#    clicked_lat = map_event['last_object_clicked']['lat']
#    clicked_lon = map_event['last_object_clicked']['lon']
    
    # その座標を持つ行を noto データから探す
    # (浮動小数点の誤差を考慮して、非常に近い値を探す処理が安全ですが、ここでは完全一致で検索)
#   target_row = noto_p[
#      (noto_p['lat'] == clicked_lat) & 
#      (noto_p['lon'] == clicked_lon)
#    ]
    
#if not target_row.empty:
    # その行のURLを取得 (列名が 'video_url' だと仮定)
    # ※実際のExcelにある列名に変えてください
#    video_url = target_row.iloc[0]['Youtube']
#    fes_name = target_row.iloc[0]['FESname']
        
    # サイドバーに表示
#   st.sidebar.write(f"**選択中:** {fes_name}")
        
#   if pd.notna(video_url):
#       st.sidebar.video(video_url)
#   else:
#       st.sidebar.info("この地点の動画はありません。")
#else:
#    st.sidebar.info("地図上のピンをクリックしてください。")
# --------------------------------------------------