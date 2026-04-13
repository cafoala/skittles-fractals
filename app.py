"""Skittles Fractals – Chaos Game Fractal Generator using Streamlit."""

import io
import smtplib
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Skittles Fractals", page_icon="🌀", layout="centered")
st.title("🌀 Skittles Fractal Generator")
st.markdown(
    "Enter your name and your skittles scores from three rounds to generate a unique "
    "**Sierpiński Triangle** fractal using the Chaos Game algorithm!"
)

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------
if "gallery" not in st.session_state:
    st.session_state.gallery = []  # list of dicts: {name, timestamp, image_bytes}

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------
st.header("Your Details")

user_name = st.text_input("Your name", placeholder="Enter your name")

st.subheader("Skittles Scores (0 – 10)")
col1, col2, col3 = st.columns(3)
with col1:
    score1 = st.number_input("Round 1", min_value=0, max_value=10, value=5, step=1)
with col2:
    score2 = st.number_input("Round 2", min_value=0, max_value=10, value=5, step=1)
with col3:
    score3 = st.number_input("Round 3", min_value=0, max_value=10, value=5, step=1)

# ---------------------------------------------------------------------------
# Chaos Game – Sierpiński Triangle
# ---------------------------------------------------------------------------
NUM_POINTS = 10_000

VERTEX_COLORS = {0: "#E53935", 1: "#1E88E5", 2: "#43A047"}  # Red, Blue, Green
VERTEX_LABELS = {0: "Vertex 1 (Red)", 1: "Vertex 2 (Blue)", 2: "Vertex 3 (Green)"}

# Triangle vertices (equilateral)
VERTICES = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, np.sqrt(3) / 2]])


def _name_seed(name: str, s1: float, s2: float, s3: float) -> int:
    """Derive a deterministic seed from the user's name and scores."""
    raw = f"{name.strip().lower()}:{int(s1)}:{int(s2)}:{int(s3)}"
    return abs(hash(raw)) % (2**31)


def generate_fractal(
    s1: float, s2: float, s3: float, name: str = "", n_points: int = NUM_POINTS
):
    """Run the Chaos Game and return (x, y, vertex_indices)."""
    total = s1 + s2 + s3
    if total == 0:
        # Equal weights when all scores are zero
        weights = [1 / 3, 1 / 3, 1 / 3]
    else:
        weights = [s1 / total, s2 / total, s3 / total]

    seed = _name_seed(name, s1, s2, s3)
    rng = np.random.default_rng(seed=seed)
    chosen = rng.choice(3, size=n_points, p=weights)

    # Start from the centroid
    point = np.mean(VERTICES, axis=0)
    xs = np.empty(n_points)
    ys = np.empty(n_points)

    for i, v in enumerate(chosen):
        point = (point + VERTICES[v]) / 2.0
        xs[i] = point[0]
        ys[i] = point[1]

    return xs, ys, chosen


def build_figure(xs, ys, chosen, title: str) -> plt.Figure:
    """Render the fractal with per-vertex colours and return the Figure."""
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_facecolor("black")
    fig.patch.set_facecolor("black")

    for v_idx, color in VERTEX_COLORS.items():
        mask = chosen == v_idx
        ax.scatter(
            xs[mask],
            ys[mask],
            c=color,
            s=0.3,
            linewidths=0,
            label=VERTEX_LABELS[v_idx],
        )

    legend = ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.07),
        ncol=3,
        fontsize=7,
        framealpha=0.2,
        labelcolor="white",
        markerscale=8,
    )
    legend.get_frame().set_facecolor("black")

    ax.set_title(title, color="white", fontsize=10, pad=8)
    fig.tight_layout()
    return fig


