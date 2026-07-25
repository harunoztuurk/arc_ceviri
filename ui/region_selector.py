from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont

class RegionSelectorWidget(QWidget):
    """
    Interactive full-screen overlay for selecting a custom capture region across any monitor.
    Emits region_selected signal with dict: {'top': y, 'left': x, 'width': w, 'height': h}
    """
    region_selected = pyqtSignal(dict)

    def __init__(self, monitor_index: int = None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        
        # Determine screen positioning
        screens = QApplication.screens()
        if monitor_index is not None and 0 <= monitor_index < len(screens):
            target_screen = screens[monitor_index]
            self.setGeometry(target_screen.geometry())
        else:
            # Union of all screen geometries (Virtual Desktop)
            combined_geo = QRect()
            for screen in screens:
                combined_geo = combined_geo.united(screen.geometry())
            if not combined_geo.isEmpty():
                self.setGeometry(combined_geo)
            elif screens:
                self.setGeometry(screens[0].geometry())

        self.start_point = None
        self.end_point = None
        self.is_selecting = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.position().toPoint()
            self.end_point = self.start_point
            self.is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.is_selecting:
            self.end_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.is_selecting:
            self.is_selecting = False
            rect = QRect(self.start_point, self.end_point).normalized()
            
            if rect.width() > 10 and rect.height() > 10:
                selected_region = {
                    "top": int(rect.top()),
                    "left": int(rect.left()),
                    "width": int(rect.width()),
                    "height": int(rect.height())
                }
                self.region_selected.emit(selected_region)
                self.close()
            else:
                # Selection too small, reset
                self.start_point = None
                self.end_point = None
                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Semi-transparent dark overlay background
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.start_point and self.end_point:
            rect = QRect(self.start_point, self.end_point).normalized()
            # Clear selected area so underlying screen is crystal clear
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            
            # Draw cyan selection border and dimensions text
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            pen = QPen(QColor("#38BDF8"), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)
            
            # Text dimensions indicator
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            text = f"Region: {rect.width()}x{rect.height()} at ({rect.left()}, {rect.top()})"
            painter.fillRect(rect.left(), max(0, rect.top() - 25), 240, 22, QColor("#0F172A"))
            painter.setPen(QPen(QColor("#FFFFFF")))
            painter.drawText(rect.left() + 5, max(15, rect.top() - 8), text)
