import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QRadioButton, QButtonGroup, 
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QFileDialog, QStackedWidget, QGridLayout)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QColor, QBrush

from dvr_scanner import DVRScanner

class VideoGridItem(QWidget):
    """A single quadrant in the 2x2 grid with a label bar above the video."""
    def __init__(self, label_text):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Label bar on top of video
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setFixedHeight(24)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(20, 20, 20, 220);
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                padding: 2px 0px;
            }
        """)
        layout.addWidget(self.label)

        self.video_widget = QVideoWidget()
        layout.addWidget(self.video_widget)

class DVRPlayer(QMainWindow):
    def __init__(self, directory_path=None):
        super().__init__()
        self.setWindowTitle("DVR Video Player")
        self.setGeometry(100, 100, 1280, 800)

        # Video Data
        self.video_groups = []
        self.current_group_index = 0
        self.current_angle = 'F'  # Default angle ('F', 'B', 'L', 'R', 'S', or 'ALL')
        
        # --- Primary Player (Single View) ---
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        
        # --- Multi Players (All View: S, B, L, R) ---
        self.multi_players = []
        self.multi_widgets = []
        self.multi_angles = ['S', 'B', 'L', 'R']
        
        for angle in self.multi_angles:
            player = QMediaPlayer()
            # Only the first player in multi-view gets audio to avoid echo, 
            # or we could mute all. Let's mute all for now to be safe.
            audio = QAudioOutput()
            audio.setMuted(True)
            player.setAudioOutput(audio)
            self.multi_players.append(player)

        # Setup UI
        self.init_ui()
        
        # Connect signals for primary player
        self.media_player.mediaStatusChanged.connect(self.handle_media_status)
        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.update_slider_duration)

        # Initialize Data if directory provided on startup
        if directory_path:
            self.set_dvr_directory(directory_path)

    def init_ui(self):
        main_widget = QWidget()
        main_h_layout = QHBoxLayout()
        main_widget.setLayout(main_h_layout)
        self.setCentralWidget(main_widget)
        
        # --- LEFT PANEL (Video + Controls) ---
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        main_h_layout.addWidget(left_panel, stretch=3)

        # Top Bar: Directory Selection
        top_bar_layout = QHBoxLayout()
        self.open_dir_btn = QPushButton("📂 Open NOR Directory")
        self.open_dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.open_dir_btn.clicked.connect(self.open_directory_dialog)
        self.dir_label = QLabel("No directory selected")
        top_bar_layout.addWidget(self.open_dir_btn)
        top_bar_layout.addWidget(self.dir_label)
        top_bar_layout.addStretch(1)
        left_layout.addLayout(top_bar_layout)

        # 1. Video Display (Stacked: Single vs Grid)
        self.display_stack = QStackedWidget()
        
        # Single view
        self.display_stack.addWidget(self.video_widget)
        
        # Grid view (2x2)
        grid_widget = QWidget()
        self.grid_layout = QGridLayout(grid_widget)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(2)
        
        # S (Front Wide), B (Back)
        # L (Left), R (Right)
        angle_names = {'S': '前广角 (S)', 'B': '后 (B)', 'L': '左 (L)', 'R': '右 (R)'}
        for i, angle in enumerate(self.multi_angles):
            item = VideoGridItem(angle_names[angle])
            self.multi_players[i].setVideoOutput(item.video_widget)
            self.multi_widgets.append(item)
            self.grid_layout.addWidget(item, i // 2, i % 2)
            
        self.display_stack.addWidget(grid_widget)
        left_layout.addWidget(self.display_stack, stretch=1)

        # 2. Timeline and Time Label
        timeline_layout = QHBoxLayout()
        self.time_label = QLabel("00:00 / 00:00")
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.sliderMoved.connect(self.set_position)
        
        timeline_layout.addWidget(self.timeline_slider)
        timeline_layout.addWidget(self.time_label)
        left_layout.addLayout(timeline_layout)

        # 3. Controls Layout (Play, Prev, Next, Angles)
        controls_layout = QHBoxLayout()
        
        # Play/Pause
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self.toggle_play)
        controls_layout.addWidget(self.play_btn)
        
        # Prev/Next
        self.prev_btn = QPushButton("<< Prev")
        self.prev_btn.clicked.connect(self.play_previous_group)
        self.next_btn = QPushButton("Next >>")
        self.next_btn.clicked.connect(self.play_next_group)
        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.next_btn)
        
        controls_layout.addStretch(1)

        # Angle Selection
        self.angle_group = QButtonGroup(self)
        angles = [
            ('F', "Front (F)"), 
            ('B', "Back (B)"), 
            ('L', "Left (L)"), 
            ('R', "Right (R)"), 
            ('S', "Front Wide (S)"),
            ('ALL', "All Views (4-Grid)")
        ]
        
        angle_label = QLabel("View Angle:")
        controls_layout.addWidget(angle_label)

        for code, label in angles:
            radio = QRadioButton(label)
            if code == 'F':
                radio.setChecked(True)
            self.angle_group.addButton(radio)
            # using lambda magic to capture the code
            radio.clicked.connect(lambda checked, c=code: self.change_angle(c))
            controls_layout.addWidget(radio)

        left_layout.addLayout(controls_layout)

        # 4. Info Label
        self.info_label = QLabel("Status: Ready")
        left_layout.addWidget(self.info_label)
        
        # --- RIGHT PANEL (Timeline Playlist) ---
        self.playlist_widget = QTreeWidget()
        self.playlist_widget.setHeaderHidden(True)
        self.playlist_widget.setColumnCount(1)
        self.playlist_widget.setFixedWidth(280)
        self.playlist_widget.setIndentation(16)
        self.playlist_widget.itemClicked.connect(self.jump_to_video)
        self.playlist_widget.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e2e;
                border: none;
                outline: none;
                font-size: 13px;
                color: #cdd6f4;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                border-radius: 4px;
                margin: 1px 4px;
            }
            QTreeWidget::item:hover {
                background-color: #313244;
            }
            QTreeWidget::item:selected {
                background-color: #1e66f5;
                color: #ffffff;
            }
            QTreeWidget::branch {
                background-color: #1e1e2e;
            }
        """)
        main_h_layout.addWidget(self.playlist_widget)

    def open_directory_dialog(self):
        directory = QFileDialog.getExistingDirectory(self, "Select DVR 'NOR' Directory", "/Volumes")
        if directory:
            self.set_dvr_directory(directory)

    def set_dvr_directory(self, directory_path):
        self.dir_label.setText(f"Source: {directory_path}")
        self.scanner = DVRScanner(directory_path)
        self.video_groups = self.scanner.scan_and_group()
        
        if not self.video_groups:
            QMessageBox.warning(self, "No Videos", f"No videos found in {directory_path}")
            self.playlist_widget.clear()
            return
            
        self.current_group_index = 0
        self.populate_timeline()
        self.load_video()

    def populate_timeline(self):
        self.playlist_widget.clear()
        current_date = ""
        date_node = None
        all_angles = ['F', 'B', 'L', 'R', 'S']
        angle_colors = {
            'F': '#a6e3a1', 'B': '#f38ba8', 'L': '#89b4fa', 'R': '#fab387', 'S': '#cba6f7'
        }
        dim_color = '#45475a'

        for i, group in enumerate(self.video_groups):
            dt = group['timestamp']
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            available = set(group['angles'].keys())

            if date_str != current_date:
                current_date = date_str
                date_node = QTreeWidgetItem(self.playlist_widget)
                date_node.setText(0, f"  📅  {date_str}")
                bold_font = QFont()
                bold_font.setBold(True)
                bold_font.setPointSize(13)
                date_node.setFont(0, bold_font)
                date_node.setForeground(0, QBrush(QColor('#cdd6f4')))
                date_node.setFlags(Qt.ItemFlag.ItemIsEnabled)

            angle_parts = []
            for a in all_angles:
                angle_parts.append(a if a in available else '·')
            angles_display = '  '.join(angle_parts)

            child = QTreeWidgetItem(date_node)
            child.setText(0, f"  {time_str}    {angles_display}")
            child.setData(0, Qt.ItemDataRole.UserRole, i)

            tooltip_lines = []
            names = {'F': 'Front', 'B': 'Back', 'L': 'Left', 'R': 'Right', 'S': 'Front Wide'}
            for a in all_angles:
                status = '●' if a in available else '○'
                tooltip_lines.append(f"{status} {names[a]} ({a})")
            child.setToolTip(0, '\n'.join(tooltip_lines))

        self.playlist_widget.expandAll()
            
    def jump_to_video(self, item):
        if item.parent() is None: return
        index = item.data(0, Qt.ItemDataRole.UserRole)
        if index is not None:
            self.current_group_index = index
            self.load_video()

    def format_time(self, ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def update_slider_position(self, position):
        self.timeline_slider.setValue(position)
        duration = self.media_player.duration()
        self.time_label.setText(f"{self.format_time(position)} / {self.format_time(duration)}")

    def update_slider_duration(self, duration):
        self.timeline_slider.setRange(0, duration)

    def set_position(self, position):
        self.media_player.setPosition(position)
        if self.current_angle == 'ALL':
            for p in self.multi_players:
                p.setPosition(position)

    def toggle_play(self):
        is_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        if is_playing:
            self.media_player.pause()
            if self.current_angle == 'ALL':
                for p in self.multi_players: p.pause()
            self.play_btn.setText("Play")
        else:
            self.media_player.play()
            if self.current_angle == 'ALL':
                for p in self.multi_players: p.play()
            self.play_btn.setText("Pause")

    def change_angle(self, new_angle):
        if self.current_angle == new_angle: return
            
        current_pos = self.media_player.position()
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        # Stop everything first
        self.media_player.stop()
        for p in self.multi_players: p.stop()
        
        self.current_angle = new_angle
        
        # Switch display
        if new_angle == 'ALL':
            self.display_stack.setCurrentIndex(1)
        else:
            self.display_stack.setCurrentIndex(0)
            
        loaded = self.load_video()
        if loaded:
            self.set_position(current_pos)
            if was_playing:
                self.media_player.play()
                if new_angle == 'ALL':
                    for p in self.multi_players: p.play()

    def load_video(self):
        if self.current_group_index >= len(self.video_groups) or self.current_group_index < 0:
            return False
            
        group = self.video_groups[self.current_group_index]
        
        if self.current_angle == 'ALL':
            # Load all 4 angles (S, B, L, R)
            paths = []
            for angle in self.multi_angles:
                path = group['angles'].get(angle)
                paths.append(path)
            
            # Use Front Wide (S) as the primary for duration/position tracking
            primary_path = group['angles'].get('S') or group['angles'].get('F')
            if primary_path:
                self.media_player.setSource(QUrl.fromLocalFile(primary_path))
            
            for i, p_path in enumerate(paths):
                if p_path:
                    self.multi_players[i].setSource(QUrl.fromLocalFile(p_path))
                    self.multi_players[i].play()
                else:
                    self.multi_players[i].stop()
            
            self.media_player.play()
            self.info_label.setText(f"Playing: All Views for {group['timestamp_str']}")
        else:
            # Single view
            video_path = self.get_best_angle_path(group)
            if not video_path:
                self.info_label.setText(f"Angle '{self.current_angle}' not found.")
                return False
            self.media_player.setSource(QUrl.fromLocalFile(video_path))
            self.media_player.play()
            self.info_label.setText(f"Playing: {os.path.basename(video_path)}")
            
        self.play_btn.setText("Pause")
        self.sync_playlist_selection()
        return True

    def get_best_angle_path(self, group):
        angles_dict = group['angles']
        if self.current_angle in angles_dict:
            return angles_dict[self.current_angle]
        if self.current_angle == 'F' and 'S' in angles_dict:
            return angles_dict['S']
        return None

    def sync_playlist_selection(self):
        for i in range(self.playlist_widget.topLevelItemCount()):
            parent = self.playlist_widget.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.data(0, Qt.ItemDataRole.UserRole) == self.current_group_index:
                    self.playlist_widget.setCurrentItem(child)
                    self.playlist_widget.scrollToItem(child)
                    return

    def play_next_group(self):
        if self.current_group_index < len(self.video_groups) - 1:
            self.current_group_index += 1
            self.load_video()

    def play_previous_group(self):
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self.load_video()

    def handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next_group()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = DVRPlayer()
    player.show()
    sys.exit(app.exec())
