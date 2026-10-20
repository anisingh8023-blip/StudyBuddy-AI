import hashlib
import streamlit as st
import re
from io import BytesIO
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from google import genai

st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="📚",
    layout="wide"
)

st.title("📚 StudyBuddy AI")
st.subheader("Your Personal AI Study Partner")
st.write(
    "Turn your study material into revision notes "
    "and practice questions."
)

# Connect to Gemini using Streamlit Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
except Exception:
    client = None
    st.error(
        "Gemini API key missing. Check your Streamlit Cloud Secrets."
    )
    st.divider()
st.subheader("📂 Upload Study Material PDF")

st.session_state.setdefault("study_material", "")
st.session_state.setdefault("quiz_history", [])

uploaded_pdf = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"]
)

if uploaded_pdf is not None:
    pdf_bytes = uploaded_pdf.getvalue()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    if pdf_hash != st.session_state.get("uploaded_pdf_hash"):
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            pdf_text = "\n".join(
                page.extract_text() or ""
                for page in reader.pages
            )
            st.session_state["uploaded_pdf_hash"] = pdf_hash

            if pdf_text.strip():
                st.session_state["study_material"] = pdf_text
                st.success("PDF text extracted into the study material box.")
            else:
                st.warning(
                    "PDF me readable text nahi mila. "
                    "Ho sakta hai PDF scanned images se bani ho."
                )
        except Exception as e:
            st.session_state["uploaded_pdf_hash"] = pdf_hash
            st.error("PDF read nahi ho payi.")
            st.caption(str(e))

st.text_area(
    "Paste your study material here",
    height=200,
    placeholder="Enter your notes or textbook content...",
    key="study_material"
)

st.divider()
st.subheader("📝 AI Summary")

if st.button("Generate Summary"):
    material = st.session_state.get("study_material", "")

    if not material.strip():
        st.warning("Please enter your study material first.")
    elif client is None:
        st.error("Gemini connection is not configured.")
    else:
        with st.spinner("Gemini is preparing your summary..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=(
                        "Create clear, concise exam revision notes "
                        "using headings and bullet points. "
                        "Do not add unsupported facts.\n\n"
                        + material
                    )
                )
                summary = response.text
                if not summary or not summary.strip():
                    raise ValueError("Gemini returned an empty summary.")

                st.session_state["summary_result"] = summary

            except Exception as e:
                st.error("AI Summary generate nahi ho payi.")
                st.caption(str(e))

if st.session_state.get("summary_result"):
    st.markdown(st.session_state["summary_result"])

st.divider()
st.subheader("🎯 AI MCQ Quiz")

quiz_material = st.text_area(
    "Quiz ke liye study material paste karo",
    height=150,
    key="quiz_material",
    placeholder="Paste your chapter notes here..."
)

if st.button("Generate MCQ Quiz"):
    if not quiz_material.strip():
        st.warning("Pehle study material paste karo.")
    elif client is None:
        st.error("Gemini connection is not configured.")
    else:
        with st.spinner("Gemini is creating your quiz..."):
            try:
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=(
                        "Create exactly 5 MCQs from the study material below. "
                        "Use this exact format for every question:\n"
                        "QUESTION: question text\n"
                        "A: option text\n"
                        "B: option text\n"
                        "C: option text\n"
                        "D: option text\n"
                        "ANSWER: A, B, C, or D\n"
                        "EXPLANATION: short explanation\n"
                        "Separate questions with a line containing only ---.\n"
                        "Use only the supplied study material.\n\n"
                        + quiz_material
                    )
                )

                quiz_text = response.text
                if not quiz_text:
                    raise ValueError("Gemini returned an empty quiz.")

                st.session_state["quiz_result"] = quiz_text
                st.session_state["quiz_submitted"] = False
                st.session_state.pop("quiz_score", None)

            except Exception as e:
                st.error("Quiz generate nahi hua.")
                st.caption(str(e))

