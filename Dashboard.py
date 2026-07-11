import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
from datetime import datetime
import base64
import textwrap

def render_html(s: str):
    """
    Streamlit's markdown parser treats any line indented with 4+ spaces as
    a code block, which makes raw HTML tags show up as visible text (with
    a copy button) instead of being rendered. textwrap.dedent() alone is
    not enough here because it only strips whitespace that is common to
    EVERY line — content built inside loops/nested f-strings often keeps
    leftover indentation on only some lines. So instead we strip leading
    whitespace from each line individually before rendering.
    """
    flattened = "\n".join(line.lstrip() for line in s.strip("\n").split("\n"))
    st.markdown(flattened, unsafe_allow_html=True)

st.set_page_config(
    page_title="Smart Spray Drone",
    page_icon="🚁",
    layout="wide"
)

# ================= DATA =================
telemetry = [
    {"icon": "🔋", "label": "Battery", "value": "85%", "sub": "11.4 V"},
    {"icon": "📍", "label": "GPS", "value": "Connected", "sub": "12 satelit"},
    {"icon": "📏", "label": "Altitude", "value": "2.5 m", "sub": "target 1–2 m"},
    {"icon": "🚀", "label": "Speed", "value": "0.0 m/s", "sub": "hover"},
    {"icon": "💧", "label": "Pump", "value": "OFF", "sub": "tangki 100%"},
]
battery_pct = 85

healthy_count = 120
damaged_count = 15
total_count = healthy_count + damaged_count
damage_pct = round(damaged_count / total_count * 100, 1)
healthy_pct = round(100 - damage_pct, 1)

log_entries = [
    {"time": "10:15:12", "event": "Drone Connected", "kind": "info"},
    {"time": "10:15:20", "event": "Disease Detected", "kind": "warn"},
    {"time": "10:16:05", "event": "Spraying Performed", "kind": "ok"},
]

# Koordinat bounding box hasil deteksi (dalam persen, relatif thd ukuran foto)
detection_boxes = [
    {"type": "healthy", "top": 8,  "left": 6,  "width": 32, "height": 30, "conf": 97},
    {"type": "healthy", "top": 45, "left": 55, "width": 30, "height": 28, "conf": 94},
    {"type": "damaged", "top": 12, "left": 55, "width": 22, "height": 22, "conf": 89},
    {"type": "damaged", "top": 55, "left": 15, "width": 20, "height": 25, "conf": 91},
]

# ================= CSS =================
render_html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root{
    --bg: #0b1410;
    --panel: #10201a;
    --panel-2: #16291f;
    --border: #1f3d30;
    --text: #eaf3ee;
    --muted: #7fa08e;
    --accent: #57d9a3;
    --accent-dark: #2c7a5a;
    --warn: #e8b04b;
    --danger: #ff7a6e;
    --font-display: 'Space Grotesk', sans-serif;
    --font-body: 'Inter', sans-serif;
}

html, body, [class*="css"] {
    overflow: hidden !important;
    height: 100vh !important;
    font-family: var(--font-body) !important;
    background: var(--bg) !important;
}

.main .block-container{
    padding-top:0.4rem;
    padding-bottom:0rem;
    padding-left:1rem;
    padding-right:1rem;
    max-width:100%;
    height: 100vh;
}

