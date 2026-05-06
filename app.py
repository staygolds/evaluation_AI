import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- ページ基本設定 ---
st.set_page_config(page_title="福祉施設 AI評価システム", layout="wide")

# --- データの読み込み関数 ---
@st.cache_data
def load_data():
    # GitHubリポジトリ直下のCSVファイルを読み込みます
    # Googleスプレッドシート形式のUTF-8を想定しています
    staff = pd.read_csv('m_staff.csv', encoding='utf-8')
    missions = pd.read_csv('m_missions.csv', encoding='utf-8')
    criteria = pd.read_csv('m_evaluation_criteria.csv', encoding='utf-8')
    return staff, missions, criteria

try:
    df_staff, df_missions, df_criteria = load_data()
except Exception as e:
    st.error(f"CSVファイルの読み込みに失敗しました。ファイル名を確認してください: {e}")
    st.stop()

# --- サイドバー：評価対象者の選択 ---
st.sidebar.header("評価対象者の選択")
staff_names = df_staff['氏名'].tolist()
selected_name = st.sidebar.selectbox("職員を選んでください", staff_names)

# --- 重要：.iloc を使用してエラーを回避 ---
# 選択された職員の情報を「職員マスター」から1行分取得 [1]
staff_matches = df_staff[df_staff['氏名'] == selected_name]
if not staff_matches.empty:
    staff_info = staff_matches.iloc # ここをにすることでSeriesとして取得
    staff_id = staff_info['職員ID']
    job_type = staff_info['職種区分']
    qualifications = staff_info['保有資格']
else:
    st.error("職員情報が見つかりません。")
    st.stop()

# 職員IDをキーに「職務分掌マスター」からミッション情報を取得 [2]
mission_matches = df_missions[df_missions['職員ID'] == staff_id]
if not mission_matches.empty:
    mission_info = mission_matches.iloc # ここもで確定させる
    main_mission = mission_info['重要ミッション']
    target_metric = mission_info['主要数値目標']
    target_value = mission_info['目標値']
else:
    main_mission = "未設定"
    target_metric = "未設定"
    target_value = "-"

# --- メイン画面：基本情報の表示 ---
st.title(f"📊 AI分析レポート作成: {selected_name} さん")

col1, col2 = st.columns(2)
with col1:
    st.subheader("👤 職員プロフィール")
    st.write(f"**職種区分:** {job_type}") [1]
    st.write(f"**保有資格:** {qualifications}") [1]
with col2:
    st.subheader("🎯 今期のミッション")
    st.info(f"**最優先事項:**\n{main_mission}") [2]
    st.write(f"**数値目標:** {target_metric} ({target_value})") [2]

st.divider()

# --- 評価入力セクション ---
st.subheader(f"✅ {job_type}職 評価項目入力")
# 職種区分（幹部、事務、医務、支援など）に一致する20項目を抽出 [3]
relevant_criteria = df_criteria[df_criteria['職種区分'] == job_type]

scores = {}
if not relevant_criteria.empty:
    for _, item in relevant_criteria.iterrows():
        # 各項目（例：伝票処理の正確性など）をスライダーで入力 [4], [3]
        scores[item['評価項目名']] = st.slider(item['評価項目名'], 1, 5, 3)
else:
    st.warning(f"「{job_type}」職用の評価項目が見つかりません。マスターデータを確認してください。")

# --- AI分析実行 ---
if st.button("🚀 AI分析レポートを生成する"):
    # 入力された点数リストを作成
    eval_text = "\n".join([f"- {k}: {v}点" for k, v in scores.items()])
    
    # AIへのプロンプト組み立て
    prompt = f"""
    あなたは社会福祉施設の経営人事エキスパートです。
    以下のソース資料データに基づき、職員の能力開発と施設目標達成のための個別分析レポートを作成してください。

    # 職員プロフィール
    - 氏名：{selected_name}
    - 職種：{job_type}
    - 保有資格：{qualifications}

    # 今期の最優先ミッションと数値目標
    - 重要ミッション：{main_mission}
    - 主要数値目標：{target_metric} ({target_value})

    # 今回の行動評価結果（5点満点）
    {eval_text}

    # レポート構成
    1. 【現状の総評】
    2. 【強みの分析】（保有資格やミッションへの貢献度を踏まえて）
    3. 【課題と改善アドバイス】（重要ミッション達成に向けた具体的な行動提案）
    4. 【本人へのフィードバックメッセージ】
    """

    try:
        # StreamlitのSecretsからAPIキーを取得
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner('AIがソース資料を基に分析中...'):
            response = model.generate_content(prompt)
            st.success("分析が完了しました！")
            st.markdown("---")
            st.markdown(response.text)
    except Exception as e:
        st.error("AI分析中にエラーが発生しました。SettingsのSecretsにAPIキーが正しく設定されているか確認してください。")
