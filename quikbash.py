from nicegui import ui, app
import os
import subprocess

HISTORY_FILE = "qb_history.txt"
STARTUP_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
MAX_HISTORY = 5

primary = "#ff7f11"
light = "#ffffff"
dark = "#262626"
success = "#00f48e"
warning = "#ff0f39"

# ======================================================================================================================
# STATE MANAGEMENT =====================================================================================================
# ======================================================================================================================

class Main:
    def __init__(self):
        # input
        self.folder = ""
        self.url = ""
        self.branch = "main"
        self.commit_msg = ""
        self.history = []
        self.status_text = "READY"
        # controls
        self.status_label = None
        self.spinner = None
        self.init_button = None
        self.commit_button = None
        self.push_button = None
        self.sync_button = None
        self.pull_button = None
        self.folder_input = None
        self.is_processing = False
        # history
        self.load_history()

    def load_history(self):
        """Load saved repository paths"""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    self.history = [line.strip() for line in f.readlines() if line.strip()]
            except Exception:
                self.history = []
        return self.history

    def save_history(self, path):
        """Save a new repository path"""
        if path in self.history:
            self.history.remove(path)
        self.history.insert(0, path)
        self.history = self.history[:MAX_HISTORY]

        with open(HISTORY_FILE, 'w') as f:
            f.write('\n'.join(self.history))

# Create a single state instance
app_state = Main()

# ======================================================================================================================
# VALIDATION ===========================================================================================================
# ======================================================================================================================

def validate_fields():
    """Enable/disable buttons based on input"""
    # For init button
    if app_state.init_button:
        if app_state.folder and app_state.folder.strip() and app_state.url and app_state.url.strip():
            app_state.init_button.enable()
        else:
            app_state.init_button.disable()

    # For repo commands
    can_operate = bool(app_state.folder and app_state.folder.strip() and app_state.commit_msg and app_state.commit_msg.strip())
    if app_state.commit_button:
        if can_operate:
            app_state.commit_button.enable()
        else:
            app_state.commit_button.disable()
    if app_state.push_button:
        if can_operate:
            app_state.push_button.enable()
        else:
            app_state.push_button.disable()
    if app_state.sync_button:
        if can_operate:
            app_state.sync_button.enable()
        else:
            app_state.sync_button.disable()

    # Pull only needs a folder
    if app_state.pull_button:
        if app_state.folder and app_state.folder.strip():
            app_state.pull_button.enable()
        else:
            app_state.pull_button.disable()

