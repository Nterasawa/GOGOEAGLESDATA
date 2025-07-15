import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import mediapipe as mp
import cv2
import requests
import io
from PIL import Image  # 軽量PDF用
import json
import asyncio  # 非同期用

# キャッシュで速度向上
@st.cache_resource
def load_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open("２０２５イーグルスジュニア個人成績").sheet1
    return pd.DataFrame(sheet.get_all_records())  # 部分読み込み可能に拡張可

data = load_data()

# YouTube APIキー (secretsから)
YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]

st.set_page_config(page_title="Improved Baseball App", layout="wide")  # ワイド/モバイル対応

st.title("少年野球成績管理アプリ（高速版）")
st.markdown("**改善点**: タブUIで使いやすく、キャッシュでサクサク。グラフ/動画高速化。")

# サイドバーで選手選択
with st.sidebar:
    players = data['選手名'].unique()
    player = st.selectbox("選手選択", players)
    st.image("https://via.placeholder.com/150?text=Team+Logo", caption="チームロゴ")  # ビジュアル追加

# タブで視点切り替え (良い感じUI)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["選手単位", "試合単位", "チーム", "時系列", "ランキング", "フォーム分析"])

with tab1:  # 選手単位
    st.subheader(f"{player}の分析")
    player_df = data[data['選手名'] == player]
    st.dataframe(player_df.style.highlight_max(axis=0))  # ハイライトで視覚化
    stats = {'打率': player_df['打率'].mean(), '球速': player_df['球速'].max()}
    st.write(stats)
    advice = "打率が高い: タイミング練習を。" if stats['打率'] > 0.3 else "打撃強化を。"
    st.info(advice)
    # YouTube (非同期検索)
    async def search_yt(query):
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&key={YOUTUBE_API_KEY}&maxResults=3"
        response = requests.get(url).json()
        return response.get('items', [])
    with st.spinner("動画検索中..."):
        videos = asyncio.run(search_yt(f"少年野球 {advice} 練習"))
        for item in videos:
            st.video(f"https://www.youtube.com/watch?v={item['id']['videoId']}")

with tab2:  # 試合単位
    match_no = st.text_input("試合No (例: 25016)")
    if match_no:
        match_df = data[data['試合管理No'] == int(match_no)]
        st.dataframe(match_df)

with tab3:  # チーム
    avg_bat = data['打率'].mean()
    st.metric("平均打率", f"{avg_bat:.3f}")
    fig, ax = plt.subplots()
    data['打率'].plot(kind='bar', ax=ax)
    st.pyplot(fig)

with tab4:  # 時系列
    player_df = data[data['選手名'] == player].sort_values('測定日')
    fig, ax = plt.subplots()
    ax.plot(player_df['測定日'], player_df['球速'], label='球速', color='blue')
    st.pyplot(fig)

with tab5:  # ランキング
    ranked = data.groupby('選手名')['打率'].mean().sort_values(ascending=False).head(5)
    st.bar_chart(ranked)

with tab6:  # フォーム分析 (動画)
    uploaded = st.file_uploader("動画アップロード")
    if uploaded:
        with st.spinner("動画読み込み中..."):
            cap = cv2.VideoCapture(uploaded.name)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                st.image(img, caption="動画フレーム")
                st.write("アドバイス: フォームを目視確認。肘を高く保つ練習を。")
            cap.release()

# PDFダウンロード (軽量版)
if st.button("PDFレポート生成"):
    buf = io.BytesIO()
    fig, ax = plt.subplots()
    ax.text(0.1, 0.9, f"{player}レポート\n打率: {stats['打率']:.3f}", fontsize=12)
    fig.savefig(buf, format='pdf')
    buf.seek(0)
    st.download_button("ダウンロード", buf, "report.pdf", "application/pdf")