def fig_to_bytes(fig: plt.Figure) -> bytes:
    """Encode a matplotlib Figure to PNG bytes."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Generate fractal whenever the user has entered a name
# ---------------------------------------------------------------------------
generate_btn = st.button("✨ Generate Fractal", type="primary")

if generate_btn or "current_fig_bytes" in st.session_state:
    if generate_btn:
        if not user_name.strip():
            st.warning("Please enter your name before generating a fractal.")
            st.stop()

        xs, ys, chosen = generate_fractal(score1, score2, score3, name=user_name.strip())
        title = (
            f"{user_name.strip()} · Scores: {int(score1)}, {int(score2)}, {int(score3)}"
        )
        fig = build_figure(xs, ys, chosen, title)
        img_bytes = fig_to_bytes(fig)
        plt.close(fig)

        # Persist current fractal in session state
        st.session_state.current_fig_bytes = img_bytes
        st.session_state.current_title = title
        st.session_state.current_name = user_name.strip()
        st.session_state.current_scores = (int(score1), int(score2), int(score3))

    # Display the fractal
    st.subheader("Your Fractal")
    st.image(st.session_state.current_fig_bytes, use_container_width=True)

    # Download button
    st.download_button(
        label="⬇️ Download PNG",
        data=st.session_state.current_fig_bytes,
        file_name="fractal.png",
        mime="image/png",
    )

    # -----------------------------------------------------------------------
    # Save to Gallery
    # -----------------------------------------------------------------------
    if st.button("💾 Save to Gallery"):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.gallery.append(
            {
                "name": st.session_state.current_name,
                "timestamp": ts,
                "title": st.session_state.current_title,
                "image_bytes": st.session_state.current_fig_bytes,
            }
        )
        st.success(f"Saved to gallery! ({ts})")

    # -----------------------------------------------------------------------
    # Send to Email
    # -----------------------------------------------------------------------
    st.subheader("📧 Send to Email")
    with st.expander("Configure email sending"):
        st.info(
            "Provide your SMTP credentials below. "
            "For Gmail you can use an **App Password** "
            "(https://myaccount.google.com/apppasswords)."
        )
        st.warning(
            "⚠️ Credentials are stored temporarily in memory for this session only "
            "and are cleared when you close the browser tab."
        )
        email_to = st.text_input("Recipient email address", key="email_to")
        smtp_server = st.text_input("SMTP server", value="smtp.gmail.com", key="smtp_server")
        smtp_port = st.number_input("SMTP port", value=587, step=1, key="smtp_port")
        smtp_user = st.text_input("SMTP username (your email)", key="smtp_user")
        smtp_password = st.text_input("SMTP password / App Password", type="password", key="smtp_password")

        if st.button("📤 Send Fractal"):
            if not all([email_to, smtp_server, smtp_user, smtp_password]):
                st.error("Please fill in all email fields.")
            else:
                try:
                    msg = MIMEMultipart()
                    msg["From"] = smtp_user
                    msg["To"] = email_to
                    msg["Subject"] = f"Your Skittles Fractal – {st.session_state.current_name}"

                    body = (
                        f"Hi {st.session_state.current_name},\n\n"
                        "Here is your personalised Skittles fractal generated by the "
                        "Chaos Game algorithm.\n\n"
                        f"Scores: Round 1 = {st.session_state.current_scores[0]}, "
                        f"Round 2 = {st.session_state.current_scores[1]}, "
                        f"Round 3 = {st.session_state.current_scores[2]}\n\n"
                        "Enjoy!\n"
                    )
                    msg.attach(MIMEText(body, "plain"))

                    img_attachment = MIMEImage(
                        st.session_state.current_fig_bytes, name="fractal.png"
                    )
                    img_attachment.add_header(
                        "Content-Disposition", "attachment", filename="fractal.png"
                    )
                    msg.attach(img_attachment)

                    with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                        server.ehlo()
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.sendmail(smtp_user, email_to, msg.as_string())

                    st.success(f"Email sent successfully to {email_to}!")
                except smtplib.SMTPAuthenticationError:
                    st.error("Authentication failed. Please check your username and password.")
                except smtplib.SMTPConnectError:
                    st.error("Could not connect to the SMTP server. Check the server address and port.")
                except smtplib.SMTPException as exc:
                    st.error(f"An SMTP error occurred: {exc}")
                except OSError:
                    st.error("Network error. Please check your connection and SMTP settings.")

# ---------------------------------------------------------------------------
# Gallery
# ---------------------------------------------------------------------------
st.divider()
st.header("🖼️ Gallery")

if not st.session_state.gallery:
    st.info("No fractals saved yet. Generate a fractal and click 'Save to Gallery'!")
else:
    st.markdown(f"**{len(st.session_state.gallery)} fractal(s) saved this session.**")
    # Display in a 3-column grid
    cols = st.columns(3)
    for idx, entry in enumerate(reversed(st.session_state.gallery)):
        col = cols[idx % 3]
        with col:
            st.image(entry["image_bytes"], caption=f"{entry['name']} · {entry['timestamp']}", use_container_width=True)