def validate_environment(folder_name, check_git=True):
    """Verify if folder exists and if a Git repo"""
    if not os.path.isdir(folder_name):
        ui.notify(f"❌ Path '{folder_name}' is not a valid directory.", type='negative')
        return False

    if check_git:
        result = subprocess.run(
            ['git', '-C', folder_name, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if result.returncode != 0:
            ui.notify("❌ Not a Git repository. Initialize it first.", type='negative')
            return False
    return True


def set_processing(active):
    """Show/hide spinner and disable/enable buttons"""
    app_state.is_processing = active

    if app_state.spinner:
        if active:
            app_state.spinner.classes(remove='hidden')
        else:
            app_state.spinner.classes('hidden')

    buttons = [
        app_state.init_button,
        app_state.commit_button,
        app_state.push_button,
        app_state.sync_button,
        app_state.pull_button
    ]

    for btn in buttons:
        if btn:
            if active:
                btn.disable()
            else:
                btn.enable()

    if not active:
        validate_fields()

    ui.update()

def set_status(text):
    """Update status text with color coding"""
    app_state.status_text = text
    if app_state.status_label:
        if "✅" in text or "SUCCESS" in text or "COMPLETED" in text:
            css_class = "status-success"
        elif "❌" in text or "ERROR" in text or "FAILED" in text:
            css_class = "status-warning"
        else:
            css_class = "status-neutral"

        app_state.status_label.classes(remove='status-neutral status-success status-warning')
        app_state.status_label.classes(css_class)
        app_state.status_label.set_text(text)
        ui.update()  # Force UI refresh

# ======================================================================================================================
# COMMANDS =============================================================================================================
# ======================================================================================================================

def init_new_repo():
    """Initialize a new Git repository and push to GitHub"""
    if app_state.is_processing:
        return

    folder = app_state.folder
    url = app_state.url

    if not folder or not url:
        ui.notify("⚠️ Please enter both folder path and GitHub URL!", type='warning')
        return

    set_processing(True)
    set_status("Processing...")

    try:
        is_git = subprocess.run(
            ['git', '-C', folder, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if is_git.returncode != 0:
            result = subprocess.run(
                ['git', '-C', folder, 'init'],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if result.returncode != 0:
                ui.notify(f"❌ Failed to init: {result.stderr}", type='negative')
                return

        result = subprocess.run(
            ['git', '-C', folder, 'add', '.'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if result.returncode != 0:
            ui.notify(f"❌ Failed to add: {result.stderr}", type='negative')
            return

        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if status.stdout.strip():
            result = subprocess.run(
                ['git', '-C', folder, 'commit', '-m', 'Initial commit'],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if result.returncode != 0:
                ui.notify(f"❌ Failed at commit: {result.stderr}", type='negative')
                return

        result = subprocess.run(
            ['git', '-C', folder, 'branch', '-M', 'main'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if result.returncode != 0:
            ui.notify(f"❌ Failed to set branch: {result.stderr}", type='negative')
            return

        remote_check = subprocess.run(
            ['git', '-C', folder, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if remote_check.returncode != 0:
            result = subprocess.run(
                ['git', '-C', folder, 'remote', 'add', 'origin', url],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if result.returncode != 0:
                ui.notify(f"❌ Failed to add remote: {result.stderr}", type='negative')
                return
        else:
            result = subprocess.run(
                ['git', '-C', folder, 'remote', 'set-url', 'origin', url],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if result.returncode != 0:
                ui.notify(f"❌ Failed to update remote: {result.stderr}", type='negative')
                return

        set_status("CHECKING REMOTE...")
        remote_check = subprocess.run(
            ['git', '-C', folder, 'ls-remote', 'origin', 'main'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if remote_check.stdout.strip():
            set_status("REMOTE HAS CONTENT - PULLING...")
            pull_result = subprocess.run(
                ['git', '-C', folder, 'pull', 'origin', 'main', '--allow-unrelated-histories'],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if pull_result.returncode != 0:
                ui.notify(f"⚠️ Pull had issues: {pull_result.stderr}", type='warning')

        set_status("PUSHING TO GITHUB...")
        result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', 'main'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if result.returncode != 0:
            ui.notify(f"❌ Failed at push: {result.stderr}", type='negative')
            return

        app_state.save_history(folder)
        set_status("✅ CONNECTED TO GITHUB")
        ui.notify("✅ Repository successfully initialized and pushed!", type='positive')

    except Exception as e:
        ui.notify(f"❌ Error: {str(e)}", type='negative')
        set_status(f"ERROR: {str(e)}")

    finally:
        set_processing(False)
        validate_fields()

def commit_changes():
    """Commit all changes"""
    if app_state.is_processing:
        return

    folder = app_state.folder
    msg = app_state.commit_msg

    if not msg:
        ui.notify("⚠️ Please enter a commit message!", type='warning')
        return

    if not validate_environment(folder):
        return

    set_processing(True)
    set_status("Checking for changes...")

    try:
        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if not status.stdout.strip():
            ui.notify("ℹ️ No changes detected. Git doesn't track empty folders.", type='info')
            set_status("NO CHANGES")
            return

        set_status("Adding and committing...")
        subprocess.run(['git', '-C', folder, 'add', '-A'], creationflags=STARTUP_FLAGS)
        result = subprocess.run(
            ['git', '-C', folder, 'commit', '-m', msg],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if result.returncode == 0:
            app_state.save_history(folder)
            set_status("✅ READY TO PUSH")
            ui.notify("✅ Commit successful!", type='positive')
        else:
            ui.notify(f"❌ Commit failed: {result.stderr}", type='negative')

    except Exception as e:
        ui.notify(f"❌ Error: {str(e)}", type='negative')
        set_status(f"ERROR: {str(e)}")

    finally:
        set_processing(False)
        validate_fields()

def push_to_github():
    """Push to GitHub"""
    if app_state.is_processing:
        return

    folder = app_state.folder
    branch = app_state.branch or "main"

    if not validate_environment(folder):
        return

    set_processing(True)
    set_status(f"Checking {branch}...")

    try:
        checkout_res = subprocess.run(
            ['git', '-C', folder, 'checkout', branch],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if checkout_res.returncode != 0:
            create_res = subprocess.run(
                ['git', '-C', folder, 'checkout', '-b', branch],
                capture_output=True, text=True, creationflags=STARTUP_FLAGS
            )
            if create_res.returncode != 0:
                ui.notify(f"❌ Could not switch to branch '{branch}': {checkout_res.stderr}", type='negative')
                return
            else:
                set_status(f"✅ CREATED & SWITCHED TO BRANCH: {branch}")
        else:
            set_status(f"✅ SWITCHED TO BRANCH: {branch}")

        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if status.stdout.strip():
            ui.notify("⚠️ Uncommitted changes detected! Commit them first.", type='warning')
            return

        check_push = subprocess.run(
            ['git', '-C', folder, 'log', f'origin/{branch}..{branch}', '--oneline'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )
        if not check_push.stdout.strip():
            ui.notify("ℹ️ Everything is already up to date!", type='info')
            set_status("EVERYTHING UP TO DATE")
            return

        set_status("PUSHING TO GITHUB...")
        result = subprocess.run(
            ['git', '-C', folder, 'push', '-u', 'origin', branch],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if result.returncode == 0:
            app_state.save_history(folder)
            set_status("✅ REPOSITORY UPDATED")
            ui.notify("✅ Push successful!", type='positive')
        else:
            if "rejected" in result.stderr.lower():
                ui.notify("⚠️ Remote has new commits! Pull first, then push.", type='warning')
                set_status("PUSH REJECTED - NEED PULL")
            else:
                ui.notify(f"❌ Push failed: {result.stderr}", type='negative')
                set_status("PUSH FAILED")

    except Exception as e:
        ui.notify(f"❌ Error: {str(e)}", type='negative')
        set_status(f"ERROR: {str(e)}")

    finally:
        set_processing(False)
        validate_fields()

def pull_from_github():
    """Pull latest changes from GitHub"""
    if app_state.is_processing:
        return

    folder = app_state.folder
    branch = app_state.branch or "main"

    if not folder:
        ui.notify("⚠️ Please enter a folder path!", type='warning')
        return

    if not validate_environment(folder):
        return

    set_processing(True)
    set_status(f"PULLING FROM {branch}...")

    try:
        result = subprocess.run(
            ['git', '-C', folder, 'pull', 'origin', branch],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if result.returncode == 0:
            app_state.save_history(folder)
            set_status("✅ PULL SUCCESSFUL")
            ui.notify(f"✅ Successfully pulled from '{branch}'!", type='positive')
        else:
            if "no such remote" in result.stderr.lower():
                ui.notify("⚠️ No remote 'origin' found. Initialize the repo first.", type='warning')
                set_status("NO REMOTE FOUND")
            else:
                ui.notify(f"❌ Pull failed: {result.stderr}", type='negative')
                set_status("PULL FAILED")

    except Exception as e:
        ui.notify(f"❌ Error: {str(e)}", type='negative')
        set_status(f"ERROR: {str(e)}")

    finally:
        set_processing(False)
        validate_fields()

def do_all():
    """Commit and push in one action"""
    if app_state.is_processing:
        return

    folder = app_state.folder
    msg = app_state.commit_msg

    if not folder or not msg:
        ui.notify("⚠️ Please enter both folder path and commit message!", type='warning')
        return

    set_status("Checking for unpushed commits...")

    try:
        branch = app_state.branch or "main"

        check_push = subprocess.run(
            ['git', '-C', folder, 'log', f'origin/{branch}..{branch}', '--oneline'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        has_unpushed_commits = bool(check_push.stdout.strip())

        if has_unpushed_commits:
            set_status("Found unpushed commits - pushing...")
            push_to_github()
            return

        status = subprocess.run(
            ['git', '-C', folder, 'status', '--porcelain'],
            capture_output=True, text=True, creationflags=STARTUP_FLAGS
        )

        if status.stdout.strip():
            commit_changes()
            if "READY TO PUSH" in app_state.status_text:
                set_status("Pushing to GitHub...")
                push_to_github()
        else:
            ui.notify("ℹ️ No changes to commit and nothing to push.", type='info')
            set_status("EVERYTHING IS UP TO DATE")

    except Exception as e:
        ui.notify(f"❌ Error: {str(e)}", type='negative')
        set_status(f"ERROR: {str(e)}")
        set_processing(False)
        validate_fields()

def set_folder(path):
    """Set folder from history chip"""
    if path and path.strip():
        app_state.folder = path
        if app_state.folder_input:
            app_state.folder_input.value = path
        app_state.save_history(path)
        validate_fields()

def update_folder(path):
    """Update folder and trigger validation"""
    # Check if path is different from current folder
    if path != app_state.folder:
        app_state.folder = path
        if path and path.strip():
            app_state.save_history(path)
        validate_fields()


# ======================================================================================================================
# INTERFACE ============================================================================================================
# ======================================================================================================================

@ui.page('/')
def main_page():
    ui.page_title("QuikBash")
    ui.add_head_html(f'''
        <style>
            body {{ background: {light}; color: {dark}; }}
            .q-field__label {{ color: {dark} !important; font-weight: bold; }}
            .q-field__control {{ border-color: {dark} !important; }}

            .nicegui-button,
            .q-btn,
            button.nicegui-button,
            .q-btn.nicegui-button {{
                border-radius: 4px !important;
                transition: all 0.2s ease !important;
                background: {dark} !important;
                color: {light} !important;
                border: none !important;
                opacity: 1 !important;
            }}

            .nicegui-button:hover:not(:disabled),
            .q-btn:hover:not(:disabled),
            button.nicegui-button:hover:not(:disabled),
            .q-btn.nicegui-button:hover:not(:disabled) {{
                background: {primary} !important;
                color: {light} !important;
            }}

            .nicegui-button:active:not(:disabled),
            .q-btn:active:not(:disabled),
            button.nicegui-button:active:not(:disabled),
            .q-btn.nicegui-button:active:not(:disabled) {{
                background: {light} !important;
                color: {dark} !important;
                border: 1px solid {dark} !important;
            }}

            .nicegui-button:disabled,
            .q-btn:disabled,
            button.nicegui-button:disabled,
            .q-btn.nicegui-button:disabled {{
                opacity: 0.4 !important;
                background: {dark} !important;
                color: {light} !important;
                cursor: not-allowed !important;
            }}

            .status-bar {{
                background: {light};
                padding: 12px;
                border-top: 2px solid {dark};
                font-family: monospace;
                font-weight: bold;
                margin: 0;
            }}
            .status-neutral {{ color: {dark}; }}
            .status-success {{ color: {success}; }}
            .status-warning {{ color: {warning}; }}

            .main-container {{ max-width: 800px; margin: 0 auto; }}
            .gap-none {{ gap: 0 !important; }}
            .hidden {{ display: none !important; }}
        </style>
    ''')

    # Header
    with ui.column().classes('w-full main-container'):
        with ui.row().classes('w-full items-center justify-between p-4'):
            with ui.row().classes('items-center gap-3'):
                ui.label('QuikBash').classes('text-h4 font-bold').style(f'color: {dark}')
                ui.label('v3.0.gamma').classes('text-caption').style(f'color: {dark}')

    # Content
    with ui.column().classes('w-full p-4 main-container gap-none'):
        # Folder Path
        with ui.card().classes('w-full mb-4'):
            with ui.column().classes('w-full gap-2'):
                app_state.folder_input = ui.input(
                    label='Folder Path',
                ).props('outlined').classes('w-full').bind_value_to(app_state, 'folder')
                app_state.folder_input.on('change', lambda: update_folder(app_state.folder_input.value))
                app_state.folder_input.on('keyup', lambda: validate_fields())

                # History chips
                if app_state.history:
                    with ui.row().classes('gap-1 flex-wrap'):
                        ui.label('Recent:').classes('text-caption').style(f'color: {dark}; opacity: 0.6')
                        for path in app_state.history[:3]:
                            chip = ui.chip(
                                os.path.basename(path) if os.path.basename(path) else path[:20],
                                color=dark,
                                text_color=dark
                            ).props('outline dense clickable')
                            chip.on('click', lambda p=path: set_folder(p))

        # Tabs
        with ui.tabs().classes('w-full') as tabs:
            new_repo_tab = ui.tab('New Repository', icon='add_box')
            update_tab = ui.tab('Update Repository', icon='sync')

        with ui.tab_panels(tabs, value=new_repo_tab).classes('w-full'):
            # Tab 1
            with ui.tab_panel(new_repo_tab):
                with ui.card().classes('w-full'):
                    with ui.column().classes('w-full gap-4 p-4'):
                        url_input = ui.input('Remote URL:') \
                            .props('outlined') \
                            .classes('w-full') \
                            .bind_value_to(app_state, 'url')
                        url_input.on('change', validate_fields)
                        url_input.on('keyup', lambda: validate_fields())

                        app_state.init_button = ui.button(
                            'Initialize & Push',
                            on_click=init_new_repo
                        ).props('color=dark text-white').classes('w-full')
                        app_state.init_button.disable()

            # Tab 2
            with ui.tab_panel(update_tab):
                with ui.card().classes('w-full'):
                    with ui.column().classes('w-full gap-4 p-4'):
                        branch_input = ui.input('Branch:') \
                            .props('outlined') \
                            .classes('w-full') \
                            .bind_value_to(app_state, 'branch') \
                            .props('placeholder=main')

                        msg_input = ui.input('Commit Message:') \
                            .props('outlined') \
                            .classes('w-full') \
                            .bind_value_to(app_state, 'commit_msg')
                        msg_input.on('change', validate_fields)
                        msg_input.on('keyup', lambda: validate_fields())

                        with ui.row().classes('w-full gap-2'):
                            app_state.commit_button = ui.button(
                                'Commit',
                                on_click=commit_changes
                            ).props('color=dark text-white').classes('flex-1')
                            app_state.commit_button.disable()

                            app_state.push_button = ui.button(
                                'Push',
                                on_click=push_to_github
                            ).props('color=dark text-white').classes('flex-1')
                            app_state.push_button.disable()

                        with ui.row().classes('w-full gap-2'):
                            app_state.sync_button = ui.button(
                                'Commit & Push',
                                on_click=do_all
                            ).props('color=dark text-white').classes('flex-1')
                            app_state.sync_button.disable()

                            app_state.pull_button = ui.button(
                                'Pull',
                                on_click=pull_from_github
                            ).props('color=dark text-white').classes('flex-1')
                            app_state.pull_button.disable()

        # Status bar
        with ui.column().classes('w-full status-bar'):
            with ui.row().classes('w-full items-center justify-center gap-3'):
                app_state.spinner = ui.spinner('dots', size='24px') \
                    .props('color=orange') \
                    .classes('hidden')
                app_state.status_label = ui.label('READY').classes('text-center status-neutral')

    validate_fields()
    return

# ======================================================================================================================
# START ================================================================================================================
# ======================================================================================================================

if __name__ in {"__main__", "__mp_main__"}:
    print("🟠 Starting QuikBash in browser...")
    print("⚪ Server will be available at: http://127.0.0.1:8080")
    ui.run(
        host='127.0.0.1',
        port=8080,
        title='QuikBash'
    )