import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QSlider, QLabel, QRadioButton, QButtonGroup, QMessageBox, QListWidget, QListWidgetItem, QFileDialog)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl

from dvr_scanner import DVRScanner

class DVRPlayer(QMainWindow):
    def __init__(self, directory_path=None):
        super().__init__()
        self.setWindowTitle("DVR Video Player")
        self.setGeometry(100, 100, 1024, 768)

        # Video Data
        self.video_groups = []
        self.current_group_index = 0
        self.current_angle = 'F'  # Default angle
        
        # Audio/Video Players
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)

        # Setup UI
        self.init_ui()
        
        # Connect signals
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

        # 1. Video Display
        left_layout.addWidget(self.video_widget, stretch=1)

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
        angles = [('F', "Front (F)"), ('B', "Back (B)"), ('L', "Left (L)"), ('R', "Right (R)"), ('S', "Surround/Side (S)")]
        
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
        self.playlist_widget = QListWidget()
        self.playlist_widget.setFixedWidth(250)
        self.playlist_widget.itemClicked.connect(self.jump_to_video)
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
        for i, group in enumerate(self.video_groups):
            dt = group['timestamp']
            date_str = dt.strftime("%Y-%m-%d")
            time_str = dt.strftime("%H:%M:%S")
            angles_str = ", ".join(sorted(group['angles'].keys()))
            
            # Add day header if a new day begins
            if date_str != current_date:
                current_date = date_str
                header_item = QListWidgetItem(f"📅 {date_str}")
                header_item.setBackground(Qt.GlobalColor.lightGray)
                header_item.setFlags(Qt.ItemFlag.NoItemFlags) # Make unselectable
                self.playlist_widget.addItem(header_item)
                
            # Add video clip item
            item = QListWidgetItem(f"🕒 {time_str} | [{angles_str}]")
            item.setData(Qt.ItemDataRole.UserRole, i) # Store the index
            self.playlist_widget.addItem(item)
            
    def jump_to_video(self, item):
        index = item.data(Qt.ItemDataRole.UserRole)
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

    def toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("Play")
        else:
            self.media_player.play()
            self.play_btn.setText("Pause")

    def change_angle(self, new_angle):
        if self.current_angle == new_angle:
            return
            
        # Optional: Save current playback position to resume seamlessly
        current_pos = self.media_player.position()
        was_playing = self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
        
        self.current_angle = new_angle
        loaded = self.load_video()
        
        if loaded:
            # We must wait until media is loaded before seeking, usually done asynchronously
            # For simplicity, we just set it here. Qt 6 usually handles basic seeks after setSource.
            self.media_player.setPosition(current_pos)
            if was_playing:
                self.media_player.play()

    def get_best_angle_path(self, group):
        angles_dict = group['angles']
        
        # Standard lookup
        if self.current_angle in angles_dict:
            return angles_dict[self.current_angle]
            
        # Fallback logic: If requesting F, but F is missing, try S.
        if self.current_angle == 'F' and 'S' in angles_dict:
            self.info_label.setText(f"[Fallback] Front missing. Showing 'S' for {group['timestamp_str']}")
            return angles_dict['S']
            
        return None

    def load_video(self):
        if self.current_group_index >= len(self.video_groups) or self.current_group_index < 0:
            return False
            
        group = self.video_groups[self.current_group_index]
        video_path = self.get_best_angle_path(group)
        
        if not video_path:
            self.info_label.setText(f"Angle '{self.current_angle}' not found for timestamp {group['timestamp_str']}. Waiting to jump to next.")
            # Depending on UX preference, we could auto-skip to the next group, but let's just stop here for now.
            return False
            
        self.media_player.setSource(QUrl.fromLocalFile(video_path))
        self.info_label.setText(f"Playing: {os.path.basename(video_path)}")
        self.media_player.play()
        self.play_btn.setText("Pause")
        
        # Highlight in playlist
        self.sync_playlist_selection()
        return True

    def sync_playlist_selection(self):
        # Find and select the item corresponding to current_group_index
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == self.current_group_index:
                self.playlist_widget.setCurrentItem(item)
                self.playlist_widget.scrollToItem(item)
                break

    def play_next_group(self):
        if self.current_group_index < len(self.video_groups) - 1:
            self.current_group_index += 1
            self.load_video()
        else:
            self.info_label.setText("Reached the end of the video list.")

    def play_previous_group(self):
        if self.current_group_index > 0:
            self.current_group_index -= 1
            self.load_video()

    def handle_media_status(self, status):
        # Auto-play next video upon completion
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            print(f"Video ended. Moving to next group: index {self.current_group_index + 1}")
            self.play_next_group()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    player = DVRPlayer()
    player.show()
    
    sys.exit(app.exec())
