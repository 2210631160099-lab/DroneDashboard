import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
from datetime import datetime
import base64

st.set_page_config(
    page_title="Smart Spray Drone",
    page_icon="🚁",
    layout="wide"
)

# ================= DATA =================
telemetry = {
    "🔋 Battery": "85%",
    "📍 GPS": "Connected",
    "📏 Altitude": "2.5 m",
    "🚀 Speed": "0.0 m/s",
    "💧 Pump": "OFF",
}

healthy_count = 120
damaged_count = 15
total_count = healthy_count + damaged_count
damage_pct = round(damaged_count / total_count * 100, 1)
healthy_pct = round(100 - damage_pct, 1)

log_entries = [
    {"time": "10:15:12", "event": "Drone Connected"},
    {"time": "10:15:20", "event": "Disease Detected"},
    {"time": "10:16:05", "event": "Spraying Performed"},
]

# Koordinat bounding box hasil deteksi (dalam persen, relatif thd ukuran foto)
# type: "healthy" (hijau) atau "damaged" (merah)
# Ganti/tambah sesuai output model CV kamu
detection_boxes = [
    {"type": "healthy", "top": 8,  "left": 6,  "width": 32, "height": 30},
    {"type": "healthy", "top": 45, "left": 55, "width": 30, "height": 28},
    {"type": "damaged", "top": 12, "left": 55, "width": 22, "height": 22},
    {"type": "damaged", "top": 55, "left": 15, "width": 20, "height": 25},
]

