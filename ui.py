import os
import json
import logic
import threading
import subprocess
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit,
    QComboBox, QProgressBar, QMessageBox, QCheckBox
)


class IGReleaseApp(QWidget):
    """Modern GUI for IG Release Processing using PyQt6"""

    def __init__(self):
        super().__init__()

        self.config = logic.load_config(logic.CONFIG_FILE)
        self.ig_source = logic.load_config(logic.IG_SOURCE_FILE).get("ig_repo", "")

        self.init_ui()

    def init_ui(self):
        """Set up the modern PyQt6 UI."""
        self.setWindowTitle("FHIR IG Release Processor")
        self.setGeometry(200, 200, 900, 700)

        layout = QVBoxLayout()

        # **Source IG Repository**
        layout.addWidget(QLabel("🔗 Source IG Repository"))
        self.ig_repo_entry = QLineEdit(self.ig_source)
        layout.addWidget(self.ig_repo_entry)

        self.fetch_ig_button = QPushButton("🚀 Fetch IG Repo")
        self.fetch_ig_button.clicked.connect(self.fetch_ig_repo)
        layout.addWidget(self.fetch_ig_button)

        # **Branch Selector**
        layout.addWidget(QLabel("📂 Select Branch"))
        self.branch_dropdown = QComboBox()
        layout.addWidget(self.branch_dropdown)
        self.branch_dropdown.currentIndexChanged.connect(self.on_branch_selected)

        # **Repositories**
        layout.addWidget(QLabel("📁 Other Repositories"))

        self.repo_fields = {}
        for name, value in {
            "Work Folder": self.config.get("work_folder", ""),
            "History Template": self.config.get("history_template_repo", ""),
            "IG Registry": self.config.get("ig_registry_repo", ""),
            "Current Web Content": self.config.get("current_web_content_repo", ""),
        }.items():
            layout.addWidget(QLabel(f"📌 {name}"))
            entry = QLineEdit(value)
            layout.addWidget(entry)
            self.repo_fields[name] = entry

        self.fetch_all_button = QPushButton("📥 Fetch All Repos")
        self.fetch_all_button.clicked.connect(self.fetch_all_repos)
        layout.addWidget(self.fetch_all_button)

        # **Publication Request JSON Editor**
        layout.addWidget(QLabel("📝 Publication Request"))
        self.json_editor = QTextEdit()
        layout.addWidget(self.json_editor)

        self.validate_button = QPushButton("✅ Validate JSON")
        self.validate_button.clicked.connect(self.validate_json)
        layout.addWidget(self.validate_button)

        # **Build Options**
        self.clean_folders_checkbox = QCheckBox("🗑️ Clean folders before build")
        layout.addWidget(self.clean_folders_checkbox)

        self.build_button = QPushButton("🏗️ Build IG")
        self.build_button.clicked.connect(self.build_ig)
        layout.addWidget(self.build_button)

        # Deploy Buttons (Initially Hidden)
        self.deploy_built_button = QPushButton("🚀 Deploy Built IG")
        self.deploy_built_button.clicked.connect(self.deploy_built)
        self.deploy_built_button.setVisible(False)
        layout.addWidget(self.deploy_built_button)

        self.deploy_prebuilt_button = QPushButton("🚀 Deploy Pre-Built IG")
        self.deploy_prebuilt_button.clicked.connect(self.deploy_prebuilt)
        self.deploy_prebuilt_button.setVisible(False)  # Initially hidden
        layout.addWidget(self.deploy_prebuilt_button)


        # **Console Log (Scrollable)**
        layout.addWidget(QLabel("📜 Console Output"))
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        layout.addWidget(self.console_output)

        # **Progress Bar**
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # **Status Message**
        self.status_label = QLabel("Status: Ready ✅")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def log(self, message):
        """Append message to the console log."""
        self.console_output.append(message)
        print(message)  # Also print in the terminal

    def build_ig(self):
        """Main Build Process"""
        work_folder = self.repo_fields["Work Folder"].text()
        ig_source = self.ig_repo_entry.text()
        clean_folders = self.clean_folders_checkbox.isChecked()

        self.log("📥 Fetching repositories...")
        self.progress_bar.setValue(10)
        self.fetch_all_repos()

        # Check if `gh-pages` has `sitepreview`
        if logic.gh_pages_has_sitepreview(ig_source):
            self.log("🌍 Downloading pre-built IG from gh-pages...")
            logic.download_gh_pages(ig_source, work_folder)
            self.deploy_prebuilt_button.setVisible(True)
            self.progress_bar.setValue(100)
            return

        # Download publisher.jar
        self.log("📥 Downloading publisher.jar...")
        logic.download_publisher_jar()
        self.progress_bar.setValue(20)

        # Validate JSON
        self.log("✅ Validating JSON...")
        if not self.validate_json():
            self.log("❌ JSON validation failed!")
            return

        self.progress_bar.setValue(30)

        # Run Publisher JAR Commands
        self.log("🚀 Running IG Publisher...")
        success = self.run_publisher(ig_source, work_folder)

        if success:
            self.deploy_built_button.setVisible(True)
            self.progress_bar.setValue(100)
            self.log("🎉 Build Complete!")
        else:
            self.log("❌ Build Failed!")

    def run_publisher(self, source, work_folder):
        """Run the IG Publisher commands."""
        publisher_path = "./publisher.jar"

        cmd1 = f"java -Xmx4g -jar {publisher_path} publisher -ig {source}"
        cmd2 = f"java -Xmx4g -jar {publisher_path} -go-publish -source {source} " \
               f"-web {work_folder}/Current_Web_Content -temp {work_folder}/Work_Folder " \
               f"-registry {work_folder}/IG_Registry/fhir-ig-list.json -history {work_folder}/History_Template " \
               f"-templates {work_folder}/Current_Web_Content/templates"

        for cmd in [cmd1, cmd2]:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in process.stdout:
                self.log(line.decode().strip())  # Show output in UI
            process.wait()
            if process.returncode != 0:
                return False
        return True

    def deploy_built(self):
        """Deploy the built IG to the server."""
        self.log("🚀 Deploying Built IG...")
        logic.deploy_built(self.repo_fields["Current Web Content"].text())

    def deploy_prebuilt(self):
        """Deploy the Pre-Built IG."""
        self.log("🚀 Deploying Pre-Built IG...")
        logic.deploy_prebuilt(
            self.repo_fields["Current Web Content"].text(),
            self.repo_fields["Work Folder"].text()
        )

    def fetch_ig_repo(self):
        """Fetch the IG repository, update branches, and check for pre-built IG."""
        repo_url = self.ig_repo_entry.text()
        work_folder = self.repo_fields["Work Folder"].text()
        dest_folder = os.path.join(work_folder, "New_IG_Source")

        self.log(f"📥 Fetching IG Repo from {repo_url}...")

        success = logic.fetch_or_update_repo(repo_url, dest_folder)

        if success:
            branches = logic.get_git_branches(repo_url)
            self.branch_dropdown.clear()
            self.branch_dropdown.addItems(branches)
            if branches:
                self.branch_dropdown.setCurrentIndex(0)
            self.status_label.setText("✅ IG Repo Fetched Successfully")
            self.log("✅ IG Repository Fetched Successfully.")

            # 🔹 Check if sitepreview exists in `gh-pages`
            if logic.gh_pages_has_sitepreview(repo_url):
                self.log("🌍 Pre-built IG found in gh-pages branch. Enabling 'Deploy Pre-Built'.")
                self.deploy_prebuilt_button.setVisible(True)  # Show Deploy Pre-Built button

        else:
            self.status_label.setText("❌ Failed to fetch IG Repo")
            self.log("❌ Failed to fetch IG Repository!")


    def on_branch_selected(self):
        """Switch the IG repository to the selected branch and load publication-request.json."""
        selected_branch = self.branch_dropdown.currentText()
        repo_path = os.path.join(self.repo_fields["Work Folder"].text(), "New_IG_Source")

        self.log(f"📂 Switching to branch: {selected_branch}...")

        success = logic.switch_to_branch(repo_path, selected_branch)
        if success:
            json_data = logic.load_publication_request(repo_path)
            self.json_editor.setText(json_data)
            self.status_label.setText(f"✅ Switched to Branch: {selected_branch}")
            self.log(f"✅ Switched to Branch: {selected_branch}")
        else:
            self.status_label.setText(f"❌ Failed to switch to {selected_branch}")
            self.log(f"❌ Failed to switch to branch: {selected_branch}")



    def fetch_all_repos(self):
        """Fetch all repositories with real-time UI updates."""

        def fetch_repos():
            total_repos = len(self.repo_fields) - 1  # Excluding "Work Folder"
            completed = 0

            for name, entry in self.repo_fields.items():
                if name == "Work Folder":
                    continue

                repo_url = entry.text()
                work_folder = self.repo_fields["Work Folder"].text()
                dest_folder = os.path.join(work_folder, name.replace(" ", "_"))

                self.log(f"📥 Fetching {name} from {repo_url}...")

                success = logic.fetch_or_update_repo(repo_url, dest_folder)

                if success:
                    self.log(f"✅ {name} fetched successfully.")
                else:
                    self.log(f"❌ Failed to fetch {name}")

                completed += 1
                self.progress_bar.setValue(int((completed / total_repos) * 100))

            self.status_label.setText("✅ All repositories fetched.")

        # Run in a separate thread to avoid freezing the UI
        threading.Thread(target=fetch_repos, daemon=True).start()


    def validate_json(self):
        """Validate the JSON content in the publication request editor."""
        try:
            json_content = self.json_editor.toPlainText().strip()
            json.loads(json_content)  # Try parsing the JSON
            self.status_label.setText("✅ JSON is valid!")
            self.log("✅ JSON is valid!")
            QMessageBox.information(self, "Success", "✅ Valid JSON!")
            return True
        except json.JSONDecodeError as e:
            self.status_label.setText("❌ Invalid JSON!")
            self.log(f"❌ Invalid JSON: {e}")
            QMessageBox.critical(self, "Error", f"❌ Invalid JSON: {e}")
            return False        