import ollama
import streamlit as st
import re
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

st.set_page_config(
    page_title="StudyBuddy AI",
    page_icon="📚",
    layout="wide"
)

st.title("📚 StudyBuddy AI")
st.subheader("Your Personal AI Study Partner")

st.write(
    "Welcome! Turn your study material into "
    "revision notes and practice questions."
)

st.success("Your StudyBuddy AI project is ready to build!")

st.text_area(
    "Paste your study material here",
    height=200,
    placeholder="Enter your notes or textbook content...",
key="study_material"
)
st.write("Input received:", bool(st.session_state.get("study_material", "")))
st.divider()
st.subheader("📝 AI Summary")

if st.button("Generate Summary"):
    material = st.session_state.get("study_material", "")

    if not material.strip():
        st.warning("Please enter your study material first.")
    else:
        with st.spinner("Gemma is preparing your summary..."):
            try:
                import ollama

                response = ollama.chat(
                    model="gemma4:e2b",
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                "Create clear, concise exam revision notes "
                                "from this study material. Use headings "
                                "and bullet points. Do not add unsupported facts.\n\n"
                                + material
                            )
                        }
                    ]
                )

                summary = response["message"]["content"]
                st.session_state["summary_result"] = summary
                st.markdown(summary)

            except Exception as e:
                st.error("AI Summary generate nahi ho payi.")
                st.caption(str(e))
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
    else:
        with st.spinner("Gemma is creating your quiz..."):
            try:
                response = ollama.chat(
                    model="gemma4:e2b",
                    messages=[{
                        "role": "user",
                        "content": (
    "Create exactly 5 MCQs from the study material below. "
    "For each question, use this exact format:\n"
    "QUESTION: question text\n"
    "A: option text\n"
    "B: option text\n"
    "C: option text\n"
    "D: option text\n"
    "ANSWER: A, B, C, or D\n"
    "EXPLANATION: short explanation\n\n"
    "Separate each question with ---.\n"
    "Use only the supplied study material.\n\n"
    + quiz_material
)
                    }]
                )

                st.session_state["quiz_result"] = (
                    response["message"]["content"]
                )

            except Exception as e:
                st.error("Quiz generate nahi hua. Ollama check karo.")
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
            match = re.search(
                rf"(?im)^{letter}:\s*(.+)", block
            )
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
        st.warning("MCQs ka format nahi mila. Quiz dobara generate karo.")
    else:
        st.subheader("📝 Answer the Questions")

        with st.form("mcq_quiz_form"):
            selected = {}

            for i, question in enumerate(questions):
                st.markdown(f"**Q{i + 1}. {question['question']}**")
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
            st.session_state["quiz_submitted"] = True

        if st.session_state.get("quiz_submitted", False):
            st.success(
                f"Your Score: {st.session_state['quiz_score']}/{len(questions)}"
            )
            for i, question in enumerate(questions):
                st.markdown(f"**Q{i + 1}: Correct answer — {question['answer']}**")
                if question["explanation"]:
                    st.caption(question["explanation"])
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
                pdf.drawString(50, y, line)
                y -= 16
                line = word
            else:
                line = test_line

            if y < 50:
                pdf.showPage()
                pdf.setFont("Helvetica", 11)
                y = height - 50

        if line:
            pdf.drawString(50, y, line)
            y -= 20

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 11)
            y = height - 50

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
    st.info("Pehle AI Summary generate karo, phir PDF download kar sakte ho.")