# ================= CSS =================
st.markdown("""
<style>
html, body, [class*="css"] {
    overflow: hidden !important;
    height: 100vh !important;
}

.main .block-container{
    padding-top:0.3rem;
    padding-bottom:0rem;
    padding-left:0.8rem;
    padding-right:0.8rem;
    max-width:100%;
    height: 100vh;
}

h1{
    font-size:26px !important;
    margin-bottom:0px !important;
}

h2{
    font-size:15px !important;
    margin-top:2px !important;
    margin-bottom:4px !important;
}

.metric-card{
    background:#10192f;
    padding:6px 10px;
    border-radius:10px;
    margin-bottom:6px;
}

.metric-title{
    color:#c7c7c7;
    font-size:11px;
}

.metric-value{
    color:white;
    font-size:16px;
    font-weight:bold;
}

.video-box, .map-box{
    border-radius:14px;
    overflow:hidden;
}

[data-testid="stVerticalBlock"]{
    gap:0.3rem;
}

[data-testid="stHorizontalBlock"]{
    gap:0.6rem;
}

iframe{
    border-radius:12px;
}

/* ---- Tabel log ---- */
.log-table{
    width:100%;
    border-collapse:collapse;
    font-size:12px;
    color:white;
}
.log-table thead th{
    text-align:left;
    color:#8f9bb3;
    font-weight:600;
    font-size:11px;
    padding:4px 8px;
    border-bottom:1px solid #26314f;
}
.log-table tbody td{
    padding:5px 8px;
    border-bottom:1px solid #1c2740;
}
.log-table tbody tr:last-child td{
    border-bottom:none;
}
.log-wrap{
    background:#10192f;
    border-radius:12px;
    padding:4px 4px;
    height:150px;
    overflow-y:auto;
}

/* ---- Grafik kerusakan (bar sederhana) ---- */
.chart-wrap{
    background:#10192f;
    border-radius:12px;
    padding:14px 16px;
    height:150px;
}
.bar-row{
    display:flex;
    align-items:center;
    margin-bottom:12px;
}
.bar-label{
    width:70px;
    font-size:12px;
    color:#c7c7c7;
}
.bar-track{
    flex:1;
    background:#1c2740;
    border-radius:6px;
    height:16px;
    overflow:hidden;
    margin:0 10px;
}
.bar-fill-healthy{
    height:100%;
    background:#3ddc84;
    border-radius:6px;
}
.bar-fill-damaged{
    height:100%;
    background:#ff5a5a;
    border-radius:6px;
}
.bar-value{
    width:60px;
    font-size:13px;
    font-weight:bold;
    color:white;
}

/* ---- Hasil Deteksi (foto + bounding box) ---- */
.detect-wrap{
    background:#10192f;
    border-radius:12px;
    padding:8px;
    height:150px;
    display:flex;
    flex-direction:column;
}
.detect-img-box{
    position:relative;
    width:100%;
    flex:1;
    border-radius:10px;
    overflow:hidden;
}
.detect-img-box img{
    width:100%;
    height:100%;
    object-fit:cover;
    display:block;
}
.detect-mark{
    position:absolute;
    border:3px solid;
    border-radius:4px;
    box-sizing:border-box;
}
.detect-mark.healthy{
    border-color:#3ddc84;
    box-shadow:0 0 4px rgba(61,220,132,0.6);
}
.detect-mark.damaged{
    border-color:#ff5a5a;
    box-shadow:0 0 4px rgba(255,90,90,0.6);
}
.detect-legend{
    display:flex;
    gap:14px;
    margin-top:6px;
    font-size:11px;
    color:#c7c7c7;
}
.legend-dot{
    display:inline-block;
    width:9px;
    height:9px;
    border-radius:2px;
    margin-right:4px;
}
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
col1, col2 = st.columns([5,1])

with col1:
    st.markdown(
        "<h1>🚁 SMART SPRAY DRONE GROUND STATION</h1>",
        unsafe_allow_html=True
    )

with col2:
    now = datetime.now().strftime("%H:%M:%S")
    st.markdown(
        f"""
        <div style='text-align:right'>
        <div style='font-size:12px'>🕒 Time</div>
        <div style='font-size:20px;font-weight:bold'>{now}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ================= ROW 1: KAMERA | AREA MONITORING | TELEMETRY =================
cam_col, map_col, tele_col = st.columns([2, 2, 1.2])

# ---- Live Camera ----
with cam_col:
    st.markdown("## 🎥 Live Camera")

    try:
        with open("assets/drone.mp4", "rb") as f:
            video_bytes = f.read()

        video_base64 = base64.b64encode(video_bytes).decode()

        video_html = f"""
        <div class="video-box">
        <video
            autoplay
            muted
            loop
            playsinline
            style="
                width:100%;
                height:230px;
                object-fit:cover;
                border-radius:14px;">
            <source
            src="data:video/mp4;base64,{video_base64}"
            type="video/mp4">
        </video>
        </div>
        """

        components.html(video_html, height=235)

    except:
        st.error("assets/drone.mp4 tidak ditemukan")

# ---- Area Monitoring ----
with map_col:
    st.markdown("## 🗺️ Area Monitoring")

    m = folium.Map(
        location=[-6.914744, 107.609810],
        zoom_start=16
    )

    folium.Marker(
        [-6.914744, 107.609810],
        tooltip="Drone Position"
    ).add_to(m)

    st_folium(
        m,
        width=None,
        height=230,
        use_container_width=True,
        returned_objects=[]
    )

# ---- Telemetry ----
with tele_col:
    st.markdown("## 📡 Telemetry")

    for k, v in telemetry.items():
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">{k}</div>
                <div class="metric-value">{v}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

# ================= ROW 2: SYSTEM LOG (TABEL) | GRAFIK KERUSAKAN | HASIL DETEKSI =================
log_col, chart_col, detect_col = st.columns([1.2, 0.9, 1.2])

# ---- System Log sebagai tabel rapi ----
with log_col:
    st.markdown("## 📋 System Log")

    rows_html = "".join(
        f"<tr><td>{r['time']}</td><td>{r['event']}</td></tr>"
        for r in log_entries
    )

    st.markdown(
        f"""
        <div class="log-wrap">
        <table class="log-table">
            <thead>
                <tr><th style="width:90px">Waktu</th><th>Event</th></tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Grafik Kerusakan Padi ----
with chart_col:
    st.markdown("## 📊 Grafik Kerusakan Padi")

    st.markdown(
        f"""
        <div class="chart-wrap">
            <div class="bar-row">
                <div class="bar-label">Sehat</div>
                <div class="bar-track">
                    <div class="bar-fill-healthy" style="width:{healthy_pct}%;"></div>
                </div>
                <div class="bar-value">{healthy_count} ({healthy_pct}%)</div>
            </div>
            <div class="bar-row">
                <div class="bar-label">Rusak</div>
                <div class="bar-track">
                    <div class="bar-fill-damaged" style="width:{damage_pct}%;"></div>
                </div>
                <div class="bar-value">{damaged_count} ({damage_pct}%)</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ---- Hasil Deteksi Citra (foto ditandai hijau/merah) ----
with detect_col:
    st.markdown("## 🖼️ Hasil Deteksi Citra")

    try:
        with open("assets/detection.jpeg", "rb") as f:
            detect_bytes = f.read()
        detect_base64 = base64.b64encode(detect_bytes).decode()

        marks_html = "".join(
            f"""<div class="detect-mark {b['type']}"
                 style="top:{b['top']}%; left:{b['left']}%;
                        width:{b['width']}%; height:{b['height']}%;"></div>"""
            for b in detection_boxes
        )

        st.markdown(
            f"""
            <div class="detect-wrap">
                <div class="detect-img-box">
                    <img src="data:image/jpeg;base64,{detect_base64}">
                    {marks_html}
                </div>
                <div class="detect-legend">
                    <span><span class="legend-dot" style="background:#3ddc84;"></span>Sehat</span>
                    <span><span class="legend-dot" style="background:#ff5a5a;"></span>Rusak</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    except FileNotFoundError:
        st.error("assets/detection.jpg tidak ditemukan")