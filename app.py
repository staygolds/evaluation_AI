import streamlit as st
import pandas as pd
import google.generativeai as genai
import tempfile
from datetime import datetime

# PDF用
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.pagesizes import A4


# ==================================================
# 1. ページ設定
# ==================================================

st.set_page_config(
    page_title="福祉施設 AI評価システム",
    layout="wide"
)


# ==================================================
# 2. APIキー入力
# ==================================================

st.sidebar.header("Gemini API設定")

GOOGLE_API_KEY = st.sidebar.text_input(
    "Gemini APIキーを入力",
    type="password"
)

if not GOOGLE_API_KEY:

    st.warning("Gemini APIキーを入力してください。")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)


# ==================================================
# 3. PDFフォント登録
# ==================================================

pdfmetrics.registerFont(
    UnicodeCIDFont('HeiseiKakuGo-W5')
)


# ==================================================
# 4. PDF生成関数
# ==================================================

def create_pdf(report_text, staff_name):

    tmp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    )

    doc = SimpleDocTemplate(
        tmp_file.name,
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    style = styles["BodyText"]
    style.fontName = "HeiseiKakuGo-W5"
    style.fontSize = 12
    style.leading = 20

    elements = []

    title = Paragraph(
        f"{staff_name} さん 評価レポート",
        style
    )

    elements.append(title)
    elements.append(Spacer(1, 20))

    cleaned_text = (
        report_text
        .replace("##", "")
        .replace("#", "")
        .replace("**", "")
    )

    lines = cleaned_text.split("\n")

    for line in lines:

        if line.strip() != "":

            paragraph = Paragraph(
                line,
                style
            )

            elements.append(paragraph)
            elements.append(Spacer(1, 10))

    doc.build(elements)

    return tmp_file.name


# ==================================================
# 5. CSV読み込み
# ==================================================

@st.cache_data
def load_data():

    try:

        staff = pd.read_csv(
            'm_staff.csv',
            encoding='utf-8'
        )

        missions = pd.read_csv(
            'm_missions.csv',
            encoding='utf-8'
        )

        criteria = pd.read_csv(
            'm_evaluation_criteria.csv',
            encoding='utf-8'
        )

        return staff, missions, criteria

    except Exception as e:

        st.error(
            f"CSVファイルの読み込みに失敗しました: {e}"
        )

        st.stop()


df_staff, df_missions, df_criteria = load_data()


# ==================================================
# 6. 職種マッピング
# ==================================================

job_category_mapping = {

    '管理者': '幹部',
    '副管理者兼サービス管理責任者': '幹部',

    '主任事務員': '事務',
    '事務員': '事務',

    '主任看護師': '医務',
    '看護師': '医務',

    '主任生活支援員': '幹部',
    '副主任生活支援員': '幹部',

    '生活支援員': '支援',

    '主任管理栄養士': '栄養',
    '管理栄養士': '栄養',

    '主任調理員': '栄養',
    '調理員': '栄養',

    '主任相談支援専門員': '支援',
    '相談支援専門員': '支援',

    '相談員': '支援'
}


# ==================================================
# 7. 評価対象者選択
# ==================================================

st.sidebar.header("評価対象者の選択")

selected_name = st.sidebar.selectbox(
    "職員を選んでください",
    df_staff['氏名'].tolist()
)


# ==================================================
# 8. 職員情報取得
# ==================================================

staff_info = df_staff[
    df_staff['氏名'] == selected_name
].iloc[0]

staff_id = staff_info['職員ID']
job_title = staff_info['職種区分']
department = staff_info['所属部署']
qualifications = staff_info['保有資格']


# ==================================================
# 9. ミッションデータ取得（複数行対応）
# ==================================================

mission_data = df_missions[
    df_missions['職員ID'] == staff_id
]

if mission_data.empty:

    mission_data = None


# ==================================================
# 10. メイン表示
# ==================================================

st.title(
    f"📊 AI分析レポート作成: {selected_name} さん"
)

col1, col2 = st.columns(2)

with col1:

    st.write(f"**役職:** {job_title}")
    st.write(f"**所属:** {department}")

with col2:

    st.write(f"**資格:** {qualifications}")


st.divider()


# ==================================================
# 11. 職務分掌・達成度入力
# ==================================================

st.subheader("📌 職務分掌・達成度評価")

mission_text = ""

mission_scores = {}

if mission_data is not None:

    for index, row in mission_data.iterrows():

        basic_job = (
            str(row['基本職務内容'])
            if pd.notna(row['基本職務内容'])
            else ""
        )

        mission = (
            str(row['重要ミッション'])
            if pd.notna(row['重要ミッション'])
            else ""
        )

        kpi = (
            str(row['主要数値目標'])
            if pd.notna(row['主要数値目標'])
            else ""
        )

        target = (
            str(row['目標値'])
            if pd.notna(row['目標値'])
            else ""
        )

        st.markdown("---")

        st.markdown(f"### ■ {basic_job}")

        if mission != "":
            st.write(f"重要ミッション: {mission}")

        if kpi != "":
            st.write(f"数値目標: {kpi}")

        if target != "":
            st.write(f"目標値: {target}")

        # 達成度入力
        achievement = st.select_slider(
            f"{basic_job} の達成度",
            options=[
                0,
                10,
                20,
                30,
                40,
                50,
                60,
                70,
                80,
                90,
                100
            ],
            value=50,
            key=f"mission_{index}"
        )

        mission_scores[basic_job] = achievement

        mission_text += f"""
■ 基本職務内容
{basic_job}

■ 重要ミッション
{mission}

■ 数値目標
{kpi}

■ 目標値
{target}

■ 達成度
{achievement}%

----------------------------
"""

else:

    st.warning("職務分掌データがありません")


# ==================================================
# 12. 評価項目
# ==================================================

if department == "初任者":

    search_category = "新任"

else:

    search_category = job_category_mapping.get(
        job_title,
        "支援"
    )


relevant_criteria = df_criteria[
    df_criteria['職種区分'] == search_category
]


scores = {}

if not relevant_criteria.empty:

    st.subheader(
        f"✅ {search_category}職 評価項目入力"
    )

    for _, item in relevant_criteria.iterrows():

        scores[item['評価項目名']] = st.slider(
            item['評価項目名'],
            1,
            5,
            3
        )

    total_score = sum(scores.values())

    max_score = len(relevant_criteria) * 5

    st.sidebar.markdown("---")

    st.sidebar.metric(
        label="行動評価 合計点",
        value=f"{total_score} / {max_score}"
    )

else:

    st.warning(
        "対応する評価項目が見つかりません。"
    )


# ==================================================
# 13. 面接者所感
# ==================================================

st.subheader("📝 面接者所感")

interviewer_comments = st.text_area(
    "面接での気づきやフィードバック、本人への期待を入力してください",
    placeholder="例：数値目標への意識が高く、周囲への働きかけも積極的である。",
    height=150
)


# ==================================================
# 14. AI分析
# ==================================================

if st.button("🚀 AI分析レポートを生成する"):

    if not scores:

        st.error(
            "評価項目が入力されていません。"
        )

    else:

        eval_details = "\n".join(
            [
                f"- {k}: {v}点"
                for k, v in scores.items()
            ]
        )

        prompt = f"""
あなたは社会福祉法人の人事評価専門AIです。

以下の情報を基に、
総合的人事評価レポートを作成してください。

# 職員情報

氏名:
{selected_name}

役職:
{job_title}

所属:
{department}

資格:
{qualifications}

# 職務分掌・達成度評価

{mission_text}

# 行動評価

合計点:
{total_score}/{max_score}点

項目別詳細:
{eval_details}

# 面接者所感

{interviewer_comments}

# 分析観点

以下を総合的に分析してください。

・職務責任遂行能力
・重点ミッションへの取り組み
・達成度の妥当性
・管理能力
・対人支援力
・組織運営力
・リーダーシップ
・今後期待される役割
・強み
・改善点

# レポート構成

1. 総評
2. 強み
3. 改善点
4. 今後への期待

1200文字以内で、
具体的かつ専門的に作成してください。
"""

        try:

            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash"
            )

            with st.spinner(
                "AIが分析中です..."
            ):

                response = model.generate_content(
                    prompt,
                    generation_config={

                        "temperature": 0.5,
                        "max_output_tokens": 4096,
                    }
                )

            st.success("分析完了")

            st.markdown("---")

            if response.candidates:

                st.write(response.text)

                # PDF生成
                pdf_path = create_pdf(
                    response.text,
                    selected_name
                )

                # 日付
                today_str = datetime.now().strftime(
                    "%Y%m%d"
                )

                # ダウンロード
                with open(pdf_path, "rb") as file:

                    st.download_button(
                        label="📄 PDFダウンロード",
                        data=file,
                        file_name=f"{today_str}_{selected_name}_評価レポート.pdf",
                        mime="application/pdf"
                    )

            else:

                st.error(
                    "AIから応答がありませんでした"
                )

        except Exception as e:

            st.error(
                f"AI分析中にエラーが発生しました: {e}"
            )
