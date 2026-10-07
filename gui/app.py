import sys
import random
import math
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QRectF, QPoint
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QFont

# --- Colors ---
PRIMARY_COLOR = QColor("#00FFFF")  # Cyan
ACCENT_COLOR = QColor("#FFFFFF")   # White
BG_COLOR = QColor("#000000")       # Black
WARNING_COLOR = QColor("#FFA500")  # Orange / Amber for Pause

class HexagonPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.opacity = 50
        self.increasing = True
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)

    def animate(self):
        if self.increasing:
            self.opacity += 5
            if self.opacity >= 200:
                self.increasing = False
        else:
            self.opacity -= 5
            if self.opacity <= 50:
                self.increasing = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(PRIMARY_COLOR)
        pen.setWidth(2)
        painter.setPen(pen)
        
        size = 30
        rows = 4
        cols = 3
        x_offset = 20
        y_offset = 60

        for r in range(rows):
            for c in range(cols):
                color = QColor(PRIMARY_COLOR)
                current_opacity = self.opacity
                if (r + c) % 2 == 0:
                    current_opacity = max(50, current_opacity - 50)
                
                color.setAlpha(current_opacity)
                painter.setPen(QPen(color, 2))
                
                x = x_offset + c * (size * 1.5)
                y = y_offset + r * (size * math.sqrt(3))
                if c % 2 == 1:
                    y += size * math.sqrt(3) / 2
                
                self.draw_hexagon(painter, x, y, size)

    def draw_hexagon(self, painter, x, y, size):
        points = []
        for i in range(6):
            angle_deg = 60 * i
            angle_rad = math.radians(angle_deg)
            px = x + size * math.cos(angle_rad)
            py = y + size * math.sin(angle_rad)
            points.append(QPointF(px, py))
        painter.drawPolygon(QPolygonF(points))

class TelemetryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(200)
        self.bar_heights = [20, 40, 60, 30]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(100)

    def animate(self):
        self.bar_heights = [random.randint(15, 110) for _ in range(4)]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen = QPen(ACCENT_COLOR)
        pen.setWidth(2)
        painter.setPen(pen)
        
        path_points = [
            QPointF(10, 200), QPointF(50, 240), QPointF(150, 240), QPointF(180, 200)
        ]
        painter.drawPolyline(QPolygonF(path_points))
        
        bar_width = 30
        gap = 10
        start_x = 20
        base_y = 170
        
        painter.setBrush(QBrush(PRIMARY_COLOR))
        painter.setPen(Qt.PenStyle.NoPen)
        
        for i, h in enumerate(self.bar_heights):
            x = start_x + i * (bar_width + gap)
            painter.drawRect(QRectF(x, base_y - h, bar_width, h))

class CentralReactor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle_outer = 0
        self.angle_inner = 0
        self.is_paused = False
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(30) # ~30fps

    def animate(self):
        if not self.is_paused:
            self.angle_outer = (self.angle_outer + 2) % 360
            self.angle_inner = (self.angle_inner - 4) % 360
            self.update()

    def set_paused(self, paused):
        self.is_paused = paused
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        main_color = WARNING_COLOR if self.is_paused else PRIMARY_COLOR
        
        # 1. Core
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(main_color))
        core_radius = 24
        if not self.is_paused:
            pulse = (math.sin(self.angle_outer * 0.1) + 1) * 5
            painter.drawEllipse(QPointF(center_x, center_y), core_radius + pulse, core_radius + pulse)
        else:
            painter.drawEllipse(QPointF(center_x, center_y), core_radius, core_radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 2. Middle Ring (Thick Segmented)
        pen = QPen(main_color)
        pen.setWidth(12)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        pen.setDashPattern([10, 10]) 
        painter.setPen(pen)
        
        radius_mid = 100
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle_outer)
        painter.drawEllipse(QPointF(0, 0), radius_mid, radius_mid)
        painter.restore()

        # 3. Inner Ring (Thin Dashed)
        pen = QPen(ACCENT_COLOR)
        pen.setWidth(4)
        pen.setDashPattern([5, 5])
        painter.setPen(pen)
        
        radius_inner = 70
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.angle_inner)
        painter.drawEllipse(QPointF(0, 0), radius_inner, radius_inner)
        painter.restore()

        # 4. Outer Arcs
        pen = QPen(main_color)
        pen.setWidth(3)
        pen.setStyle(Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        radius_outer = 135
        
        rect_outer = QRectF(center_x - radius_outer, center_y - radius_outer, 2*radius_outer, 2*radius_outer)
        painter.drawArc(rect_outer, 45 * 16, 90 * 16)
        painter.drawArc(rect_outer, 225 * 16, 90 * 16)

class JarvisGUI(QMainWindow):
    def __init__(self, pause_event):
        super().__init__()
        self.pause_event = pause_event
        self.is_paused = False
        self.drag_position = None
        
        self.setWindowTitle("JARVIS HUD - STARK INDUSTRIES")
        self.resize(1050, 620)
        
        # Frameless, Translucent Window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main Container
        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: rgba(5, 10, 15, 230); border: 1px solid #00FFFF; border-radius: 12px;")
        self.setCentralWidget(central_widget)
        
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(15, 12, 15, 15)
        
        # Top Header Bar
        header_layout = QHBoxLayout()
        self.title_label = QLabel("JARVIS HUD // WAKE WORD: 'DELULU' | 'JARVIS'")
        self.title_label.setStyleSheet("color: #00FFFF; font-family: 'Segoe UI', sans-serif; font-size: 13px; font-weight: bold; letter-spacing: 2px;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.status_badge = QLabel("● ACTIVE")
        self.status_badge.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 12px; margin-right: 10px;")
        header_layout.addWidget(self.status_badge)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("background-color: transparent; color: #00FFFF; border: 1px solid #00FFFF; border-radius: 4px; font-weight: bold;")
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)
        
        root_layout.addLayout(header_layout)
        
        # Center Visuals Area
        hud_layout = QHBoxLayout()
        hud_layout.setContentsMargins(0, 0, 0, 0)
        
        self.left_panel = HexagonPanel()
        hud_layout.addWidget(self.left_panel)
        
        self.reactor = CentralReactor()
        hud_layout.addWidget(self.reactor, stretch=2)
        
        self.right_panel = TelemetryPanel()
        hud_layout.addWidget(self.right_panel)
        
        root_layout.addLayout(hud_layout)
        
        # Bottom Status & Help Bar
        footer_label = QLabel("Click Arc Reactor to Pause / Resume | Drag HUD anywhere to reposition | ESC to Exit")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        root_layout.addWidget(footer_label)

    # Window Dragging Handling
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicked reactor region
            reactor_geom = self.reactor.geometry()
            click_pos = event.pos()
            if reactor_geom.contains(click_pos):
                self.toggle_pause()
            else:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_position is not None:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.reactor.set_paused(self.is_paused)
        
        if self.is_paused:
            self.pause_event.set()
            self.status_badge.setText("■ PAUSED")
            self.status_badge.setStyleSheet("color: #FFA500; font-weight: bold; font-size: 12px; margin-right: 10px;")
            print("JARVIS: Listening PAUSED.")
        else:
            self.pause_event.clear()
            self.status_badge.setText("● ACTIVE")
            self.status_badge.setStyleSheet("color: #00FF88; font-weight: bold; font-size: 12px; margin-right: 10px;")
            print("JARVIS: Listening RESUMED.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

def run_gui(pause_event):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    window = JarvisGUI(pause_event)
    window.show()
    sys.exit(app.exec())