h1{
    font-family: var(--font-display) !important;
    font-size:25px !important;
    font-weight:700 !important;
    margin-bottom:0px !important;
    letter-spacing:0.2px;
    background: linear-gradient(90deg, var(--text) 0%, var(--accent) 120%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

h2{
    font-family: var(--font-display) !important;
    font-size:13.5px !important;
    font-weight:600 !important;
    margin-top:0px !important;
    margin-bottom:8px !important;
    color: var(--text) !important;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    display:flex; align-items:center; gap:7px;
}

/* garis identitas hijau tipis di atas tiap panel */
.panel-frame{
    background:var(--panel);
    border:1px solid var(--border);
    border-radius:14px;
    padding:10px 14px 12px;
    position:relative;
    overflow:hidden;
}
.panel-frame::before{
    content:"";
    position:absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, var(--accent) 0%, var(--warn) 100%);
}

.video-box, .map-box{
    border-radius:12px;
    overflow:hidden;
    border:1px solid var(--border);
}

[data-testid="stVerticalBlock"]{ gap:0.4rem; }
[data-testid="stHorizontalBlock"]{ gap:0.7rem; }
iframe{ border-radius:12px; }

/* ---- Telemetry ---- */
.tele-list{ display:flex; flex-direction:column; gap:7px; }
.tele-item{
    display:flex; align-items:center; justify-content:space-between;
    background:var(--panel-2); border:1px solid var(--border);
    border-radius:10px; padding:7px 12px;
}
.tele-left{ display:flex; align-items:center; gap:9px; }
.tele-icon{ font-size:15px; }
.tele-label{ color:var(--muted); font-size:10.5px; font-family:var(--font-body); }
.tele-value{ color:var(--text); font-size:15px; font-weight:600; font-family:var(--font-display); line-height:1.1; }
.tele-sub{ color:var(--muted); font-size:9.5px; text-align:right; }

.battery-shell{
    width:34px; height:15px; border:1.6px solid var(--muted); border-radius:3px;
    position:relative; padding:1.5px; display:flex; align-items:center;
    margin-right:2px;
}
.battery-shell::after{
    content:""; position:absolute; right:-4px; top:4px; width:2.5px; height:6px;
    background:var(--muted); border-radius:0 2px 2px 0;
}
.battery-fill{ height:100%; border-radius:1px; background:var(--accent); }

/* ---- Log ---- */
.log-table{ width:100%; border-collapse:collapse; font-size:12px; color:var(--text); }
.log-table thead th{
    text-align:left; color:var(--muted); font-weight:600; font-size:10px;
    text-transform:uppercase; letter-spacing:0.4px;
    padding:4px 8px; border-bottom:1px solid var(--border);
}
.log-table tbody td{ padding:6px 8px; border-bottom:1px solid var(--border); }
.log-table tbody tr:last-child td{ border-bottom:none; }
.log-wrap{ background:var(--panel-2); border-radius:10px; padding:4px 4px; height:150px; overflow-y:auto; border:1px solid var(--border);}
.log-dot{ display:inline-block; width:7px; height:7px; border-radius:50%; margin-right:7px; }
.log-dot.info{ background:#5b9bd5; }
.log-dot.warn{ background:var(--warn); }
.log-dot.ok{ background:var(--accent); }

/* ---- Grafik kerusakan ---- */
.chart-wrap{ background:var(--panel-2); border-radius:10px; padding:16px 16px; height:150px; border:1px solid var(--border);}
.bar-row{ display:flex; align-items:center; margin-bottom:14px; }
.bar-label{ width:64px; font-size:11.5px; color:var(--muted); font-weight:500; }
.bar-track{ flex:1; background:#0d1a15; border-radius:6px; height:14px; overflow:hidden; margin:0 10px; }
.bar-fill-healthy{ height:100%; background:linear-gradient(90deg, var(--accent-dark), var(--accent)); border-radius:6px; }
.bar-fill-damaged{ height:100%; background:linear-gradient(90deg, #a83f38, var(--danger)); border-radius:6px; }
.bar-value{ width:74px; font-size:12.5px; font-weight:600; color:var(--text); font-family:var(--font-display); }

/* ---- Deteksi ---- */
.detect-wrap{ background:var(--panel-2); border-radius:10px; padding:8px; height:150px; display:flex; flex-direction:column; border:1px solid var(--border);}
.detect-img-box{ position:relative; width:100%; flex:1; border-radius:8px; overflow:hidden; }
.detect-img-box img{ width:100%; height:100%; object-fit:cover; display:block; }
.detect-mark{ position:absolute; border:2.5px solid; border-radius:4px; box-sizing:border-box; }
.detect-mark.healthy{ border-color:var(--accent); box-shadow:0 0 6px rgba(87,217,163,0.5); }
.detect-mark.damaged{ border-color:var(--danger); box-shadow:0 0 6px rgba(255,122,110,0.5); }
.detect-tag{
    position:absolute; top:-18px; left:-2.5px; font-size:8.5px; font-weight:600;
    padding:1px 5px; border-radius:3px; color:#0b1410; font-family:var(--font-display);
    white-space:nowrap;
}
.detect-tag.healthy{ background:var(--accent); }
.detect-tag.damaged{ background:var(--danger); }
.detect-legend{ display:flex; gap:14px; margin-top:6px; font-size:10.5px; color:var(--muted); }
.legend-dot{ display:inline-block; width:8px; height:8px; border-radius:2px; margin-right:4px; }
</style>
""")

# ================= HEADER =================
col1, col2 = st.columns([5, 1])

with col1:
    render_html(
        "<h1>🚁 SMART SPRAY DRONE — GROUND STATION</h1>",
    )
    render_html(
        "<div style='color:#7fa08e; font-size:11.5px; margin-top:2px; font-family:Inter;'>"
        "Agro-Drone Penyemprot Pestisida Berbasis Computer Vision — Deteksi Kerusakan Tanaman Padi</div>",
    )

with col2:
    now = datetime.now().strftime("%H:%M:%S")
    render_html(
        f"""
        <div style='text-align:right'>
        <div style='font-size:10.5px; color:#7fa08e;'>🕒 WAKTU SISTEM</div>
        <div style='font-size:22px; font-weight:700; font-family:"Space Grotesk"; color:#eaf3ee;'>{now}</div>
        </div>
        """,
    )

# ================= ROW 1: KAMERA | AREA MONITORING | TELEMETRY =================
cam_col, map_col, tele_col = st.columns([2, 2, 1.2])

# ---- Live Camera ----
with cam_col:
    render_html('<div class="panel-frame">')
    render_html("## 🎥 Live Camera")
    try:
        with open("assets/drone.mp4", "rb") as f:
            video_bytes = f.read()
        video_base64 = base64.b64encode(video_bytes).decode()
        video_html = f"""
        <div class="video-box">
        <video autoplay muted loop playsinline
            style="width:100%; height:225px; object-fit:cover;">
            <source src="data:video/mp4;base64,{video_base64}" type="video/mp4">
        </video>
        </div>
        """
        components.html(video_html, height=230)
    except:
        st.error("assets/drone.mp4 tidak ditemukan")
    render_html('</div>')

# ---- Area Monitoring ----
with map_col:
    render_html('<div class="panel-frame">')
    render_html("## 🗺️ Area Monitoring")
    m = folium.Map(location=[-6.914744, 107.609810], zoom_start=16, tiles="CartoDB dark_matter")
    folium.Marker(
        [-6.914744, 107.609810],
        tooltip="Drone Position",
        icon=folium.Icon(color="green", icon="plane", prefix="fa")
    ).add_to(m)
    st_folium(m, width=None, height=225, use_container_width=True, returned_objects=[])
    render_html('</div>')

# ---- Telemetry ----
with tele_col:
    render_html('<div class="panel-frame">')
    render_html("## 📡 Telemetry")

    items_html = ""
    for t in telemetry:
        if t["label"] == "Battery":
            fill_color = "var(--accent)" if battery_pct > 30 else "var(--danger)"
            left_html = f"""
                <div class="battery-shell"><div class="battery-fill" style="width:{battery_pct}%; background:{fill_color};"></div></div>
                <div>
                    <div class="tele-label">{t['label']}</div>
                    <div class="tele-value">{t['value']}</div>
                </div>
            """
        else:
            left_html = f"""
                <div class="tele-icon">{t['icon']}</div>
                <div>
                    <div class="tele-label">{t['label']}</div>
                    <div class="tele-value">{t['value']}</div>
                </div>
            """
        items_html += f"""
        <div class="tele-item">
            <div class="tele-left">{left_html}</div>
            <div class="tele-sub">{t['sub']}</div>
        </div>
        """

    render_html(f'<div class="tele-list">{items_html}</div>')
    render_html('</div>')

render_html("<div style='height:10px'></div>")

# ================= ROW 2 =================
log_col, chart_col, detect_col = st.columns([1.2, 0.9, 1.2])

# ---- System Log ----
with log_col:
    render_html('<div class="panel-frame">')
    render_html("## 📋 System Log")
    rows_html = "".join(
        f"""<tr><td><span class="log-dot {r['kind']}"></span>{r['time']}</td><td>{r['event']}</td></tr>"""
        for r in log_entries
    )
    render_html(
        f"""
        <div class="log-wrap">
        <table class="log-table">
            <thead><tr><th style="width:110px">Waktu</th><th>Event</th></tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        </div>
        """,
    )
    render_html('</div>')

# ---- Grafik Kerusakan Padi ----
with chart_col:
    render_html('<div class="panel-frame">')
    render_html("## 📊 Grafik Kerusakan Padi")
    render_html(
        f"""
        <div class="chart-wrap">
            <div class="bar-row">
                <div class="bar-label">Sehat</div>
                <div class="bar-track"><div class="bar-fill-healthy" style="width:{healthy_pct}%;"></div></div>
                <div class="bar-value">{healthy_count} ({healthy_pct}%)</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Rusak</div>
                <div class="bar-track"><div class="bar-fill-damaged" style="width:{damage_pct}%;"></div></div>
                <div class="bar-value">{damaged_count} ({damage_pct}%)</div>
            </div>
        </div>
        """,
    )
    render_html('</div>')

# ---- Hasil Deteksi Citra ----
with detect_col:
    render_html('<div class="panel-frame">')
    render_html("## 🖼️ Hasil Deteksi Citra")
    try:
        with open("assets/detection.jpeg", "rb") as f:
            detect_bytes = f.read()
        detect_base64 = base64.b64encode(detect_bytes).decode()

        marks_html = "".join(
            f"""<div class="detect-mark {b['type']}"
                 style="top:{b['top']}%; left:{b['left']}%; width:{b['width']}%; height:{b['height']}%;">
                 <div class="detect-tag {b['type']}">{b['conf']}%</div>
                 </div>"""
            for b in detection_boxes
        )
        render_html(
            f"""
            <div class="detect-wrap">
                <div class="detect-img-box">
                    <img src="data:image/jpeg;base64,{detect_base64}">
                    {marks_html}
                </div>
                <div class="detect-legend">
                    <span><span class="legend-dot" style="background:var(--accent);"></span>Sehat</span>
                    <span><span class="legend-dot" style="background:var(--danger);"></span>Rusak</span>
                </div>
            </div>
            """,
        )
    except FileNotFoundError:
        st.error("assets/detection.jpeg tidak ditemukan")
    render_html('</div>')
