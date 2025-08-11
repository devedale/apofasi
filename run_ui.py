import sys
from PyQt6.QtWidgets import QApplication
from log_analyzer.ui.main_window import MainWindow

def main():
    """
    The main entry point for the GUI application.
    """
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