if st.session_state.get("quiz_result"):
    quiz_text = st.session_state["quiz_result"]
    blocks = re.split(r"(?m)^\s*---\s*$", quiz_text)
    questions = []

    for block in blocks:
        q = re.search(r"(?im)^QUESTION:\s*(.+)", block)
        answer = re.search(r"(?im)^ANSWER:\s*([ABCD])\b", block)
        explanation = re.search(r"(?im)^EXPLANATION:\s*(.+)", block)

        options = {}
        for letter in "ABCD":
            match = re.search(rf"(?im)^{letter}:\s*(.+)", block)
            if match:
                options[letter] = match.group(1).strip()

        if q and answer and len(options) == 4:
            questions.append({
                "question": q.group(1).strip(),
                "options": options,
                "answer": answer.group(1).upper(),
                "explanation": explanation.group(1).strip()
                if explanation else ""
            })

    if not questions:
        st.warning("MCQ format nahi mila. Quiz dobara generate karo.")
        st.text(quiz_text)
    else:
        st.subheader("📝 Answer the Questions")

        with st.form("mcq_quiz_form"):
            selected = {}

            for i, question in enumerate(questions):
                st.markdown(
                    f"**Q{i + 1}. {question['question']}**"
                )
                selected[i] = st.radio(
                    "Choose your answer:",
                    ["A", "B", "C", "D"],
                    format_func=lambda letter, opts=question["options"]: (
                        f"{letter}: {opts[letter]}"
                    ),
                    key=f"mcq_answer_{i}",
                    index=None
                )
                st.divider()

            submitted = st.form_submit_button("Submit Quiz")

        if submitted:
            score = sum(
                1 for i, question in enumerate(questions)
                if selected[i] == question["answer"]
            )
            st.session_state["quiz_score"] = score
            st.session_state["quiz_history"].append({
                "score": score,
                "total": len(questions)
            })
            st.session_state["quiz_submitted"] = True

        if st.session_state.get("quiz_submitted", False):
            st.success(
                f"Your Score: {st.session_state['quiz_score']}/{len(questions)}"
            )
            for i, question in enumerate(questions):
                st.markdown(
                    f"**Q{i + 1}: Correct answer — {question['answer']}**"
                )
                if question["explanation"]:
                    st.caption(question["explanation"])
                    # Student Progress Dashboard
st.divider()
st.header("📊 Student Progress Dashboard")

history = st.session_state.get("quiz_history", [])

if history:
    total_quizzes = len(history)
    average_score = sum(
        item["score"] / item["total"] * 100
        for item in history
        if item["total"] > 0
    ) / total_quizzes

    best_score = max(
        item["score"] / item["total"] * 100
        for item in history
        if item["total"] > 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Quizzes Attempted", total_quizzes)
    col2.metric("Average Score", f"{average_score:.1f}%")
    col3.metric("Best Score", f"{best_score:.1f}%")

    st.subheader("📈 Quiz Score History")
    chart_data = [
        {
            "Quiz": f"Quiz {i + 1}",
            "Score (%)": round(item["score"] / item["total"] * 100, 1)
        }
        for i, item in enumerate(history)
        if item["total"] > 0
    ]

    if chart_data:
        st.line_chart(
            {item["Quiz"]: item["Score (%)"] for item in chart_data}
        )
else:
    st.info("Abhi quiz history nahi hai. Pehla quiz complete karo!")
def create_revision_pdf(notes):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "StudyBuddy AI - Revision Notes")
    y -= 35
    pdf.setFont("Helvetica", 11)

    for paragraph in notes.splitlines():
        words = paragraph.split()
        line = ""

        for word in words:
            test_line = f"{line} {word}".strip()

            if pdf.stringWidth(test_line, "Helvetica", 11) > width - 100:
                if y < 50:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 11)
                    y = height - 50

                pdf.drawString(50, y, line)
                y -= 16
                line = word
            else:
                line = test_line

        if line:
            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = height - 50

            pdf.drawString(50, y, line)
            y -= 20

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


st.divider()
st.subheader("📄 Download Revision Notes")

notes_for_pdf = st.session_state.get("summary_result", "")

if notes_for_pdf:
    pdf_bytes = create_revision_pdf(notes_for_pdf)
    st.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name="StudyBuddy_Revision_Notes.pdf",
        mime="application/pdf"
    )
else:
    st.info(
        "Pehle AI Summary generate karo, phir PDF download kar sakte ho."
    )